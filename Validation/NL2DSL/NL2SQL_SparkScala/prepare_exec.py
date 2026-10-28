import os
import shutil
import json
import pandas as pd
from tqdm import tqdm

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--sql_path", '-s', type=str, required=True)
parser.add_argument("--scala_path", '-ss', type=str, required=True)
parser.add_argument("--exec_dir", '-d', type=str, required=True)
parser.add_argument("--batch_size", type=int, default=200,
                    help="Deprecated: code/table pairs now execute in separate sandboxes")
args = parser.parse_args()

data_scala = pd.read_json(args.scala_path, lines=True)
data_sql = pd.read_json(args.sql_path, lines=True)

data_sql_scala = pd.merge(data_sql, data_scala, on=['table', 'question'], how='inner', suffixes=('_sql', '_scala'))
print(f"Total {len(data_sql_scala)} pairs are found.")

assert not os.path.exists(args.exec_dir)
os.makedirs(args.exec_dir)

cnt = 0
for idx, d in tqdm(data_sql_scala.iterrows(), total=len(data_sql_scala)):
    d = d.to_dict()
    tbl = d["table"]
    tbl_name = tbl.split("/")[-1].split(".")[0]
    d["SQLNotFoundError"] = True if not d["response_sql"] or "sql" not in d["response_sql"] or not d['response_sql']['sql'] else False
    d["SCALANotFoundError"] = True if not d["response_scala"] or "scala" not in d["response_scala"] or not d['response_scala']['scala'] else False

    if not d["SQLNotFoundError"] and not d['SCALANotFoundError']:
        df = pd.read_csv(tbl, dtype=str, keep_default_na=False)
        for r_seed in range(10):
            df_sample = df.sample(frac=0.5, random_state=r_seed)
            os.makedirs(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}"), exist_ok=True)
            df_sample.to_csv(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "data.csv"), index=False)
            json.dump(d, open(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "info.json"), "w"), indent=4)
            
            with open(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "query.scala"), "w", encoding="utf-8") as f:
                f.write(d['response_scala']['scala'])
            with open(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "query.sql"), "w") as f:
                f.write(d['response_sql']['sql'])


            cnt += 1

print(f"Total {cnt} isolated Scala execution cases are prepared.")
