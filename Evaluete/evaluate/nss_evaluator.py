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
import subprocess
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
from pandas.errors import EmptyDataError


class SQLStandardizeError(Exception):
    pass


def _run_spark(exec_dir, scala_path, num_cpu):
    cur_dir = os.getcwd()
    os.chdir(exec_dir)
    print(f"Running SparkScala code in {scala_path}")
    with open(scala_path+".log", "w+") as outfile, open(scala_path+".err", "w+") as errfile:
        proc = subprocess.Popen(["spark-shell", "--conf", "spark.ui.enabled=False", "--master", f"local[{num_cpu}]"], stdin=subprocess.PIPE, stdout=outfile, stderr=errfile, text=True)
        proc.communicate(f":load {scala_path}\n")
    os.chdir(cur_dir)
    return


class NSSEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__()
        self.answer_key = "SparkScala"

    def _evaluate_row(self, y_true_sql, y_pred_scala, test_id, exec_dir, benchmark="WikiSQL"):
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

        cur_exec_dir = None
        if y_pred_scala == "ScalaCodeNotFound":
            y_pred_res = None
        else:
            try:
                cur_dir = os.getcwd()

                assert os.path.isdir(f"{exec_dir}/result_{benchmark}_{test_id}"), "No result folder after SparkScala execution"
                out_csv = [x for x in os.listdir(f"{exec_dir}/result_{benchmark}_{test_id}") if x.endswith(".csv")]
                assert len(out_csv) == 1, "No output csv file"
                y_pred_res_path = os.path.abspath(os.path.join(f"{exec_dir}/result_{benchmark}_{test_id}", out_csv[0]))
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
            finally:
                os.chdir(cur_dir)


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
            row_res["y_gt"], row_res["y_pred"], row_res["dataset"], exec_dir, benchmark=row_res["benchmark"])
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
        scala_code_s = []
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
                continue
            scala_code = scala_code.replace("data.csv", csv_path)
            scala_code = scala_code.replace(""".write.option("header", "true").csv("result")""", f""".write.option("header", "true").csv("{exec_dir}/result_{metadata['benchmark']}_{test_id}")""")
            scala_code_s.append(scala_code)
            scala_code_execs.append(scala_code)

        scala_lists = []
        cur_list = []
        for scala_code in scala_code_s:
            cur_list.append(scala_code)
            if len(cur_list) == len(scala_code_s) // n_jobs + 1:
                scala_lists.append(cur_list)
                cur_list = []
        if len(cur_list) > 0:
            scala_lists.append(cur_list)

        print(raw_result.shape[0])
        print(len(scala_code_s), sum([len(x) for x in scala_lists]))
        for i, scala_list in enumerate(scala_lists):
            print(len(scala_list))
            with open(f"{exec_dir}/all_scala_code_{i}.scala", "w") as outfile:
                for scala_code in scala_list:
                    outfile.write(scala_code + '\n:reset\n')
                outfile.write(":quit\n")
        
        with Pool(n_jobs) as pool:
            pool.starmap(_run_spark, [(exec_dir, f"{exec_dir}/all_scala_code_{i}.scala", cpu_count() // n_jobs) for i in range(len(scala_lists))])

        return scala_code_execs

    


    def parse_raw_result(self, raw_result, n_jobs=1):
        result = []
        print("n_jobs", n_jobs)
        # prepare for SparkScala runtime
        exec_root = "<PATH-TO-TableSpecialist>/tmp_runtime"
        os.makedirs(exec_root, exist_ok=True)
        exec_dir = os.path.join(exec_root, f"timestamp_{time.time_ns()}")
        print("exec_dir", exec_dir)
        os.mkdir(exec_dir)

        scala_code_execs = self.batch_run_spark(exec_dir, raw_result, n_jobs=n_jobs)
        raw_result["scala_exec"] = scala_code_execs


        if n_jobs == 1:
            for _, row in raw_result.head(5).iterrows():
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
