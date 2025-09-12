import json
import pandas as pd
from tqdm import tqdm
import os
import random

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
sample_cols = []
distinct_values = []
prompts = []

for tbl in tqdm(file_list):
    df = pd.read_csv(tbl, keep_default_na=False)
    sample_col = random.choice(df.columns)
    distinct_value = df[sample_col].unique()
    df_col = pd.DataFrame({sample_col: distinct_value})

    prompt = f"""# Task Description: Given the table column below, please brainstorm an erroneous cell <CELL>, which if added into the column, would be considered as an outlier or data quality issue in the context of this column.

Please create a <CELL> that would be a typo/misspelling of an existing value in this column. Please make sure that the typo you create should look realistic that may actually occur in a real column (and not some obvious outliers like "12345").


Input:
{serialize_df(df_col)}

Please generate a new cell not in the column, which if added to the column, would be considered as a typo in the column. Return a JSON in the format {{"typo cell": "<CELL>"}}.

Output:
"""
    tables.append(tbl)
    prompt = prompt.replace(u"\u00A0", " ")
    prompts.append(prompt)
    sample_cols.append(sample_col)
    distinct_values.append(distinct_value)
    if len(tables) == 9000:
        break


data = pd.DataFrame({"table": tables, "sample_col": sample_cols, "distinct_value": distinct_values, "prompt": prompts})
data = data[6000:]
print(data.shape)
save_to = "data/v1/table2typo_v1_web_3rd_3K.jsonl"
data.to_json(save_to, orient="records", lines=True)