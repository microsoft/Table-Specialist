import os
import pandas as pd
import numpy as np
from ..base.base_data_generator import BaseDataGenerator, partial, Pool, tqdm
from .sm_prompt_generator import SMPromptGenerator
from .sm_task_descriptor import SMTaskDescriptor
import json
from copy import deepcopy

class SMDataGenerator(BaseDataGenerator):            
    def _get_prompt_generator(self, params):
        prompt_generator = SMPromptGenerator(**params)
        return prompt_generator
    
    def _get_task_descriptor(self, params):
        task_descriptor = SMTaskDescriptor(**params)
        return task_descriptor
    
    def _load_data_label(self, data_info):
        data_dir = data_info["dataset_dir"]
        with open(os.path.join(data_dir, "info.json"), "r") as f:
            info = json.load(f)
        table1 = self.load_df(os.path.join(data_dir, "table1.csv"))
        table2 = self.load_df(os.path.join(data_dir, "table2.csv"))
        column_map = {}
        for c1, c2 in zip(info["old_headers"], info["alternative_headers"]):
            column_map[c1] = c2
        label = []
        
        for c in table1.columns:
            if c not in column_map:
                label.append((c, None))
            else:
                c2 = column_map[c]
                if c2 in table2.columns:
                    label.append((c, c2))
                else:
                    label.append((c, None))
                
        return (table1, table2), label

    def _get_generated_train_datasets_info(self, data_dir, selected_benchmarks=None):
        datasets = []
        if not os.path.exists(data_dir):
            print("Not Exists Warning:", data_dir)
            return datasets

        if selected_benchmarks is not None:
            benchmarks = selected_benchmarks
        else:
            benchmarks = sorted(os.listdir(data_dir))

        for benchmark in benchmarks:
            assert os.path.exists(os.path.join(
                data_dir, benchmark)), f"benchmark {benchmark} not exists in {data_dir}"
        print(f"Benchmarks used in {data_dir} : {benchmarks}")

        for benchmark in benchmarks:
            for dataset in sorted(os.listdir(os.path.join(data_dir, benchmark))):
                dataset_info = {
                    "benchmark": benchmark,
                    "dataset": dataset,
                    "dataset_dir": os.path.join(data_dir, benchmark, dataset),
                }
                datasets.append(dataset_info)
        return datasets

    def generate_test_one_dataset(self, idx, datasets):
        test_dataset_info = deepcopy(datasets[idx])
        if self.verbose:
            print("Processing dataset", test_dataset_info["dataset"])

        seed = self.random_state

        # load test data
        test_data_dict = self._load_data_dict(test_dataset_info)

        test_data = []

        # zeroshot
        for _ in range(3):
            zero_df = self._generate_data_one_case(test_data_dict, None, random_state=seed)
            test_data.append(zero_df)

        # load fewshot data info
        # few shot
        if self.num_few_shot_samples > 0:
            fewshot_datasets_info = self._get_fewshot_datasets_info(
                test_dataset_info, self.sample_method)
            if fewshot_datasets_info is not None:
                for trial_num in range(self.num_few_shot_trials):
                    fewshot_data_dict = self._load_fewshot_data_dict(
                        fewshot_datasets_info, num_samples=self.num_few_shot_samples, random_state=seed+trial_num)
                    fewshot_df = self._generate_data_one_case(
                        test_data_dict, fewshot_data_dict, random_state=seed+trial_num)
                    test_data.append(fewshot_df)

        test_data = pd.concat(test_data, axis=0).reset_index(drop=True)

        if self.debug_dir is not None:
            save_path = os.path.join(
                self.debug_dir, f"{test_dataset_info['benchmark']}_{test_dataset_info['dataset']}.csv")
            test_data.to_csv(save_path, index=False)
        return test_data
