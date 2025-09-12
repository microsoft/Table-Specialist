import numpy as np
import pandas as pd
from utils import balance_sample_two_classes, makedir
from collections import defaultdict
from copy import deepcopy
from tqdm import tqdm
from multiprocessing import Pool
from .em_prompt_generator import EMPromptGenerator
from .em_task_descriptor_with_prob import EMTaskDescriptor
from ..base.base_data_generator import BaseDataGenerator
import json
import os
from functools import partial


class EMDataGenerator(BaseDataGenerator):
    def _get_prompt_generator(self, params):
        prompt_generator = EMPromptGenerator(**params)
        return prompt_generator

    def _get_task_descriptor(self, params):
        task_descriptor = EMTaskDescriptor(**params)
        return task_descriptor

    def _load_prompt_generator_params(self, dataset_info):
        with open(os.path.join(dataset_info["dataset_dir"], "info.json"), "r") as f:
            info = json.load(f)
        unimportant_columns = info["unimportant_columns"] if "unimportant_columns" in info else [
        ]
        params = {
            "unimportant_columns": unimportant_columns
        }
        return params

    def _load_task_descriptor_params(self, dataset_info):
        topic = "Entity"
        if self.mode == "test" and self.sample_method == "random-Ben":
            with open(os.path.join(dataset_info["dataset_dir"], "info.json"), "r") as f:
                info = json.load(f)
                topic = info["topic"] if "topic" in info else "Entity"
        params = {
            "topic": topic
        }
        return params

    def _load_datasets(self, data_dir) -> list:
        """return a list of dictionary"""
        generated_train_data_dir = os.path.join(
            data_dir, self.task, "generated", "train")
        benchmark_train_data_dir = os.path.join(
            data_dir, self.task, "benchmark", "train")
        benchmark_test_data_dir = os.path.join(
            data_dir, self.task, "benchmark", "test")
        if self.generated_data_dir:
            generated_train_datasets = self._get_generated_train_datasets_info(
                generated_train_data_dir, [self.generated_data_dir])
        else:
            generated_train_datasets = self._get_generated_train_datasets_info(
                generated_train_data_dir)
        raw_train_datasets = self._get_datasets_info(benchmark_train_data_dir, self.mode)
        raw_test_datasets = self._get_datasets_info(benchmark_test_data_dir, self.mode)
        return generated_train_datasets, raw_train_datasets, raw_test_datasets

    def _load_task_descriptor_params_generated(self, dataset_info):
        return {"topic": "Entity"}

    def _load_data_dict_generated(self, dataset_info) -> dict:
        data, label = self._load_data_label_generated(dataset_info)
        metadata = self._load_metadata_generated(dataset_info)
        prompt_generator_params = self._load_prompt_generator_params_generated(
            dataset_info)
        task_descriptor_params = self._load_task_descriptor_params_generated(
            dataset_info)

        data_dict = {
            "data": data,
            "label": label,
            "dataset_info": dataset_info,
            "metadata": metadata,
            "prompt_generator_params": prompt_generator_params,
            "task_descriptor_params": task_descriptor_params
        }
        return data_dict

    def _get_generated_train_datasets_info(self, data_dir, selected_benchmarks=None):
        datasets = []

        if selected_benchmarks is not None:
            benchmarks = selected_benchmarks
        else:
            benchmarks = sorted(os.listdir(data_dir))

        for benchmark in benchmarks:
            assert os.path.exists(os.path.join(
                data_dir, benchmark)), f"benchmark {benchmark} not exists in {data_dir}"
        print(f"Benchmarks used in {data_dir} : {benchmarks}")

        for benchmark in benchmarks:
            gt = pd.read_json(os.path.join(
                data_dir, benchmark, "train.jsonl"), lines=True, orient="records")
            for i in range(len(gt)):
                dataset_info = {
                    "benchmark": benchmark,
                    "dataset": benchmark,
                    "dataset_dir": os.path.join(data_dir, benchmark),
                    "mode": "train",
                    "row_id": i,
                    "table": gt.loc[i, "table"]
                }
                datasets.append(dataset_info)
        return datasets

    def _get_datasets_info(self, data_dir, mode):
        datasets = []
        for benchmark in sorted(os.listdir(data_dir)):
            for dataset in sorted(os.listdir(os.path.join(data_dir, benchmark))):
                gt = pd.read_csv(os.path.join(
                    data_dir, benchmark, dataset, f"{mode}.csv"))
                for i in range(len(gt)):
                    dataset_info = {
                        "benchmark": benchmark,
                        "dataset": dataset,
                        "dataset_dir": os.path.join(data_dir, benchmark, dataset),
                        "mode": mode,
                        "row_id": i,
                    }
                    datasets.append(dataset_info)
        return datasets

    def _load_data_label_generated(self, data_info):
        data_dir = data_info["dataset_dir"]

        gt = pd.read_json(os.path.join(data_dir, "train.jsonl"),
                          lines=True, orient="records", dtype=str)

        row = gt.iloc[data_info["row_id"]]
        try:
            l = pd.read_json(row.l, typ="series", dtype=str)
            r = pd.read_json(row.r, typ="series", dtype=str)
        except Exception as e:
            print(row.l)
            raise e
        label = row.label
        probability = row.get("probability", 1.0)
        data = (l, r)

        y = {
            "label": label,
            "probability": probability,
            "cot": None,
            "cot_position": self.cot_position
        }
        return data, y

    def _load_data_label(self, data_info):
        data_dir = data_info["dataset_dir"]

        with open(os.path.join(data_dir, "info.json"), "r") as f:
            info = json.load(f)

        left = self.load_df(os.path.join(data_dir, "tableA.csv"), info=info)
        right = self.load_df(os.path.join(data_dir, "tableB.csv"), info=info)
        gt = self.load_df(os.path.join(data_dir, f"{data_info['mode']}.csv"))

        left = left.set_index("id")
        right = right.set_index("id")

        row = gt.iloc[data_info["row_id"]]
        row_l = left.loc[row.ltable_id]
        row_r = right.loc[row.rtable_id]
        label = row.label
        probability = row.get("probability", 1.0)
        data = (row_l, row_r)

        y = {
            "label": label,
            "probability": probability,
            "cot": None,
            "cot_position": self.cot_position
        }

        if self.use_cot:
            cot_data_path = os.path.join(
                self.cot_data_dir, self.task, data_info['mode'], data_info["benchmark"], data_info["dataset"], "data.csv")
            if os.path.exists(cot_data_path):
                cot_data = pd.read_csv(cot_data_path)
                cot_data = cot_data.set_index("lrid")
                if f"{row.ltable_id}-{row.rtable_id}" in cot_data.index:
                    row_cot = cot_data.loc[f"{row.ltable_id}-{row.rtable_id}"]
                    y["cot"] = row_cot["cot"]
        return data, y

    def _load_metadata(self, data_info):
        gt = self.load_df(os.path.join(
            data_info["dataset_dir"], f"{data_info['mode']}.csv"))
        row = gt.iloc[data_info["row_id"]]
        metadata = {
            "lrid": f"{row.ltable_id}-{row.rtable_id}"
        }
        return metadata

    def _get_fewshot_datasets_info(self, data_info, sample_method):
        data_dir = data_info["dataset_dir"]
        if sample_method == "random-Ben":

            with open(os.path.join(data_dir, "info.json"), "r") as f:
                info = json.load(f)

            left = self.load_df(os.path.join(
                data_dir, "tableA.csv"), info=info)
            right = self.load_df(os.path.join(
                data_dir, "tableB.csv"), info=info)
            train = self.load_df(os.path.join(data_dir, "train.csv"))

            cot_data = None
            if self.use_cot:
                cot_data_path = os.path.join(
                    self.cot_data_dir, self.task, data_info['mode'], data_info["benchmark"], data_info["dataset"], "data.csv")
                if os.path.exists(cot_data_path):
                    cot_data = pd.read_csv(cot_data_path)
                    cot_data = cot_data.set_index("lrid")

            fewshot_datasets_info = {
                "gt": train,
                "left": left.set_index("id"),
                "right": right.set_index("id"),
                "sample_method": sample_method,
                "cot_data": cot_data
            }
            return fewshot_datasets_info
        elif sample_method == "random-Gen":
            if self.static_fewshot_datasets_info:
                return self.static_fewshot_datasets_info
            assert os.path.exists(os.path.join(
                data_dir, "train.jsonl")), f"train.jsonl does not exist in the dataset directory {data_dir}."
            gt = pd.read_json(os.path.join(data_dir, "train.jsonl"),
                              lines=True, orient="records", dtype=str)
            fewshot_datasets_info = {
                "gt": gt,
                "sample_method": sample_method
            }
            return fewshot_datasets_info
        elif sample_method == "static":
            if self.static_fewshot_datasets_info:
                return self.static_fewshot_datasets_info
            if not self.static_few_shots_version:
                raise ValueError("static_few_shots_version is not provided.")
            static_few_shots_path = os.path.join(
                data_dir, f"few_shots_v{self.static_few_shots_version}.jsonl")
            assert os.path.exists(
                static_few_shots_path), f"few_shots_v{self.static_few_shots_version}.jsonl does not exist in the dataset directory {data_dir}."
            gt = pd.read_json(static_few_shots_path,
                              lines=True, orient="records", dtype=str)
            fewshot_datasets_info = {
                "gt": gt,
                "sample_method": sample_method
            }
            return fewshot_datasets_info
        elif sample_method == "RAG":
            if self.static_fewshot_datasets_info:
                return self.static_fewshot_datasets_info
            assert os.path.exists(os.path.join(
                data_dir, "rag.jsonl")), f"rag.jsonl does not exist in the dataset directory {data_dir}."
            gt = pd.read_json(os.path.join(data_dir, "rag.jsonl"),
                              lines=True, orient="records", dtype=str)
            fewshot_datasets_info = {
                "gt": gt,
                "sample_method": sample_method
            }
            return fewshot_datasets_info
        else:
            return None

    def _load_fewshot_data_dict(self, fewshot_datasets_info, num_samples, random_state=1, table_id=None):
        # take a sample and load data dict
        fewshot_data_labels = []
        if fewshot_datasets_info["sample_method"] == "random-Ben":
            fewshot_sample_gt = balance_sample_two_classes(
                fewshot_datasets_info["gt"], num_samples, random_state=random_state)
            for _, row in fewshot_sample_gt.iterrows():
                l = fewshot_datasets_info["left"].loc[row.ltable_id]
                r = fewshot_datasets_info["right"].loc[row.rtable_id]
                data = (l, r)
                label = row.label
                probability = row.get("probability", 1.0)
                cot_text = None
                if self.use_cot and fewshot_datasets_info["cot_data"] is not None:
                    if f"{row.ltable_id}-{row.rtable_id}" in fewshot_datasets_info["cot_data"].index:
                        cot_text = fewshot_datasets_info["cot_data"].loc[
                            f"{row.ltable_id}-{row.rtable_id}"]["cot"]

                y = {
                    "label": label,
                    "probability": probability,
                    "cot": cot_text,
                    "cot_position": self.cot_position
                }
                fewshot_data_labels.append((data, y))
        elif fewshot_datasets_info["sample_method"] == "random-Gen":
            fewshot_sample_gt = balance_sample_two_classes(
                fewshot_datasets_info["gt"], num_samples, random_state=random_state)
            for _, row in fewshot_sample_gt.iterrows():
                l = pd.read_json(row.l, typ="series", dtype=str)
                r = pd.read_json(row.r, typ="series", dtype=str)
                data = (l, r)
                label = str(row.label)
                probability = row.get("probability", 1.0)
                cot_text = None
                y = {
                    "label": label,
                    "probability": probability,
                    "cot": cot_text,
                    "cot_position": self.cot_position
                }
                fewshot_data_labels.append((data, y))
        elif fewshot_datasets_info["sample_method"] == "static":
            for _, row in fewshot_datasets_info["gt"].iterrows():
                # print(row)
                # print(row.l)
                # print(type(row.l))
                l = pd.read_json(row.l, typ="series", dtype=str)
                r = pd.read_json(row.r, typ="series", dtype=str)
                data = (l, r)
                label = str(row.label)
                cot_text = None
                y = {
                    "label": label,
                    "cot": cot_text,
                    "cot_position": self.cot_position
                }
                fewshot_data_labels.append((data, y))
            assert len(
                fewshot_data_labels) == num_samples, f"len(static_fewshot)={len(fewshot_data_labels)} != num_samples={num_samples}"
        elif fewshot_datasets_info["sample_method"] == "RAG":
            few_shot_filtered = fewshot_datasets_info["gt"]
            few_shot_filtered = few_shot_filtered[few_shot_filtered["table"] == table_id]
            assert len(
                few_shot_filtered) >= num_samples, f"RAG_examples={len(few_shot_filtered)} < num_samples={num_samples}"
            fewshot_sample_gt = balance_sample_two_classes(
                few_shot_filtered, num_samples, random_state=random_state)
            for _, row in fewshot_sample_gt.iterrows():
                l = pd.read_json(row.l, typ="series", dtype=str)
                r = pd.read_json(row.r, typ="series", dtype=str)
                data = (l, r)
                label = str(row.label)
                cot_text = None
                y = {
                    "label": label,
                    "cot": cot_text,
                    "cot_position": self.cot_position
                }
                fewshot_data_labels.append((data, y))
        else:
            raise Exception(
                "Unknown sample method. Choices: ['random-Ben', 'random-Gen', 'static', 'RAG']")

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

    def _col_perturb_test_data(self, test_data_dict, random_state) -> dict:
        data_dict_perturb = deepcopy(test_data_dict)
        row_l, row_r = data_dict_perturb["data"]
        row_l_perturb = row_l.sample(frac=1, random_state=random_state)
        row_r_perturb = row_r.sample(frac=1, random_state=random_state)
        data_dict_perturb["data"] = (row_l_perturb, row_r_perturb)
        return data_dict_perturb

    def _col_perturb_fewshot_data(self, fewshot_data_dict, random_state) -> dict:
        fewshot_data_dict_perturb = deepcopy(fewshot_data_dict)
        if fewshot_data_dict_perturb["data_label_list"] is not None:
            data_label_perturb = []
            for data, y in fewshot_data_dict_perturb["data_label_list"]:
                row_l, row_r = data
                row_l_perturb = row_l.sample(frac=1, random_state=random_state)
                row_r_perturb = row_r.sample(frac=1, random_state=random_state)
                data_perturb = (row_l_perturb, row_r_perturb)
                data_label_perturb.append((data_perturb, y))
            fewshot_data_dict_perturb["data_label_list"] = data_label_perturb
        return fewshot_data_dict_perturb

    def generate_train_one_dataset(self, idx, datasets):
        train_dataset_info = deepcopy(datasets[idx])
        if self.verbose:
            print("Processing training dataset", train_dataset_info["dataset"])

        # set seed with dataset index
        seed = self.random_state + idx

        # load train data
        train_data_dict = self._load_data_dict_generated(train_dataset_info)

        # load fewshot data info
        if self.sample_method == "random-Gen":
            fewshot_datasets_info = self._get_fewshot_datasets_info(
                train_dataset_info, self.sample_method)
        elif self.sample_method == "static":
            fewshot_datasets_info = self._get_fewshot_datasets_info(
                train_dataset_info, self.sample_method)
        elif self.sample_method == "RAG":
            fewshot_datasets_info = self._get_fewshot_datasets_info(
                train_dataset_info, self.sample_method)
        else:
            raise Exception(
                "Unknown sample method. Choices: ['random-Gen', 'static', 'rag']")
        train_data = []
        # generate one few-shot train data
        # num_samples = self._get_random_mixed_shot_num(random_state=seed)
        try:
            fewshot_data_dict = self._load_fewshot_data_dict(
                fewshot_datasets_info, num_samples=self.num_few_shot_samples, random_state=seed, table_id=train_dataset_info["table"])
        except AssertionError as e:
            print(e)
            print(
                f"Few-shot data error for {train_dataset_info['table']}. Skip this dataset.")
            raise e
            return pd.DataFrame()
        data_df = self._generate_data_one_case(
            train_data_dict, fewshot_data_dict, random_state=seed)
        train_data.append(data_df)

        # generate more train data with column perturb
        # for i in range(self.num_col_perturb):
        #     perturb_test_data_dict = self._col_perturb_test_data(test_data_dict, random_state=seed+i)
        #     perturb_fewshot_data_dict = self._col_perturb_fewshot_data(fewshot_data_dict, random_state=seed+i)
        #     tag_dict = {"colPerturbSeed": seed+i}
        #     perturb_df = self._generate_data_one_case(perturb_test_data_dict, perturb_fewshot_data_dict, random_state=seed+i, tag_dict=tag_dict)
        #     train_data.append(perturb_df)

        train_data = pd.concat(train_data, axis=0).reset_index(drop=True)

        if self.debug_dir is not None:
            save_path = os.path.join(
                self.debug_dir, f"{train_dataset_info['dataset']}.csv")
            train_data.to_csv(save_path, index=False)
        return train_data

    def generate_test_one_dataset(self, idx, datasets):
        test_dataset_info = deepcopy(datasets[idx])
        if self.verbose:
            print("Processing dataset", test_dataset_info["dataset"])

        seed = self.random_state

        # load test data
        test_data_dict = self._load_data_dict(test_dataset_info)

        test_data = []
        # disable zero shot
        if self.num_few_shot_samples == 0:
            zero_df = self._generate_data_one_case(
                test_data_dict, None, random_state=seed)
            test_data.append(zero_df)
            test_data = pd.concat(test_data, axis=0).reset_index(drop=True)
            return test_data
        # zero_df = self._generate_data_one_case(test_data_dict, None, random_state=seed)
        # test_data.append(zero_df)

        # load fewshot data info
        # few shot

        if self.sample_method == "random-Gen":
            train_dataset_info = deepcopy(self.generated_train_datasets[0])
            fewshot_datasets_info = self._get_fewshot_datasets_info(
                train_dataset_info, self.sample_method)
        elif self.sample_method == "static":
            train_dataset_info = deepcopy(self.generated_train_datasets[0])
            fewshot_datasets_info = self._get_fewshot_datasets_info(
                train_dataset_info, self.sample_method)
        elif self.sample_method == "random-Ben":
            fewshot_datasets_info = self._get_fewshot_datasets_info(
                test_dataset_info, self.sample_method)
        else:
            raise Exception("Unknown sample method")
        if fewshot_datasets_info is not None:
            for trial_num in range(self.num_few_shot_trials):
                fewshot_data_dict = self._load_fewshot_data_dict(
                    fewshot_datasets_info, num_samples=self.num_few_shot_samples, random_state=seed+trial_num)
                fewshot_df = self._generate_data_one_case(
                    test_data_dict, fewshot_data_dict, random_state=seed+trial_num)
                test_data.append(fewshot_df)

        # stanford manual
        # stanford_datasets_info = self._get_fewshot_datasets_info(test_dataset_info, "stanford")
        # if stanford_datasets_info is not None:
        #     fewshot_data_dict = self._load_fewshot_data_dict(stanford_datasets_info, num_samples=self.num_few_shot_samples, random_state=seed)
        #     stanford_df = self._generate_data_one_case(test_data_dict, fewshot_data_dict, random_state=seed)
        #     test_data.append(stanford_df)

        test_data = pd.concat(test_data, axis=0).reset_index(drop=True)

        if self.debug_dir is not None:
            save_path = os.path.join(
                self.debug_dir, f"{test_dataset_info['benchmark']}_{test_dataset_info['dataset']}.csv")
            test_data.to_csv(save_path, index=False)
        return test_data
