import json
import pandas as pd
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

input_file = "<PATH-TO-TableSpecialist>/Generation/NL2DSL/Table2Question/data/V4/table2question_all_webtable_v4_1st_3K.jsonl.llama3.1-8b.result.jsonl.extracted.jsonl"
print(input_file)
with open(input_file) as f:
    data = f.readlines()
data = [json.loads(x) for x in data]

tables = []
prompts = []
questions = []
question_reqs = []

for d in tqdm(data, ncols=100):
    tbl = d['table']
    if not d['response'] or 'question' not in d['response']:
        continue
    q = d['response']['question']
    prompt = """Task: 
You are given a table containing structured data and a natural language question referring to the table. Your goal is to analyze the table and provide an accurate and concise answer based on the given data.

Instructions:
1. Understand the Table: Examine the structure, headers, and data in the table. Identify relevant columns and rows related to the question.
2. Interpret the Question: Determine whether the question requires direct retrieval, aggregation, comparison, sorting, filtering, or inference.
3. Extract the Answer: Use logical reasoning and numerical operations (if necessary) to derive the correct response from the table.
4. Format the Answer: No explanation, return the answer in a structured JSON format: {"answer": <answer>}. If the question cannot be answered due to missing or ambiguous data, return a JSON response with {"answer": null}.

Table:
""" + serialize_df(pd.read_csv(tbl, keep_default_na=False)) + """

Question: 
""" + q + """

No explanation, return the answer in a structured JSON format: {"answer": <answer>}.

"""
    tables.append(tbl)
    prompt = prompt.replace(u"\u00A0", " ")
    prompts.append(prompt)
    questions.append(q)
    question_reqs.append(d['requirements'])

df = pd.DataFrame({"table": tables, "prompt": prompts, "question": questions, "question_requirement": question_reqs})
print(df.shape)

save_to = "data/V2/tqa_prompt_1_1st_3K_V4_llama3.1-8b.jsonl"
import os
os.makedirs(os.path.dirname(save_to), exist_ok=True)
df.to_json(save_to, lines=True, orient="records")
print(f"Saved to {save_to}")