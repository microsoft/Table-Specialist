import ast
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import table_specialist_sandbox as sandbox


ROOT = Path(__file__).resolve().parents[1]
IMAGE = "sha256:" + "a" * 64


def archive_of(entries):
    """Entries are (name, bytes) or (name, tar type, link target)."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as tar:
        for entry in entries:
            item = tarfile.TarInfo(entry[0])
            if len(entry) == 2:
                item.size = len(entry[1])
                tar.addfile(item, io.BytesIO(entry[1]))
            else:
                item.type, item.linkname = entry[1:]
                tar.addfile(item)
    return output.getvalue()


class FakeDocker:
    def __init__(self, output=None, exit_code=0, timeout=False, fail_at=None):
        self.output = output if output is not None else archive_of([("result.csv", b"answer\n3\n")])
        self.exit_code = exit_code
        self.timeout = timeout
        self.fail_at = fail_at
        self.calls = []
        self.copied_files = {}
        self.staging_directory = None

    def __call__(self, args, **kwargs):
        self.calls.append((args, kwargs))
        if args[0] == self.fail_at:
            return 1, b"", b"configured failure"
        if args[0] == "info":
            return 0, json.dumps({"OSType": "linux", "SecurityOptions": ["name=seccomp,profile=builtin"]}).encode(), b""
        if args[:2] == ["image", "inspect"]:
            return 0, json.dumps([{"Os": "linux", "Config": {}}]).encode(), b""
        if args[0] == "context":
            return 0, b'"unix:///var/run/docker.sock"', b""
        if args[0] == "wait":
            if self.timeout:
                raise sandbox.SandboxExecutionError("Sandbox operation timed out")
            return 0, str(self.exit_code).encode(), b""
        if args[0] == "cp" and args[-1] != "-":
            directory = Path(args[1])
            self.staging_directory = directory
            self.copied_files = {p.name: p.read_bytes() for p in directory.iterdir()}
        if args[0] == "cp" and args[-1] == "-":
            return 0, archive_of([("export.tar", self.output)]), b""
        if args[0] == "logs":
            return 0, b"runtime log", b"runtime stderr"
        return 0, b"", b""


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.work = Path(self.directory.name)
        (self.work / "data.csv").write_text("value\n1\n2\n", encoding="utf-8")
        (self.work / "query.py").write_text("# untrusted code; unit tests never execute it\n", encoding="utf-8")

    @contextmanager
    def configured(self, fake):
        with patch.dict(os.environ, {var: IMAGE for var, _, _ in sandbox.RUNTIMES.values()}), patch.object(sandbox, "_docker", fake):
            yield

    def test_no_image_configuration_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sandbox, "_docker") as docker:
            with self.assertRaises(sandbox.SandboxError):
                sandbox.run_generated_code(self.work, "python")
            docker.assert_not_called()
        self.assertFalse((self.work / "result.csv").exists())

    def test_no_docker_fails_closed(self):
        with patch.object(sandbox.shutil, "which", return_value=None), patch.object(sandbox.subprocess, "Popen") as popen:
            with self.assertRaises(sandbox.SandboxError):
                sandbox._docker(["info"])
            popen.assert_not_called()

    def test_mutable_images_are_rejected(self):
        with patch.dict(os.environ, {"TABLE_SPECIALIST_PYTHON_IMAGE": "python:latest"}), patch.object(sandbox, "_docker") as docker:
            with self.assertRaises(sandbox.SandboxError):
                sandbox.ensure_sandbox("python")
            docker.assert_not_called()

    def test_remote_docker_hosts_are_rejected(self):
        fake = FakeDocker()
        for host in ["ssh://remote.example", "tcp://remote.example:2376"]:
            with self.subTest(host=host), self.configured(fake), patch.dict(os.environ, {"DOCKER_HOST": host}), self.assertRaises(sandbox.SandboxError):
                sandbox.ensure_sandbox("python")

    def test_daemon_and_image_must_be_hardened_linux(self):
        bad_responses = [
            (0, b'{"OSType":"windows","SecurityOptions":["name=seccomp"]}', b""),
            (0, b'{"OSType":"linux","SecurityOptions":[]}', b""),
            (0, b'{"OSType":"linux","SecurityOptions":["name=seccomp,profile=unconfined"]}', b""),
        ]
        for response in bad_responses:
            with self.subTest(response=response), patch.dict(os.environ, {"TABLE_SPECIALIST_PYTHON_IMAGE": IMAGE}), patch.object(sandbox, "_docker", return_value=response):
                with self.assertRaises(sandbox.SandboxError):
                    sandbox.ensure_sandbox("python")
        fake = FakeDocker()
        def image_with_volume(args, **kwargs):
            if args[:2] == ["image", "inspect"]:
                return 0, b'[{"Os":"linux","Config":{"Volumes":{"/extra":{}}}}]', b""
            return fake(args, **kwargs)
        with self.configured(image_with_volume), self.assertRaises(sandbox.SandboxError):
            sandbox.ensure_sandbox("python")

    def test_python_success_uses_hardening_and_only_selected_files(self):
        (self.work / "credentials.txt").write_text("DO NOT COPY")
        fake = FakeDocker()
        with self.configured(fake):
            result = sandbox.run_generated_code(self.work, "python")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "runtime log")
        self.assertEqual((self.work / "result.csv").read_bytes(), b"answer\n3\n")
        self.assertEqual(set(fake.copied_files), {"query.py", "data.csv", "stdin.txt", "export.tar"})
        self.assertEqual(fake.copied_files["export.tar"], b"")
        create = next(args for args, _ in fake.calls if args[0] == "create")
        for flag in ["--network", "--read-only", "--cap-drop", "--security-opt", "--user", "--pids-limit", "--memory", "--memory-swap", "--cpus", "--ulimit", "--tmpfs", "--log-driver", "--pull=never"]:
            self.assertIn(flag, create)
        self.assertEqual(create[create.index("--network") + 1], "none")
        self.assertEqual(create[create.index("--user") + 1], "65534:65534")
        self.assertEqual(create[create.index("--mount") + 1], "type=volume,destination=/input,volume-nocopy")
        self.assertNotIn("--privileged", create)
        self.assertNotIn("--env-file", create)
        self.assertNotIn("--volume", create)
        self.assertNotIn(str(self.work), " ".join(create))
        self.assertIn("python3", create)
        self.assertIn("-I", create)
        launcher = create[create.index("-c") + 1]
        self.assertIn('"$@" < /input/stdin.txt; tar -cf /input/export.tar -- result.csv', launcher)
        self.assertIn('if [ -w /input ]', launcher)
        download = next(args for args, _ in fake.calls if args[0] == "cp" and args[-1] == "-")
        self.assertTrue(download[1].endswith(":/input/export.tar"))
        self.assertNotIn("/tmp/job", download[1])
        wait = next(kwargs for args, kwargs in fake.calls if args[0] == "wait")
        self.assertEqual(wait["timeout"], 10)
        self.assertEqual(fake.calls[-1][0][:3], ["rm", "--force", "--volumes"])

    def test_scala_success_and_path_adaptation(self):
        code = 'spark.read.csv("data.csv").coalesce(1).write.option("header", "true").csv("result")'
        (self.work / "query.scala").write_text(code)
        fake = FakeDocker(archive_of([("result_scala", tarfile.DIRTYPE, ""), ("result_scala/part-00000.csv", b"a\n1\n"), ("result_scala/_SUCCESS", b"")]))
        with self.configured(fake):
            sandbox.run_generated_code(self.work, "scala")
        self.assertIn(b'.csv("result_scala")', fake.copied_files["query.scala"])
        self.assertEqual(fake.copied_files["stdin.txt"], b":load /tmp/job/query.scala\n:quit\n")
        self.assertEqual((self.work / "result_scala" / "part-00000.csv").read_bytes(), b"a\n1\n")
        self.assertEqual(list((self.work / "result_scala").iterdir()), [self.work / "result_scala" / "part-00000.csv"])
        wait = next(kwargs for args, kwargs in fake.calls if args[0] == "wait")
        self.assertEqual(wait["timeout"], 120)

    def test_r_uses_vanilla_and_preserves_lowercase_source(self):
        (self.work / "query.r").write_text("# R test\n")
        fake = FakeDocker()
        with self.configured(fake):
            sandbox.run_generated_code(self.work, "r", "query.r")
        self.assertIn("query.R", fake.copied_files)
        create = next(args for args, _ in fake.calls if args[0] == "create")
        self.assertEqual(create[-3:], ["Rscript", "--vanilla", "query.R"])

    def test_timeout_kills_container_and_imports_nothing(self):
        fake = FakeDocker(timeout=True)
        with self.configured(fake), self.assertRaises(sandbox.SandboxExecutionError):
            sandbox.run_generated_code(self.work, "python", timeout=0.1)
        self.assertEqual(fake.calls[-1][0][:3], ["rm", "--force", "--volumes"])
        self.assertFalse((self.work / "result.csv").exists())

    def test_nonzero_exit_imports_nothing(self):
        fake = FakeDocker(exit_code=7)
        with self.configured(fake):
            self.assertEqual(sandbox.run_generated_code(self.work, "python").returncode, 7)
        self.assertFalse((self.work / "result.csv").exists())
        self.assertFalse(any(args[0] == "cp" and args[-1] == "-" for args, _ in fake.calls))

    def test_control_failures_cleanup_and_never_fallback(self):
        for operation in ["create", "cp", "start", "wait"]:
            fake = FakeDocker(fail_at=operation)
            with self.subTest(operation=operation), self.configured(fake), self.assertRaises(sandbox.SandboxError):
                sandbox.run_generated_code(self.work, "python")
            self.assertEqual(fake.calls[-1][0][:3], ["rm", "--force", "--volumes"])

    def test_cleanup_failure_is_visible(self):
        fake = FakeDocker(exit_code=1, fail_at="rm")
        with self.configured(fake), self.assertRaisesRegex(sandbox.SandboxError, "cleanup failed"):
            sandbox.run_generated_code(self.work, "python")

    def test_output_validation_is_atomic(self):
        fake = FakeDocker(archive_of([("result.csv", b"ok"), ("../escape", b"bad")]))
        with self.configured(fake), self.assertRaises(sandbox.SandboxExecutionError):
            sandbox.run_generated_code(self.work, "python")
        self.assertFalse((self.work / "result.csv").exists())

    def test_existing_output_is_refused(self):
        (self.work / "result.csv").write_text("old result")
        fake = FakeDocker()
        with self.configured(fake), self.assertRaises(sandbox.SandboxError):
            sandbox.run_generated_code(self.work, "python")
        self.assertEqual((self.work / "result.csv").read_text(), "old result")
        self.assertFalse(any(args[0] == "create" for args, _ in fake.calls))

    def test_invalid_command_path_and_limits_are_rejected(self):
        for kwargs in [{"code_file": "../query.py"}, {"code_file": "query.py\n:quit"}, {"timeout": 0}, {"timeout": float("nan")}, {"num_cpu": 0}, {"num_cpu": 8}, {"num_cpu": True}]:
            fake = FakeDocker()
            with self.subTest(kwargs=kwargs), self.configured(fake), self.assertRaises(sandbox.SandboxError):
                sandbox.run_generated_code(self.work, "python", **kwargs)
            self.assertFalse(any(args[0] == "create" for args, _ in fake.calls))

    def test_input_size_limit(self):
        fake = FakeDocker()
        with self.configured(fake), patch.object(sandbox, "MAX_INPUT_BYTES", 1), self.assertRaises(sandbox.SandboxError):
            sandbox.run_generated_code(self.work, "python")

    @unittest.skipUnless(os.name == "posix", "POSIX directory permission semantics")
    def test_copied_directory_is_traversable_but_host_parent_is_private(self):
        fake = FakeDocker()
        def check_modes(args, **kwargs):
            if args[0] == "cp" and args[-1] != "-":
                directory = Path(args[1])
                self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o755)
                self.assertEqual(stat.S_IMODE(directory.parent.stat().st_mode), 0o700)
            return fake(args, **kwargs)
        with self.configured(check_modes):
            sandbox.run_generated_code(self.work, "python")

    def test_input_symlink_is_refused(self):
        link = self.work / "linked.py"
        try:
            link.symlink_to(self.work / "query.py")
        except OSError:
            self.skipTest("OS does not permit creating symlinks")
        fake = FakeDocker()
        with self.configured(fake), self.assertRaises(sandbox.SandboxError):
            sandbox.run_generated_code(self.work, "python", "linked.py")


class ArchiveTests(unittest.TestCase):
    def test_traversal_absolute_unexpected_and_duplicate_paths(self):
        for entries in [[("../result.csv", b"x")], [("/result.csv", b"x")], [("result.csv/../escape", b"x")], [("other.csv", b"x")], [("result.csv\\escape", b"x")], [("result.csv", b"a"), ("result.csv", b"b")]]:
            with self.subTest(entries=entries), self.assertRaises(sandbox.SandboxExecutionError):
                sandbox._read_csv_artifacts(archive_of(entries), "result.csv", directory=False)

    def test_links_devices_and_fifos_are_rejected(self):
        for kind in [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE]:
            with self.subTest(kind=kind), self.assertRaises(sandbox.SandboxExecutionError):
                sandbox._read_csv_artifacts(archive_of([("result.csv", kind, "/etc/passwd")]), "result.csv", directory=False)

    def test_invalid_and_oversized_archives(self):
        with self.assertRaises(sandbox.SandboxExecutionError):
            sandbox._read_csv_artifacts(b"not tar", "result.csv", directory=False)
        with patch.object(sandbox, "MAX_OUTPUT_BYTES", 2), self.assertRaises(sandbox.SandboxExecutionError):
            sandbox._read_csv_artifacts(archive_of([("result.csv", b"large")]), "result.csv", directory=False)

    def test_multiple_spark_parts_or_no_csv_are_rejected(self):
        for entries in [[("result_scala/_SUCCESS", b"")], [("result_scala/part-1.csv", b"x"), ("result_scala/part-2.csv", b"y")]]:
            with self.subTest(entries=entries), self.assertRaises(sandbox.SandboxExecutionError):
                sandbox._read_csv_artifacts(archive_of(entries), "result_scala", directory=True)


class BoundedCliTests(unittest.TestCase):
    def test_oversized_stream_kills_client(self):
        class Process:
            stdout = io.BytesIO(b"a" * 100)
            stderr = io.BytesIO()
            returncode = 0
            killed = False
            def wait(self, timeout=None):
                return self.returncode
            def kill(self):
                self.killed = True
        process = Process()
        with patch.object(sandbox.shutil, "which", return_value="docker"), patch.object(sandbox.subprocess, "Popen", return_value=process), self.assertRaises(sandbox.SandboxExecutionError):
            sandbox._docker(["logs"], max_stdout=10)
        self.assertTrue(process.killed)

    def test_cli_timeout_kills_client(self):
        class Process:
            stdout = io.BytesIO()
            stderr = io.BytesIO()
            returncode = 0
            killed = False
            def wait(self, timeout=None):
                if timeout is not None:
                    raise subprocess.TimeoutExpired("docker", timeout)
                return 0
            def kill(self):
                self.killed = True
        process = Process()
        with patch.object(sandbox.shutil, "which", return_value="docker"), patch.object(sandbox.subprocess, "Popen", return_value=process), self.assertRaises(sandbox.SandboxExecutionError):
            sandbox._docker(["wait"])
        self.assertTrue(process.killed)


class EntryPointTests(unittest.TestCase):
    def test_no_host_execution_sinks_remain_in_pipelines(self):
        for folder in ["Generation", "Validation", "Evaluete"]:
            for path in (ROOT / folder).rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    target = ast.unparse(node.func)
                    self.assertNotIn(target, {"subprocess.run", "subprocess.Popen", "subprocess.call", "os.system", "exec", "eval"}, str(path))

    def test_all_reported_spark_sinks_route_to_sandbox(self):
        paths = ["Generation/NL2DSL/NL2SparkScala/execute.py", "Validation/NL2DSL/NL2SQL_SparkScala/execute.py", "Evaluete/evaluate/nss_evaluator.py"]
        for name in paths:
            tree = ast.parse((ROOT / name).read_text())
            function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_run_spark")
            namespace = {"os": os, "run_generated_code": None, "SandboxExecutionError": sandbox.SandboxExecutionError}
            exec(compile(ast.Module(body=[function], type_ignores=[]), name, "exec"), namespace)
            with tempfile.TemporaryDirectory() as directory:
                scala_path = str(Path(directory) / "query.scala")
                with patch.dict(namespace, {"run_generated_code": lambda *args, **kwargs: sandbox.ExecutionResult(0, "ok", "")}):
                    if "nss_evaluator" in name:
                        self.assertTrue(namespace["_run_spark"](directory, scala_path, 1))
                    else:
                        self.assertTrue(namespace["_run_spark"]((directory, scala_path, 1)))
                self.assertEqual(Path(scala_path + ".log").read_text(), "ok")


if __name__ == "__main__":
    unittest.main()
