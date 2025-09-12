import json
import pandas as pd
from tqdm import tqdm
import os
import random
import re
import shutil

file_list = [] # Assign file_list with the paths of your table corpus
random.seed(42)
random.shuffle(file_list)
print(len(file_list))

def serialize_df(df):
    text = [""]
    for c in df.columns:
        text.append(str(c))
    text.append("\n")

    # add separating line
    for c in df.columns:
        text.append("---")
    text.append("\n")
    
    for row in df.values:
        for x in row:
            text.append(str(x))
        text.append("\n")
    return "|".join(text)

tables = []

target_folder = "<PATH-TO-TableSpecialist>/Generation/Row2RowTransformation/Table2MergedColumn/exec/V3_Web_2nd_30K"
os.mkdir(target_folder)

for idx, tbl in tqdm(enumerate(file_list[30000:60000])):
    df = pd.read_csv(tbl, dtype=str, keep_default_na=False)
    K = random.randint(1, 3)
    sampled_columns = random.sample(df.columns.tolist(), K)
    punctuations = [" , ", " ", " - "]
    punctuation = random.choice(punctuations)
    df["MergedColumn"] = df[sampled_columns].apply(lambda x: punctuation.join(x), axis=1)
    cur_dir = os.path.join(target_folder, f"exec_{idx}")
    os.mkdir(cur_dir)
    shutil.copy(tbl, os.path.join(cur_dir, "data.csv"))
    df[["MergedColumn"]].to_csv(os.path.join(cur_dir, "result.csv"), index=False)
    # print(df["MergedColumn"])
    # exit()
    