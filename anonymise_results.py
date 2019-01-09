import json
import os
import sys
from common_utils import make_sure_path_exists
import hashlib

def remove_username_field(d):
    if d['name_field'] != 'THIS_USER_WAS_NOT_SUPPOSED_TO_BE_IN_THE_STUDY_CAUSE_NO_TOKEN_YEAH_SUCKS':
        print(d['name_field'])
        d['name_field'] = 'REDACTED'
    return d

def main():
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    starting_day = 12
    starting_month = 12
    all_filenames = os.listdir(input_dir)
    all_filenames = [x for x in all_filenames if int(x.split('_')[2]) >= starting_day or
                                                 int(x.split('_')[1]) != starting_month]
    all_jsons = dict()
    for x in all_filenames:
        print(x)
        with open(os.path.join(input_dir, x), 'r') as f:
            all_jsons[x] = json.load(f)
    with_username_removed = {x: remove_username_field(all_jsons[x]) for x in all_jsons}
    make_sure_path_exists(output_dir)
    for x in with_username_removed:
        with open(os.path.join(output_dir, 'anon_'+hashlib.md5(x.encode('utf8')).hexdigest()), 'w') as f:
            json.dump(with_username_removed[x], f)

if __name__ == '__main__':
    main()