# Executing generated code safely

Model completions, extracted code blocks, and prepared execution files are
**untrusted executable code**. Do not run them in your workstation's Python, R,
or Spark shell. Changing directories, disabling the Spark UI, a code denylist,
or adding a timeout does not constitute a security boundary.

The execution entry points now use `table_specialist_sandbox.run_generated_code`.
There is **no host-execution fallback or unsafe override**. Without a configured
sandbox, generation/validation/evaluation execution fails closed. The repository's
other research dependencies and `<PATH-TO-TableSpecialist>` placeholders still
need their original setup; the sandbox package does not supply them.

## Setup (trusted operator only)

1. Install the shared standard-library-only runner from the repository root:

   ```sh
   python -m pip install -e .
   ```

2. Use an up-to-date, trusted **Linux Docker daemon with seccomp enabled**,
   preferably rootless and hosted in a dedicated disposable VM. Review the
   active Docker context before use. The runner permits only local Unix sockets
   or Windows named pipes, not TCP/SSH remote daemons. Images declaring extra
   writable volumes are rejected. Docker access itself is privileged; never give generated code the
   Docker socket or run this pipeline with production credentials.

3. Build images separately, after reviewing/scanning the base images and
   dependencies. Each Dockerfile requires an immutable `BASE_IMAGE` digest;
   replace the placeholders with reviewed real digests. For example:

   ```sh
   docker build -f sandbox/Dockerfile.python --build-arg BASE_IMAGE=python@sha256:<reviewed-digest> -t table-specialist-python-sandbox .
   docker build -f sandbox/Dockerfile.spark --build-arg BASE_IMAGE=apache/spark@sha256:<reviewed-digest> -t table-specialist-spark-sandbox .
   docker build -f sandbox/Dockerfile.r --build-arg BASE_IMAGE=r-base@sha256:<reviewed-digest> -t table-specialist-r-sandbox .
   ```

   The Python recipe supplies NumPy/Pandas; the R recipe supplies the selected
   base's packages only. Add reviewed, pinned dependencies as needed. The Spark
   image must provide `/opt/spark/bin/spark-shell`. Verify that all runtimes work
   as UID/GID `65534` with a read-only root filesystem.
   All images must also provide `/bin/sh`, `cp`, and `tar` for the trusted wrapper.

4. Configure the **built immutable image IDs**, not mutable tags. Only the
   runtimes you use require configuration:

   ```sh
   export TABLE_SPECIALIST_PYTHON_IMAGE=$(docker image inspect --format '{{.Id}}' table-specialist-python-sandbox)
   export TABLE_SPECIALIST_SPARK_IMAGE=$(docker image inspect --format '{{.Id}}' table-specialist-spark-sandbox)
   export TABLE_SPECIALIST_R_IMAGE=$(docker image inspect --format '{{.Id}}' table-specialist-r-sandbox)
   ```

   PowerShell equivalent for one runtime:

   ```powershell
   $env:TABLE_SPECIALIST_PYTHON_IMAGE = docker image inspect --format '{{.Id}}' table-specialist-python-sandbox
   ```

   A locally present `repository@sha256:<digest>` is also accepted. Execution
   never pulls images, builds them, installs packages, or grants permissions.

## Boundary and limits

- One fresh container **per code/table pair**, including Scala. Predictions no
  longer share a Spark REPL or access each other's benchmark inputs/results.
- Only the selected code file and `data.csv` are copied into an anonymous,
  container-owned input volume. They are root-owned/readable, and the runtime
  runs as non-root. **No host bind mounts, repo mounts, credentials, or Docker
  sockets.** Code/data copies and the anonymous volume are removed on cleanup.
  Trusted transport files are added too: a fixed stdin file and an empty,
  writable `export.tar`. The volume's directory is not writable by the runtime;
  it cannot create/replace volume entries. The export file's size is capped by
  the inherited hard file-size limit.
- The host environment is not passed into the container. The reviewed image's
  built-in environment remains part of the image trust boundary.
- No external network; read-only root; all Linux capabilities dropped;
  no-new-privileges; default daemon seccomp policy. Writable job files live in
  a size-limited `/tmp` tmpfs, not a host directory.
- Limits: 3 GiB memory with no extra swap, 256 processes, 1 CPU by default
  (at most 4), 512 MiB temporary disk, 64 MiB total input/output, bounded CLI
  output and rotated container logs. Default execution deadlines: Python 10s,
  R 15s, Scala 120s. Control/cleanup operations are separately bounded.
- Timeout/error cleanup force-removes the **container and its entire process
  tree**, plus anonymous volumes. A cleanup failure raises an explicit operator
  error identifying the container; resolve it before further runs.
- After successful exit, only `result.csv` or one `result_scala/part-*.csv` is
  imported. A wrapper archives the result **before** the container exits,
  while its tmpfs exists, into the fixed export file. After stop, that file is
  downloaded from the anonymous volume. Both the outer transport archive and
  inner output archive are parsed as bounded data, never
  extracted. Links, special files, traversal, duplicate paths, excessive sizes,
  and unexpected CSV counts are rejected before writing a host result.
- Existing result paths are refused, preventing stale-result reuse and writes
  through pre-existing result symlinks. Archive or remove old results yourself
  before rerunning a case. Result CSVs/logs remain untrusted data.

The runner still executes arbitrary code **inside** the container. It does not
prove code correctness or make a malicious prediction's result trustworthy.
Containers share a kernel with their daemon host: keep Docker/kernel/images
patched and use a VM or stronger container runtime for hostile multi-tenant
inputs. This is containment, not a claim of immunity to sandbox escapes.
Treat benchmark metadata and explicitly selected input tables as trusted
operator inputs; this patch is not an audit of the repository's SQL parsers,
dataset loaders, model APIs, or all other attack surfaces.

## Compatibility changes

- Re-run the Scala preparation scripts to create `exec_*/query.scala` and
  `exec_*/data.csv`. Execution now ignores legacy root-level `all_scala_code_*`
  batches and uses each case's raw `query.scala`. The old `--batch_size` option
  is accepted but deprecated/unused. Expect higher Spark startup overhead.
- Normal relative `data.csv` reads are preserved. The documented Spark output
  expression `.write.option("header", "true").csv("result")` is routed to
  `result_scala` **inside the container**. This is output-path adaptation,
  **not code validation**. Host absolute paths and extra filesystem/network
  dependencies intentionally no longer work.
- The Scala evaluator records a distinct result directory per prediction,
  including repeated test IDs. Failed/missing outputs are execution failures,
  not a reason to retry on the host.

## Tests

Unit/regression tests do not execute model payloads on the host:

```sh
python -m unittest discover -s tests -v
```

The evaluator compatibility tests additionally need NumPy/Pandas (install with
`python -m pip install -e '.[test]'`); those tests skip if Pandas is unavailable.

Before merging, also run the opt-in live tests on the reviewed Docker setup:

```sh
TABLE_SPECIALIST_SANDBOX_INTEGRATION=1 python -m unittest discover -s tests -v
```

These verify a legitimate Python/Pandas result, host-marker/credential and
network isolation, process-tree termination, invalid-output rejection, and a
legitimate Spark result if `TABLE_SPECIALIST_SPARK_IMAGE` is set. Never run
generated payloads outside the sandbox to test a security fix.

Report security findings privately as directed by the root `SECURITY.md`.
