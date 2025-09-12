from ..base.base_prompt_generator import BasePromptGenerator, np


class CTAPromptGenerator(BasePromptGenerator):    
    def _generate_fewshot_prompt(self, test_data, train_samples):
        """train_samples: a dataframe with multi-index (lid, rid, label). 
                            The columns from left and right table have suffix "_A" and "_B".
        """
        test_query = self.task_descriptor.get_input(test_data, random_state=self.random_state)
        
        train_prompt_list = []
        for i, (train_data, y, prob) in enumerate(train_samples):
            query = self.task_descriptor.get_input(train_data, random_state=self.random_state)
            answer = self._generate_completion(y, prob)  
            prompt = self.generate_fewshot_example_prompt(query, answer, random_state=self.random_state)
            train_prompt_list.append(prompt)
        
        prompt = self.format_fewshot_prompt(train_prompt_list, test_query)
        if self.use_system_message:
            system_message = self.get_system_message()
            prompt = f"{system_message}\n\n{prompt}"
        return prompt
    
    def _generate_completion(self, y, prob) -> str:
        return self.task_descriptor.get_output(y, prob)
    
    def generate_completion(self, y, prob):
        completion = self._generate_completion(y, prob)
        return  f" {completion} {self.completion_ending}"
    
    def format_zeroshot_prompt(self, test_query, random_state=None):
        if random_state is not None:
            np.random.seed(random_state)
        
        position = self.get_zeroshot_position(random_state=None)
        task_desc_title = self.get_task_desc_title(random_state=None)
        task_desc_text = self.task_descriptor.get_task_description(random_state=None)
        # output_title = self.get_output_section_title(random_state=None)
        # input_title = self.get_input_section_title(random_state=None)
        input_title, output_title = self.get_input_output_section_title_pair(random_state=random_state)
        
        # if position == "decription_first":
        prompt = (
            f"{task_desc_title} "
            f"{task_desc_text}\n\n"
            f"{input_title}\n"
            f"{test_query.strip()}\n\n"
            f"{self._get_suffix()}Please give no explanations, just one JSON result for the last table above."
            f"{output_title}\n"
        )
        # else:
        #     prompt = (
        #         f"{task_desc_title}\n\n"
        #         f"{input_title}\n"
        #         f"{test_query.strip()}\n\n"
        #         f"{task_desc_text}\n\n"
        #         f"{output_title}\n"
        #     )
        return prompt
    
    def format_fewshot_prompt(self, train_prompt_list, test_query, random_state=None):
        if random_state is not None:
            np.random.seed(random_state)
            
        example_sep = self.get_example_sep(random_state=None)
        section_sep = self.get_example_sep(random_state=None)
        task_desc_title = self.get_task_desc_title(random_state=None)
        task_desc_title_2 = self.get_task_desc_title(random_state=None)
        task_desc_text = self.task_descriptor.get_task_description(random_state=None)
        task_desc_text_2 = self.task_descriptor.get_task_description(random_state=None)
        # input_title = self.get_input_section_title(random_state=None)
        # output_title = self.get_output_section_title(random_state=None)
        task_desc_text_2 = task_desc_text
        task_desc_title_2 = task_desc_title
        input_title, output_title = self.get_input_output_section_title_pair(self.random_state)
        
        example_title = self.get_example_section_title(random_state=None)
        position = self.get_zeroshot_position(random_state=None)
        
        few_shot_text = []
        for i, ex in enumerate(train_prompt_list):
            ex_text = (
                # f"Example {i+1}:\n"
                f"{ex}"
            )
            few_shot_text.append(ex_text)
        # train_prompt = f"{example_sep}".join(few_shot_text)
        train_prompt = f"\n\n".join(few_shot_text)
        
        # if position == "decription_first":
        prompt = (
            f"{task_desc_title} "
            f"{task_desc_text}\n\n"
            # f"{section_sep}"
            # f"{example_title}\n"
            f"{train_prompt}\n\n"
            # f"{section_sep}"
            # f"{task_desc_title_2}\n"
            # f"{task_desc_text_2}\n\n"
            f"{input_title}\n"
            f"{test_query.strip()}\n\n"
            f"{self._get_suffix()}Please give no explanations, just one JSON result for the last table above."
            f"{output_title}\n"
        )
        # else:
        #     prompt = (
        #         f"{task_desc_title}\n"
        #         f"{task_desc_text}\n"
        #         f"{section_sep}"
        #         f"{example_title}\n"
        #         f"{train_prompt}\n"
        #         f"{section_sep}"
        #         f"# Task:\n"
        #         f"{input_title}\n"
        #         f"{test_query.strip()}\n\n"
        #         f"{task_desc_text_2}\n"
        #         f"{output_title}\n"
        #     )
        return prompt
    
