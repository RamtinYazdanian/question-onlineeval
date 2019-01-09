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
    usage_str = 'Input dir (the JSON files), The JSON file containing each user\'s contributions, Output dir'
    if len(sys.argv) != 4:
        print(usage_str)
        return
    input_dir = sys.argv[1]
    contribs_filename = sys.argv[2]
    output_dir = sys.argv[3]

    contribs_dict = json.load(open(contribs_filename, 'r'))
    starting_day = 12
    starting_month = 12
    all_filenames = os.listdir(input_dir)
    all_filenames = [x for x in all_filenames if int(x.split('_')[2]) >= starting_day or
                                                 int(x.split('_')[1]) != starting_month]
    all_jsons = dict()
    for x in all_filenames:
        print(x)
        with open(os.path.join(input_dir, x), 'r') as f:
            current_json = json.load(f)
            current_username = current_json['name_field']
            if current_username in contribs_dict:
                current_json['contrib_count'] = len(contribs_dict[current_username])
            else:
                current_json['contrib_count'] = 0
            all_jsons[x] = current_json
    with_username_removed = {x: remove_username_field(all_jsons[x]) for x in all_jsons}
    make_sure_path_exists(output_dir)
    for x in with_username_removed:
        with open(os.path.join(output_dir, 'anon_'+hashlib.md5(x.encode('utf8')).hexdigest())+'.json', 'w') as f:
            json.dump(with_username_removed[x], f)

if __name__ == '__main__':
    main()
