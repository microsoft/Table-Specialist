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
from table_specialist_sandbox import run_generated_code, ensure_sandbox
from multiprocessing import Pool
from pandas.errors import EmptyDataError

class SQLStandardizeError(Exception):
    pass

def are_lists_equal(list1, list2):
    # Check if the lengths of the lists are equal
    if len(list1) != len(list2):
        return False
    
    # Iterate through the elements of the lists
    for i in range(len(list1)):
        # Check if the lengths of the sublists are equal
        if len(list1[i]) != len(list2[i]):
            return False
        
        # Compare the elements of the sublists
        for j in range(len(list1[i])):
            if list1[i][j] != list2[i][j]:
                try:
                    if abs((float(list1[i][j]) -  float(list2[i][j])) / float(list2[i][j])) < 0.01 and abs(float(list1[i][j]) -  float(list2[i][j])) < 0.01:
                        return True
                except:
                    return False
                return False
    
    # If all comparisons pass, the lists are equivalent
    return True

class NPEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__()
        self.answer_key = "PYTHON"

        
    def _evaluate_row(self, y_true_sql, y_pred_python, test_id, exec_dir, benchmark="WikiSQL"):
        y_pred_res = None
        y_true_res = None
        y_pred_res_path = None
        y_true_exec = None
        y_pred_exec = None
        sqlite_db_path = None
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
            

            try:
                conn = sqlite3.connect(sqlite_db_path)
                c = conn.cursor()
                y_true_exec = y_true_sql.replace("from table", "from \"table\"").replace("FROM table", "FROM \"table\"")
                y_true_res = pd.read_sql(y_true_exec, conn).applymap(lambda x: pd.to_numeric(x, errors='ignore')).fillna("None").values.tolist()
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
        else:
            y_true_res = [[pd.to_numeric(x, errors='ignore') for x in y_true_sql.split('|')]]
            csv_path = f"<PATH-TO-TableSpecialist>/Finetune/data/data_v2.0/NL2Pandas/benchmark/test/WikiQA/{test_id}/data.csv"
            
        cur_exec_dir = None
        if y_pred_python == "PythonCodeBlockNotFound":
            y_pred_res = None
        else:
            try:
                cur_exec_dir = tempfile.mkdtemp(prefix="python_", dir=exec_dir)
                shutil.copy(csv_path, os.path.join(cur_exec_dir, "data.csv"))
                with open(os.path.join(cur_exec_dir, "query.py"), "w", encoding="utf-8") as f:
                    f.write(y_pred_python)
                # run the python code
                result = run_generated_code(cur_exec_dir, "python", "query.py", timeout=10)
                exit_code = result.returncode
                output = result.stdout.strip()
                error = result.stderr.strip()

                if exit_code != 0:
                    with open(os.path.join(cur_exec_dir, "python_exec.err"), "w", encoding="utf-8") as f:
                        f.write(error)
                    raise Exception(f"Python execution error: {error}")
                
                result_path = os.path.join(cur_exec_dir, "result.csv")
                assert os.path.exists(result_path)
                try:
                    y_pred_res = pd.read_csv(result_path, index_col=False, header=None).applymap(lambda x: pd.to_numeric(x, errors='ignore')).fillna("None").values.tolist()
                except EmptyDataError:
                    y_pred_res = []
                y_pred_res_path = os.path.abspath(result_path)
            except Exception as e:
                print("-----------------------")
                print("Error y_pred")
                print(e)
                y_pred_res = "PythonExecutionError"

        flag = False
        errorMsg = ""
        if y_pred_python != "PythonCodeBlockNotFound" and y_true_res != "SQLExecutionError" and y_pred_res != "PythonExecutionError":
            # if len(y_true_res) == len(y_pred_res):
            # flag = y_true_res == y_pred_res
            flag = are_lists_equal(y_pred_res, y_true_res)
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
            "y_pred_exec": y_pred_python,
            "y_true_exec": y_true_exec,
            "y_pred_res_path": y_pred_res_path,
            "db_path": sqlite_db_path,
            "exec_dir": cur_exec_dir,
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
        row_res["prompt_completion"] = row_res["prompt"] + "\n" + row_res["completion"]
        row_res["y_pred"] = self._get_pred(row_res["completion"])
        row_res["y_gt"] = self._get_gt(row_res["label"])

        row_eval = self._evaluate_row(row_res["y_gt"], row_res["y_pred"], row_res["dataset"], exec_dir, benchmark=row_res["benchmark"])
        for k, v in row_eval.items():
            row_res[k] = v

        return row_res
    
    def _get_pred(self, completion):
        pattern = re.compile(r"```python(.*?)```", re.DOTALL)
        matches = re.findall(pattern, completion)
        if len(matches) == 0:
            return "PythonCodeBlockNotFound"
        return matches[0].strip()
    
    def _get_gt(self, completion):
        pattern = re.compile(r"```python(.*?)```", re.DOTALL)
        matches = re.findall(pattern, completion)
        if len(matches) == 0:
            return "PythonCodeBlockNotFound"
        return matches[0].strip()

    
    def parse_raw_result(self, raw_result, n_jobs=1):
        ensure_sandbox("python")
        result = []
        print("n_jobs", n_jobs)
        
        # prepare for python runtime
        exec_root = "<PATH-TO-TableSpecialist>/tmp_runtime"
        os.makedirs(exec_root, exist_ok=True)
        exec_dir = os.path.join(exec_root, f"timestamp_{time.time_ns()}")
        os.mkdir(exec_dir)

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
        