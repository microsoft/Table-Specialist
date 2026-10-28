import json
import pandas as pd
import os
from table_specialist_sandbox import run_generated_code, ensure_sandbox
import sqlite3
from multiprocessing import Pool
from tqdm import tqdm
import shutil

def execute_one(exec_dir):
    assert os.path.isdir(exec_dir)
    os.chdir(exec_dir)
    # print("Executing: ", exec_dir)
    PYTHONNotFoundError = False
    RUN_PYTHON_SUCCESSED = False
    with open(exec_dir + "/exec.log", "w+") as f:
        info = json.load(open(exec_dir + "/info.json"))
        PYTHONNotFoundError = info["PYTHONNotFoundError"]
        if info["PYTHONNotFoundError"]:
            f.write("PYTHONNotFoundError: " +
                    str(info["PYTHONNotFoundError"]) + "\n")
        else:
            # run the python code
            try:
                result = run_generated_code(os.getcwd(), "python", "query.py", timeout=10)
                exit_code = result.returncode
                output = result.stdout.strip()
                error = result.stderr.strip()

                if exit_code != 0:
                    f.write("Error when running Python code: \n")
                    f.write(error + "\n")
                else:
                    f.write("Successfully run Python code\n")
                    if os.path.exists("result.csv"):
                        shutil.move("result.csv", "result_python.csv")
                        f.write("result.csv renamed to result_python.csv\n")
                        RUN_PYTHON_SUCCESSED = True
                    else:
                        f.write("No result.csv generated for python\n")
            except Exception as e:
                f.write("Error when running Python code: \n")
                f.write(str(e) + "\n")

        PYTHON_DERIVED_COLUMN_Generated = False
        if RUN_PYTHON_SUCCESSED:
            try:
                df_python = pd.read_csv("result_python.csv")
                if "derived_column" in df_python.columns:
                    PYTHON_DERIVED_COLUMN_Generated = True
            except Exception as e:
                PYTHON_DERIVED_COLUMN_Generated = False

    exec_info = {
        "RUN_PYTHON_SUCCESSED": RUN_PYTHON_SUCCESSED,
        "PYTHONNotFoundError": PYTHONNotFoundError,
        "PYTHON_DERIVED_COLUMN_Generated": PYTHON_DERIVED_COLUMN_Generated,
    }
    with open(exec_dir + "/exec.json", "w+") as f:
        json.dump(exec_info, f, indent=4)
    return exec_info


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("exec_dir", type=str,
                        help="The directory to execute")
    args = parser.parse_args()
    ensure_sandbox("python")
    
    exec_root = os.path.abspath(args.exec_dir)
    exec_dirs = [exec_root + "/" + x for x in os.listdir(
        exec_root) if os.path.isdir(exec_root + "/" + x)]
    with Pool() as p:
        results = list(
            tqdm(p.imap(execute_one, exec_dirs), total=len(exec_dirs), ncols=100))
        # results = p.map(execute_one, exec_dirs)
    rst_df = pd.DataFrame(results)
    print(rst_df.sum(axis=0))  # count
    print(rst_df.sum(axis=0) / rst_df.shape[0])  # success rate
