from collections import defaultdict
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
import utils
import os
from .base_evaluator import BaseEvaluator
import json
import re
from sqlglot import exp, parse_one, diff
from sqlglot.diff import Keep, Move
import sqlite3
import time
import shutil
import tempfile
from table_specialist_sandbox import run_generated_code, ensure_sandbox, SandboxExecutionError
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
from pandas.errors import EmptyDataError


class SQLStandardizeError(Exception):
    pass


def _run_spark(exec_dir, scala_path, num_cpu):
    # Each model output gets its own container and its own input table.
    try:
        result = run_generated_code(exec_dir, "scala", os.path.basename(scala_path), num_cpu=num_cpu)
    except SandboxExecutionError as exc:
        with open(scala_path + ".err", "w", encoding="utf-8") as file:
            file.write(str(exc))
        return False
    with open(scala_path + ".log", "w", encoding="utf-8") as file:
        file.write(result.stdout)
    with open(scala_path + ".err", "w", encoding="utf-8") as file:
        file.write(result.stderr)
    return result.returncode == 0


class NSSEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__()
        self.answer_key = "SparkScala"

    def _evaluate_row(self, y_true_sql, y_pred_scala, test_id, exec_dir, benchmark="WikiSQL", result_dir=None):
        y_pred_res = None
        y_true_res = None
        y_pred_res_path = None
        sqlite_db_path = None
        # print(benchmark, test_id, y_true_sql)
        if benchmark == "WikiSQL":
            try:
                if os.path.exists("<PATH-TO-TableSpecialist>/Finetune/data/data_v1.0/NL2SQL/benchmark/test/WikiSQL/" + test_id + '/info.json'):
                    with open("<PATH-TO-TableSpecialist>/Finetune/data/data_v1.0/NL2SQL/benchmark/test/WikiSQL/" + test_id + '/info.json') as f:
                        data = json.load(f)
                        tbl_id = data["table_id"]
                else:
                    if os.path.exists("<PATH-TO-TableSpecialist>/Finetune/data/data_v2.0/NL2SQL/benchmark/test/WikiSQL/" + test_id + '/info.json'):
                        with open("<PATH-TO-TableSpecialist>/Finetune/data/data_v2.0/NL2SQL/benchmark/test/WikiSQL/" + test_id + '/info.json') as f:
                            data = json.load(f)
                            tbl_id = data["table_id"]
                sqlite_db_path = f"<PATH-TO-TableSpecialist>/resources/NL2SQL/WikiSQL_processed/test/{tbl_id}.db"
                csv_path = f"<PATH-TO-TableSpecialist>/resources/NL2SQL/WikiSQL_processed/test/{tbl_id}.csv"
                assert os.path.exists(sqlite_db_path)
                assert os.path.exists(csv_path)
            except Exception as e:
                print(e)
                raise Exception("Cannot find the database: " + sqlite_db_path)
                return {
                    "correct": 0
                }
            conn = sqlite3.connect(sqlite_db_path)

            try:
                c = conn.cursor()
                y_true_sql = y_true_sql.replace("from table", "from \"table\"")
                
                y_true_res = pd.read_sql(y_true_sql, conn).applymap(lambda x: pd.to_numeric(x, errors='ignore')).fillna("None").values.tolist()
            except Exception as e:
                print("-----------------------")
                print("Error y_true")
                print(e)
                print(sqlite_db_path, y_true_sql)
                y_true_res = "SQLExecutionError"
            finally:
                c.close()
        elif benchmark == "Text2Analysis":
            if os.path.exists(os.path.join("<PATH-TO-TableSpecialist>/Finetune/data/data_v7.0/NL2Pandas/benchmark/test/Text2Analysis", test_id, "info.json")):
                with open(os.path.join("<PATH-TO-TableSpecialist>/Finetune/data/data_v7.0/NL2Pandas/benchmark/test/Text2Analysis", test_id, "info.json")) as f:
                    data = json.load(f)
                    csv_path = data["table"]
                    y_true_res = pd.read_csv(os.path.join("<PATH-TO-TableSpecialist>/Finetune/data/data_v7.0/NL2Pandas/benchmark/test/Text2Analysis", test_id, "result_gt.csv"), index_col=False, header=0).applymap(lambda x: pd.to_numeric(x, errors='ignore')).fillna("None").values.tolist()
                    y_true_exec = y_true_sql
            else:
                raise Exception("Cannot find the test cse: " + test_id)
        elif benchmark == "spider":
            if os.path.exists(os.path.join("<PATH-TO-TableSpecialist>/Finetune/data/data_v9.0/NL2SQL/benchmark/test/spider", test_id, "info.json")):
                with open(os.path.join("<PATH-TO-TableSpecialist>/Finetune/data/data_v9.0/NL2SQL/benchmark/test/spider", test_id, "info.json")) as f:
                    data = json.load(f)
                    sqlite_db_path = f"<PATH-TO-TableSpecialist>/Finetune/data/data_v9.0/NL2SQL/benchmark/test/spider/{test_id}/data.sqlite"
                    csv_path = f"<PATH-TO-TableSpecialist>/Finetune/data/data_v9.0/NL2SQL/benchmark/test/spider/{test_id}/data.csv"
                    assert os.path.exists(sqlite_db_path), "Cannot find the database: " + sqlite_db_path
                    assert os.path.exists(csv_path)
            else:
                raise Exception("Cannot find the test cse: " + test_id)
            try:
                conn = sqlite3.connect(sqlite_db_path)
                c = conn.cursor()
                y_true_exec = y_true_sql.replace("from table", "from \"table\"").replace("FROM table", "FROM \"table\"")
                y_true_res = pd.read_sql(y_true_exec, conn).applymap(lambda x: pd.to_numeric(x, errors='ignore')).fillna("None").values.tolist()
            except Exception as e:
                print("-----------------------")
                print("Error y_true")
                print(e)
                print(sqlite_db_path, y_true_exec)
                y_true_res = "SQLExecutionError"
            finally:
                c.close()
        elif benchmark.startswith("bird"):
            if os.path.exists(os.path.join(f"<PATH-TO-TableSpecialist>/Finetune/data/data_v10.0/NL2SQL/benchmark/test/{benchmark}", test_id, "info.json")):
                with open(os.path.join(f"<PATH-TO-TableSpecialist>/Finetune/data/data_v10.0/NL2SQL/benchmark/test/{benchmark}", test_id, "info.json")) as f:
                    data = json.load(f)
                    sqlite_db_path = data["sqlite_path"]
                    csv_path = data["csv_path"]
                    # csv_path = f"<PATH-TO-TableSpecialist>/Finetune/data/data_v10.0/NL2SQL/benchmark/test/{benchmark}/{test_id}/data.csv"
                    assert os.path.exists(sqlite_db_path), "Cannot find the database: " + sqlite_db_path
                    assert os.path.exists(csv_path)
            else:
                raise Exception("Cannot find the test cse: " + test_id)
            try:
                conn = sqlite3.connect(sqlite_db_path)
                c = conn.cursor()
                y_true_exec = y_true_sql.replace("from table", "from \"table\"").replace("FROM table", "FROM \"table\"")
                y_true_res = pd.read_sql(y_true_exec, conn).applymap(lambda x: pd.to_numeric(x, errors='ignore')).fillna("None").values.tolist()
            except Exception as e:
                print("-----------------------")
                print("Error y_true")
                print(e)
                print(sqlite_db_path, y_true_exec)
                y_true_res = "SQLExecutionError"
            finally:
                c.close()
        else:
            y_true_res = [[pd.to_numeric(x, errors='ignore')] for x in y_true_sql.split('|')]
            csv_path = f"<PATH-TO-TableSpecialist>/Finetune/data/data_v2.0/NL2Pandas/benchmark/test/WikiQA/{test_id}/data.csv"

        cur_exec_dir = result_dir
        if y_pred_scala == "ScalaCodeNotFound":
            y_pred_res = None
        else:
            try:
                assert result_dir and os.path.isdir(result_dir), "No result folder after sandboxed SparkScala execution"
                out_csv = [x for x in os.listdir(result_dir) if x.endswith(".csv")]
                assert len(out_csv) == 1, "No output csv file"
                y_pred_res_path = os.path.abspath(os.path.join(result_dir, out_csv[0]))
                try:
                    y_pred_res = pd.read_csv(
                        y_pred_res_path, index_col=False, header=0).applymap(lambda x: pd.to_numeric(x, errors='ignore')).fillna("None").values.tolist()
                except EmptyDataError:
                    y_pred_res = []
            except Exception as e:
                print("-----------------------")
                print("Error y_pred")
                print(e)
                y_pred_res = "SparkScalaExecutionError"


        flag = False
        errorMsg = ""
        if y_pred_scala != "ScalaCodeNotFound" and y_true_res != "SQLExecutionError" and y_pred_res != "SparkScalaExecutionError":
            # if len(y_true_res) == len(y_pred_res):
            flag = y_true_res == y_pred_res
            if y_true_res in [[], [[]], [["None"]]] and y_pred_res in [[], [[]], [["None"]]]:
                flag = True
            if not flag:
                y_pred_res_flatten = [item for sublist in y_pred_res for item in sublist]
                y_true_res_flatten = [item for sublist in y_true_res for item in sublist]
                if (len(y_pred_res) == len(y_true_res)) and set(y_true_res_flatten).issubset(set(y_pred_res_flatten)):
                    errorMsg = "superset" 
                elif (len(y_pred_res) == len(y_true_res)) and set(y_pred_res_flatten).issubset(set(y_true_res_flatten)) and y_pred_res_flatten not in [[], ["None"]]:
                    errorMsg = "subset"
                else:
                    errorMsg = "others"
            # else:
                # errorMsg = "others"
        else:
            errorMsg = "compile/execution error"

        return {
            "correct": 1 if flag else 0,
            "y_pred_rst": y_pred_res,
            "y_true_rst": y_true_res,
            "y_pred_exec": y_pred_scala,
            "y_true_exec": y_true_sql,
            "y_pred_res_path": y_pred_res_path,
            "y_pred_exec_dir": cur_exec_dir,
            "db_path": sqlite_db_path,
            "error": errorMsg
        }

    def _compute_metric(self, res):
        acc = res["correct"].values.mean()
        metric = {
            "acc": acc
        }
        return metric

    def parse_raw(self, row, exec_dir):
        row_res = utils.parse_metadata(row.metadata)
        row_res["metadata"] = row.metadata
        row_res["prompt"] = row.prompt
        if "choices" in row:
            row_res["completion"] = self.remove_ending(row.choices[0]["text"])
        elif "response" in row:
            row_res["completion"] = self.remove_ending(row.response)
        else:
            raise Exception("Unknown format")
        row_res["method"] = row_res["sampleMethod"] + row_res["numSamples"]
        row_res["label"] = self.remove_ending(row_res["label"])
        row_res["prompt_completion"] = row_res["prompt"] + \
            "\n" + row_res["completion"]
        row_res["y_pred"] = self._get_pred(row_res["completion"])
        row_res["scala_exec"] = row.scala_exec
        row_res["y_gt"] = self._get_gt(row_res["label"])
        row_eval = self._evaluate_row(
            row_res["y_gt"], row_res["y_pred"], row_res["dataset"], exec_dir, benchmark=row_res["benchmark"], result_dir=row["scala_result_dir"])
        for k, v in row_eval.items():
            row_res[k] = v

        return row_res
    
    def _get_pred(self, completion):
        pattern = re.compile(r"```scala(.*?)```", re.DOTALL)
        matches = re.findall(pattern, completion)
        if len(matches) == 0:
            if completion.lower().strip().startswith("val"):
                return completion
            return "ScalaCodeNotFound"
        return matches[-1].strip()
        # return self.extract_json_answer(completion, self.answer_key)
    
    def _get_gt(self, completion):
        pattern = re.compile(r"```scala(.*?)```", re.DOTALL)
        matches = re.findall(pattern, completion)
        if len(matches) == 0:
            # if completion.lower().strip().startswith("val"):
            return completion
            # return "ScalaCodeNotFound"
        return matches[0].strip()
        # return self.extract_json_answer(completion, self.answer_key)

    
    def batch_run_spark(self, exec_dir, raw_result, n_jobs=1):
        params = []
        result_dirs = []
        scala_code_execs = []
        for _, row in raw_result.iterrows():
            metadata = utils.parse_metadata(row["metadata"])
            test_id = metadata["dataset"]
            csv_path = ""
            if metadata['benchmark'] == "WikiSQL":
                if os.path.exists("<PATH-TO-TableSpecialist>/Finetune/data/data_v1.0/NL2SQL/benchmark/test/WikiSQL/" + test_id + '/info.json'):
                    with open("<PATH-TO-TableSpecialist>/Finetune/data/data_v1.0/NL2SQL/benchmark/test/WikiSQL/" + test_id + '/info.json') as f:
                        d = json.load(f)
                        tbl_id = d["table_id"]
                else:
                    if os.path.exists("<PATH-TO-TableSpecialist>/Finetune/data/data_v2.0/NL2SQL/benchmark/test/WikiSQL/" + test_id + '/info.json'):
                        with open("<PATH-TO-TableSpecialist>/Finetune/data/data_v2.0/NL2SQL/benchmark/test/WikiSQL/" + test_id + '/info.json') as f:
                            d = json.load(f)
                            tbl_id = d["table_id"]
                csv_path = f"<PATH-TO-TableSpecialist>/resources/NL2SQL/WikiSQL_processed/test/{tbl_id}.csv"
            elif metadata['benchmark'] == "Text2Analysis":
                if os.path.exists(os.path.join("<PATH-TO-TableSpecialist>/Finetune/data/data_v7.0/NL2Pandas/benchmark/test/Text2Analysis", test_id, "info.json")):
                    with open(os.path.join("<PATH-TO-TableSpecialist>/Finetune/data/data_v7.0/NL2Pandas/benchmark/test/Text2Analysis", test_id, "info.json")) as f:
                        d = json.load(f)
                        csv_path = d["table"]
            elif metadata['benchmark'] == "spider":
                if os.path.exists(os.path.join("<PATH-TO-TableSpecialist>/Finetune/data/data_v9.0/NL2SQL/benchmark/test/spider", test_id, "info.json")):
                    with open(os.path.join("<PATH-TO-TableSpecialist>/Finetune/data/data_v9.0/NL2SQL/benchmark/test/spider", test_id, "info.json")) as f:
                        data = json.load(f)
                        sqlite_db_path = f"<PATH-TO-TableSpecialist>/Finetune/data/data_v9.0/NL2SQL/benchmark/test/spider/{test_id}/data.sqlite"
                        csv_path = f"<PATH-TO-TableSpecialist>/Finetune/data/data_v9.0/NL2SQL/benchmark/test/spider/{test_id}/data.csv"
                        assert os.path.exists(sqlite_db_path), "Cannot find the database: " + sqlite_db_path
                        assert os.path.exists(csv_path)
                else:
                    raise Exception("Cannot find the test cse: " + test_id)
            elif metadata['benchmark'].startswith("bird"):
                if os.path.exists(os.path.join(f"<PATH-TO-TableSpecialist>/Finetune/data/data_v10.0/NL2SQL/benchmark/test/{metadata['benchmark']}", test_id, "info.json")):
                    with open(os.path.join(f"<PATH-TO-TableSpecialist>/Finetune/data/data_v10.0/NL2SQL/benchmark/test/{metadata['benchmark']}", test_id, "info.json")) as f:
                        data = json.load(f)
                        sqlite_db_path = data["sqlite_path"]
                        csv_path = data["csv_path"]
                        # csv_path = f"<PATH-TO-TableSpecialist>/Finetune/data/data_v10.0/NL2SQL/benchmark/test/{benchmark}/{test_id}/data.csv"
                        assert os.path.exists(sqlite_db_path), "Cannot find the database: " + sqlite_db_path
                        assert os.path.exists(csv_path)
                else:
                    raise Exception("Cannot find the test cse: " + test_id)
            else:
                csv_path = f"<PATH-TO-TableSpecialist>/Finetune/data/data_v2.0/NL2Pandas/benchmark/test/WikiQA/{test_id}/data.csv"
            
            completion = row['response']
            scala_code = self._get_pred(completion)

            if scala_code.find("data.csv") == -1 or scala_code.find(""".write.option("header", "true").csv("result")""") == -1:
                print("Scala code format error")
                scala_code_execs.append("ScalaCodeError")
                result_dirs.append(None)
                continue
            # Never share a shell between predictions, or expose benchmark host paths.
            case_dir = tempfile.mkdtemp(prefix="scala_", dir=exec_dir)
            shutil.copyfile(csv_path, os.path.join(case_dir, "data.csv"))
            scala_path = os.path.join(case_dir, "query.scala")
            with open(scala_path, "w", encoding="utf-8") as file:
                file.write(scala_code)
            params.append((case_dir, scala_path, 1))
            result_dirs.append(os.path.join(case_dir, "result_scala"))
            scala_code_execs.append(scala_code)

        with Pool(n_jobs) as pool:
            pool.starmap(_run_spark, params)
        return scala_code_execs, result_dirs

    


    def parse_raw_result(self, raw_result, n_jobs=1):
        ensure_sandbox("scala")
        if n_jobs < 1:
            raise ValueError("n_jobs must be positive")
        result = []
        print("n_jobs", n_jobs)
        # prepare for SparkScala runtime
        exec_root = "<PATH-TO-TableSpecialist>/tmp_runtime"
        os.makedirs(exec_root, exist_ok=True)
        exec_dir = os.path.join(exec_root, f"timestamp_{time.time_ns()}")
        print("exec_dir", exec_dir)
        os.mkdir(exec_dir)

        scala_code_execs, result_dirs = self.batch_run_spark(exec_dir, raw_result, n_jobs=n_jobs)
        raw_result = raw_result.copy()
        raw_result["scala_exec"] = scala_code_execs
        raw_result["scala_result_dir"] = result_dirs


        if n_jobs == 1:
            for _, row in raw_result.iterrows():
                row_res = self.parse_raw(row, exec_dir)
                result.append(row_res)
        else:
            rows = []
            for _, row in raw_result.iterrows():
                rows.append((row, exec_dir))
            with Pool(n_jobs) as pool:
                result = pool.starmap(self.parse_raw, rows)
        result = pd.DataFrame(result)
        return result
