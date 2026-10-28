"""Opt-in live containment tests. All payload execution uses the real sandbox."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

import table_specialist_sandbox as sandbox


@unittest.skipUnless(os.environ.get("TABLE_SPECIALIST_SANDBOX_INTEGRATION") == "1", "Opt-in Linux Docker integration tests")
class LiveSandboxTests(unittest.TestCase):
    def setUp(self):
        sandbox.ensure_sandbox("python")
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.work = Path(self.directory.name)
        (self.work / "data.csv").write_text("value\n1\n2\n", encoding="utf-8")

    def python(self, code, **kwargs):
        (self.work / "query.py").write_text(code, encoding="utf-8")
        return sandbox.run_generated_code(self.work, "python", **kwargs)

    def test_legitimate_pandas_result(self):
        result = self.python('import pandas as pd\nd = pd.read_csv("data.csv")\nd.sum().to_csv("result.csv", header=False, index=False)\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.work / "result.csv").read_text().strip(), "3")

    def test_host_marker_credentials_and_network_are_isolated(self):
        marker = self.work / "host-marker.txt"
        marker.write_text("unchanged")
        (self.work / "credentials.txt").write_text("test-only-secret")
        code = f'''import os
from pathlib import Path
import socket
assert "TABLE_SPECIALIST_TEST_SECRET" not in os.environ
assert not Path("/input/credentials.txt").exists()
assert set(os.listdir("/sys/class/net")) == {{"lo"}}
try:
    Path({str(marker)!r}).write_text("changed")
except OSError:
    pass
try:
    socket.create_connection(("198.51.100.1", 80), timeout=1)
except OSError:
    pass
else:
    raise AssertionError("Unexpected external networking")
Path("result.csv").write_text("isolated\\n")
'''
        with patch.dict(os.environ, {"TABLE_SPECIALIST_TEST_SECRET": "test-only-secret"}):
            result = self.python(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(marker.read_text(), "unchanged")
        self.assertEqual((self.work / "result.csv").read_text(), "isolated\n")

    def test_infinite_loop_and_descendant_are_removed(self):
        identity = uuid.uuid4()
        with patch.object(sandbox.uuid, "uuid4", return_value=identity), self.assertRaises(sandbox.SandboxExecutionError):
            self.python('import subprocess\nsubprocess.Popen(["python3", "-c", "import time; time.sleep(3600)"])\nwhile True: pass\n', timeout=1)
        remaining = sandbox._checked(["ps", "-a", "--filter", "name=table-specialist-" + identity.hex, "--format", "{{.ID}}"])
        self.assertFalse(remaining.strip(), "Container/process tree remains after timeout")

    def test_symlink_result_is_not_imported(self):
        with self.assertRaises(sandbox.SandboxExecutionError):
            self.python('import os\nos.symlink("data.csv", "result.csv")\n')
        self.assertFalse((self.work / "result.csv").exists())

    @unittest.skipUnless(os.environ.get("TABLE_SPECIALIST_SPARK_IMAGE"), "Configure reviewed Spark image")
    def test_legitimate_spark_result(self):
        (self.work / "query.scala").write_text('val data = spark.read.option("header", "true").csv("data.csv")\ndata.coalesce(1).write.option("header", "true").csv("result")\n', encoding="utf-8")
        result = sandbox.run_generated_code(self.work, "scala")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = list((self.work / "result_scala").glob("part-*.csv"))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0].read_text().strip(), "value\n1\n2")

    @unittest.skipUnless(os.environ.get("TABLE_SPECIALIST_R_IMAGE"), "Configure reviewed R image")
    def test_legitimate_r_result(self):
        (self.work / "query.R").write_text('d <- read.csv("data.csv")\nwrite.csv(data.frame(answer=sum(d$value)), "result.csv", row.names=FALSE)\n', encoding="utf-8")
        result = sandbox.run_generated_code(self.work, "r")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("3", (self.work / "result.csv").read_text())


if __name__ == "__main__":
    unittest.main()
