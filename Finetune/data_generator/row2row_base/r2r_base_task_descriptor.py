from ..base.base_task_descriptor import BaseTaskDescriptor
import pandas as pd
import numpy as np

class R2RBaseTaskDescriptor(BaseTaskDescriptor):
    def __init__(self, mode=None, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode
        self.pl = "<PL>"
    
    def get_input(self, df, random_state=None):
        if random_state is not None:
            np.random.seed(random_state)
        if self.mode == "test":
            df_ex = df.copy()
            df_ex.loc[df_ex.shape[0]-1, "Output"] = "<MISSING>"
            # Rename columns with col_{idx}
            df_ex.columns = [f"Col_{idx}" for idx in range(len(df_ex.columns))]
            df_ex.columns = list(df_ex.columns)[:-1] + ["DERIVED_COLUMN"]
            prompt = (
                f"**Input table:**\n"
                f"""{self.serializer.serialize_df(df_ex.drop(columns=["DERIVED_COLUMN"]).head(len(df_ex)-1))}\n"""
                f"**Desired Output Table:**\n"
                f"{self.serializer.serialize_df(df_ex.head(len(df_ex)-1))}"
            )
            return prompt
        else:
            prompt = (
                f"**Input table:**\n"
                f"""{self.serializer.serialize_df(df.drop(columns=["DERIVED_COLUMN"]).head(3))}\n"""
                f"**Desired Output Table:**\n"
                f"{self.serializer.serialize_df(df.head(3))}"
            )
            return prompt
    
    def get_output(self, y):
        if self.mode == "test":
            answer = str(y["label"])
            answer = self.answer_to_json(answer)
    
            if y["cot"] is not None:
                cot_text = y["cot"].strip()
                completion = f"{cot_text} Therefore, the final answer is {answer}."
            else:
                completion = answer
            return completion
        else:
            return f"```{self.pl}\n" + y["label"] + "\n```"
    
    def add_format_suffix(self, desc):
        # _, ans1, = self.get_output_example()
        if len(desc) > 0 and desc[-1] != "\n":
            desc += " "
        # if not self.use_cot:
        text = f"""{desc}No explanation, Return the final result as a markdown code block, as ```{self.pl}\n<{self.pl.upper()}-CODE>\n```."""
        # else:
        # text = f"""{desc}Please first summarize your understanding of the purpose of the transformation, then explain your thoughts on performing the transformation step by step, and then return the final result as a markdown code block, as ```{self.pl}\n<{self.pl.upper()}-CODE>\n```."""
        return text
    
    def get_output_example(self):
        return "output_value", "<output value transformed from the input value>"