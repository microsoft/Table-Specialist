from .base_evaluator import BaseEvaluator
import utils
import pandas as pd
import re
import numpy as np
import os
import time
from multiprocessing import Pool
import subprocess
from pandas.errors import EmptyDataError
import json

class R2RBaseEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__()
        self.answer_key = "output_value"

        self.run_time_executive = "<CMD>"
        self.run_time_file = "<FILE>"
        self.pl = "<PL>"
        self.codeBlockNotFound = f"{self.pl}CodeBlockNotFound"
        self.executionError = f"{self.pl}ExecutionError"
        
    def _evaluate_row(self, y_true, y_pred, test_id, exec_dir):
        y_pred_res = None
        y_true_res = None
        y_pred_res_path = None
        y_true_exec = None
        if os.path.exists(os.path.join("<PATH-TO-TableSpecialist>/Finetune/data/data_v1.0/Row2RowPandas/benchmark/test/TDE", test_id, "data.csv")):
            test_csv = os.path.join("<PATH-TO-TableSpecialist>/Finetune/data/data_v1.0/Row2RowPandas/benchmark/test/TDE", test_id, "data.csv")
        elif os.path.exists(os.path.join("<PATH-TO-TableSpecialist>/Finetune/data/data_v2.0/Row2RowPandas/benchmark/test/prose", test_id, "data.csv")):
            test_csv = os.path.join("<PATH-TO-TableSpecialist>/Finetune/data/data_v2.0/Row2RowPandas/benchmark/test/prose", test_id, "data.csv")
        else:
            raise Exception("Cannot find the test csv file")

        cur_exec_dir = f"{exec_dir}/{test_id}"
        if y_pred == self.codeBlockNotFound:
            y_pred_res = None
        else:
            try:
                cur_dir = os.getcwd()
                os.mkdir(cur_exec_dir)
                os.chdir(cur_exec_dir)

                input_csv_df = pd.read_csv(test_csv, keep_default_na=False)
                input_csv_df.loc[input_csv_df.shape[0]-1, "Output"] = "<MISSING>"
                input_csv_df.columns = [f"Col_{idx}" for idx in range(len(input_csv_df.columns))]
                input_csv_df.columns = list(input_csv_df.columns)[:-1] + ["DERIVED_COLUMN"]
                input_csv_df.drop(columns=["DERIVED_COLUMN"], inplace=True)
                input_csv_df.to_csv("data.csv", index=False)

                gt_csv_df = pd.read_csv(test_csv, keep_default_na=False)
                gt_csv_df.loc[gt_csv_df.shape[0]-1, "Output"] = y_true
                y_true_res = gt_csv_df["Output"].tolist()

                y_pred = y_pred.replace("derived_column", "DERIVED_COLUMN")
                with open(self.run_time_file, "w") as f:
                    f.write(y_pred)

                # run the python code
                try:
                    result = subprocess.run(
                        [self.run_time_executive, self.run_time_file], capture_output=True, text=True, timeout=10)
                    exit_code = result.returncode
                    output = result.stdout.strip()
                    error = result.stderr.strip()
                except Exception as e:
                    print("-----TEST-----")
                    print(test_id)
                    print(e)
                    

                if exit_code != 0:
                    # print(f"{self.pl} execution error: {error}")
                    raise Exception(f"{self.pl} execution error: {error}")
                
                try:
                    assert os.path.exists("result.csv")
                    y_pred_res = pd.read_csv("result.csv", index_col=False, dtype=str).fillna('nan')
                    if "DERIVED_COLUMN" in y_pred_res.columns:
                        y_pred_res = y_pred_res["DERIVED_COLUMN"].tolist()
                    elif "derived_column" in y_pred_res.columns:
                        y_pred_res = y_pred_res["derived_column"].tolist()
                    else:
                        y_pred_res = "DerivedColumnNotFound"
                except AssertionError:
                    y_pred_res = "ResultFileNotFound"
                except Exception as e:
                    y_pred_res = "DerivedColumnNotFound"
                y_pred_res_path = os.path.abspath("result.csv")
            except Exception as e:
                # print("-----------------------")
                # print("Error y_pred")
                # print(e)
                y_pred_res = self.executionError
            finally:
                os.chdir(cur_dir)

        flag = False
        if y_pred != self.codeBlockNotFound and y_pred_res != self.executionError:
            try:
                flag = y_true_res == y_pred_res
            except Exception as e:
                pass

        res = {
            "correct": 1 if flag else 0,
            "y_pred_rst": y_pred_res,
            "y_true_rst": y_true_res,
            "y_pred_exec": y_pred,
            "y_true_exec": y_true,
            "y_pred_res_path": y_pred_res_path,
            "y_pred_exec_dir": cur_exec_dir
        }
        return res
    
    def _compute_metric(self, res):
        acc = res["correct"].values.max()
        metric = {
            "acc": acc
        }
        return metric

    def _get_pred(self, completion):
        pattern = re.compile(f"```{self.pl}(.*?)```", re.DOTALL)
        matches = re.findall(pattern, completion)
        if len(matches) == 0:
            return self.codeBlockNotFound
        return matches[0].strip()
        
    def _get_gt(self, label):
        js = json.loads(label)
        return js[self.answer_key]
        # gt = self.extract_json_answer(label, self.answer_key)
        # if gt == "JSONParsingError":
        #     raise Exception("Parsing Error on ground truth")
        # return gt
    
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

        # if row_res["benchmark"] == "TDE":
        #     if "benchmark-stackoverflow" in row_res["filename"]:
        #         row_res["benchmark"] = "Stackoverflow"
        #     elif "unit" in row_res["filename"]:
        #         row_res["benchmark"] = "BingQL-Unit"
        #     elif "benchmark-FF-Trifacta-GoogleRefine" in row_res["filename"]:
        #         row_res["benchmark"] = "FF-GR-Trifacta"
        #     elif "benchmark-headcase" in row_res["filename"]:
        #         row_res["benchmark"] = "Headcase"
        #     else:
        #         row_res["benchmark"] = "BingQL-other"
        
        # evaluate each row
        row_eval = self._evaluate_row(row_res["y_gt"], row_res["y_pred"], row_res["dataset"], exec_dir)
        for k, v in row_eval.items():
            row_res[k] = v

        return row_res
    
    def parse_raw_result(self, raw_result, n_jobs=1):
        result = []
        print("n_jobs", n_jobs)
        
        # prepare for runtime
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
    