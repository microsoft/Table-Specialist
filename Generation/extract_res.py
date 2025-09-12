import re
import ast
import json

import argparse
parser = argparse.ArgumentParser(
    description='Extract the response from the gpt result')
parser.add_argument('infile', type=str, help='input file')
args = parser.parse_args()

with open(args.infile, 'r') as f:
    data = f.readlines()
json_data = [json.loads(d) for d in data]

error_count = 0
success_count = 0
with open(args.infile + ".extracted.jsonl", 'w+') as outfile:
    for d in json_data:
        res = d["response"]
        pattern = r'{[^}]*}'
        try:
            matches = re.findall(pattern, res)
        except Exception as e:
            print(f"!!!!! Error: {d}")
            error_count += 1
            continue
        res_dict = None
        for match in matches:
            try:
                res_dict = ast.literal_eval(match)
            except:
                try:
                    res_dict = json.loads(match)
                except:
                    print('-----------MATCH----------------')
                    print(match)
                    continue
        if not matches:
            error_count += 1
            print('---------------------------')
            print(res)
            continue
        if res_dict:
            d["response"] = res_dict
            success_count += 1
        else:
            d["response"] = None
            error_count += 1
        try:
            outfile.write(json.dumps(d) + "\n")
        except Exception as e:
            print('err')
            # error_count += 1
            

print(f"Error count: {error_count}")
print(f"Success count: {success_count}")