import json
import pandas as pd
import os
import subprocess
from multiprocessing import Pool
from tqdm import tqdm


def execute_one(exec_dir):
    assert os.path.isdir(exec_dir)
    os.chdir(exec_dir)
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
                result = subprocess.run(
                    ['python3', "query.py"], capture_output=True, text=True, timeout=10)
                exit_code = result.returncode
                output = result.stdout.strip()
                error = result.stderr.strip()

                if exit_code != 0:
                    f.write("Error when running Python code: \n")
                    f.write(error + "\n")
                else:
                    RUN_PYTHON_SUCCESSED = True
                    f.write("Successfully run Python code\n")
            except Exception as e:
                f.write("Error when running Python code: \n")
                f.write(str(e) + "\n")

    exec_info = {
        "RUN_PYTHON_SUCCESSED": RUN_PYTHON_SUCCESSED,
        "PYTHONNotFoundError": PYTHONNotFoundError,
    }
    with open(exec_dir + "/exec.json", "w+") as f:
        json.dump(exec_info, f)
    return exec_info


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("exec_dir", type=str, nargs="+",
                        help="The directory to execute")
    args = parser.parse_args()
    
    for exec_dir in args.exec_dir:
        print(f"Executing {exec_dir}")
        if not os.path.isdir(exec_dir):
            print(f"Error: {exec_dir} is not a directory")
            exit(1)
        exec_root = os.path.abspath(exec_dir)
        exec_dirs = [exec_root + "/" + x for x in os.listdir(
            exec_root) if os.path.isdir(exec_root + "/" + x)]
        with Pool() as p:
            results = list(
                tqdm(p.imap(execute_one, exec_dirs), total=len(exec_dirs), desc="Executing Python code", ncols=100))
            # results = p.map(execute_one, exec_dirs)
        rst_df = pd.DataFrame(results)
        print(rst_df.sum(axis=0))  # count
        print(rst_df.sum(axis=0) / rst_df.shape[0])  # success rate
