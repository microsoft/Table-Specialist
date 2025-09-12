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
prompts = []
drop_cols_s = []

file_list = file_list[:3000]
for tbl in tqdm(file_list, ncols=100):
    df = pd.read_csv(tbl, keep_default_na=False)
    drop_col_num = min(3, len(df.columns) // 2)
    if drop_col_num > 0:
        drop_cols = random.sample(df.columns.tolist(), drop_col_num)
        df = df.drop(columns=drop_cols)
    else:
        drop_cols = []
    prompt = f"""## Instruction:
Given the Table A shown below, please generate a new table Table B, so that *some* (but not all) of the generated columns in Table B can "map" to *some* (but not all) of columns in Table A, in the sense that they will refer to the same semantic concepts, such that they can "map" to each other.

When you generate new column names in Table B, please make sure that the new column names are different from the original column names in Table A.

When you generate new data values in Table B, please also make sure that you generate new data values not found in Table A.

After you generate Table B, please show how columns in Table A can map to columns in Table B. For each column in Table A, specify the corresponding column in Table B. If a column in A has no corresponding column in Table B, you can map it to None. Represent each column mapping using a pair of column headers in a list, i.e., [Table A Column, Table B column or None]. Provide the mapping for each column in Table A and return all mappings in a list. Return the final result as JSON in the format {{"column_mappings": "<a list of column pairs>"}}.

## Input:

Table A:
{serialize_df(df)}

Please first return Table B in markdown format.
 
Please then return the column mapping result between Table A and Table B, using the following JSON format {{"column_mappings": "<a list of column pairs>"}}.

## Output:
"""
    tables.append(tbl)
    prompt = prompt.replace(u"\u00A0", " ")
    prompts.append(prompt)
    drop_cols_s.append(drop_cols)


data = pd.DataFrame({"table": tables, "prompt": prompts})
save_to = "data/v3/table2mappedtable_v3_1st_3K.jsonl"
os.makedirs(os.path.dirname(save_to), exist_ok=True)
data.to_json(save_to, orient="records", lines=True)
print(f"Saved to {save_to}")