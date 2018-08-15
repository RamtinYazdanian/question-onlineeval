import numpy as np
import json
import sys
from common_utils import *
from user_matching_tools import *
import os
import random

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

    # We can only match an even number of people, so if the total number is odd, we sacrifice the last one.
    if len(files_list) % 2 == 1:
        files_list = files_list[:len(files_list)-1]

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
    q_based_matched_indices = set(max_pair_matching(adj_mat))

    random_done = False
    while not random_done:
        random_permutation = random.sample(list(range(len(resulting_users))), len(resulting_users))
        random_matched_indices = []
        no_repetitions = True
        for i in range(0, len(random_permutation) - 1, 2):
            if (random_permutation[i], random_permutation[i+1]) not in q_based_matched_indices and \
                (random_permutation[i+1], random_permutation[i]) not in q_based_matched_indices:
                random_matched_indices.append((random_permutation[i], random_permutation[i + 1]))
            else:
                no_repetitions = False
                break
        if no_repetitions:
            random_done = True
            break

    random_match_names = dict(enumerate([(index_to_user[x[0]], index_to_user[x[1]]) for x in random_matched_indices]))
    q_based_match_names = dict(enumerate([(index_to_user[x[0]], index_to_user[x[1]], adj_mat[x[0],x[1]])
                                          for x in q_based_matched_indices]))

    q_based_matched_indices = list(q_based_matched_indices)

    user_to_matches_dict = {i:[] for i in range(0,len(resulting_users))}
    matching_lists = [q_based_matched_indices, random_matched_indices]
    for j in range(len(matching_lists)):
        current_matched_indices_list = matching_lists[j]
        for user_pair in current_matched_indices_list:
            user_to_matches_dict[user_pair[0]].append(user_pair[1])
            user_to_matches_dict[user_pair[1]].append(user_pair[0])

    user_to_matches_dict = {index_to_user[i]: [index_to_user[y] for y in user_to_matches_dict[i]]
                            for i in user_to_matches_dict}

    make_sure_path_exists(output_dir)
    with open(os.path.join(output_dir, 'random_matches.json'), mode='w') as f:
        json.dump(random_match_names, f)

    with open(os.path.join(output_dir, 'q_based_matches.json'), mode='w') as f:
        json.dump(q_based_match_names, f)

    with open(os.path.join(output_dir, 'user_to_matches.json'), mode='w') as f:
        json.dump(user_to_matches_dict, f)

if __name__ == '__main__':
    main()