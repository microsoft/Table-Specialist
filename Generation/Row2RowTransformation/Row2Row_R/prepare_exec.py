import os
import shutil
import json
import pandas as pd
from tqdm import tqdm

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("path", type=str)
parser.add_argument("--exec_dir", '-d', type=str, required=True)
args = parser.parse_args()

data = pd.read_json(args.path, lines=True)

pl = "r"
suffix = "R"

assert not os.path.exists(args.exec_dir)
os.makedirs(args.exec_dir)

cnt = 0
for idx, d in tqdm(data.iterrows(), total=len(data)):
    d = d.to_dict()
    tbl = d["table"]
    tbl_name = tbl.split("/")[-1].split(".")[0]
    d[f"{pl.upper()}NotFoundError"] = True if not d["response"] or pl not in d["response"] or not d['response'][pl] else False

    if not d[f"{pl.upper()}NotFoundError"]:
        os.makedirs(os.path.join(args.exec_dir, f"exec_{idx}"))
        shutil.copyfile(tbl, os.path.join(args.exec_dir, f"exec_{idx}", "data.csv"))
        shutil.copyfile(tbl.replace("data.csv", "result_python.csv"), os.path.join(args.exec_dir, f"exec_{idx}", "gt.csv"))
        json.dump(d, open(os.path.join(args.exec_dir, f"exec_{idx}", "info.json"), "w"), indent=4)
        with open(os.path.join(args.exec_dir, f"exec_{idx}", f"query.{suffix}"), "w") as f:
            f.write(d['response'][pl])

        cnt += 1

print(f"Generated {cnt} executions in {args.exec_dir}")