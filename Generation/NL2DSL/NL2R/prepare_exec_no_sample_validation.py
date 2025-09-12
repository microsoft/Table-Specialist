import os
import shutil
import json
import pandas as pd
from tqdm import tqdm

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("r_path", type=str)
parser.add_argument("--exec_dir", '-d', type=str, required=True)
args = parser.parse_args()

data_r = pd.read_json(args.r_path, lines=True)


assert not os.path.exists(args.exec_dir)
os.makedirs(args.exec_dir)

cnt = 0
for idx, d in tqdm(data_r.iterrows(), total=len(data_r)):
    d = d.to_dict()
    tbl = d["table"]
    tbl_name = tbl.split("/")[-1].split(".")[0]
    d["RNotFoundError"] = True if not d["response"] or "r" not in d["response"] or not d['response']['r'] else False

    if not d['RNotFoundError']:
        df = pd.read_csv(tbl, dtype=str, keep_default_na=False)
        for r_seed in range(1):
            df_sample = df#.sample(frac=0.5, random_state=r_seed)
            os.makedirs(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}"), exist_ok=True)
            df_sample.to_csv(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "data.csv"), index=False)
            json.dump(d, open(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "info.json"), "w"), indent=4)
            
            with open(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "query.r"), "w") as f:
                f.write(d['response']['r'])

        cnt += 1

print(f"Generated {cnt} executions in {args.exec_dir}")