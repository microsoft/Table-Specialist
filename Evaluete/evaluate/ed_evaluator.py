from collections import defaultdict
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
import utils
import os
from .base_evaluator import BaseEvaluator
from multiprocessing import Pool

class EDEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__()
        self.group_keys = ["method", "benchmark", "note", "seed"]
        self.merge_keys = ["method", "benchmark", "note"]
        self.err_merge_keys = ["method", "benchmark", "note"]
        # self.answer_key = "likely erroneous cell"
        self.answer_key = "obvious_error"
    
    def preprocess(self, y):
        if y == "JSONParsingError" or y is None:
            y = []
        elif type(y) == str:
            if y.lower() == "null":
                y = []
            else:
                y = [y]
        return set(y)
    
    def _evaluate_row(self, y_true, y_pred):
        y_true_set = set(y_true)
        y_pred_set = self.preprocess(y_pred)

        if len(y_true_set) == 0:
            return {
                "recall" : None,
                "precision" : None if len(y_pred_set) == 0 else 0,
            }
        
        if len(y_pred_set) == 0:
            return {
                "recall" : 0,
                "precision" : None,
            }

        tp_set = y_true_set.intersection(y_pred_set)
        
        res = {
            "precision" : len(tp_set) / len(y_pred_set) if len(y_pred_set) > 0 else 0,
            "recall" : len(tp_set) / len(y_true_set)
        }
        return res
    
    def _compute_metric(self, res):        
        prec = res["precision"].dropna().mean()
        recall = res["recall"].dropna().mean()
        if not prec == 0 or not recall == 0:
            f1 = 2 * prec * recall / (prec + recall)
        else:
            f1 = 0
        metric = {
            "prec": prec,
            "recall": recall,
            "f1": f1
        }
        return metric
    
    def _get_pred(self, label):
        gt = self.extract_json_answer(label, "obvious_error")
        # if gt == "JSONParsingError":
            # print(label)
            # raise Exception("Parsing Error on ground truth")
        return gt

    def parse_raw_result(self, raw_result, n_jobs=1):
        result = []
        for _, row in raw_result.iterrows():
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
            if self.extract_json_answer(row_res["completion"], "corrected cell") == "NULL":
                row_res["y_pred"] = "NULL"
            
            # evaluate each row
            row_eval = self._evaluate_row(row_res["y_gt"], row_res["y_pred"])
            for k, v in row_eval.items():
                row_res[k] = v
                
            result.append(row_res)
        result = pd.DataFrame(result)
        return result