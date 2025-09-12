from .r2r_base_evaluator import R2RBaseEvaluator
import utils
import pandas as pd
import re
import numpy as np
import os
import time
from multiprocessing import Pool
import subprocess
from pandas.errors import EmptyDataError
import sqlite3
import signal

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Function call timed out")

def call_function_with_timeout(func, timeout_seconds, *args, **kwargs):
    # Set the signal handler and alarm
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)  # set the alarm

    try:
        result = func(*args, **kwargs)
    except TimeoutError:
        print("Function call timed out!")
        result = None
    finally:
        # Reset the alarm
        signal.alarm(0)
    return result

class R2RSEvaluator(R2RBaseEvaluator):
    def __init__(self):
        super().__init__()
        self.answer_key = "output_value"

        self.pl = "sql"
        self.codeBlockNotFound = f"{self.pl}CodeBlockNotFound"
        self.executionError = f"{self.pl}ExecutionError"
        
    def _evaluate_row(self, y_true, y_pred, test_id, exec_dir):
        y_pred_res = None
        y_true_res = None
        y_pred_res_path = None
        y_true_exec = None
        y_pred_exec = None
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
                # input_csv_df.to_csv("data.csv", index=False)

                conn = sqlite3.connect("data.db")
                input_csv_df.to_sql('table', conn, index=False, if_exists="replace")
                conn.commit()
                conn.close()

                # gt_csv_df = call_function_with_timeout(pd.read_csv, 5, test_csv, keep_default_na=False)
                gt_csv_df = pd.read_csv(test_csv, keep_default_na=False)
                gt_csv_df.loc[gt_csv_df.shape[0]-1, "Output"] = y_true
                y_true_res = gt_csv_df["Output"].tolist()
                try:
                    conn = sqlite3.connect("data.db")
                    y_pred_exec = y_pred.replace(" Table ", " \"Table\" ").replace("input_table", "\"table\"").replace(" table", " \"table\"")
                    # print("-----BEFORE EXECUTE-----")
                    # print(y_pred_exec)
                    # y_pred_res = call_function_with_timeout(pd.read_sql, 5, y_pred_exec, conn)
                    if y_pred_exec.startswith("WITH RECURSIVE"):
                        y_pred_res = None
                    else:
                        y_pred_res = pd.read_sql(y_pred_exec, conn)
                except Exception as e:
                    print(e)
                    y_pred_res = self.executionError
                if isinstance(y_pred_res, pd.DataFrame):
                    if "DERIVED_COLUMN" in y_pred_res.columns:
                        y_pred_res = y_pred_res["DERIVED_COLUMN"].tolist()
                        y_pred_res = [str(x) for x in y_pred_res]
                    else:
                        y_pred_res = "DerivedColumnNotFound"
            except Exception as e:
                print("-----------------------")
                print("Error y_pred")
                print(e)
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
            "y_pred_exec": y_pred_exec,
            "y_true_exec": y_true,
            "y_pred_res_path": y_pred_res_path,
            "y_pred_exec_dir": cur_exec_dir
        }
        return res
    