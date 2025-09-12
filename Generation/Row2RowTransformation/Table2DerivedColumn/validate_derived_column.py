import pandas as pd
import os
import json
from multiprocessing import Pool
from tqdm import tqdm

def validate_one(dir_path):
    with open(os.path.join(dir_path, "exec.json"), "r") as f:
        exec = json.load(f)
        if not exec['PYTHON_R_Derived_Column_Same']:
            return False

    df_original = pd.read_csv(os.path.join(dir_path, "data.csv"))
    assert len(df_original.columns) == 1
    col_original = df_original[df_original.columns[0]]
    df_derived = pd.read_csv(os.path.join(dir_path, "result_python.csv"))
    col_derived = df_derived['derived_column']

    # same with original column
    if col_original.values.tolist() == col_derived.values.tolist():
        return False

    # derived not all nan
    if col_derived.isna().all():
        return False

    if col_derived.nunique() == col_derived.head(3).nunique():
        return False

    return True

def execute_one(exec_dir):
    if os.path.exists(os.path.join(exec_dir, "DERIVED_COLUMN_NON_TRIVIAL_FLAG")):
        os.remove(os.path.join(exec_dir, "DERIVED_COLUMN_NON_TRIVIAL_FLAG"))
    flag =  validate_one(exec_dir)
    if flag:
        open(os.path.join(exec_dir, "DERIVED_COLUMN_NON_TRIVIAL_FLAG"), "w").close()
    return {"validate": flag}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("exec_dir", type=str,
                        help="The directory to execute")
    args = parser.parse_args()
    
    exec_root = os.path.abspath(args.exec_dir)
    exec_dirs = [exec_root + "/" + x for x in os.listdir(
        exec_root) if os.path.isdir(exec_root + "/" + x)]
    with Pool() as p:
        results = list(
            tqdm(p.imap(execute_one, exec_dirs), total=len(exec_dirs)))
        # results = p.map(execute_one, exec_dirs)
    rst_df = pd.DataFrame(results)
    print(rst_df.sum(axis=0))  # count
    print(rst_df.sum(axis=0) / rst_df.shape[0])  # success rate
