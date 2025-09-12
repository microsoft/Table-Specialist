from collections import defaultdict
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
import utils
import os
from .base_evaluator import BaseEvaluator
import json

class TQAEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__()
        self.answer_key = "answer"
        
    def _evaluate_row(self, y_true, y_pred):
        correct = 0
        if str(y_true).lower() == str(y_pred).lower():
            return {"correct": 1}
        else:
            if type(y_pred) == str:
                try:
                    if "%" in y_pred:
                        y_pred = y_pred.replace("%", "")
                        if round(float(y_true), 2) == round(float(y_pred), 2):
                            return {"correct": 1}
                        
                        y_pred = float(y_pred) / 100
                        if round(float(y_true), 2) == round(float(y_pred), 2):
                            return {"correct": 1}
                    elif "$" in y_pred:
                        y_pred = y_pred.replace("$", "").replace(",", "")
                        if round(float(y_true), 2) == round(float(y_pred), 2):
                            return {"correct": 1}
                except:
                    pass
            else:
                try:
                    if round(float(y_true), 2) == round(float(y_pred), 2):
                        correct = 1
                    else:
                        correct = 0
                except:
                    correct = 0
            
        res = {
            "correct": correct
        }
        return res
    
    def _compute_metric(self, res):
        acc = res["correct"].values.mean()
        metric = {
            "acc": acc
        }
        return metric
        