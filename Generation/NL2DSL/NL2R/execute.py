import json
import pandas as pd
import os
from table_specialist_sandbox import run_generated_code, ensure_sandbox
from multiprocessing import Pool
from tqdm import tqdm


def execute_one(exec_dir):
    assert os.path.isdir(exec_dir)
    os.chdir(exec_dir)
    RNotFoundError = False
    RUN_R_SUCCESSED = False
    with open(exec_dir + "/exec.log", "w+") as f:
        info = json.load(open(exec_dir + "/info.json"))
        RNotFoundError = info["RNotFoundError"]
        if info["RNotFoundError"]:
            f.write("RNotFoundError: " +
                    str(info["RNotFoundError"]) + "\n")
        else:

            # run the R code
            try:
                result = run_generated_code(os.getcwd(), "r", "query.r", timeout=15)
                exit_code = result.returncode
                output = result.stdout.strip()
                error = result.stderr.strip()

                if exit_code != 0:
                    f.write("Error when running R code: \n")
                    f.write(error + "\n")
                else:
                    RUN_R_SUCCESSED = True
                    f.write("Successfully run R code\n")
            except Exception as e:
                f.write("Error when running R code: \n")
                f.write(str(e) + "\n")

    exec_info = {
        "RUN_R_SUCCESSED": RUN_R_SUCCESSED,
        "RNotFoundError": RNotFoundError,
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
    ensure_sandbox("r")
    
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
                tqdm(p.imap(execute_one, exec_dirs), total=len(exec_dirs), desc="Executing R code", ncols=100))
            # results = p.map(execute_one, exec_dirs)
        rst_df = pd.DataFrame(results)
        print(rst_df.sum(axis=0))  # count
        print(rst_df.sum(axis=0) / rst_df.shape[0])  # success rate
