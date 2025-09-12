import json
import pandas as pd
import os
from tqdm import tqdm

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

src_folder = "<PATH-TO-TableSpecialist>/Generation/Row2RowTransformation/Table2DerivedColumn/exec/V3_Web_1st_30K_V9_24659_llama3.1-8b_ALL"
print(src_folder)

tables = []
prompts = []
derived_columns = []
transform_reqs = []

for d in tqdm(os.listdir(src_folder), ncols=50):
    cur_folder = os.path.join(src_folder, d)
    if not os.path.exists(os.path.join(cur_folder, "DERIVED_COLUMN_NON_TRIVIAL_FLAG")):
        continue
    with open(os.path.join(cur_folder, "info.json")) as f:
        info = json.load(f)
        # !!! for v10, 11
        sample_col = info["sample_col"]
        # sample_col = "Col_0"
    df_data = pd.read_csv(os.path.join(cur_folder, "data.csv"))
    df_derived_column = pd.read_csv(os.path.join(cur_folder, "result_python.csv"))

    df = pd.DataFrame()
    df[sample_col] = df_data[sample_col]
    df["DERIVED_COLUMN"] = df_derived_column["derived_column"]

    prompt = """# Task description: The task of row-to-row transformation using examples, is to perform data transformation using table columns, to produce a new "DERIVED_COLUMN" in the table.
 
The task of "program-by-example" or "transform data by-example", is to use a few given example output values in the new "DERIVED_COLUMN", to infer the underlying transformation program that was used to derive the given output values in the "DERIVED_COLUMN". This is also known as program-synthesis or program-by-example in the research literature.
 
Given the **Input table** shown below, we want to perform data transformations on this Input Table, to produce a **Desired Output Table**, with the new "DERIVED_COLUMN" shown as the rightmost column of the **Desired Output Table**.
 
Please inspect the given output examples in the "DERIVED_COLUMN" of the **Desired Output Table**, to identify the transformation program that can be used to produce the "DERIVED_COLUMN" using columns in the **Input table**. Please generate Python Pandas code for the transformation that can execute on the **Input table**, to produce an output column that can exactly match the given output examples in the "DERIVED_COLUMN".
 

 pay close attention to the format and the details of the given output examples in the "DERIVED_COLUMN", to make sure that your code will generate output values exactly matching the given examples, in terms of style, format, and casing.

To read this table, you can assume that the input table is always stored in a file named "data.csv", and always read everything as string (using "dtype=str"). So always start your Python code with the boilerplate prefix:
"import pandas as pd
df = pd.read_csv('data.csv', dtype=str)
"

For numerical computation, please use Python Decimal class to avoid floating point precision issues, so always include "from decimal import Decimal" at the beginning of your code.

Please do not hard code your transformation program (e.g., if row id == 1, return output-value-1, etc.). Please produce transformation programs that can *generalize* to new data rows from the same table, that are not shown below in the interest of space.
Your Python Pandas code should always generate your target column in a column named "DERIVED_COLUMN" in the final dataframe. Please always save your final dataframe with this  "DERIVED_COLUMN" into a file named "result.csv" with header and no index column.

**Input table:**
""" + serialize_df(df_data.head(3)) + """

**Desired Output Table:**
""" + serialize_df(df.head(3)) + """

No explanation, return the final result as a markdown code block, as ```python <PYTHON-CODE>```.
Output:
"""
    tables.append(os.path.join(cur_folder, "data.csv"))
    prompts.append(prompt)
    derived_columns.append(df["DERIVED_COLUMN"].tolist())
    transform_reqs.append(info["transformation_req"])

df = pd.DataFrame({"table": tables, "prompt": prompts, "derived_column": derived_columns, "transformation_req": transform_reqs})
print(df.shape)
save_to = f"data/v5_llama3.1-8b/row2row_pandas_v5_webtable_V3_Web_1st_30K_V9_24659_llama3.1-8b_ALL_{len(df)}.jsonl"
os.makedirs(os.path.dirname(save_to), exist_ok=True)
assert not os.path.exists(save_to)
df.to_json(save_to, lines=True, orient="records")
print("Saved to ", save_to)