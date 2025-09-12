import json
import pandas as pd
import os
import subprocess
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
    RUN_R_SUCCESSED = False
    with open(exec_dir + "/exec.log", "w+") as f:
        info = json.load(open(exec_dir + "/info.json"))
        PYTHONNotFoundError = info["PYTHONNotFoundError"]
        if info["PYTHONNotFoundError"]:
            f.write("PYTHONNotFoundError: " +
                    str(info["PYTHONNotFoundError"]) + "\n")
        else:
            # run the python code
            try:
                result = subprocess.run(
                    ['python3', "query.py"], capture_output=True, text=True, timeout=10)
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

        if info["RNotFoundError"]:
            f.write("RNotFoundError: " + str(info["RNotFoundError"]) + "\n")
        else:
            # run the R code
            try:
                result = subprocess.run(
                    ['Rscript', "query.R"], capture_output=True, text=True, timeout=10)
                exit_code = result.returncode
                output = result.stdout.strip()
                error = result.stderr.strip()

                if exit_code != 0:
                    f.write("Error when running R code: \n")
                    f.write(error + "\n")
                else:
                    f.write("Successfully run R code\n")
                    if os.path.exists("result.csv"):
                        shutil.move("result.csv", "result_R.csv")
                        f.write("result.csv renamed to result_R.csv\n")
                        RUN_R_SUCCESSED = True
                    else:
                        f.write("No result.csv generated for R\n")
            except Exception as e:
                f.write("Error when running R code: \n")
                f.write(str(e) + "\n")
        PYTHON_DERIVED_COLUMN_Generated = False
        R_DERIVED_COLUMN_Generated = False
        PYTHON_R_Derived_Column_Same = False
        PYTHON_R_Derived_Column = None
        if RUN_PYTHON_SUCCESSED and RUN_R_SUCCESSED:
            # compare the result
            try:
                df_python = pd.read_csv("result_python.csv")
                if "derived_column" in df_python.columns:
                    PYTHON_DERIVED_COLUMN_Generated = True
            except Exception as e:
                PYTHON_DERIVED_COLUMN_Generated = False

            try:
                df_R = pd.read_csv("result_R.csv")
                if "derived_column" in df_R.columns:
                    R_DERIVED_COLUMN_Generated = True
            except Exception as e:
                R_DERIVED_COLUMN_Generated = False
            
            if PYTHON_DERIVED_COLUMN_Generated and R_DERIVED_COLUMN_Generated:
                if df_python["derived_column"].equals(df_R["derived_column"]):
                    f.write("Python and R derived columns are the same\n")
                    PYTHON_R_Derived_Column_Same = True
                    PYTHON_R_Derived_Column = df_python["derived_column"].tolist()
                else:
                    f.write("Python and R derived columns are different\n")
                    PYTHON_R_Derived_Column = {
                        "Python": df_python["derived_column"].tolist(),
                        "R": df_R["derived_column"].tolist()}
    exec_info = {
        "RUN_PYTHON_SUCCESSED": RUN_PYTHON_SUCCESSED,
        "PYTHONNotFoundError": PYTHONNotFoundError,
        "RNotFoundError": info["RNotFoundError"],
        "RUN_R_SUCCESSED": RUN_R_SUCCESSED,
        "PYTHON_DERIVED_COLUMN_Generated": PYTHON_DERIVED_COLUMN_Generated,
        "R_DERIVED_COLUMN_Generated": R_DERIVED_COLUMN_Generated,
        "PYTHON_R_Derived_Column_Same": PYTHON_R_Derived_Column_Same,
        "PYTHON_R_Derived_Column": PYTHON_R_Derived_Column
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
