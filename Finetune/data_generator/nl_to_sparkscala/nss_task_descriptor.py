from ..base.base_task_descriptor import BaseTaskDescriptor

class NSSTaskDescriptor(BaseTaskDescriptor):
    def _get_task_description(self, random_state=None):
        descriptions = [
"""Natural language to Spark Scala, is a problem of generating Scala code using the Apache Spark library that can be executed on a input CSV table, for a given natural language question.

You will be given an input table called "table" in the markdown format, as well as a question. Your task is to generate Scala code using the Apache Spark library that can be executed on the input table to answer the question.

Please ensure that the generated Scala code only return relevant columns being specifically asked in the question.

When generating Scala code, you can assume that the input table is always stored in a file named "data.csv", so always start your Scala code with the boilerplate prefix:
"val df = spark.read.option("header", "true").csv("data.csv")"

After you generate Scala code to produce results, please always save your final results into a single CSV file named in the "result" directory, so your Scala code should always end with:
"finalResult.coalesce(1).write.option("header", "true").csv("result")"

""",
#====================================================
"""Natural Language to Spark Scala involves creating Scala code using the Apache Spark library to process an input CSV table based on a given natural language question.

You will receive an input table named "table" in markdown format and a question. Your task is to write Scala code with the Apache Spark library to answer the question using the input table.

Ensure the generated Scala code only returns the columns specifically requested in the question.

Begin your Scala code with the boilerplate prefix:
"val df = spark.read.option("header", "true").csv("data.csv")"

After producing the results, always save the final output to a single CSV file in the "result" directory with the following code:
"finalResult.coalesce(1).write.option("header", "true").csv("result")"

""",
"""Natural Language to Spark Scala is the task of generating Scala code with the Apache Spark library that can run on an input CSV table based on a natural language question.

You will be provided with a table called "table" in markdown format and a question. Your job is to create Scala code using Apache Spark to answer the question using the input table.

Make sure the Scala code only includes the columns explicitly needed to answer the question.

Start your Scala code with the following boilerplate:
"val df = spark.read.option("header", "true").csv("data.csv")"

Ensure to save the final results to a single CSV file named in the "result" directory using:
"finalResult.coalesce(1).write.option("header", "true").csv("result")"

""",
"""The task of Natural Language to Spark Scala involves writing Scala code using the Apache Spark library to execute on a given input CSV table based on a natural language question.

You will receive an input table named "table" in markdown format along with a question. Your task is to generate Scala code with Apache Spark to process the input table and answer the question.

Ensure that the Scala code returns only the relevant columns specified in the question.

Start the Scala code with this prefix:
"val df = spark.read.option("header", "true").csv("data.csv")"

Always save the final output to a single CSV file in the "result" directory using:
"finalResult.coalesce(1).write.option("header", "true").csv("result")"

""",
"""Natural Language to Spark Scala requires generating Scala code with Apache Spark that can process an input CSV table based on a given natural language query.

You will be provided with a table named "table" in markdown format and a question. Your task is to write Scala code using Apache Spark to answer the question with the input table.

Ensure that the Scala code only returns the columns needed to answer the question.

Begin your Scala code with the following boilerplate:
"val df = spark.read.option("header", "true").csv("data.csv")"

Finally, save the results to a single CSV file in the "result" directory using:
"finalResult.coalesce(1).write.option("header", "true").csv("result")"

""",
#====================================================
            """Natural language to Spark Scala, is a problem of generating Scala code using the Apache Spark library that can be executed on a input CSV table, for a given natural language question.

You will be given an input table called "table" in the markdown format, as well as a question. Your task is to generate Scala code using the Apache Spark library that can be executed on the input table to answer the question.

Please ensure that the generated Scala code only return relevant columns being specifically asked in the question.

When generating Scala code, you can assume that the input table is always stored in a file named "data.csv", so always start your Scala code with the boilerplate prefix:
"val df = spark.read.option("header", "true").csv("data.csv")"

After you generate Scala code to produce results, please always save your final results into a single CSV file named in the "result" directory, so your Scala code should always end with:
"finalResult.coalesce(1).write.option("header", "true").csv("result")"

Please first think of an almost correct, but still incorrect Spark Scala code for this question first, output as [INCORRECT] folowed by a ```scala<Spark Scala Code>``` markdown code block, explain why this is likely incorrect, and then produce a correct Spark Scala code for this question, as [CORRECT] followed by a ```scala<Spark Scala Code>``` code block.

If you cannot think of any almost correct but still incorrect Spark Scala code for this question, just output [CORRECT] followed by a ```scala<Spark Scala Code>``` code block.

""",
            """Natural language to Spark Scala, is a problem of generating Scala code using the Apache Spark library that can be executed on a input CSV table, for a given natural language question.

You will be given an input table called "table" in the markdown format, as well as a question. Your task is to generate Scala code using the Apache Spark library that can be executed on the input table to answer the question.

Please ensure that the generated Scala code only return relevant columns being specifically asked in the question.

When generating Scala code, you can assume that the input table is always stored in a file named "data.csv", so always start your Scala code with the boilerplate prefix:
"val df = spark.read.option("header", "true").csv("data.csv")"

After you generate Scala code to produce results, please always save your final results into a single CSV file named in the "result" directory, so your Scala code should always end with:
"finalResult.coalesce(1).write.option("header", "true").csv("result")"

Please explain how you plan to answer this query first in a markdown JSON codeblock. In your plan in JSON, please follow this format:
	explain your planned filters as {"Filters": [{"Column": "filter-column-1", "Condition": "equal/less-than/greater-than/…", "Value": "filter-value-1"}, …]}.
	explain your planned group-by as {"GroupBy": ["groupby-column-1", …]}
	explain your aggregation as {"Aggregation": [{"Column": "aggregate-column-name-1", "Aggregation-Function": "min/max/average/…"}, …]}.
	explain your other operations in {"Other": "other plans that do not fit above"}

After the JSON plan, please then return the code only with the following markdown codeblock format : ```scala<Spark Scala Code>```.

"""
        ]
        return self.select_one_option(descriptions[:5], random_state=random_state)

    def get_input(self, data, random_state=None):
        df, question, incorrect_label = data
        df_text = self.serializer.serialize_df(df)
        text = (
            "**Input table:**\n"
            f"{df_text}\n"
            f"**Question:**\n{question}\n"
        )
        return text

    def add_format_suffix(self, desc):
        # key, placeholder = self.get_output_example()
        if len(desc) > 0 and desc[-1] != "\n":
            desc += " "
        text = f"""{desc}No explanation, return the code only with the following markdown codeblock format : ```scala<Spark Scala Code>```."""
        # text = f"""{desc}No explanation, return the code only with the following markdown codeblock format : ```scala<Spark Scala Code>```. After your codeblock, please then reflect on your generated code, to see whether it is syntactically correct that can run, and whether it can accurately answer the given question, if not please correct your code."""
        # text = f"""{desc}Please explain how you plan to answer this query first in a markdown JSON codeblock. After the JSON plan, please then return the code only with the following markdown codeblock format : ```scala<Spark Scala Code>```."""
        # text = f"""{desc}Please explain how you plan to answer this query first, then return the code only with the following markdown codeblock format : ```scala<Spark Scala Code>```."""
        # text = f"""{desc}Please explain how you plan to answer this query **step-by-step** first, then return the code only with the following markdown codeblock format : ```scala<Spark Scala Code>```."""
        # text = f"""{desc}Return the code only with the following markdown codeblock format : ```scala<Spark Scala Code>```\n\n[Correct]: here is a correct response that succeeds for the task."""
        # text = f"""{desc}Return the code only with the following markdown codeblock format : ```scala<Spark Scala Code>```\n\n[Incorrect]: here is an incorrect response that fails for the task."""
        # text = f"""{desc}Please first think of an almost correct, but still incorrect Spark Scala code for this question first, output as [INCORRECT] folowed by a ```scala<Spark Scala Code>``` markdown code block, explain why this is likely incorrect, and then produce a correct Spark Scala code for this question, as [CORRECT] followed by a ```scala<Spark Scala Code>``` code block.

# If you cannot think of any almost correct but still incorrect Spark Scala code for this question, just output [CORRECT] followed by a ```scala<Spark Scala Code>``` code block."""
        return text

    def get_output(self, y):
        incorrect_label, label = y

        if incorrect_label:
            return (
                f"```scala\n{incorrect_label}\n```\n"
                f"Upon review, code is incorrect and should be rewritten as follows:\n"
                f"```scala\n{label}\n```"
            )
        return (
            f"```scala\n{label}\n```"
            # "Upon review, code is correct and can be executed to answer the given question."
        )
        # return "```scala\n" + y + "\n```"
        # return "Upon review, code is incorrect and should be rewritten as follows: \n```scala\n" + y + "\n```"
        # return y
        
    def _get_output(self, y):
        return y

    def get_output_example(self):
        return "SparkScala", "<Spark Scala Code>"