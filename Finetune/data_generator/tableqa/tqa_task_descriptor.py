from ..base.base_task_descriptor import BaseTaskDescriptor
import json

class TQATaskDescriptor(BaseTaskDescriptor):
    def _get_task_description(self, random_state=None):
        descriptions = [
"""You are given a table containing structured data and a natural language question referring to the table. Your goal is to analyze the table and provide an accurate and concise answer based on the given data.

Instructions:
1. Understand the Table: Examine the structure, headers, and data in the table. Identify relevant columns and rows related to the question.
2. Interpret the Question: Determine whether the question requires direct retrieval, aggregation, comparison, sorting, filtering, or inference.
3. Extract the Answer: Use logical reasoning and numerical operations (if necessary) to derive the correct response from the table.
4. Format the Answer: No explanation, return the answer in a structured JSON format: {"answer": <answer>}. If the question cannot be answered due to missing or ambiguous data, return a JSON response with {"answer": null}.

"""
        ]
        return self.select_one_option(descriptions[:5], random_state=random_state)
    
    def add_format_suffix(self, desc):
        # _, ans1, = self.get_output_example()
        if len(desc) > 0 and desc[-1] != "\n":
            desc += " "
        text = f"""{desc}No explanation, return the final answer only with the following JSON format : {{"answer": <answer>}}"""
        # text = f"""{desc}No explanation, return the code only with the following markdown codeblock format : ```sql<SQL CODE>```. After your codeblock, please then reflect on your generated code, to see whether it is syntactically correct that can run, and whether it can accurately answer the given question, if not please correct your code."""
        # text = f"""{desc}Please explain how you plan to answer this query first in a markdown JSON codeblock. After the JSON plan, please then return the code only with the following markdown codeblock format : ```sql<SQL CODE>```."""
        # text = f"""{desc}Please explain how you plan to answer this query first, then return the code only with the following markdown codeblock format : ```sql<SQL CODE>```."""
        # text = f"""{desc}Please explain how you plan to answer this query **step-by-step** first, then return the code only with the following markdown codeblock format : ```sql<SQL CODE>```."""
        # text = f"""{desc}Return the code with the following markdown codeblock format : ```sql<SQL CODE>```.\n\n[Correct]: here is a correct response that succeeds for the task."""
        # text = f"""{desc}Return the code with the following markdown codeblock format : ```sql<SQL CODE>```.\n\n[Incorrect]: here is an incorrect response that fails for the task."""
        # text = f"""{desc}Please first think of an almost correct, but still incorrect SQL for this question first, output as [INCORRECT] folowed by a ```sql<SQL CODE>``` markdown code block, explain why this is likely incorrect, and then produce a correct SQL for this question, as [CORRECT] followed by a ```sql<SQL CODE>``` code block.

# If you cannot think of any almost correct but still incorrect SQL for this question, just output [CORRECT] followed by a ```sql<SQL CODE>``` code block."""
        return text

    def get_input(self, data, random_state=None):
        df, question, incorrect_label = data
        df_text = self.serializer.serialize_df(df)
        text = (
            "**Input table:**\n"
            f"{df_text}\n"
            f"**Question:**\n{question}\n"   
        )
        return text
    
    def get_output(self, y):
        return json.dumps({"answer": y})
        # return "Upon review, code is incorrect and should be rewritten as follows: \n```sql\n" + y + "\n```"
        # return y
    
    def _get_output(self, y):
        return y

    def get_output_example(self):
        return "answer", "<answer>"