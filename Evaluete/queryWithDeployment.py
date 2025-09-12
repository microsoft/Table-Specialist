import pandas as pd
import openai
import os
import random
from io import StringIO
import threading
import queue
import json
from datetime import date
from openai import AzureOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff
from tqdm import tqdm
import time

import logging
logger = logging.getLogger()
# logger.setLevel(logging.INFO)
logformatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logformatter)
logger.addHandler(consoleHandler)


# Queue to hold queries
query_queue = queue.Queue()

# Lock for synchronizing file write operations
file_lock = threading.Lock()

@retry(wait=wait_random_exponential(min=1, max=30), stop=stop_after_attempt(3))
def query_request(client, model, prompt, temperature=1.0, timeout=60):
    try:
        completion = client.chat.completions.create(
            model=model, messages=[
                {"role": "system", "content": "You are an AI assistant. Provide an answer to some data/table related questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            timeout=timeout
        )
        return completion.choices[0].message.content
    except openai.NotFoundError as e:
        logger.error(f"Deployment {model} not found")
        exit(1)
    except openai.APITimeoutError as e:
        logger.error(f"Timeout error (timeout={timeout}): {e}")
        return f"API Timeout (timeout={timeout})"
    except openai.RateLimitError as e:
        logger.error(f"Rate limit error.")
        raise e
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise e



def create_query_azure_openai_func(model):
    def query(prompt, temperature):
        client = AzureOpenAI(
            azure_endpoint="https://<YOUR-AZURE-ENDPOINT>.openai.azure.com/",
            api_key=os.getenv("<AZURE_OPENAI_KEY>"),
            api_version="2024-12-01-preview"
        )
        return query_request(client, model, prompt, temperature)
    query.__name__ = f"query_with_azure_openai_{model.replace('-', '_')}"
    return query


def query_worker(one_query_function_pointer, temperature, output_file, pbar):
    while not query_queue.empty():
        json_line = None
        result = ""
        try:
            json_line = query_queue.get()
            messages = json_line['prompt']
            result = one_query_function_pointer(messages, temperature)
            logger.info(
                f"processed with {one_query_function_pointer.__name__}")
        except queue.Empty:
            break
        except Exception as e:
            print(f"Error processing query: {e}")
            result = ""
        finally:
            query_queue.task_done()
        if json_line:
            json_line['response'] = result
            line = json.dumps(json_line) + "\n"

            pbar.update(1)

            # Safely write response to a file
            with file_lock:
                with open(output_file, 'a') as file:
                    file.write(line)

# main entry point for multi-thread querying


def query_chat_endpoint(input_file, output_file, query_endpoints, temperature, n_parallel_call_per_key=4):
    print(f"Evaluating {input_file} ...")
    with open(output_file, 'w') as f:
        pass  # create empty file

    with open(input_file, 'r') as f:

        for line in f:
            # Parse each line as JSON and add to the list
            json_line = json.loads(line)

            # add all queries to queue
            query_queue.put(json_line)

    # mutli-threaded querying
    all_query_function_pointers = query_endpoints*n_parallel_call_per_key
    threads = []

    total_tasks = query_queue.qsize()
    progress_bar = tqdm(total=total_tasks, desc="Querying OpenAI", ncols=100)

    for one_query_function_pointer in all_query_function_pointers:
        thread = threading.Thread(target=query_worker, args=(
            one_query_function_pointer, temperature, output_file, progress_bar))
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    progress_bar.close()

    print("All threads completed\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", nargs="+", type=str,
                        help="input file path")
    parser.add_argument("--save_dir", default=None)
    parser.add_argument("-n", "--n_parallel_call_per_key", default=1,
                        type=int, help="number of parallel calls per key")
    parser.add_argument(
        "-e", "--engine", default="gpt-3.5-turbo-1106", type=str, help="engine name")
    parser.add_argument("-l", "--log_level", default="warn", choices=["info", "warn"], type=str)
    parser.add_argument("--temperature", "-t", default=0, type=float)
    parser.add_argument("--timeout", default=60, type=int)
    args = parser.parse_args()

    print(f"Model: {args.engine}")

    if args.log_level == "info":
        logger.setLevel(logging.INFO)
    elif args.log_level == "warn":
        logger.setLevel(logging.WARN)

    for input_file in args.input_file:
        assert os.path.exists(input_file), "input file not found"
        logger.info(f"Evaluating {input_file} with {args.engine}...")

        task_name = os.path.abspath(input_file).split('/')[8]
        
        today = date.today().strftime("%m_%d_%Y")
        if args.save_dir is None:
            save_dir = f'result_{task_name.upper()}/result_{today}'
        else:
            save_dir = args.save_dir
        if not os.path.exists(os.path.join(save_dir, 'preds')):
            os.makedirs(os.path.join(save_dir, 'preds'))


        output_file = input_file.split(
            '/')[-1] + '.' + args.engine + "_temp_" + "_".join(str(args.temperature).split('.')) + '.result.jsonl'
        output_file = os.path.join(save_dir, 'preds', output_file)
        if args.engine == "gpt-3.5-turbo-1106":
            query_chat_endpoint(input_file, output_file,
                                [
                                    create_query_azure_openai_func("gpt-3.5-turbo-1106"),
                                ], args.temperature, args.n_parallel_call_per_key)
        else:
            raise ValueError("Invalid engine name")
