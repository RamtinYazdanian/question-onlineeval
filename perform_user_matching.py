import numpy as np
import json
import sys
from common_utils import *
from user_matching_tools import *
import os
import random

def generate_answers_mat(user_to_contents, user_to_index, n_q=20):
    answers_mat = np.zeros((len(user_to_contents), n_q))

    for username in user_to_contents:
        current_responses = user_to_contents[username]['answers']
        current_index = user_to_index[username]
        current_response_vector = np.zeros((n_q))
        for i in range(n_q):
            current_response_vector[i] = current_responses[str(i)]
        answers_mat[current_index, :] = current_response_vector

    return answers_mat

def main():
    usage_str = "Receives a directory containing JSON files of user responses, an output directory, and a " \
                "list of usernames to discard, and performs two matchings: one score-based and one random, saving the " \
                "results in the output dir. The results are two JSON files with the matched pairs as values " \
                "(and indices as keys), and " \
                "one JSON file that maps the username of each participant to their two matches. In the " \
                "latter file, each username is mapped to a list of two usernames, the first of which is " \
                "their question-based match, and the second is their random match.\n" \
                "Args:\n" \
                "1. Input dir containing the JSON files\n" \
                "2. Text file containing the usernames to skip.\n" \
                "3. Output dir.\n" \
                "4. -k if you want to keep users who have provided emails, -d if you want them deleted."

    if len(sys.argv) != 5:
        print(usage_str)
        return

    input_dir = sys.argv[1]
    discard_file = sys.argv[2]
    output_dir = sys.argv[3]
    in_keep_delete_emails = sys.argv[4]

    if in_keep_delete_emails not in ['-k', '-d']:
        print(usage_str)
        return

    if in_keep_delete_emails == '-k':
        keep_emails = True
    else:
        keep_emails = False

    users_to_discard = open(discard_file, mode='r').readlines()
    users_to_discard = {y.encode('utf8') for y in [x.strip() for x in users_to_discard] if y != ''}

    resulting_users = dict()
    files_list = os.listdir(input_dir)
    files_list = sorted(files_list)

    n_q = 0
    n_users_with_emails = 0
    for response_filename in files_list:
        current_content = json.load(open(os.path.join(input_dir, response_filename), mode='r'))
        current_username = current_content['username'].strip().encode('utf8')
        if current_username in users_to_discard:
            print('Discarding username:')
            print(current_username)
            continue
        if str(current_username).find('@') != -1:
            n_users_with_emails += 1
            if not keep_emails:
                print('Skipping user with email address instead of username:')
                print(current_username)
                continue
            else:
                print('User with email kept:')
                print(current_username)
        if resulting_users.get(current_username, None) is not None:
            print('Repeated user: ' + str(current_username))
            print('Keeping latest response')
        resulting_users[current_username] = current_content
        n_q = len(current_content['answers'])

    # We can only match an even number of people, so if the total number is odd, we sacrifice the last one.
    if len(resulting_users) % 2 == 1:
        resulting_usernames = list(resulting_users.keys())
        resulting_usernames = resulting_usernames[:len(resulting_usernames) - 1]
        resulting_users = {k:resulting_users[k] for k in resulting_usernames}

    print('Number of questions:')
    print(n_q)
    print('Number of users')
    print(len(resulting_users))
    print('Number of users who provided emails instead of usernames')
    print(n_users_with_emails)

    index_to_user = dict(enumerate(resulting_users.keys()))
    user_to_index = invert_dict(index_to_user)

    # Question-based matching
    print('Starting question-based matching...')
    answers_mat = generate_answers_mat(resulting_users, user_to_index, n_q)
    adj_mat = create_user_mat(answers_mat)
    q_based_matched_indices = set(max_pair_matching(adj_mat))

    print('Length of question-based matching list:')
    print(len(q_based_matched_indices))
    print('Question-based matching done, starting random matching...')

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

    print('Length of random matching list')
    print(len(random_matched_indices))
    print('Random matching finished, producing outputs.')

    random_match_names = dict(enumerate([(index_to_user[x[0]], index_to_user[x[1]]) for x in random_matched_indices]))
    q_based_match_names = dict(enumerate([(index_to_user[x[0]], index_to_user[x[1]], adj_mat[x[0],x[1]])
                                          for x in q_based_matched_indices]))

    q_based_matched_indices = list(q_based_matched_indices)

    # In the following dict, each username will be mapped to two other usernames, the first of which
    # comes from q_based_matched_indices and the second of which comes from random_matched_indices.
    user_to_matches_dict = {i:[] for i in range(0,len(resulting_users))}
    matching_lists = [q_based_matched_indices, random_matched_indices]
    for j in range(len(matching_lists)):
        current_matched_indices_list = matching_lists[j]
        for user_pair in current_matched_indices_list:
            user_to_matches_dict[user_pair[0]].append(user_pair[1])
            user_to_matches_dict[user_pair[1]].append(user_pair[0])
        print('Performing sanity checks!')
        print('The following two must be equal:')
        print(sum([len(x) for x in user_to_matches_dict.values()]))
        print((j+1)*len(user_to_matches_dict))


    user_to_matches_dict = {index_to_user[i]: [index_to_user[y] for y in user_to_matches_dict[i]]
                            for i in user_to_matches_dict}

    make_sure_path_exists(output_dir)
    with open(os.path.join(output_dir, 'random_matches_'+in_keep_delete_emails[1]+'.json'), mode='w') as f:
        json.dump(random_match_names, f)

    with open(os.path.join(output_dir, 'q_based_matches_'+in_keep_delete_emails[1]+'.json'), mode='w') as f:
        json.dump(q_based_match_names, f)

    with open(os.path.join(output_dir, 'user_to_matches_'+in_keep_delete_emails[1]+'.json'), mode='w') as f:
        json.dump(user_to_matches_dict, f)

if __name__ == '__main__':
    main()