import hashlib
import sys
import os
import json
from common_utils import make_sure_path_exists

def hash_usernames(usernames_list):
    usernames_list = [x.strip() for x in usernames_list]
    hash_to_username = {hashlib.md5(x.encode('utf8')).hexdigest(): x for x in usernames_list}
    tab_separated_string = '\n'.join([hash_to_username[x] + '\t' + x for x in hash_to_username])
    return hash_to_username, tab_separated_string

def main():
    if len(sys.argv) != 4:
        print('Input file 1 (experienced), Input file 2 (novice), output dir.')
        return

    experienced_file = sys.argv[1]
    novice_file = sys.argv[2]
    output_dir = sys.argv[3]

    experienced_usernames = open(experienced_file, 'r').readlines()
    novice_usernames = open(novice_file, 'r').readlines()

    experienced_hash_to_username, experienced_str = hash_usernames(experienced_usernames)
    novice_hash_to_username, novice_str = hash_usernames(novice_usernames)

    e_hashes = set(experienced_hash_to_username.keys())
    n_hashes = set(novice_hash_to_username.keys())

    print('Intersection of the two hash sets (alternatively known as "Are we fucked, or not?"):')
    print(e_hashes.intersection(n_hashes))

    make_sure_path_exists(output_dir)

    with open(os.path.join(output_dir, 'experienced_user_and_hash.txt'), 'w') as f:
        f.write(experienced_str)
    with open(os.path.join(output_dir, 'novice_user_and_hash.txt'), 'w') as f:
        f.write(novice_str)

    all_hash_to_username = experienced_hash_to_username.copy()
    all_hash_to_username.update(novice_hash_to_username)

    with open(os.path.join(output_dir, 'token_to_name_map.json'), 'w') as f:
        json.dump(all_hash_to_username, f)

if __name__ == '__main__':
    main()