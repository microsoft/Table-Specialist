import json
import pandas as pd
from io import StringIO
import os
import random

input_file = "<PATH-TO-TableSpecialist>/Generation/SchemaMatching/Table2MappedTable/data/v3/table2mappedtable_v3_1st_3K.jsonl.llama3.1-8b.result.jsonl.extracted.jsonl"
data = pd.read_json(input_file, lines=True)
print(input_file)
print(data.shape)

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

def fromMarkdown(rst: str) -> pd.DataFrame:
    df = pd.read_table(StringIO(rst), sep="|", index_col=None).dropna(
            axis=1,
            how='all'
        ).iloc[1:].reset_index(drop=True)
    df.columns = df.columns.str.strip()
    return df

tables = []
prompts = []
tbl_mds = []
column_mappings = []

cnt_markdown_error = 0
cnt_json_error = 0
for i, row in data.iterrows():
    if not row["response"]["tbl_md"] or not row["response"]["json"]:
        continue

    table = row["table"]
    df_A = pd.read_csv(table)
    try:
        df_B = fromMarkdown(row["response"]["tbl_md"])
    except Exception as e:
        # print(e)
        cnt_markdown_error += 1
        continue

    col_mappings = row["response"]["json"]["column_mappings"]

    try:
        assert isinstance(col_mappings, list)
        for [col_a, col_b] in col_mappings:
            assert col_a in df_A.columns, f"col_a: {col_a} not in {df_A.columns}"
            assert col_b in df_B.columns if col_b != None else True, f"col_b: {col_b} not in {df_B.columns}"
    except Exception as e:
        # print(type(e))
        # print(e)
        # print(col_mappings)
        cnt_json_error += 1
        continue
    # print("=====================================")
    # print(df_A.head())
    # print(df_B.head())
    # print(col_mappings)

    for i in range(5):
        col_a_s = df_A.columns.to_list()
        col_b_s = df_B.columns.to_list()
        random.seed(i)
        random.shuffle(col_a_s)
        random.shuffle(col_b_s)

        df_A_cp = df_A.copy()
        df_B_cp = df_B.copy()
        df_A_cp = df_A_cp[col_a_s]
        df_B_cp = df_B_cp[col_b_s]
        df_A_cp = df_A_cp.sample(frac=1, random_state=i).reset_index(drop=True)
        df_B_cp = df_B_cp.sample(frac=1, random_state=i).reset_index(drop=True)

        prompt = f"""# Task Description: Please identify the matching columns between Table A and Table B. For each column in Table A, specify the corresponding column in Table B. If a column in A has no corresponding column in Table B, you can map it to None. Represent each column mapping using a pair of column headers in a list, i.e., [Table A Column, Table B column or None]. Provide the mapping for each column in Table A and return all mappings in a list. Return the final result as JSON in the format {{"column_mappings": "<a list of column pairs>"}}.

## Input:
Table A:
{serialize_df(df_A_cp)}

Table B:
{serialize_df(df_B_cp)}

Return the final result as JSON in the format {{"column_mappings": "<a list of column pairs>"}}.

## Output:
"""
        prompts.append(prompt)
        tables.append(table)
        tbl_mds.append(row["response"]["tbl_md"])
        column_mappings.append(col_mappings)
    #     print("------------------------------------")
    #     print(prompt)
    # exit()


df_save = pd.DataFrame({"table": tables, "prompt": prompts, "column_mappings": column_mappings, "tbl_md": tbl_mds})
save_to = f"data/v2_llama3.1-8b/sm_validation_prompt_v2_v3_1st_3K_{len(df_save)}_llama3.1-8b.jsonl"
os.makedirs(os.path.dirname(save_to), exist_ok=True)
df_save.to_json(save_to, orient="records", lines=True)
print(f"Saved to {save_to}")

print(f"Markdown error: {cnt_markdown_error}")
print(f"JSON error: {cnt_json_error}")