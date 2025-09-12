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
reqs = []

predicates = [
    "*ONE (1)* filtering predicate",
    "*TWO (2)* different filtering predicates",
    "*THREE (3)* different filtering predicates",
    "*FOUR (4)* different filtering predicates",
]

requirements = [
    "different filtering predicate(s)",
    "*ONE (1)* string preprocessing step (e.g., removing prefix/suffix, normalize casing, etc.)",
    "*ONE (1)* number preprocessing step (e.g., extracting numbers from a column for comparisons/sorting)",
    "*ONE (1)* group-by, aggregation function",
    "*ONE (1)* sorting then take top-K step",
    "*ONE (1)* mathematical operation (e.g., subtraction, addition)"
]

def random_requirements():
    selected = []
    for idx, req in enumerate(requirements):
        if idx == 0:
            flag = random.choices([True, False], weights=[0.7, 0.3], k=1)[0]
        else:
            flag = random.choices([True, False], weights=[0.33, 0.67], k=1)[0]
        if flag:
            if idx == 0:
                num = random.randint(0, 3)
                selected.append(predicates[num])
            else:
                selected.append(req)
    selected_reqs = "\n".join(["({}) {}".format(idx+1, req) for idx, req in enumerate(selected)])
    return selected_reqs
for tbl in tqdm(file_list):
    df = pd.read_csv(tbl, keep_default_na=False)
    if len(df.columns) < 5:
        continue
    selected_reqs = random_requirements()
    while not selected_reqs:
        selected_reqs = random_requirements()
    prompt = f"""Task description: Given the input table below, your task is to generate questions that can be answered by the given table with a SQL query.

Input:
Table:
{serialize_df(df)}

Please return one natural language question, and ensure that when your question is answered in SQL, the corresponding SQL would contain all of the below:
{selected_reqs}

Return your answer in the following JSON format: {{"question": <QUESTION>}}.

Output:
"""
    tables.append(tbl)
    prompt = prompt.replace(u"\u00A0", " ")
    prompts.append(prompt)
    reqs.append(selected_reqs)
    if len(tables) == 18000:
        break

df = pd.DataFrame({"table": tables[9000:18000], "prompt": prompts[9000:18000], "requirements": reqs[9000:18000]})
df.to_json("data/V4/table2question_all_webtable_v4_2nd_9K.jsonl", orient="records", lines=True)

# df = pd.DataFrame({"table": tables[3000:6000], "prompt": prompts[3000:6000], "requirements": reqs[3000:6000]})
# df.to_json("data/V4/table2question_all_webtable_v4_2nd_3K.jsonl", orient="records", lines=True)

# df = pd.DataFrame({"table": tables[6000:9000], "prompt": prompts[6000:9000], "requirements": reqs[6000:9000]})
# df.to_json("data/V4/table2question_all_webtable_v4_3rd_3K.jsonl", orient="records", lines=True)

# for i in range(0, 5):
#     print(df.iloc[i]["prompt"])
#     print("-------------------")