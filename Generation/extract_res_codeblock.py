import re
import ast
import json

import argparse
parser = argparse.ArgumentParser(
    description='Extract the response from the gpt result')
parser.add_argument('infile', type=str, help='input file')
parser.add_argument('pl', nargs='+')
args = parser.parse_args()

def extract_biggest_json(text):
    # Find the starting index of the first opening curly brace
    start_index = text.find('{')
    
    if start_index == -1:
        return None
    
    # Initialize a stack to keep track of nested braces
    stack = []
    # Initialize variables to keep track of the largest JSON object
    max_len = 0
    max_json = None
    current_json = ''
    
    # Iterate through the text starting from the index of the first opening brace
    for i in range(start_index, len(text)):
        char = text[i]
        
        if char == '{':
            # Push opening brace index to the stack
            stack.append(i)
        elif char == '}':
            # Pop the last opening brace index from the stack
            opening_brace_index = stack.pop()
            # Extract the JSON object
            json_str = text[opening_brace_index:i+1]
            # Update max_json if the current JSON object is larger
            if len(json_str) > max_len:
                max_len = len(json_str)
                max_json = json_str
        # Break loop if stack is empty (no more nested JSON objects)
        if not stack:
            break
    
    return max_json

with open(args.infile, 'r') as f:
    data = f.readlines()
json_data = [json.loads(d) for d in data]

error_count = 0
success_count = 0
with open(args.infile + ".extracted.jsonl", 'w+') as outfile:
    for d in json_data:
        res = d["response"]
        res_json = {}
        success_flag = True
        if res:
            for pl in args.pl:
                if pl == "json":
                    pattern = re.compile(r'{.*}', re.DOTALL)
                else:
                    pattern = re.compile(r"```{}(.*?)```".format(pl), re.DOTALL)
                matches = re.findall(pattern, res)
                rst = None
                if matches:
                    if pl == 'json':
                        try:
                            res_json[pl] = json.loads(matches[0].strip())
                        except Exception as e:
                            res_json[pl] = None
                            # print('-------------------ERROR-------JSON------------')
                            # print(matches[0].strip())
                            # print(res)
                            # success_flag = False
                    else:
                        res_json[pl] = matches[0].strip()
                else:
                    res_json[pl] = None
                    success_flag = False
        else:
            success_flag = False

        d["response"] = res_json
        try:
            outfile.write(json.dumps(d) + "\n")
        except Exception as e:
            success_flag = False
            pass
        if success_flag:
            success_count += 1
        else:
            error_count += 1
            print('-------------------ERROR-------------------')
            print(res)
            # print('err')
            # error_count += 1
            

print(f"Error count: {error_count}")
print(f"Success count: {success_count}")