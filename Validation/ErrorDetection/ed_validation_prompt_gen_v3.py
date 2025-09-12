import json
import pandas as pd
from tqdm import tqdm
import os
import random

def serialize_df(df):
    text = [""]
    # for c in df.columns:
    #     text.append(str(c))
    # text.append("\n")

    # add separating line
    # for c in df.columns:
    #     text.append("---")
    # text.append("\n")
    
    for row in df.values:
        for x in row:
            text.append(str(x))
        text.append("\n")
    return "|".join(text)


input_file_1 = "<PATH-TO-TableSpecialist>/Generation/ErrorDetection/Table2Typo/data/v1/table2typo_v1_web_1st_10K.jsonl.llama3.1-8b.result.jsonl.extracted.jsonl"
input_file_2 = "<PATH-TO-TableSpecialist>/Generation/ErrorDetection/Table2SemanticError/data/v6/table2semantic_v6_web_1st_3K.jsonl.llama3.1-8b.result.jsonl.extracted.jsonl"

df_1 = pd.read_json(input_file_1, orient="records", lines=True)
df_2 = pd.read_json(input_file_2, orient="records", lines=True)

df_1["type"] = df_1["prompt"].apply(lambda x: "typo cell")
# df_2["type"] = df_2["prompt"].apply(lambda x: "erroneous cell")
df_2["type"] = df_2["prompt"].apply(lambda x: "ERROR")

df = pd.concat([df_1[:3000], df_2[:3000]], ignore_index=True)

tables = []
sample_cols = []
distinct_values = []
target_values = []
target_value_types = []
prompts = []

for idx, row in tqdm(df.iterrows(), total=len(df)):
    if row["response"] and "json" in row["response"] and row["response"]["json"] and row["type"] in row["response"]["json"]:
        target_value = row["response"]["json"][row["type"]]
    else:
        continue
    sample_col = row["sample_col"]
    distinct_value = list(row["distinct_value"]) + [target_value]


    for i in range(5):
        distinct_value_copy = distinct_value.copy()
        random.seed(i)
        random.shuffle(distinct_value_copy)
        df_col = pd.DataFrame({sample_col: distinct_value_copy})

        prompt = f"""# Task Description: The table column below is a high-quality real data column. In the unlikely event that you see any one cell that is clearly a data error, either because the cell is a typo/misspelling (e.g., Mississipi that is a misspelling of Mississippi), or because it is a semantic outlier that does not fit in the context of this column (e.g., a city name mixed in a column with country names, etc.), please point it out.

*** Please be aware that cell values that appear unusual are often NOT ERRORS, such as code values (e.g., "mdl-1023"), abbreviations (e.g., "MDX"), out-of-vocabulary words (e.g., foreign languages, or properietary terminologies), etc.. In all those cases, simply DO NOT make any prediction. Users will be very angry if they see incorrect predictions. ***
 
Please return {{"obvious_error": "NULL"}} if you believe the column is a high-quality column. Otherwise, please return any error cell you identified in JSON {{"obvious_error": "<CELL>"}}, ONLY IF you are ABSOLUTELY SURE that <CELL> is erroneous. We will manually verify and you will be punished if it turns out that <CELL> is not erroneous.

Input:
{serialize_df(df_col)}

*** Please be aware that cell values that appear unusual are often NOT ERRORS, such as code values (e.g., "mdl-1023"), abbreviations (e.g., "MDX"), out-of-vocabulary words (e.g., foreign languages, or properietary terminologies), etc.. In all those cases, simply DO NOT make any prediction. Users will be very angry if they see incorrect predictions. ***
 
Please return {{"obvious_error": "NULL"}} if you believe the column is a high-quality column. Otherwise, please return any error cell you identified in JSON {{"obvious_error": "<CELL>"}}, ONLY IF you are ABSOLUTELY SURE that <CELL> is erroneous. We will manually verify and you will be punished if it turns out that <CELL> is not erroneous.

Output:
"""
        tables.append(row["table"])
        prompt = prompt.replace(u"\u00A0", " ")
        prompts.append(prompt)
        sample_cols.append(sample_col)
        distinct_values.append(distinct_value_copy)
        target_values.append(target_value)
        target_value_types.append(row["type"])


data = pd.DataFrame({
    "table": tables,
    "sample_col": sample_cols,
    "distinct_value": distinct_values,
    "target_value": target_values,
    "target_value_type": target_value_types,
    "prompt": prompts
})

save_to = f"data/v3_llama3.1-8b/ed_validation_v3_web_1st_3K_{len(data)}_typo_v1_sem_v6_llama3.1-8b.jsonl"
os.makedirs(os.path.dirname(save_to), exist_ok=True)
assert not os.path.exists(save_to), f"{save_to} already exists"
data.to_json(save_to, orient="records", lines=True)
print(f"Saved to {save_to}")