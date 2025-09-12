from ..base.base_task_descriptor import BaseTaskDescriptor

class NRTaskDescriptor(BaseTaskDescriptor):
    def _get_task_description(self, random_state=None):
        descriptions = [
            """Natural language to R script, is a problem of generating R script  that can be executed on a input CSV table, for a given natural language question.

You will be given an input table called "table" in the markdown format, as well as a question. Your task is to generate a R script that can be executed on the input table to answer the question.

Please ensure that the generated R script only return relevant columns being specifically asked in the question.

When generating R script, you can assume that the input table is always stored in a file named "data.csv", so always start your R script with the boilerplate prefix:
"library(dplyr)

data <- read.csv("data.csv", check.names = FALSE)
"

After you generate R script code to produce results, please always save your final results into a file named "result.csv" with no index column, so your R script should always end with:
"write.csv(final_result, "result.csv", row.names = FALSE)"

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
        text = f"""{desc}No explanation, return the code only with the following markdown codeblock format : ```r<R CODE>```."""
        return text
    
    def get_output(self, y):
        return "```r\n" + y + "\n```"
    
    def _get_output(self, y):
        return y

    def get_output_example(self):
        return "R", "<R Script>"