import json
import pandas as pd
from tqdm import tqdm
import os
import random
import numpy as np

file_list = [] # Assign file_list with the paths of your table corpus
random.seed(42)
random.shuffle(file_list)
print(len(file_list))

def serialize_df(df):
    text = [""]
    # for c in df.columns:
    #     text.append(str(c))
    # text.append("\n")

    # # add separating line
    # for c in df.columns:
    #     text.append("---")
    # text.append("\n")
    
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
    if df[sample_col].dropna().apply(lambda x: len(str(x))).max() > 50:
        continue
    distinct_value = df[sample_col].replace('', np.nan).dropna().unique()
    df_col = pd.DataFrame({"<Column>": distinct_value})

    prompt = f"""Instruction:
# Task Description: Given the table column <Column> below, please brainstorm an erroneous cell <CELL> that is NOT compatible with the <Column>, which if added to the <Column>, would be considered as a data error.

For example:
(1) When the <Column> has a list of string-valued names, an error <CELL> can be a number as a special placeholder such as "99999" or "0". 
(2) When the <Column> has a list of numbers, an error <CELL> can be is a string.
(3) An error <CELL> can also be placeholder punctuation like "?", "!", "***" and "--"
(4) An error <CELL> can also be of a semantic type that is obviously not compatible with the rest of the  <Column>, e.g., <CELL> is an email address while the  <Column> has a list of URLs, or <CELL> is a phone number while <Column> has a list of countries, etc.

Please brainstorm an **ERROR** cell <CELL>  **NOT** compatible with the <Column>. 

**DO** generate <CELL> using realistic strings
** NEVER ** generate fake <CELL> like "123 Main Street".
** NEVER ** generate fake <CELL> like "123456789"
** NEVER ** generate fake <CELL> like "12345"
** NEVER ** generate fake <CELL> like "ABC"
** NEVER ** generate fake <CELL> like "ABCD"
** NEVER ** generate fake <CELL> like "john.doe@example.com"

Return a JSON in the format {{"ERROR": "<CELL>"}}.

------

## Input:


|11:43.1|
|10:30.1|
|10:54.7|
|23:03.1|
|11:01|
|11:27.4|
|08:24.6|
|13:44.4|


## Output:

{{"ERROR": "new zealand"}}


------

## Input:


|Mens 100m butterfly|
|Womens 100m freestyle|
|Mens 200m breaststroke|
|Womens 200m backstroke|


## Output:

{{"ERROR": "Olivia.Mcbath@gmail.com"}}


------


## Input:

|Jefferson|
|Benton|
|Franklin|
|Faulkner|
|Madison|
|Garland|
|Poinsett|
|Craighead|
|Crawford|
|Lonoke|
|Lincoln|
|Pulaski|
|Crittenden|
|Miller|
|Cleveland|


## Output:

{{"ERROR": "99999"}}


------

## Input:

|2|
|4|
|1|
|6|
|29|


## Output:

{{"ERROR": "$129.00"}}

------

## Input:


|$70,000|
|$40,000|
|$90,000|
|$80,000|
|$60,000|
|$100,000|
|$130,000|
|$150,000|
|$50,000|
|$120,000|
|$160,000|
|$170,000|
|$110,000|
|$30,000|
|$10,000|
|$20,000|


## Output:

{{"ERROR": "+1 800-425-1829"}}



------

## Input:


|James Smith|
|Chris White|
|Jane Doe|
|Bill Gates|
|Steve Jobs|

## Output:

{{"ERROR": "***"}}


------

## Input:

|Labrador Retriever|
|French Bulldog|
|Golden Retriever|
|Poodle|
|German Shepherds|


## Output:

{{"ERROR": "---"}}

------

## Input:

|(41) 9635-0575|
|(47) 9285-3910|
|(15) 6518-6603|
|(91) 2727-6856|
|(61) 4425-1329|
|(78) 4464-7756|
|(23) 1443-9130|
|(94) 6570-4540|
|(54) 4294-8441|
|(62) 4022-2429|
|(29) 3528-8592|
|(72) 4078-7452|
|(12) 8805-7156|


## Output:

{{"ERROR": "?"}}

------

## Input:

|#ffd66a|
|#fbc527|
|#ff9212|


## Output:

{{"ERROR": "2025"}}

------

## Input:

|$100,000 to $250,000|
|$60,000 to $80,000|
|$80,000 to $100,000|
|$40,000 to $60,000|
|$20,000 to $40,000|
|less than $20,000|
|more than $250,000|


## Output:

{{"ERROR": "-"}}

------

## Input:

|108 lakeside court|
|2947 vine lane|
|620 woodside ct.|
|9539 glenside dr|
|101 candy rd.|
|6369 ellis street|
|9495 limewood place|
|5980 icicle circle|


## Output:

{{"ERROR": "RGB(255, 87, 51)"}}

------

## Input:

|1899-12-30 10:00:00.000|
|1899-12-30 14:00:00.000|
|1899-12-30 08:00:00.000|
|1899-12-30 12:00:00.000|
|1899-12-30 09:00:00.000|


## Output:

{{"ERROR": "MD-192038"}}

------

## Input:

|2017-wk19|
|2017-wk20|
|2017-wk21|
|2017-wk23|
|2017-wk24|
|2017-wk25|
|2017-wk26|
|2017-wk28|
|2017-wk29|
|2017-wk30|
|2017-wk31|


## Output:

{{"ERROR": "g79"}}

------

## Input:

|lonnie brien pol / lonnie.b.pol2@uscg.mil|
|shirley kraft / shirley.kraft@bpd.treas.gov|
|paulette anne swann / paulette.a.swann@uscg.mil|
|nekiesha michel bone-williams / nekiesha.m.edler@uscg.mil|
|alyssa chevalier / alyssa.chevalier@bpd.treas.gov|
|jeff hoge / jeffrey.hoge@fms.treas.gov|
|william stimmel / william.stimmel1@dhs.gov|
|james d. rapley / james.rapley@dhs.gov|
|/ kelly.rapley@dhs.gov|

## Output:

{{"ERROR": "[4.72|2022-12-23 00:00:00|2022-12-23 00:00:00|Delivery]"}}

------

Now given the input column below:

## Input:

{serialize_df(df_col)}

Please brainstorm an **ERROR** cell <CELL>  **NOT** compatible with the <Column>. 

**DO** generate <CELL> using realistic strings
** NEVER ** generate fake <CELL> like "123 Main Street".
** NEVER ** generate fake <CELL> like "123456789"
** NEVER ** generate fake <CELL> like "12345"
** NEVER ** generate fake <CELL> like "ABC"
** NEVER ** generate fake <CELL> like "ABCD"
** NEVER ** generate fake <CELL> like "john.doe@example.com"

## Output:
"""
    tables.append(tbl)
    prompt = prompt.replace(u"\u00A0", " ")
    prompts.append(prompt)
    sample_cols.append(sample_col)
    distinct_values.append(distinct_value)
    if len(tables) == 6000:
        break

data = pd.DataFrame({"table": tables, "sample_col": sample_cols, "distinct_value": distinct_values, "prompt": prompts})
data = data[3000:]
print(data.shape)
save_to = "data/v6/table2semantic_v6_web_2nd_3K.jsonl"
os.makedirs(os.path.dirname(save_to), exist_ok=True)
data.to_json(save_to, orient="records", lines=True)
print(f"Saved to {save_to}")