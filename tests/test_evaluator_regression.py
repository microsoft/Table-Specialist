"""Exercise trusted evaluator methods with a mocked sandbox, never model code."""

import ast
import contextlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import table_specialist_sandbox as sandbox

try:
    import pandas as pd
except ImportError:
    pd = None

ROOT = Path(__file__).resolve().parents[1]


def load_class(filename, name, source_replacements=None, **extra):
    source = (ROOT / filename).read_text()
    for old, new in (source_replacements or {}).items():
        source = source.replace(old, new)
    tree = ast.parse(source)
    # Compile only trusted repository definitions, excluding dependency imports.
    body = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))]
    namespace = {"BaseEvaluator": object, "pd": pd, "os": os, "shutil": shutil,
                 "tempfile": tempfile, "time": time, "re": re, "EmptyDataError": pd.errors.EmptyDataError,
                 "run_generated_code": Mock(), **extra}
    exec(compile(ast.Module(body=body, type_ignores=[]), filename, "exec"), namespace)
    return namespace[name](), namespace


@unittest.skipIf(pd is None, "Pandas required for evaluator compatibility tests")
class NPEvaluatorRegressionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.input = self.root / "fixture.csv"
        self.input.write_text("value\n1\n2\n")
        self.runs = self.root / "runs"
        self.runs.mkdir()
        self.evaluator, self.namespace = load_class("Evaluete/evaluate/np_evaluator.py", "NPEvaluator")
        self.cwd = os.getcwd()
        real_copy = shutil.copy
        self.copy = patch.object(shutil, "copy", side_effect=lambda source, target: real_copy(self.input, target))
        self.copy.start()
        self.addCleanup(self.copy.stop)

    def test_legitimate_result_and_untrusted_completion_are_preserved(self):
        payload = 'raise RuntimeError("This completion must not run on the host")'
        def result(work_dir, runtime, code_file, **kwargs):
            self.assertEqual(runtime, "python")
            self.assertEqual(kwargs["timeout"], 10)
            self.assertEqual((Path(work_dir) / code_file).read_text(), payload)
            (Path(work_dir) / "result.csv").write_text("3\n")
            return sandbox.ExecutionResult(0, "", "")
        self.namespace["run_generated_code"] = Mock(side_effect=result)
        with contextlib.redirect_stdout(io.StringIO()):
            row = self.evaluator._evaluate_row("3", payload, "../../untrusted-id", str(self.runs), benchmark="WikiQA")
        self.assertEqual(row["correct"], 1)
        self.assertEqual(row["y_pred_exec"], payload)
        self.assertEqual(Path(row["exec_dir"]).parent, self.runs)
        self.assertEqual(os.getcwd(), self.cwd)
        self.namespace["run_generated_code"].assert_called_once()

    def test_timeout_records_failure_and_keeps_host_cwd(self):
        self.namespace["run_generated_code"] = Mock(side_effect=sandbox.SandboxExecutionError("timeout"))
        with contextlib.redirect_stdout(io.StringIO()):
            row = self.evaluator._evaluate_row("3", "while True: pass", "case", str(self.runs), benchmark="WikiQA")
        self.assertEqual(row["correct"], 0)
        self.assertEqual(row["y_pred_rst"], "PythonExecutionError")
        self.assertEqual(os.getcwd(), self.cwd)
        self.assertFalse(list(self.runs.rglob("result.csv")))

    def test_missing_code_never_invokes_sandbox(self):
        row = self.evaluator._evaluate_row("3", "PythonCodeBlockNotFound", "case", str(self.runs), benchmark="WikiQA")
        self.namespace["run_generated_code"].assert_not_called()
        self.assertIsNone(row["exec_dir"])


@unittest.skipIf(pd is None, "Pandas required for evaluator compatibility tests")
class NSSEvaluatorRegressionTests(unittest.TestCase):
    def test_predictions_with_duplicate_ids_are_isolated_and_all_rows_evaluated(self):
        class Base:
            def remove_ending(self, text):
                return text

        class InlinePool:
            def __init__(self, *args):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def starmap(self, function, params):
                return [function(*args) for args in params]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            table = root / "fixture.csv"
            table.write_text("value\n1\n")
            metadata = json.dumps({"dataset": "same-id", "benchmark": "WikiQA", "label": "1", "sampleMethod": "greedy", "numSamples": "1"})
            code = 'val data = spark.read.csv("data.csv")\ndata.coalesce(1).write.option("header", "true").csv("result")'
            rows = pd.DataFrame([{"metadata": metadata, "prompt": "test", "response": "```scala\n" + code + "\n```"} for _ in range(5)] + [{"metadata": metadata, "prompt": "test", "response": "No Scala code"}])
            evaluator, namespace = load_class(
                "Evaluete/evaluate/nss_evaluator.py", "NSSEvaluator",
                source_replacements={"<PATH-TO-TableSpecialist>/tmp_runtime": root.as_posix() + "/runtime"},
                BaseEvaluator=Base, Pool=InlinePool, json=json,
                utils=SimpleNamespace(parse_metadata=json.loads), ensure_sandbox=Mock(),
                SandboxExecutionError=sandbox.SandboxExecutionError,
            )
            cases = []
            def run(work_dir, runtime, code_file, **kwargs):
                case = Path(work_dir)
                cases.append(case)
                self.assertEqual((case / code_file).read_text(), code)
                self.assertEqual((case / "data.csv").read_text(), table.read_text())
                output = case / "result_scala"
                output.mkdir()
                (output / "part-00000.csv").write_text("value\n1\n")
                return sandbox.ExecutionResult(0, "", "")
            namespace["run_generated_code"] = Mock(side_effect=run)
            real_copy = shutil.copyfile
            cwd = os.getcwd()
            with patch.object(shutil, "copyfile", side_effect=lambda source, target: real_copy(table, target)), contextlib.redirect_stdout(io.StringIO()):
                result = evaluator.parse_raw_result(rows, n_jobs=1)
            self.assertEqual(len(result), 6)
            self.assertEqual(result["correct"].tolist(), [1] * 5 + [0])
            self.assertEqual(len(set(cases)), 5)
            self.assertEqual(len({path.parent for path in cases}), 1)
            self.assertEqual(os.getcwd(), cwd)
            self.assertFalse(list(root.rglob("all_scala_code*.scala")))


if __name__ == "__main__":
    unittest.main()
