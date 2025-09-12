import pandas as pd
import os
import argparse
import numpy as np
from datetime import date
import json
from sklearn.metrics import precision_score, recall_score, f1_score
from collections import defaultdict
import utils
import pickle
from evaluate.em_evaluator import EMEvaluator
from evaluate.di_evaluator import DIEvaluator
from evaluate.ed_evaluator import EDEvaluator
from evaluate.hvm_evaluator import HVMEvaluator
from evaluate.r2r_evaluator import R2REvaluator
from evaluate.sm_evaluator import SMEvaluator
from evaluate.cta_evaluator import CTAEvaluator
from evaluate.mcr_evaluator import MCREvaluator
from evaluate.mcc_evaluator import MCCEvaluator
from evaluate.tt_evaluator import TTEvaluator
from evaluate.tm_evaluator import TMEvaluator
from evaluate.tq_evaluator import TQEvaluator
from evaluate.sd_evaluator import SDEvaluator
from evaluate.cf_evaluator import CFEvaluator
from evaluate.re_evaluator import REEvaluator
from evaluate.tf_evaluator import TFEvaluator
from evaluate.ns_evaluator import NSEvaluator
from evaluate.np_evaluator import NPEvaluator
from evaluate.nr_evaluator import NREvaluator
from evaluate.nss_evaluator import NSSEvaluator
from evaluate.r2rp_evaluator import R2RPEvaluator
from evaluate.r2rr_evaluator import R2RREvaluator
from evaluate.r2rs_evaluator import R2RSEvaluator
from evaluate.tqa_evaluator import TQAEvaluator
import time
import shutil

parser = argparse.ArgumentParser()
parser.add_argument("result_dir", type=str)
parser.add_argument("--n_jobs", default=-1, type=int)
parser.add_argument("--debug", action="store_true", default=False)
args = parser.parse_args()


if args.n_jobs < 0:
    args.n_jobs = os.cpu_count()
    
summary_metric = {
    "EntityMatching": "f1",
    "DataImputation": "acc",
    "ErrorDetection": ["prec", "recall", "f1"],
    "HeaderValueMatching": "acc",
    "Row2Row": "acc",
    "Row2RowZeroshot": "acc",
    "Row2RowFewshot": "acc",
    "SchemaMatching": ["prec", "recall", "f1"],
    "ColumnTypeAnnotation": "f1",
    "MissingCellRowSep": "acc",
    "MissingCellRowNoSep": "acc",
    "MissingCellColSep": "acc",
    "MissingCellColNoSep": "acc",
    "TableTransformation": "acc",
    "TableTransformationZeroshot": "acc",
    "TableTransformationFewshot": "acc",
    "SemanticDedup": "f1",
    "RowColumnFiltering": "acc",
    "RowColumnSorting": "acc",
    "RowColumnSwapping": "acc",
    "TableQuestion": "acc",
    "ColumnFinding": "acc",
    "RelationExtraction": "f1",
    "TableFact": "acc",
    "NL2SQL": "acc",
    "NL2Pandas": "acc",
    "NL2R": "acc",
    "NL2SparkScala": "acc",
    "Row2RowPandas": "acc",
    "Row2RowR": "acc",
    "Row2RowSQL": "acc",
    "TableQA": "acc"
}

evaluator_dict = {
    "EntityMatching": EMEvaluator(),
    "DataImputation": DIEvaluator(),
    "ErrorDetection": EDEvaluator(),
    "HeaderValueMatching": HVMEvaluator(),
    "Row2Row": R2REvaluator(),
    "Row2RowFewshot": R2REvaluator(),
    "Row2RowZeroshot": R2REvaluator(),
    "SchemaMatching": SMEvaluator(),
    "ColumnTypeAnnotation": CTAEvaluator(),
    "MissingCellRowSep": MCREvaluator(),
    "MissingCellRowNoSep": MCREvaluator(),
    "MissingCellColSep": MCCEvaluator(),
    "MissingCellColNoSep": MCCEvaluator(),
    "TableTransformation": TTEvaluator(),
    "TableTransformationZeroshot": TTEvaluator(),
    "TableTransformationFewshot": TTEvaluator(),
    "SemanticDedup": SDEvaluator(),
    "RowColumnFiltering": TMEvaluator(),
    "RowColumnSorting": TMEvaluator(),
    "RowColumnSwapping": TMEvaluator(),
    "TableQuestion": TQEvaluator(),
    "ColumnFinding": CFEvaluator(),
    "RelationExtraction": REEvaluator(),
    "TableFact": TFEvaluator(),
    "NL2SQL": NSEvaluator(),
    "NL2Pandas": NPEvaluator(),
    "NL2R": NREvaluator(),
    "NL2SparkScala": NSSEvaluator(),
    "Row2RowPandas": R2RPEvaluator(),
    "Row2RowR": R2RREvaluator(),
    "Row2RowSQL": R2RSEvaluator(),
    "TableQA": TQAEvaluator()
}
    
summary_benchmarks = []
summary_tasks = defaultdict(list)
avg_results_dict = {} # avg_results_dict[task][model_name]
detail_results_dict = {} # detail_results_dict[task][model_name]
error_cnt_dict = {} # error_cnt_dict[task][model_name]

