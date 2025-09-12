from ..base.base_task_descriptor import BaseTaskDescriptor

class NPTaskDescriptor(BaseTaskDescriptor):
    def _get_task_description(self, random_state=None):
        descriptions = [
            """Natural language to Python Pandas, is a problem of generating Python code using the Pandas library that can be executed on a input CSV table, for a given natural language question.

You will be given an input table called "table" in the markdown format, as well as a question. Your task is to generate generate the Python code using the Pandas library to process the input table and answer the question.

Please ensure that the generated Python code only return relevant columns being specifically asked in the question.

When generating Python code, you can assume that the input table is always stored in a file named "data.csv", so always start your Python code with the boilerplate prefix:
"import pandas as pd
df = pd.read_csv('data.csv')
"
After you generate Python Pandas code to produce results, please always save your final results into a file named "result.csv", so your Python code should always end with:
"df.to_csv("result.csv", index=False, header=False)"
"""
        ]
        return self.select_one_option(descriptions, random_state=random_state)

    def get_input(self, data, random_state=None):
        df, question = data
        df_text = self.serializer.serialize_df(df)
        text = (
            "**Input table:**\n"
            f"{df_text}\n"
            f"**Question:**\n{question}\n"   
        )
        return text
    
    def add_format_suffix(self, desc):
        key, placeholder = self.get_output_example()
        if len(desc) > 0 and desc[-1] != "\n":
            desc += " "
        text = f"""{desc}No explanation, return the code only with the following markdown codeblock format : ```python<PYTHON PANDAS CODE>```."""
        return text

    def get_output(self, y):
        return "```python\n" + y + "\n```"
    
    def _get_output(self, y):
        return y

    def get_output_example(self):
        return "PYTHON", "<Python Code>"