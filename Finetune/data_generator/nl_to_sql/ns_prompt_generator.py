import pandas as pd
import numpy as np
from ..base.base_prompt_generator import BasePromptGenerator


class NSPromptGenerator(BasePromptGenerator):
    def get_task_desc_title(self, random_state=None):
        titles = [
            # "[Bad]\n# Task Description:",
            "# Task Description:",
            "Objective:",
            "Task:",
            "Description:",
            "Instruction:",
            # "The task instruction is described as follows:",
            # "Here is a description of the task:",
            # "The following is a description of the task instruction.",
            # "This is the explanation for the task instruction:",
            # "The task instruction is articulated as follows.",
            # "The task instruction is defined as follows:",
        ]
        return self.select_one_option(titles, random_state=random_state)  

    # def _generate_zeroshot_prompt(self, test_data):
    #     """train_samples: a dataframe with multi-index (lid, rid, label). 
    #                         The columns from left and right table have suffix "_A" and "_B".
    #     """
    #     test_query = self.task_descriptor.get_input(test_data, random_state=self.random_state)
    #     prompt = self.format_zeroshot_prompt(test_query.strip(), test_data, random_state=self.random_state)        
    #     if self.use_system_message:
    #         system_message = self.get_system_message()
    #         prompt = f"{system_message}\n\n{prompt}"
    #     return prompt
    
    # def format_zeroshot_prompt(self, test_query, test_data, random_state=None):
    #     if random_state is not None:
    #         np.random.seed(random_state)
        
    #     position = self.get_zeroshot_position(random_state=None)
    #     task_desc_title = self.get_task_desc_title(random_state=None)
    #     task_desc_text = self.task_descriptor.get_task_description(random_state=None)
    #     # output_title = self.get_output_section_title(random_state=None)
    #     # input_title = self.get_input_section_title(random_state=None)
    #     input_title, output_title = self.get_input_output_section_title_pair(random_state=random_state)
        
    #     # if position == "decription_first":
    #     incorrect_label = test_data[2]
    #     prompt = (
    #         f"{task_desc_title} "
    #         f"{task_desc_text}\n\n"
    #         f"{input_title}\n"
    #         f"{test_query.strip()}\n\n"
    #         f"{self._get_suffix()}"
    #         f"{output_title}\n"
    #         f"```sql\n{incorrect_label}\n```"
    #     )
    #     # else:
    #     #     prompt = (
    #     #         f"{task_desc_title}\n\n"
    #     #         f"{input_title}\n"
    #     #         f"{test_query.strip()}\n\n"
    #     #         f"{task_desc_text}\n\n"
    #     #         f"{output_title}\n"
    #     #     )
    #     return prompt
