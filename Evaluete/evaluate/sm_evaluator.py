from .base_evaluator import BaseEvaluator
import numpy as np
import utils
import pandas as pd

class SMEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__()
        self.answer_key = "column_mappings"
        
    def parse_matching(self, label):
        gt = {}
        if type(label) != list:
            return gt
        for x in label:
            if not x or len(x) != 2:
                # print(x)
                continue
            source, target = x
            if target is None:
                target = "None"
            if source is None:
                source = "None"
            source = str(source).strip()
            target = str(target).strip()
            if source == "nan":
                source = "None"
            if target == "nan":
                target = "None"
            if len(target) == 0:
                continue
            if source == "None" or target == "None":
                continue
            gt[source] = target
        return gt
        
    def _evaluate_row(self, y_true, y_pred):
        y_true = self.parse_matching(y_true)
        y_pred = self.parse_matching(y_pred)
        # no rand
        count = 0
        for k in y_pred.keys():
            if k in y_true and y_pred[k] == y_true[k]:
                count += 1
        if len(y_true) == 0:
            recall = None
        else:
            recall = count / len(y_true)
        if len(y_pred) == 0:
            precision = None
        else:
            precision = count / len(y_pred)
        res = {
            "recall": recall,
            "precision": precision
        }
        return res
    
    def _compute_metric(self, res):
        acc = res["recall"].mean()
        prec = res["precision"].mean()
        if not acc == 0 and not prec == 0:
            f1 = 2 * acc * prec / (acc + prec)
        else:
            f1 = 0
        # f1 = 2 * acc * prec / (acc + prec)
        metric = {
            "recall": acc,
            "prec": prec,
            "f1": f1
        }
        return metric
    
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
            row_res["y_pred_eval"] = self.parse_matching(row_res["y_pred"])
            row_res["y_gt_eval"] = self.parse_matching(row_res["y_gt"])
            
            # evaluate each row
            row_eval = self._evaluate_row(row_res["y_gt"], row_res["y_pred"])
            for k, v in row_eval.items():
                row_res[k] = v
                
            result.append(row_res)
        result = pd.DataFrame(result)
        return result