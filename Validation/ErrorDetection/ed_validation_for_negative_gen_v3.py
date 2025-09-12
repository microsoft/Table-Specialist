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


file_list = [] # Assign file_list with the paths of your table corpus
random.seed(42)
random.shuffle(file_list)
print(len(file_list))

tables = []
sample_cols = []
distinct_values = []
prompts = []

file_list = file_list[:1000]
for file in tqdm(file_list):
    df_tbl = pd.read_csv(file, keep_default_na=False)

    cols = random.sample(df_tbl.columns.to_list(), min(2, len(df_tbl.columns)))

    for sample_col in cols:
        distinct_value = df_tbl[sample_col].unique()
        df_col = pd.DataFrame({sample_col: distinct_value})


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
            tables.append(file)
            prompt = prompt.replace(u"\u00A0", " ")
            prompts.append(prompt)
            sample_cols.append(sample_col)
            distinct_values.append(distinct_value_copy)

data = pd.DataFrame({
    "table": tables,
    "sample_col": sample_cols,
    "distinct_value": distinct_values,
    "prompt": prompts
})

save_to = f"data/v3_llama3.1-8b/ed_validation_for_negative_v3_web_1st_3K_{len(data)}.jsonl"
os.makedirs(os.path.dirname(save_to), exist_ok=True)
data.to_json(save_to, orient="records", lines=True)
print(f"Saved to {save_to}")