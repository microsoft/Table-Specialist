import json
import pandas as pd
from tqdm import tqdm
import os
import random
import re

input_path = "<PATH-TO-TableSpecialist>/Generation/Row2RowTransformation/Table2MergedColumn/exec/V3_Web_2nd_30K"
print(input_path)
file_list = [os.path.join(input_path, sub_dir, "result.csv") for sub_dir in os.listdir(input_path) if os.path.exists(os.path.join(input_path, sub_dir, "result.csv"))]

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


string_verb = [
    "Concatenate", "Repeat", "Extract", "Index/slice", "Replace", "Count", "Change casing", "Split/parse", "Convert encoding"
]

string_noun = [
    "digits", "letters", "punctuation", "words", "characters"
]

string_noun_prefix = ["all", "some"]

numeric_venb_1 = [
    "Convert into different unit (length, weight, time, etc.)", 
    "Floor/truncate", 
    "Convert into different base (hexidecimal, Octal, binary)", 
    "Convert into roman numerals"
]

numeric_formatings = [
    "round to <K> decimal places",
    "format to <K> significant figures (Significant figures are the digits that carry meaning contributing to its precision. In a floating-point number, significant figures include all digits from the first non-zero digit on the left to the last digit on the right)",
    "no rounding or formatting required"
]


def random_transformations(col_type):
    if col_type == "Numeric":
        op = random.choice(numeric_venb_1)
        format = random.choice(numeric_formatings)
        if "<K>" in format:
            format = format.replace("<K>", str(random.randint(1, 5)))
        return f"{op}, then {format}" if format != "no rounding or formatting required" else op
    elif col_type == "String":
        return f"{random.choice(string_verb)} {random.choice(string_noun_prefix)} {random.choice(string_noun)}"
    else:
        raise ValueError("Invalid column type")
    
def has_digit(s):
    # Regular expression to match any digit
    regex = re.compile(r'\d')
    # Search for a digit in the string
    return bool(regex.search(s))

tables = []
prompts = []
sample_cols = []
sample_col_values = []
transformatiom_reqs = []

for tbl in tqdm(file_list):
    df = pd.read_csv(tbl, dtype=str, keep_default_na=False)
    if "MergedColumn" not in df.columns:
        continue
    sample_col = "MergedColumn"
    if df[sample_col].nunique() < 10:
        continue
    
    sampled_values = pd.Series(df[sample_col].unique()).sample(10, random_state=42).reset_index(drop=True)
    df_sample = pd.DataFrame({sample_col: sampled_values})
    col_concat = df_sample.fillna("nan")[sample_col].str.cat(sep=" ")
    if has_digit(col_concat):
        col_type = "Numeric" if random.randint(0, 10) <= 5 else "String"
    else:
        col_type = "String"
    transformatiom_req = random_transformations(col_type)

    prompt = f"""Instruction:
You are given a table below with a single column, please produce a derived column that can be generated from the column using a transformation program. In this specific case, your transformation should:

Perform a {col_type} transformation that:
{transformatiom_req}

If the suggested transformation above is not feasible on the table column, please return your transformation plan in a JSON object as {{"plan": "NULL"}} and then return two empty code blocks for Pandas and R.

If the suggested transformation is feasible on the table column, please (1) first explain your plan in terms of how to transform the values in the column, in a JSON object as {{"plan": "<PLAN>"}}. Please then (2) return its Python implementation and R implementation, using two *code blocks*. Remember, the new derived column should always be named as "derived_column" in your python Pandas code and R code.

Please produce your Python Pandas code that can run on this table, to generate the derived column. To read this table, you can assume that the input table is always stored in a file named "data.csv", so always start your Python code with the boilerplate prefix:
"import pandas as pd
df = pd.read_csv('data.csv')
"

You should always generate your derived column in a column named "derived_column" in the final dataframe. Please always save your final dataframe into a file named "result.csv".
Return the final result as a markdown code block, as ```python <PYTHON-CODE>```

Similarly, please also produce your R code that can run on this table, to generate the derived column. To read this table, you can assume that the input table is always stored in a file named "data.csv", so always start your R code with the boilerplate prefix:
"library(dplyr)

data <- read.csv("data.csv", check.names = FALSE)
"

You should always generate your derived column in a column named "derived_column" in the final dataframe. Please always save your final dataframe into a file named "result.csv".
Return the final result as a markdown code block, as ```r <R-CODE>```

**Input table:**
{serialize_df(df_sample)}

If the suggested transformation above is not feasible on the table column, please return your transformation plan in a JSON object as {{"plan": "NULL"}} and then return two empty code blocks for Pandas and R.

If the suggested transformation is feasible on the table column, please (1) first explain your plan in terms of how to transform the values in the column, in a JSON object as {{"plan": "<PLAN>"}}. Please then (2) return its Python implementation and R implementation, using two *code blocks*. Remember, the new derived column should always be named as "derived_column" in your python Pandas code and R code.

Output:
"""
    prompt = prompt.replace(u"\u00A0", " ")
    tables.append(tbl)
    prompts.append(prompt)
    sample_cols.append(sample_col)
    sample_col_values.append(sampled_values.to_list())
    transformatiom_reqs.append(transformatiom_req)

df = pd.DataFrame({"table": tables, "prompt": prompts, "sample_col": sample_cols, "sample_col_value": sample_col_values, "transformation_req": transformatiom_reqs})
print(df.shape)

save_to = f"data/V9/table2derivedcolumns_V3_Web_2nd_30K_V9_{df.shape[0]}.jsonl"
os.makedirs(os.path.dirname(save_to), exist_ok=True)
df.to_json(save_to, orient="records", lines=True)
print(f"Saved to {save_to}")
# for i in range(0, 5):
#     print(df.iloc[i]["prompt"])
#     print("-------------------")