import numpy as np
import json
import sys
from common_utils import *
from user_matching_tools import *
import os

def generate_answers_mat(user_to_contents, user_to_index, n_q=20):
    answers_mat = np.zeros(len(user_to_contents), n_q)

    for username in user_to_contents:
        current_responses = user_to_contents[username]['answers']
        current_index = user_to_index[username]
        current_response_vector = np.zeros(n_q)
        for i in range(n_q):
            current_response_vector[i] = current_responses[str(i)]
        answers_mat[current_index, :] = current_response_vector

    return answers_mat

def main():
    usage_str = "Receives a directory containing JSON files of user responses, an output directory, and a " \
                "list of usernames to discard, and performs two matchings: one score-based and one random, saving the " \
                "results in the output dir. The results are two JSON files with the matched pairs as values " \
                "(and indices as keys), and " \
                "one JSON file that maps the username of each participant to their two matches.\n" \
                "Args:\n" \
                "1. Input dir containing the JSON files\n" \
                "2. Text file containing the usernames to skip.\n" \
                "3. Output dir."

    if len(sys.argv) != 4:
        print(usage_str)
        return

    input_dir = sys.argv[1]
    discard_file = sys.argv[2]
    output_dir = sys.argv[3]

    users_to_discard = open(discard_file, mode='r').readlines()
    users_to_discard = {y for y in [x.strip() for x in users_to_discard] if y != ''}

    resulting_users = dict()
    files_list = os.listdir(input_dir)
    files_list = sorted(files_list)

    n_q = 0

    for response_filename in files_list:
        current_content = json.load(open(os.path.join(input_dir, response_filename), mode='r'))
        current_username = current_content['username']
        if current_username in users_to_discard:
            continue
        if resulting_users.get(current_username, None) is not None:
            print('Repeated user: ' + current_username)
            print('Keeping latest response')
        resulting_users[current_username] = current_content
        n_q = len(current_content['answers'])

    index_to_user = dict(enumerate(resulting_users.keys()))
    user_to_index = invert_dict(index_to_user)

    # Question-based matching
    answers_mat = generate_answers_mat(resulting_users, user_to_index, n_q)
    adj_mat = create_user_mat(answers_mat)
    q_based_matched_indices = max_pair_matching(adj_mat)
    q_based_matches = dict(enumerate([(index_to_user[x[0]], index_to_user[x[1]]) for x in q_based_matched_indices]))


