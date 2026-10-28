import json
import pandas as pd
import os
from table_specialist_sandbox import run_generated_code, ensure_sandbox, SandboxExecutionError
import sqlite3
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import shutil

def _run_spark(params):
    exec_dir, scala_path, num_cpu = params
    # Each model output gets its own container and its own input table.
    try:
        result = run_generated_code(exec_dir, "scala", os.path.basename(scala_path), num_cpu=num_cpu)
    except SandboxExecutionError as exc:
        with open(scala_path + ".err", "w", encoding="utf-8") as file:
            file.write(str(exc))
        return False
    with open(scala_path + ".log", "w", encoding="utf-8") as file:
        file.write(result.stdout)
    with open(scala_path + ".err", "w", encoding="utf-8") as file:
        file.write(result.stderr)
    return result.returncode == 0

def process_one_spark_result(exec_dir):
    assert os.path.isdir(exec_dir)
    os.chdir(exec_dir)
    with open(os.path.join(exec_dir, 'exec.json'), 'r') as f:
        exec_info = json.load(f)
    
    RUNScalaSuccess = False
    with open(exec_dir + "/exec.log", "a+") as f:
        if os.path.exists(os.path.join(exec_dir, 'result_scala')):
            out_csv = [x for x in os.listdir(os.path.join(exec_dir, 'result_scala')) if x.endswith(".csv")]
            if len(out_csv) == 1:
                shutil.copy(os.path.join(exec_dir, 'result_scala', out_csv[0]), os.path.join(exec_dir, 'result_scala.csv'))
                RUNScalaSuccess = True
            else:
                f.write("No output csv found or more than one csv file found\n")
        else:
            f.write("No result_scala directory found\n")
    
    exec_info["RUNScalaSuccess"] = RUNScalaSuccess
    with open(exec_dir + "/exec.json", "w+") as f:
        json.dump(exec_info, f, indent=4)

    return exec_info

def execute_one_sql(exec_dir):
    assert os.path.isdir(exec_dir)
    os.chdir(exec_dir)
    # print("Executing: ", exec_dir)
    SQLNotFoundError = False
    CREATE_TABLE_SUCCESSED = False
    QUERY_SQLITE3_SUCCESSED = False
    with open(exec_dir + "/exec.log", "w+") as f:
        info = json.load(open(exec_dir + "/info.json"))
        SQLNotFoundError = info["SQLNotFoundError"]
        if info["SQLNotFoundError"]:
            f.write("SQLNotFoundError: " +
                    str(info["SQLNotFoundError"]) + "\n")
        else:
            df = pd.read_csv(exec_dir + "/data.csv", keep_default_na=False)

            try:
                db_path = exec_dir + "/data.db"
                conn = sqlite3.connect(db_path)
                df.to_sql("table", conn, index=False, if_exists="replace")
                conn.commit()
                CREATE_TABLE_SUCCESSED = True
                f.write("Successfully write table to sqlite3\n")
            except Exception as e:
                f.write("Error when writing to sqlite: \n")
                f.write(str(e) + "\n")

            # query the table
            if CREATE_TABLE_SUCCESSED:
                with open(exec_dir + "/query.sql", "r") as f_sql:
                    sql = f_sql.readlines()
                    sql = "".join(sql)
                # sql = info["response"]["SQL"]
                sql = sql.replace("FROM table", "FROM \"table\"")
                f.write("Query SQL: \n" + sql + "\n")
                try:
                    cursor = conn.cursor()
                    rst = cursor.execute(sql).fetchall()
                    header = [x[0] for x in cursor.description]
                    conn.close()
                    pd.DataFrame(rst, columns=header).to_csv(
                        exec_dir + "/query_rst.csv", index=False)
                    QUERY_SQLITE3_SUCCESSED = True
                    f.write("Successfully query table from sqlite3\n")
                except Exception as e:
                    f.write("Error when querying SQLite3: \n")
                    f.write(str(e) + "\n")

    exec_info = {
        "CREATE_TABLE_SUCCESSED": CREATE_TABLE_SUCCESSED,
        "QUERY_SQLITE3_SUCCESSED": QUERY_SQLITE3_SUCCESSED,
        "SQLNotFoundError": SQLNotFoundError,
    }
    with open(exec_dir + "/exec.json", "w+") as f:
        json.dump(exec_info, f, indent=4)
    return exec_info


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("exec_dir", type=str,
                        help="The directory to execute")
    parser.add_argument("--n_jobs", type=int, default=16,
                        help="The number of processes")
    args = parser.parse_args()
    ensure_sandbox("scala")
    
    exec_root = os.path.abspath(args.exec_dir)
    exec_dirs = [exec_root + "/" + x for x in os.listdir(
        exec_root) if os.path.isdir(exec_root + "/" + x) and x.startswith("exec")]
    
    with Pool() as p:
        results = list(
            tqdm(p.imap(execute_one_sql, exec_dirs), total=len(exec_dirs), desc="Executing SQL"))
        # results = p.map(execute_one, exec_dirs)
    rst_df = pd.DataFrame(results)
    print(rst_df.sum(axis=0))  # count
    print(rst_df.sum(axis=0) / rst_df.shape[0])  # success rate

    params_list = [(case_dir, os.path.join(case_dir, "query.scala"), 1)
                   for case_dir in exec_dirs if os.path.isfile(os.path.join(case_dir, "query.scala"))]
    with Pool(args.n_jobs) as pool:
        results = tqdm(pool.map(_run_spark, params_list), total=len(params_list), desc="Running Scala code")

    with Pool() as p:
        results = list(
            tqdm(p.imap(process_one_spark_result, exec_dirs), total=len(exec_dirs), desc="Processing Scala result"))
    rst_df = pd.DataFrame(results)
    print(rst_df.sum(axis=0))  # count
    print(rst_df.sum(axis=0) / rst_df.shape[0])  # success rate
