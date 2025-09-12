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
# input_file = "<PATH-TO-TableSpecialist>/Generation/NL2DSL/Table2Question/data/V4/table2question_all_webtable_v4_2nd_9K.jsonl.gpt-3.5-turbo-1106.result.jsonl.extracted.jsonl.shuffeled.head3000"
print(input_file)
with open(input_file) as f:
    data = f.readlines()
data = [json.loads(x) for x in data]


tables = []
prompts = []
questions = []
question_reqs = []

for d in tqdm(data):
    tbl = d['table']
    if not d['response'] or 'question' not in d['response']:
        continue
    q = d['response']['question']
    prompt = """# Task description:
Natural language to R script, is a problem of generating R script  that can be executed on a input CSV table, for a given natural language question.

You will be given an input table called "table" in the markdown format, as well as a question. Your task is to generate a R script that can be executed on the input table to answer the question.

Please ensure that the generated R script only return relevant columns being specifically asked in the question.

When generating R script, you can assume that the input table is always stored in a file named "data.csv", so always start your R script with the boilerplate prefix:
"library(dplyr)

data <- read.csv("data.csv", check.names = FALSE)
"

After you generate R script code to produce results, please always save your final results into a file named "result.csv" with no index column, so your R script should always end with:
"write.csv(final_result, "result.csv", row.names = FALSE)"

No explanation, return the code only with the following markdown codeblock format : ```r<R CODE>```.

For example:
 
Input:
Table:
|City|Population (2015)|Area|Density|City class|Income class|Province|
|---|---|---|---|---|---|---|
|Bacolod|561,875|62.81|9,100|Highly urbanized|1st|Negros Occidental|
|Bago|170,981|154.9|1,100|Component|2nd|Negros Occidental|
|Bais|76,291|123.41|620|Component|3rd|Negros Oriental|
|Bayawan|117,900|269.92|440|Component|2nd|Negros Oriental|
|Cadiz|154,723|202.54|750|Component|2nd|Negros Occidental|
|Canlaon|54,509|66.0|830|Component|4th|Negros Oriental|
|Dumaguete|131,377|12.98|10,000|Component|2nd|Negros Oriental|
|Escalante|94,070|74.43|1,300|Component|4th|Negros Occidental|
|Guihulngan|95,969|150.02|650|Component|5th|Negros Oriental|
|Himamaylan|106,880|141.71|750|Component|3rd|Negros Occidental|
|Kabankalan|181,977|269.25|670|Component|1st|Negros Occidental|
|La Carlota|64,469|53.01|1,200|Component|4th|Negros Occidental|
|Sagay|146,264|127.54|1,100|Component|3rd|Negros Occidental|
|San Carlos|132,536|174.33|750|Component|2nd|Negros Occidental|
|Silay|126,930|82.93|1,500|Component|3rd|Negros Occidental|
|Sipalay|70,070|146.63|470|Component|4th|Negros Occidental|
|Talisay|102,214|77.68|1,300|Component|4th|Negros Occidental|
|Tanjay|80,532|106.58|750|Component|4th|Negros Oriental|
|Victorias|87,933|51.71|1,700|Component|4th|Negros Occidental|

question: What is the top-3 most populous city in 2015 in the table?

Output: 
```r
library(dplyr)

data <- read.csv("data.csv", check.names = FALSE)

data$`Population (2015)` <- as.numeric(gsub(",", "", data$`Population (2015)`))

top_3_cities <- data %>%
  arrange(desc(`Population (2015)`)) %>%
  slice(1:3)

final_result <- top_3_cities %>%
  select(City)

write.csv(final_result, "result.csv", row.names = FALSE)
```
 
Input:
Table:
|Contestant ID|Finalist|Gender|
|---|---|---|
|SSJ01|Monisha|Female|
|SSJ02|Alka Ajith|Female|
|SSJ03|Balasarangan|Male|
|SSJ04|Sahana|Female|
|SSJ05|Manisha|Female|
|SSJ06|Prasanna Sundar|Male|
|SSJ07|Sowmya|Female|
|SSJ08|Oviya|Female|
|SSJ09|Vishnucharan|Male|
|SSJ10|Sivaranjani|Female|
|SSJ11|Nithyashree|Female|
|SSJ12|Harish|Male|
|SSJ13|Shri Prasanna|Male|
|SSJ14|Sanjana|Female|
|SSJ15|Shravan|Male|
|SSJ16|Srinisha|Female|
|SSJ17|Shrihari|Male|
|SSJ18|Sharath|Male|
|SSJ19|Roshan|Male|
|SSJ20|Srikanth|Male|
|SSJ21|Priyanka|Female|
|SSJ22|Soundarya|Female|
|SSJ23|Sathyanarayanan|Male|
|SSJ24|Srinidhi|Female|
|SSJ25|Ponmozhi|Female|

question: How many female contestants are there in total?
 
Output: 
```r
library(dplyr)

data <- read.csv("data.csv", check.names = FALSE)

female_count <- data %>%
  filter(Gender == "Female") %>%
  summarise(Count = n())

write.csv(female_count, "result.csv", row.names = FALSE)
```
 
Input:
Table:
|Club|Coach|Replaced Coach|Home stadium|
|---|---|---|---|
|FC Dynamo Kyiv|Yozhef Sabo|Mykhailo Fomenko|Republican Stadium|
|FC Shakhtar Donetsk|Valery Yaremchenko||Shakhtar Stadium|
|FC Chornomorets Odessa|Viktor Prokopenko||Black Sea Shipping Stadium|
|FC Dnipro Dnipropetrovsk|Mykola Pavlov||Meteor Stadium|
|FC Karpaty Lviv|Myron Markevych||Ukraina Stadium|
|FC Kryvbas Kryvyi Rih|Volodymyr Brukhtiy|Ihor Nadein|Metalurh Stadium|
|FC Nyva Ternopil|Leonid Buriak||City Stadium|
|SC Tavriya Simferopol|Anatoliy Zayaev||Lokomotyv Stadium|
|FC Temp Shepetivka|Leonid Tkachenko||Temp Stadium|
|FC Nyva Vinnytsia|Yukhym Shkolnykov||Central City Stadium|
|FC Volyn Lutsk|Roman Pokora||Avanhard Stadium|
|FC Veres Rivne|Vyacheslav Kobyletskyi|Mykhailo Dunets|Avanhard Stadium|
|FC Torpedo Zaporizhia|Ihor Nadein|Viktor Matviyenko|AvtoZAZ Stadium|
|FC Zorya-MALS|Volodymyr Kobzarev|Anatoliy Shakun|Avanhard Stadium|
|FC Kremin Kremenchuk|Evhen Rudakov|Boris Streltsov 8 games Tiberiy Korponay 9 games|Dnipro Stadium|
|FC Metalurh Zaporizhia|Anatoliy Kuksov|Janis Skredelis Hryhoriy Vul|Metalurh Stadium|
|FC Bukovyna Chernivtsi|Oleksandr Pavlenko||Bukovyna Stadium|
|FC Metalist Kharkiv|Viktor Kamarzayev|Oleksandr Dovbiy Yevhen Lemeshko|Metalist Stadium|

question: What is the name of the home statium of the football club FC Kryvbas Kryvyi Rih?"
 
Output: 
```r
library(dplyr)

data <- read.csv("data.csv", check.names = FALSE)

home_stadium <- data %>%
  filter(Club == "FC Kryvbas Kryvyi Rih") %>%
  select(`Home stadium`)

write.csv(home_stadium, "result.csv", row.names = FALSE)
```
 
Input:
Table:
|Title|Year|Director(s)|
|---|---|---|
|"Red Morning Light"|2003|Douglas Biro|
|"Molly's Chambers"|2003|Honey|
|"Wasted Time"|2003|Mark Pellington|
|"The Bucket"|2004|Patrick Daughters|
|"Four Kicks"|2005|Patrick Daughters|
|"King of the Rodeo"|2005|Patrick Daughters|
|"On Call"|2007|Adria Petty|
|"Charmer"|2007|Robert Hales|
|"Crawl"|2008|Nick Wickham|
|"Sex on Fire"|2008|Sophie Muller|
|"Use Somebody"|2008|Sophie Muller|
|"Notion"|2009|Phil Griffin|
|"Radioactive"|2010|Sophie Muller|
|"Pyro"|2010|Max Goldman, Paul Greenhouse, Casey McGrath|
|"Back Down South"|2011|Casey McGrath|
|"Supersoaker"|2013|W.I.Z.|
|"Beautiful War"|2013|Casey McGrath|
|"Temple"|2014|Casey McGrath|
|"Waste a Moment"|2016|Dimitri Basil|
|"Walls"|2016|Dimitri Basil|
|"Around the World"|2016||

question: What are the names of the directors that have directed movies since 2010, and how many movies have they produced?
 
Output: 
```r
library(dplyr)

data <- read.csv("data.csv", stringsAsFactors = FALSE, check.names = FALSE)

movies_since_2010 <- subset(data, Year >= 2010)

director_counts <- aggregate(Title ~ `Director(s)`, data = movies_since_2010, FUN = function(x) length(x))

# colnames(director_counts) <- c("Director", "MoviesProduced")

write.csv(director_counts, "result.csv", row.names = FALSE)
```

Now, for the input table and question below,  generate its corresponding R code for the natural language question. No explanation, return the code only with the following markdown codeblock format : ```r<R CODE>```.

Input:
Table:
""" + serialize_df(pd.read_csv(tbl, keep_default_na=False)) + """

question: """ + q + """

Output:
"""
    tables.append(tbl)
    prompt = prompt.replace(u"\u00A0", " ")
    prompts.append(prompt)
    questions.append(q)
    question_reqs.append(d['requirements'])

df = pd.DataFrame({"table": tables, "prompt": prompts, "question": questions, "question_requirement": question_reqs})

save_to = "data/V6_llama3.1-8b/nl2r_prompt_V6_1st_3K_V4_llama3.1-8b.jsonl"
df.to_json(save_to, lines=True, orient="records")
print(len(df))
print(f"Saved to {save_to}")

# save_to = "data/V6_2/nl2r_prompt_V6_2_2nd_3K_V4.jsonl"
# df[3000:6000].to_json(save_to, lines=True, orient="records")
# print(f"Saved to {save_to}")

# save_to = "data/V6_2/nl2r_prompt_V6_2_3rd_3K_V4.jsonl"
# df[6000:].to_json(save_to, lines=True, orient="records")
# print(f"Saved to {save_to}")
