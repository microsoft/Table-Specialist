import os
import pandas as pd
import numpy as np
from ..base.base_data_generator import BaseDataGenerator
from .r2r_base_prompt_generator import R2RBasePromptGenerator
from .r2r_base_task_descriptor import R2RBaseTaskDescriptor
import json
from functools import partial
from copy import deepcopy

class R2RBaseDataGenerator(BaseDataGenerator):     
    def __init__(self, pass_k=1, *args, **kwargs):
        super().__init__(*args, **kwargs) 
        # no few shot for row transformation
        self.num_few_shot_samples = 0
        self.num_few_shot_trials = 0
        self.prob_train_few_shot = 0
        self.pass_k = pass_k
        
    def load_df(self, df_path, info=None):
        try:
            df = pd.read_csv(df_path, dtype=str, keep_default_na=False)
        except:
            try:
                df = pd.read_csv(df_path, encoding="latin", keep_default_na=False)
            except Exception as e:
                print(str(e))
                raise

        return df

    
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
        
    def _load_task_descriptor_params(self, dataset_info):
        with open(os.path.join(dataset_info["dataset_dir"], "info.json"), "r") as f:
            info = json.load(f)
        params = {"mode": self.mode}
        return params
            
    def _get_prompt_generator(self, params):
        prompt_generator = R2RBasePromptGenerator(**params)
        return prompt_generator
    
    def _get_task_descriptor(self, params):
        task_descriptor = R2RBaseTaskDescriptor(**params)
        return task_descriptor
    
    def _load_metadata(self, data_info):
        with open(os.path.join(data_info["dataset_dir"], "info.json"), "r") as f:
            info = json.load(f)
        metadata = {
            "filename": info["filename"]
        }
        return metadata
    
    def _load_data_label(self, data_info):
        data_dir = data_info["dataset_dir"]
        with open(os.path.join(data_dir, "info.json"), "r") as f:
            info = json.load(f)
        data = self.load_df(os.path.join(data_dir, "data.csv"))
        
        y = {
            "label": info["label"],
            "cot": None
        }
        if self.use_cot:
            cot_data_path = self.get_cot_data_path(data_info["dataset_dir"])
            if os.path.exists(cot_data_path):
                cot_data = pd.read_csv(cot_data_path)
                y["cot"] = cot_data["cot"].values[0]
        return data, y
    
    def generate_test_one_dataset(self, idx, datasets):
        test_dataset_info = deepcopy(datasets[idx])
        if self.verbose:
            print("Processing dataset", test_dataset_info["dataset"])

        seed = self.random_state

        # load test data
        test_data_dict = self._load_data_dict(test_dataset_info)

        test_data = []

        # zeroshot
        for _ in range(self.pass_k):
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