from ..base.base_task_descriptor import BaseTaskDescriptor

class EDTaskDescriptor(BaseTaskDescriptor):
    def _get_task_description(self, random_state=None):
        descriptions = [
            "The table column below is a high-quality real data column. In the unlikely event that you see any one cell that is clearly a data error, either because the cell is a typo/misspelling (e.g., Mississipi that is a misspelling of Mississippi), or because it is a semantic outlier that does not fit in the context of this column (e.g., a city name mixed in a column with country names, etc.), please point it out.",
            "The table column below may or may not have an erroneous cell mixed in the column. Please check the column carefully to see if there is any one cell that may be considered a data error, either because the cell is a typo/misspelling (e.g., Mississipi that is a misspelling of Mississippi), or because it is a semantic outlier that does not fit in the context of this column (e.g., a city name mixed in a column with country names, or a zip-code mixed in a column of addresses, etc.).",
        ]
        return self.select_one_option(descriptions, random_state=random_state)
    
    def get_input(self, df, random_state=None):
        return self.serializer.serialize_df(df)
    
    def get_output_example(self):
        return "obvious_error", '<a list of erroneous cells or None>'
    
    def add_format_suffix(self, desc):
        # _, ans1, = self.get_output_example()
        if len(desc) > 0 and desc[-1] != "\n":
            desc += " "
        text = f"""{desc}
*** Please be aware that cell values that appear unusual are often NOT ERRORS, such as code values (e.g., "mdl-1023"), abbreviations (e.g., "MDX"), out-of-vocabulary words (e.g., foreign languages, or properietary terminologies), etc.. In all those cases, simply DO NOT make any prediction. Users will be very angry if they see incorrect predictions. ***
 
Please return {{"obvious_error": "NULL"}} if you believe the column is a high-quality column. Otherwise, please return any error cell you identified in JSON {{"obvious_error": "<CELL>"}}, ONLY IF you are ABSOLUTELY SURE that <CELL> is erroneous. We will manually verify and you will be punished if it turns out that <CELL> is not erroneous.
"""
#         text = f"""{desc}

# *** Please be aware that table data have different characteristics from natural language data, and can have code (e.g., "mdl-1023"), abbreviations (e.g., "MDX"), out-of-vocabulary words (e.g., foreign languages, or properietary terminologies). If you are unsure whether a cell is an error, then absolutely DO NOT make any prediction!! Users will be very angry if they see incorrect predictions!! ***

# Please return your answer in JSON {{"likely erroneous cell": "<CELL>", "corrected cell": <CORRECTED-CELL>}}, ONLY IF you are ABSOLUTELY SURE that <CELL> is erroneous, and in which case also produce the corrected-version of the cell in <CORRECTED-CELL>. If you are unsure what <CORRECTED-CELL> should be, then don't predict any cell as erroneous, by just return  {{"likely erroneous cell": "NULL", "corrected cell": "NULL"}}.
 
# There is only a very small chance that a column has erroneous cells, so in the majority of other cases, please simply return {{"likely erroneous cell": "NULL", "corrected cell": "NULL"}}."""
#         text = f"""{desc}

# *** Please be aware that table data have different characteristics from natural language data, and can have code (e.g., "mdl-1023"), abbreviations (e.g., "MDX"), out-of-vocabulary words (e.g., foreign languages, or properietary terminologies). If you are unsure whether a cell is an error, then absolutely DO NOT make any prediction!! Users will be very angry if they see incorrect predictions!! ***

# Please return your answer in JSON {{"likely erroneous cell": "<CELL>"}}. If you cannot find such an erroneous cell, please return {{"likely erroneous cell": "NULL"}}."""
#         text = f"""{desc}

# *** Please be aware that table data have different characteristics from natural language data, and can have code, abbreviations, out-of-vocabulary words. So if you are unsure whether a cell is an error or not, err on the side of caution, DO NOT make a prediction unless you are absolutely certain about it!! ***
    
# Please return your answer in JSON {{"likely erroneous cell": "<CELL>"}}. If you cannot find such an erroneous cell, please return {{"likely erroneous cell": "NULL"}}."""
        # text = f"""{desc}Please return your answer in JSON {{"likely erroneous cell": "<CELL>"}}. If you cannot find such an erroneous cell, please return {{"likely erroneous cell": "NULL"}}."""
        return text
    
    def get_output(self, y):
        label = y["label"]
        
        if label is None:
            return self.answer_to_json("NULL")

        return self.answer_to_json(label)
        
        #     if y["use_cot"]:
        #         return f"All cells in the table seem to be correct and no apparent error is found. Therefore, the final answer is {answer}"
        #     else:
        #         return answer
        # else:
        #     answer = self.answer_to_json(label)

        #     if y["cot"] is not None:
        #         cot_text = []
        #         for err, cor in y["cot"]:
        #             cot_text.append(f'The cell "{err}" is misspelled and should be "{cor}".')
        #         cot_text = " ".join(cot_text)
                
        #         if y["cot_position"] == "before_answer":
        #             completion = f"{cot_text} Therefore, the answer is {answer}"
        #         elif y["cot_position"] == "after_answer":
        #             completion = f"{answer}. {cot_text}"
        #         else:
        #             raise
        #         return completion
        #     else:
        #         return answer