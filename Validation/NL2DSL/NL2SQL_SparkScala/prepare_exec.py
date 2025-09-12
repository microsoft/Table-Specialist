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
parser.add_argument("--batch_size", type=int, default=200)
args = parser.parse_args()

data_scala = pd.read_json(args.scala_path, lines=True)
data_sql = pd.read_json(args.sql_path, lines=True)

data_sql_scala = pd.merge(data_sql, data_scala, on=['table', 'question'], how='inner', suffixes=('_sql', '_scala'))
print(f"Total {len(data_sql_scala)} pairs are found.")

assert not os.path.exists(args.exec_dir)
os.makedirs(args.exec_dir)

cnt = 0
scala_code_s = []
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
            
            with open(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "query.scala"), "w") as f:
                f.write(d['response_scala']['scala'])
            with open(os.path.join(args.exec_dir, f"exec_{idx}_{r_seed}", "query.sql"), "w") as f:
                f.write(d['response_sql']['sql'])


            # prepare scala batch run
            scala_code = d['response_scala']['scala']
            exec_dir_abs = os.path.abspath(args.exec_dir)
            data_path = os.path.join(exec_dir_abs, f"exec_{idx}_{r_seed}", "data.csv")
            scala_code = scala_code.replace("data.csv", data_path)
            tgt_path = os.path.join(exec_dir_abs, f"exec_{idx}_{r_seed}", "result_scala")
            scala_code = scala_code.replace(""".write.option("header", "true").csv("result")""", f""".write.option("header", "true").csv("{tgt_path}")""")
            scala_code_s.append(scala_code)
            cnt += 1

scala_lists = []
cur_list = []
for scala_code in scala_code_s:
    cur_list.append(scala_code)
    if len(cur_list) == args.batch_size:
        scala_lists.append(cur_list)
        cur_list = []
if len(cur_list) > 0:
    scala_lists.append(cur_list)

assert len(scala_code_s) == sum([len(x) for x in scala_lists])

for i, scala_list in enumerate(scala_lists):
    with open(f"{args.exec_dir}/all_scala_code_{i}.scala", "w") as outfile:
        for scala_code in scala_list:
            outfile.write(scala_code + '\n:reset\n')
        outfile.write(":quit\n")
print(f"Total {len(scala_code_s)} scala code are generated in {len(scala_lists)} files.")
    
print(f"Total {cnt} execution pairs are generated.")