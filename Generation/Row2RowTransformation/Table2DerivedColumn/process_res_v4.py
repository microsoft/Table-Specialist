import re
import ast
import json

import argparse
parser = argparse.ArgumentParser(
    description='Extract the response from the gpt result')
parser.add_argument('infile', type=str, help='input file')
parser.add_argument('pl', nargs='+')
args = parser.parse_args()

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
        for pl in args.pl:
            if pl == "json":
                pattern = r'{[^}]*}'
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
                        # success_flag = False
                else:
                    res_json[pl] = matches[0].strip()
            else:
                res_json[pl] = None
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
            print(res)
            # print('err')
            # error_count += 1
            

print(f"Error count: {error_count}")
print(f"Success count: {success_count}")