for subfolder in ["metrics", "summary", "csv", "debug"]:
    if os.path.exists(os.path.join(args.result_dir, subfolder)):
        shutil.rmtree(os.path.join(args.result_dir, subfolder))

for jsonl_file in os.listdir(os.path.join(args.result_dir, "preds")):
    print("Evaluating", jsonl_file)
    model_name = jsonl_file[:-6]
    if model_name.find(".jsonl") != -1:
        model_name = model_name[model_name.find(".jsonl")+7:]
    model_name = model_name.replace(".result", "")
    preds = pd.read_json(os.path.join(args.result_dir, "preds", jsonl_file), lines=True)
    preds["task"] = preds["metadata"].apply(lambda x: utils.parse_metadata(x)["task"])
    
    summary_benchmark_list = []
    for task, preds_group in preds.groupby("task"):
        # if task != "SemanticDedup":
        #     continue
        if task not in avg_results_dict:
            avg_results_dict[task] = defaultdict(list)
            detail_results_dict[task] = defaultdict(list)
            error_cnt_dict[task] = defaultdict(list)
        print(task)
        debug_dir = utils.makedir([args.result_dir, "debug", task, model_name]) if args.debug else None
        evaluator = evaluator_dict[task]
        avg_results, detail_results, error_cnt = evaluator.evaluate(preds_group, debug_dir=debug_dir, n_jobs=args.n_jobs)
        # avg_results.to_excel(utils.makedir([args.result_dir, "metrics", task], f"{model_name}_avg.xlsx"))
        # detail_results.to_excel(utils.makedir([args.result_dir, "metrics", task], f"{model_name}_details.xlsx"))
        avg_results_dict[task][model_name].append(avg_results)
        detail_results_dict[task][model_name].append(detail_results)
        if error_cnt is not None:
            error_cnt["model"] = model_name
            error_cnt_dict[task][model_name].append(error_cnt)
        
        if not isinstance(summary_metric[task], list):
            summary_metric[task] = [summary_metric[task]]
        
        summ = []
        for metric in summary_metric[task]:
            summ_metric = avg_results[evaluator.merge_keys + [metric]].rename(columns={metric: f"{model_name}"})
            summ_metric["metric"] = metric
            summ.append(summ_metric)
        summ = pd.concat(summ, axis=0)
        
        # average over benchmark
        summ_benchmark = summ.groupby(["method", "benchmark", "note", "metric"], as_index=False).mean(numeric_only=True)
        summ_benchmark["task"] = task
        summary_benchmark_list.append(summ_benchmark)
        
        # save datasets results
        summ_task = summ.set_index(evaluator.merge_keys + ["metric"])
        summary_tasks[task].append(summ_task)
        
    summary_benchmark_df = pd.concat(summary_benchmark_list, axis=0)
    summary_benchmark_df = summary_benchmark_df.sort_values(by=["task", "method", "benchmark", "note", "metric"]).set_index(["task", "method", "benchmark", "note", "metric"])
    summary_benchmarks.append(summary_benchmark_df)

for task in avg_results_dict:
    for model in avg_results_dict[task]:
        avg_results_dict[task][model] = pd.concat(avg_results_dict[task][model], axis=0)
        avg_results_dict[task][model].to_excel(utils.makedir([args.result_dir, "metrics", task], f"{model}_avg.xlsx"))
        detail_results_dict[task][model] = pd.concat(detail_results_dict[task][model], axis=0)
        detail_results_dict[task][model].to_excel(utils.makedir([args.result_dir, "metrics", task], f"{model}_details.xlsx"))

        error_cnt_dict[task][model] = pd.concat(error_cnt_dict[task][model], axis=0)
        # error_cnt_dict[task][model].to_excel(utils.makedir([args.result_dir, "metrics", task], f"{model}_error_cnt.xlsx"))
    error_cnt = pd.concat(error_cnt_dict[task].values(), axis=0)
    if error_cnt.shape[0] > 0:
        error_cnt = error_cnt.set_index(["method", "benchmark", "note", "model"])
        error_cnt.to_excel(utils.makedir([args.result_dir, "metrics", task], "error_cnt.xlsx"))


groups = {}
for df in summary_benchmarks:
    # Using frozenset to ensure the columns can be used as a dictionary key
    key = frozenset(df.columns)
    if key not in groups:
        groups[key] = []
    groups[key].append(df)
concatenated_dfs = [pd.concat(group, axis=0) for group in groups.values()]

summary_benchmarks = pd.concat(concatenated_dfs, axis=1)
summary_benchmarks.to_excel(utils.makedir([args.result_dir, "summary"], f"overall_average.xlsx"))
summary_benchmarks.to_csv(utils.makedir([args.result_dir, "csv"], f"overall_average.csv"))
for task, summary in summary_tasks.items():
    res = pd.concat(summary, axis=1)
    res.to_excel(utils.makedir([args.result_dir, "summary"], f"{task}_summary.xlsx"))
    res.to_csv(utils.makedir([args.result_dir, "csv"], f"{task}_summary.csv"))

