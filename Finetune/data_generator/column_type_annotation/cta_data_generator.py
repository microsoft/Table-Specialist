import numpy as np
import pandas as pd
from utils import balance_sample_two_classes, makedir
from collections import defaultdict
from copy import deepcopy
from tqdm import tqdm
from multiprocessing import Pool
from ..base.base_data_generator import BaseDataGenerator
from .cta_prompt_generator import CTAPromptGenerator
from .cta_task_descriptor import CTATaskDescriptor, CTATaskDescriptorTest
import json
from functools import partial
import os


class CTADataGenerator(BaseDataGenerator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.static_fewshot_datasets_info = None

    def _get_prompt_generator(self, params):
        prompt_generator = CTAPromptGenerator(**params)
        return prompt_generator

    def _get_task_descriptor(self, params):
        if self.mode == "test":
            task_descriptor = CTATaskDescriptorTest(**params)
        else:
            task_descriptor = CTATaskDescriptor(**params)
        return task_descriptor

    def _get_datasets_info(self, data_dir, selected_benchmarks=None):
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
                with open(os.path.join(data_dir, benchmark, dataset, "info.json"), "r") as f:
                    info = json.load(f)
                dataset_info = {
                    "benchmark": benchmark,
                    "dataset": dataset,
                    "dataset_dir": os.path.join(data_dir, benchmark, dataset),
                    "label": info["label"],
                    "probability": info.get("probability", 1.0)
                }
                datasets.append(dataset_info)
        return datasets

    def _load_fewshot_data_dict(self, fewshot_datasets_info, num_samples, random_state):
        if num_samples == 0:
            fewshot_data_labels = None
        else:
            # balance sample
            pos_samples = []
            neg_samples = []

            np.random.seed(random_state)
            pos_train_datasets = []
            neg_train_datasets = []

            for dataset_info in fewshot_datasets_info["datasets_info"]:
                if dataset_info["label"] is None:
                    neg_train_datasets.append(dataset_info)
                else:
                    pos_train_datasets.append(dataset_info)

            neg_num = min(num_samples // 2, len(neg_train_datasets))
            pos_num = num_samples - neg_num

            if neg_num > 0:
                neg_samples_indices = np.random.choice(
                    len(neg_train_datasets), neg_num, replace=False).tolist()
                neg_samples = [neg_train_datasets[i]
                               for i in neg_samples_indices]
            if pos_num > 0:
                pos_samples_indices = np.random.choice(
                    len(pos_train_datasets), pos_num, replace=False).tolist()
                pos_samples = [pos_train_datasets[i]
                               for i in pos_samples_indices]

            sample_datasets_info = pos_samples + neg_samples

            fewshot_data_labels = []
            for dataset_info in sample_datasets_info:
                data, label, probability = self._load_data_label(dataset_info)
                fewshot_data_labels.append((data, label, probability))

        # shuffle fewshot_data_labels
        np.random.seed(random_state)
        np.random.shuffle(fewshot_data_labels)

        fewshot_data_dict = {
            "data_label_list": fewshot_data_labels,
            "sample_method": fewshot_datasets_info["sample_method"],
            "num_samples": num_samples,
            "random_state": random_state
        }
        return fewshot_data_dict

    def _load_data_label(self, data_info):
        data_dir = data_info["dataset_dir"]
        with open(os.path.join(data_dir, "info.json"), "r") as f:
            info = json.load(f)
        # df = self.load_df(os.path.join(data_dir, "data.csv"))
        df = pd.read_csv(os.path.join(data_dir, "data.csv"),
                         dtype=str, keep_default_na=False)
        label = info["label"]
        probability = info.get("probability", 1.0)
        candidates = info.get("candidates", None)
        return (df, candidates), label, probability

    def _load_data_dict(self, dataset_info) -> dict:
        data, label, probability = self._load_data_label(dataset_info)
        metadata = self._load_metadata(dataset_info)
        prompt_generator_params = self._load_prompt_generator_params(
            dataset_info)
        task_descriptor_params = self._load_task_descriptor_params(
            dataset_info)

        data_dict = {
            "data": data,
            "label": label,
            'probability': probability,
            "dataset_info": dataset_info,
            "metadata": metadata,
            "prompt_generator_params": prompt_generator_params,
            "task_descriptor_params": task_descriptor_params
        }
        return data_dict

    def _load_metadata(self, data_info):
        data_dir = data_info["dataset_dir"]
        with open(os.path.join(data_dir, "info.json"), "r") as f:
            info = json.load(f)
        candidates = info.get("candidates", None)
        if candidates is None:
            num_cand = 0
        else:
            num_cand = len(candidates)

        metadata = {
            "numCandidates": num_cand
        }
        return metadata

    def _get_fewshot_datasets_info(self, test_data_info, sample_method):
        if sample_method == "random-Ben":
            datasets_info = []
            for data_info in self.raw_train_datasets:
                train_name = data_info["benchmark"]
                test_name = test_data_info["benchmark"]

                if train_name.endswith("Train"):
                    train_name = train_name[:-5]

                if test_name.endswith("Test"):
                    test_name = test_name[:-4]
                elif test_name.endswith("Train"):
                    test_name = test_name[:-5]

                if train_name == test_name:
                    datasets_info.append(data_info)

            fewshot_datasets_info = {
                "datasets_info": datasets_info,
                "sample_method": "random-Ben"
            }
            return fewshot_datasets_info
        elif sample_method == "random-Gen":
            if self.static_fewshot_datasets_info:
                return self.static_fewshot_datasets_info
            fewshot_datasets_info = {
                "datasets_info": self.generated_train_datasets,
                "sample_method": "random-Gen"
            }
            return fewshot_datasets_info
        else:
            return None

    def _generate_data_one_case(self, test_data_dict, fewshot_data_dict, random_state, tag_dict=None):
        """generate prompt and label with test data and fewshot data"""
        # initalize task descriptor
        task_descriptor_params = {
            "serializer": self.serializer,
            "random_state": random_state,
            "use_random_description": self.use_random_description,
            "use_cot": self.use_cot
        }
        task_descriptor_params.update(test_data_dict["task_descriptor_params"])
        task_descriptor = self._get_task_descriptor(task_descriptor_params)

        # initalize prompt generator
        prompt_generator_params = {
            "task_descriptor": task_descriptor,
            "max_token_length": self.max_token_length,
            "min_fewshot_samples": self.min_train_num_few_shot_samples,
            "use_random_template": self.use_random_template,
            "random_state": random_state,
            "use_system_message": self.use_system_message,
            "use_cot": self.use_cot
        }
        prompt_generator_params.update(
            test_data_dict["prompt_generator_params"])
        prompt_generator = self._get_prompt_generator(prompt_generator_params)

        test = test_data_dict["data"]
        label = test_data_dict["label"]
        probability = test_data_dict["probability"]

        if fewshot_data_dict is None:
            prompt = prompt_generator.generate_prompt(test, None)
        else:
            prompt = prompt_generator.generate_prompt(
                test, fewshot_data_dict["data_label_list"])

        completion = prompt_generator.generate_completion(label, probability)
        sample_method = "random" if fewshot_data_dict is None else fewshot_data_dict[
            "sample_method"]
        num_samples = 0 if fewshot_data_dict is None else fewshot_data_dict["num_samples"]

        data = {
            "task": self.task,
            "benchmark": test_data_dict["dataset_info"]["benchmark"],
            "dataset": test_data_dict["dataset_info"]["dataset"],
            "sampleMethod": sample_method,
            "numSamples": num_samples,
            "seed": random_state,
            "prompt": prompt,
            "completion": completion,
            "label": completion
        }
        if self.note:
            data["note"] = self.note
        data.update(test_data_dict["metadata"])
        data_df = pd.DataFrame([data])
        data_df["metadata"] = self._generate_metadata(
            data_df, tag_dict=tag_dict)
        return data_df
