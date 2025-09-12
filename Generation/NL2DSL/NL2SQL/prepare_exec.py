import os
import shutil
import json
import pandas as pd
from tqdm import tqdm

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("sql_path", type=str)
parser.add_argument("--exec_dir", '-d', type=str, required=True)
parser.add_argument("--batch_size", type=int, default=200)
args = parser.parse_args()

data_sql = pd.read_json(args.sql_path, lines=True)
# data_sql = data_sql[:3000]

assert not os.path.exists(args.exec_dir)
os.makedirs(args.exec_dir)

cnt = 0
sql_code_s = []
for idx, d in tqdm(data_sql.iterrows(), total=len(data_sql)):
    d = d.to_dict()
    tbl = d["table"]
    tbl_name = tbl.split("/")[-1].split(".")[0]
    d["SQLNotFoundError"] = True if not d["response"] or "sql" not in d["response"] or not d['response']['sql'] else False

    if not d['SQLNotFoundError']:
        df = pd.read_csv(tbl, dtype=str, keep_default_na=False)
        for r_seed in range(10):
            df_sample = df.sample(frac=0.5, random_state=r_seed)
            os.makedirs(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}"), exist_ok=True)
            df_sample.to_csv(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "data.csv"), index=False)
            json.dump(d, open(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "info.json"), "w"), indent=4)
            
            with open(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "query.sql"), "w") as f:
                f.write(d['response']['sql'])

            cnt += 1

print(f"Generated {cnt} executions in {args.exec_dir}")