import json
import pandas as pd
import os
import subprocess
import sqlite3
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import shutil
import signal
import multiprocessing

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Function call timed out")

signal.signal(signal.SIGALRM, timeout_handler)


def call_function_with_timeout(func, timeout_seconds, *args, **kwargs):
    # Set the signal handler and alarm
    signal.alarm(timeout_seconds)  # set the alarm

    try:
        result = func(*args, **kwargs)
    except TimeoutError:
        print("Function call timed out!")
        result = None
    finally:
        # Reset the alarm
        signal.alarm(0)
    return result

def call_with_timeout(func, args=(), kwargs={}, timeout=10):
    # Create a multiprocessing Pool with 1 worker
    pool = multiprocessing.Pool(processes=1)
    
    # Use apply_async to call the function asynchronously with a timeout
    result = pool.apply_async(func, args, kwargs)
    
    # Close the pool and wait for the result with the specified timeout
    pool.close()
    pool.join(timeout)
    
    # If the result is ready, return it
    if result.ready():
        return result.get()
    else:
        # If timeout occurs, terminate the pool and raise an exception
        pool.terminate()
        raise TimeoutError(f"Function '{func.__name__}' timed out after {timeout} seconds")

import time
# Create a function to limit query execution time
def execute_with_timeout(cursor, query, timeout_ms):
    start_time = time.time()
    timeout_s = timeout_ms / 1000.0

    # Define the progress handler callback
    def progress_handler():
        if time.time() - start_time > timeout_s:
            # Returning a non-zero value aborts the query
            return 1
        return 0

    # Set the progress handler
    cursor.connection.set_progress_handler(progress_handler, 1000)  # Called every 1000 instructions

    try:
        cursor.execute(query)
        return cursor.fetchall()  # Return the results if query succeeds
    except sqlite3.OperationalError as e:
        print(f"Operational error: {e}")
        if str(e) == "interrupted":
            print("Query timed out.")
        else:
            raise  # Re-raise other operational errors
    finally:
        # Reset the progress handler after execution
        cursor.connection.set_progress_handler(None, 0)



def query(conn, sql):
    cursor = conn.cursor()
    call_function_with_timeout(cursor.execute, 10, sql)
    rst = cursor.fetchall()
    header = [x[0] for x in cursor.description]
    return pd.DataFrame(rst, columns=header)


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
                sql = sql.replace("FROM table", "FROM \"table\"").replace("FROM InputTable", "FROM \"table\"").replace("FROM input_table", "FROM \"table\"")
                f.write("Query SQL: \n" + sql + "\n")
                try:
                    if sql.startswith("WITH RECURSIVE"):
                        QUERY_SQLITE3_SUCCESSED = False
                        raise Exception("WITH RECURSIVE")
                    cursor = conn.cursor()
                    # call_function_with_timeout(cursor.execute, 10, sql)
                    # cursor.execute(sql)
                    rst = execute_with_timeout(cursor, sql, 10000)
                    # rst = cursor.fetchall()
                    header = [x[0] for x in cursor.description]
                    conn.close()
                    # rst = query(conn, sql)
                    pd.DataFrame(rst, columns=header).to_csv(
                        exec_dir + "/result_sql.csv", index=False)
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
    args = parser.parse_args()
    
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