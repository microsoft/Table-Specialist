import os
import shutil
import json
import pandas as pd
from tqdm import tqdm

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("scala_path", type=str)
parser.add_argument("--exec_dir", '-d', type=str, required=True)
parser.add_argument("--batch_size", type=int, default=200,
                    help="Deprecated: code/table pairs now execute in separate sandboxes")
args = parser.parse_args()

data_scala = pd.read_json(args.scala_path, lines=True)
data_scala = data_scala[:3000]

assert not os.path.exists(args.exec_dir)
os.makedirs(args.exec_dir)

cnt = 0
for idx, d in tqdm(data_scala.iterrows(), total=len(data_scala)):
    d = d.to_dict()
    tbl = d["table"]
    tbl_name = tbl.split("/")[-1].split(".")[0]
    d["SCALANotFoundError"] = True if not d["response"] or "scala" not in d["response"] or not d['response']['scala'] else False

    if not d['SCALANotFoundError']:
        df = pd.read_csv(tbl, dtype=str, keep_default_na=False)
        for r_seed in range(1):
            df_sample = df#.sample(frac=0.5, random_state=r_seed)
            os.makedirs(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}"), exist_ok=True)
            df_sample.to_csv(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "data.csv"), index=False)
            json.dump(d, open(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "info.json"), "w"), indent=4)
            
            with open(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "query.scala"), "w", encoding="utf-8") as f:
                f.write(d['response']['scala'])


            cnt += 1

print(f"Total {cnt} isolated Scala execution cases are prepared.")
