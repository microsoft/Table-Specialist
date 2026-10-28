"""Execute model-produced code in disposable Linux containers, never on the host.

Only the selected code file and data.csv enter the container. No host paths,
environment variables, sockets, or credentials are mounted/passed through.
See sandbox/README.md for the trust boundary and required image configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile
import threading
import uuid


MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_LOG_BYTES = 2 * 1024 * 1024
CONTROL_TIMEOUT = 15
IMAGE_PATTERN = re.compile(r"(?:sha256:|[a-z0-9][a-z0-9._:/-]*@sha256:)[0-9a-f]{64}\Z")
RUNTIMES = {
    "python": ("TABLE_SPECIALIST_PYTHON_IMAGE", "query.py", 10),
    "r": ("TABLE_SPECIALIST_R_IMAGE", "query.R", 15),
    "scala": ("TABLE_SPECIALIST_SPARK_IMAGE", "query.scala", 120),
}


class SandboxError(RuntimeError):
    """The sandbox is unavailable or its configuration/inputs are invalid."""


class SandboxExecutionError(SandboxError):
    """Untrusted execution timed out or produced invalid/oversized artifacts."""


@dataclass(frozen=True)
class ExecutionResult:
    returncode: int
    stdout: str
    stderr: str


def _docker(args, *, timeout=CONTROL_TIMEOUT, max_stdout=MAX_LOG_BYTES):
    """Bound both CLI output streams and time, including artifact downloads."""
    executable = shutil.which("docker")
    if executable is None:
        raise SandboxError("Docker is required; host execution is disabled. See sandbox/README.md.")
    try:
        process = subprocess.Popen(
            [executable, *args], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise SandboxError("Cannot start the Docker CLI") from exc

    buffers = [bytearray(), bytearray()]
    errors = []

    def read_stream(stream, buffer, limit):
        try:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    break
                if len(buffer) + len(chunk) > limit:
                    errors.append(SandboxExecutionError("Sandbox output exceeded its size limit"))
                    process.kill()
                    break
                buffer.extend(chunk)
        except OSError as exc:
            errors.append(SandboxError("Cannot read Docker output: " + str(exc)))
            process.kill()
        finally:
            stream.close()

    readers = [
        threading.Thread(target=read_stream, args=(process.stdout, buffers[0], max_stdout), daemon=True),
        threading.Thread(target=read_stream, args=(process.stderr, buffers[1], MAX_LOG_BYTES), daemon=True),
    ]
    for reader in readers:
        reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        process.wait()
    except BaseException:
        process.kill()
        process.wait()
        raise
    finally:
        for reader in readers:
            reader.join(timeout=CONTROL_TIMEOUT)
    if timed_out:
        raise SandboxExecutionError("Sandbox operation timed out")
    if any(reader.is_alive() for reader in readers):
        raise SandboxError("Docker output stream did not close")
    if errors:
        raise errors[0]
    return process.returncode, bytes(buffers[0]), bytes(buffers[1])


def _checked(args, **kwargs):
    rc, out, err = _docker(args, **kwargs)
    if rc:
        raise SandboxError("Docker operation failed: " + err.decode("utf-8", errors="replace"))
    return out


def ensure_sandbox(runtime):
    """Fail closed unless a local image and Linux/seccomp daemon are available."""
    if runtime not in RUNTIMES:
        raise SandboxError("Unsupported runtime: " + str(runtime))
    variable = RUNTIMES[runtime][0]
    image = os.environ.get(variable, "")
    if not IMAGE_PATTERN.fullmatch(image):
        raise SandboxError(f"Set {variable} to a reviewed immutable image ID/digest; see sandbox/README.md.")
    try:
        info = json.loads(_checked(["info", "--format", "{{json .}}",]))
        options = info.get("SecurityOptions") or []
        if info.get("OSType") != "linux" or not any(
                "name=seccomp" in opt and "unconfined" not in opt for opt in options):
            raise SandboxError("A Linux Docker daemon with seccomp enabled is required")
        host = os.environ.get("DOCKER_HOST") or json.loads(_checked(
            ["context", "inspect", "--format", "{{json .Endpoints.docker.Host}}"]
        ))
        if not isinstance(host, str) or not host.startswith(("unix:///", "npipe:////./pipe/")):
            raise SandboxError("A local Unix-socket/named-pipe Docker context is required; remote daemons are disabled")
        # Inspect locally, never pull an image implicitly at execution time.
        images = json.loads(_checked(["image", "inspect", image]))
        if len(images) != 1 or images[0].get("Os") != "linux":
            raise SandboxError("The configured sandbox image must be a local Linux image")
        if images[0].get("Config", {}).get("Volumes"):
            raise SandboxError("Sandbox images must not declare additional writable volumes")
    except (ValueError, TypeError, KeyError) as exc:
        raise SandboxError("Invalid Docker configuration response") from exc
    return image


def _input_file(workspace, name):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name in {".", ".."}:
        raise SandboxError("Input must be a simple filename")
    path = workspace / name
    if path.is_symlink() or not path.is_file() or path.resolve().parent != workspace:
        raise SandboxError("Input must be a regular file inside the case workspace: " + name)
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise SandboxError("Sandbox input is too large: " + name)
    return path


def _read_csv_artifacts(archive, output_name, *, directory):
    """Read a bounded tar as data. Never extract container-controlled paths."""
    artifacts = {}
    total = 0
    seen = set()
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
            for index, member in enumerate(tar):
                if index >= 1024:
                    raise SandboxExecutionError("Too many sandbox output entries")
                path = PurePosixPath(member.name)
                if (path.is_absolute() or ".." in path.parts or "\\" in member.name
                        or not path.parts or path.parts[0] != output_name):
                    raise SandboxExecutionError("Invalid sandbox output path")
                if str(path) in seen:
                    raise SandboxExecutionError("Duplicate sandbox output path")
                seen.add(str(path))
                if member.isdir() and directory:
                    continue
                if not member.isfile() or member.issparse():
                    raise SandboxExecutionError("Sandbox outputs must be regular files, not links/devices")
                if member.size < 0 or member.size > MAX_OUTPUT_BYTES:
                    raise SandboxExecutionError("Sandbox output file is too large")
                total += member.size
                if total > MAX_OUTPUT_BYTES:
                    raise SandboxExecutionError("Sandbox outputs exceed their size limit")
                if directory:
                    # Spark's CRC/_SUCCESS files are not imported; only direct CSV parts.
                    if len(path.parts) != 2 or not re.fullmatch(r"part-[A-Za-z0-9_.-]+\.csv", path.name):
                        continue
                    name = path.name
                else:
                    if len(path.parts) != 1:
                        raise SandboxExecutionError("Unexpected sandbox output file")
                    name = output_name
                source = tar.extractfile(member)
                if source is None:
                    raise SandboxExecutionError("Missing sandbox output data")
                data = source.read(MAX_OUTPUT_BYTES + 1)
                if len(data) != member.size:
                    raise SandboxExecutionError("Invalid sandbox output size")
                artifacts[name] = data
    except (tarfile.TarError, OSError) as exc:
        raise SandboxExecutionError("Invalid sandbox output archive") from exc
    if not artifacts or (directory and len(artifacts) != 1):
        raise SandboxExecutionError("Expected one output CSV from the sandbox")
    return artifacts


def run_generated_code(work_dir, runtime, code_file=None, *, timeout=None, num_cpu=1):
    """Run one code/table pair; return bounded logs and import only its CSV.

    This deliberately does not support host execution, arbitrary commands,
    additional file mounts, shared batches, or passing the host environment.
    """
    image = ensure_sandbox(runtime)
    _, default_code, default_timeout = RUNTIMES[runtime]
    timeout = default_timeout if timeout is None else timeout
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 600:
        raise SandboxError("Execution timeout must be between 0 and 600 seconds")
    if isinstance(num_cpu, bool) or not isinstance(num_cpu, int) or not 1 <= num_cpu <= 4:
        raise SandboxError("Sandbox CPU count must be between 1 and 4")
    workspace = Path(work_dir).resolve(strict=True)
    if not workspace.is_dir():
        raise SandboxError("Case workspace is not a directory")
    source = _input_file(workspace, default_code if code_file is None else code_file)
    table = _input_file(workspace, "data.csv")
    if source.stat().st_size + table.stat().st_size > MAX_INPUT_BYTES:
        raise SandboxError("Sandbox inputs exceed their size limit")
    output_name = "result_scala" if runtime == "scala" else "result.csv"
    destination = workspace / output_name
    # No stale result reuse and no writing through pre-existing host symlinks.
    if destination.exists() or destination.is_symlink():
        raise SandboxError("Remove or archive the previous result before rerunning: " + str(destination))

    if runtime == "python":
        command = ["python3", "-I", default_code]
    elif runtime == "r":
        command = ["Rscript", "--vanilla", default_code]
    else:
        command = ["/opt/spark/bin/spark-shell", "--conf", "spark.ui.enabled=false",
                   "--conf", "spark.driver.bindAddress=127.0.0.1",
                   "--master", f"local[{num_cpu}]", "--driver-memory", "1g"]

    container = "table-specialist-" + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix="table-specialist-input-") as staging:
        # Docker cp preserves directory modes. Keep the outer host directory
        # private, but make the copied inner directory traversable by the
        # container's non-root runtime (a TemporaryDirectory is normally 0700).
        stage = Path(staging) / "input"
        stage.mkdir()
        stage.chmod(0o755)
        # The staging directory is copied, not mounted. Never copy the whole repo/workspace.
        shutil.copyfile(table, stage / "data.csv")
        code = source.read_text(encoding="utf-8")
        if runtime == "scala":
            code = code.replace('.write.option("header", "true").csv("result")',
                                '.write.option("header", "true").csv("result_scala")')
        (stage / default_code).write_text(code, encoding="utf-8", newline="\n")
        (stage / "stdin.txt").write_text(
            ":load /tmp/job/query.scala\n:quit\n" if runtime == "scala" else "", encoding="utf-8", newline="\n")
        for file in stage.iterdir():
            file.chmod(0o644)
        # A single fixed-size-limited export file survives tmpfs unmount on stop.
        # The volume directory and all other files remain root-owned/read-only
        # to the runtime. It cannot create/replace entries in that directory.
        export_file = stage / "export.tar"
        export_file.write_bytes(b"")
        export_file.chmod(0o666)
        # All shell syntax is trusted/constant. Code is never interpolated into a command.
        # Export while the tmpfs is still mounted, then let the container stop.
        # The export is untrusted data and is validated twice below.
        launcher = (
            'set -eu; if [ -w /input ]; then echo "Unsafe input volume permissions" >&2; exit 1; fi; '
            'mkdir /tmp/job; cp /input/data.csv /input/' + default_code + ' /tmp/job/; '
            'cd /tmp/job; "$@" < /input/stdin.txt; tar -cf /input/export.tar -- ' + output_name
        )
        try:
            _checked([
                "create", "--pull=never", "--name", container,
                "--network", "none", "--read-only", "--cap-drop", "ALL",
                "--mount", "type=volume,destination=/input,volume-nocopy",
                "--security-opt", "no-new-privileges=true", "--user", "65534:65534",
                "--pids-limit", "256", "--memory", "3g", "--memory-swap", "3g",
                "--cpus", str(num_cpu), "--ulimit", "nofile=256:256",
                "--ulimit", f"fsize={MAX_OUTPUT_BYTES}:{MAX_OUTPUT_BYTES}",
                "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m,mode=1777",
                "--env", "HOME=/tmp", "--env", "SPARK_LOCAL_IP=127.0.0.1",
                "--env", "OMP_NUM_THREADS=1", "--workdir", "/tmp",
                "--log-driver", "local", "--log-opt", "max-size=1m",
                "--log-opt", "max-file=1", "--log-opt", "compress=false",
                "--entrypoint", "/bin/sh", image, "-c", launcher, "sandbox", *command,
            ])
            _checked(["cp", str(stage) + os.sep + ".", container + ":/input"])
            _checked(["start", container])
            wait = _checked(["wait", container], timeout=timeout)
            try:
                returncode = int(wait.decode().strip())
            except ValueError as exc:
                raise SandboxError("Invalid container exit status") from exc
            _, stdout, stderr = _docker(["logs", "--tail", "1000", container])
            if returncode == 0:
                rc, archive, err = _docker(
                    ["cp", f"{container}:/input/export.tar", "-"],
                    max_stdout=MAX_OUTPUT_BYTES + 2 * 1024 * 1024,
                )
                if rc:
                    raise SandboxExecutionError("Sandbox did not produce the expected CSV: " + err.decode(errors="replace"))
                export = _read_csv_artifacts(archive, "export.tar", directory=False)["export.tar"]
                artifacts = _read_csv_artifacts(export, output_name, directory=runtime == "scala")
                # Validate the entire archive before creating any host output.
                if runtime == "scala":
                    destination.mkdir()
                    for name, data in artifacts.items():
                        with (destination / name).open("xb") as file:
                            file.write(data)
                else:
                    with destination.open("xb") as file:
                        file.write(artifacts[output_name])
            return ExecutionResult(returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace"))
        finally:
            # Removing a running container terminates its entire process tree, not just the CLI.
            rc, _, err = _docker(["rm", "--force", "--volumes", container])
            if rc and b"No such container" not in err:
                raise SandboxError("Container cleanup failed; operator intervention required: " + container)
