from flask import Flask, render_template, request, make_response
import json
import pickle
import os
import sys
import numpy as np
from common_utils import *
import random
from datetime import datetime

app = Flask(__name__, static_folder='static')

@app.route('/')
def q_form():
    settings = json.load(open('static/settings.json', mode='r'))
    n_q = settings['n_q']
    questions = json.load(open(settings['questions'], mode='r'))
    questions = {str(k):questions[str(k)] for k in range(n_q)}
    resp = make_response(render_template('questions_form.html', questions = questions, n_q = n_q, cloud_dir = settings['cloud_dir']))
    resp.set_cookie('n_q', str(n_q))
    return resp


@app.route('/result', methods=['POST'])
def recom_result():
    if request.method == 'POST':
        settings = json.load(open('static/settings.json', mode='r'))
        recom_count = settings['recom_count']
        n_q = int(request.cookies.get('n_q'))
        answer_levels = settings['answer_levels']
        max_answer = (answer_levels - 1)/2

        result = request.form
        print(result)
        answers = {int(x.strip('u').strip('\'').strip('q_group_')):int(result[x].strip('u').strip('\''))
                                                                    for x in result if 'q_group_' in x}

        # There are two modes: If the attribute "tokens_to_usernames" doesn't exist in the settings,
        # we proceed as normal. Otherwise, the 'user_name' is treated as a token which has to be mapped
        # to the actual username using that json file.
        token_to_username = None
        if 'tokens_to_usernames' in settings:
            token_to_username = json.load(open(settings['tokens_to_usernames'], 'r'))

        user_name = result['name_field']
        if token_to_username is not None:
            user_name = token_to_username.get(user_name, None)

        if user_name is None:
            user_name = 'THIS_USER_WAS_NOT_SUPPOSED_TO_BE_IN_THE_STUDY_CAUSE_NO_TOKEN_YEAH_SUCKS'

        answers_vector = np.zeros((n_q, 1))
        for x in answers:
            answers_vector[x, 0] = 1.0*answers[x] / max_answer
        print(answers_vector)

        doc_latent_filename = settings['doc_latent']

        if sys.version_info[0] < 3:
            doc_latent = pickle.load(open(doc_latent_filename, mode='rb'))
        else:
            doc_latent = pickle.load(open(doc_latent_filename, mode='rb'), encoding='latin1')

        # We keep the original matrix for the diversification, but only use n_q columns for the recommendations.
        # Here, we calculate the dot product of the topic matrix and the answer vector, resulting in the
        # document-space representation of the user. Then, we sort it in descending order to get the highest-weighted
        # documents.

        if settings['col_normalise']:
            doc_latent = doc_latent / np.reshape(np.linalg.norm(doc_latent, axis=0), newshape=(1, doc_latent.shape[1]))

        doc_scores = (doc_latent[:, :n_q].dot(answers_vector)).flatten()
        best_docs = np.argsort(doc_scores)
        best_docs = best_docs[::-1]

        # The dictionaries needed for pretty much every set of documents
        doc_id_to_index = json.load(open(settings['article_id_to_index'], 'r'))
        doc_id_to_index = {int(x):int(doc_id_to_index[x]) for x in doc_id_to_index}
        doc_index_to_id = invert_dict(doc_id_to_index)
        # The following file is generated using get_id_name_dict in common_utils.py of the original repo.
        doc_id_to_name = json.load(open(settings['article_id_to_name'], 'r'))
        doc_id_to_name = {int(x):doc_id_to_name[x] for x in doc_id_to_name}

        # The set (as in Python 'set') of documents that appear in the questions and should be avoided in the
        # recommendations.

        documents_to_avoid = set(pickle.load(open(settings['question_doc_ids'], mode='rb'), encoding='latin1'))
        doc_names_to_avoid = pickle.load(open(settings['question_doc_names'], mode='rb'), encoding='latin1')

        # Both of the following lists are assumed to be lists of ids of top-ranking documents (in each one's
        # respective department).
        edit_pop_file = settings['edit_pop_list']
        edit_pop_list = open(edit_pop_file, mode='r', encoding='utf-8').readlines()
        view_pop_file = settings['view_pop_list']
        view_pop_list = json.load(open(view_pop_file, mode='r', encoding='utf-8'))


        q_based_recommendations = get_top_k_q_based(best_docs, recom_count, doc_id_to_name,
                                                    documents_to_avoid, doc_index_to_id=doc_index_to_id,
                                                    diversify=settings["diversify_q_based_recoms"],
                                                    doc_latent=doc_latent)

        if settings.get('cf_recoms', None) is not None:
            all_cf_personal_recommendations = json.load(open(settings['cf_recoms'], mode='r'), encoding='latin1')
            if user_name is not None and user_name in all_cf_personal_recommendations:
                n_baselines = 3
                cf_personal_recoms = get_top_k_cf([int(x) for x in all_cf_personal_recommendations[user_name]],
                                        recom_count // n_baselines, doc_id_to_name, documents_to_avoid,
                                                  doc_id_to_index, doc_latent)

                random.shuffle(cf_personal_recoms)
            elif user_name is not None and user_name.strip() in all_cf_personal_recommendations:
                user_name = user_name.strip()
                n_baselines = 3
                cf_personal_recoms = get_top_k_cf([int(x) for x in all_cf_personal_recommendations[user_name]],
                                                  recom_count // n_baselines, doc_id_to_name, documents_to_avoid,
                                                  doc_id_to_index, doc_latent)

                random.shuffle(cf_personal_recoms)
            else:
                cf_personal_recoms = None
                n_baselines = 2
        else:
            cf_personal_recoms = None
            n_baselines = 2

        # Need to shuffle this one because it's not necessarily randomised (it's not randomised if we don't use the
        # diversification scheme). The viewpop and editpop recoms are already randomised
        # so we don't shuffle them.
        random.shuffle(q_based_recommendations)
        edit_pop_recommendations = get_edit_pop_recoms(edit_pop_list, recom_count // n_baselines)
        view_pop_recommendations = get_view_pop_recoms(view_pop_list, recom_count // n_baselines)

        if cf_personal_recoms is not None:
            initial_recom_field_types = {0: Q_BASED_STR, 1: VIEW_POP_STR, 2: EDIT_POP_STR, 3: CF_BASED_STR}
            # The keys of this dictionary HAVE TO BE sequential integers, starting from 0 which is the q-based
            # list of recommendations. It MUST MATCH the previous dictionary in terms of recom types.
            initial_recom_field_values = {0: q_based_recommendations,
                                        1: view_pop_recommendations,
                                        2: edit_pop_recommendations,
                                        3: cf_personal_recoms}
        else:
            initial_recom_field_types = {0: Q_BASED_STR, 1: VIEW_POP_STR, 2: EDIT_POP_STR}
            initial_recom_field_values = {0: q_based_recommendations,
                                        1: view_pop_recommendations,
                                        2: edit_pop_recommendations}

        final_recom_field_types = {x:Q_BASED_STR for x in range(N_RECOM_GROUPS)}
        per_baseline_groups = N_RECOM_GROUPS // n_baselines
        for i in initial_recom_field_types.keys():
            if initial_recom_field_types[i] == Q_BASED_STR:
                continue
            current_dict = {N_RECOM_GROUPS + (i-1)*per_baseline_groups + x:initial_recom_field_types[i]
                            for x in range(per_baseline_groups)}
            final_recom_field_types.update(current_dict)

        print(final_recom_field_types)
        individual_list_size = recom_count // N_RECOM_GROUPS
        final_recoms = dict()
        comparison_pairs = dict()

        for i in range(N_RECOM_GROUPS):

            starting_position_q_based = i*individual_list_size
            # The key in initial_recom_field_values is the quotient + 1.
            other_list_key = (i // per_baseline_groups) + 1
            starting_position_other_list = (i % per_baseline_groups)*individual_list_size

            q_based_sublist = q_based_recommendations[starting_position_q_based:
                                                   starting_position_q_based+individual_list_size]
            other_list_full = initial_recom_field_values[other_list_key]
            other_sublist = other_list_full[starting_position_other_list:
                                                   starting_position_other_list+individual_list_size]
            final_recoms[i] = q_based_sublist
            #print(i, final_recom_field_types[i], q_based_sublist)
            final_recoms[i+N_RECOM_GROUPS] = other_sublist
            #print(i+N_RECOM_GROUPS, final_recom_field_types[i+N_RECOM_GROUPS], other_sublist)
            # Doing a coin flip to determine which list ends up on the left and which one on the right.
            comparison_pairs[i] = invert_list_by_coin_flip([i, i+N_RECOM_GROUPS])

        # Shuffle the comparison pairs
        shuffler = dictionary_shuffler_creator(list(comparison_pairs.keys()))
        comparison_pairs = shuffle_dict_using_shuffler(comparison_pairs, shuffler)

        print(comparison_pairs)

        resp = make_response(render_template("recom_results.html", recoms_dict = final_recoms, recom_count=recom_count,
                            comparison_pairs = comparison_pairs, pairwise_comparison_count = len(comparison_pairs)))
        resp.set_cookie('answers', json.dumps(answers))
        resp.set_cookie('name_field', user_name)
        resp.set_cookie('recom_types', json.dumps(final_recom_field_types))
        resp.set_cookie('comparison_pairs', json.dumps(comparison_pairs))
        resp.set_cookie('n_q', str(n_q))
        resp.set_cookie('recom_count', str(recom_count))

        return resp


@app.route('/thankyou', methods=['POST'])
def thank_you_page():
    if request.method == 'POST':
        #Saving the results
        settings = json.load(open('static/settings.json', mode='r'))
        answers = request.cookies.get('answers')
        user_name = request.cookies.get('name_field')
        recom_types_json = request.cookies.get('recom_types')
        comparison_pairs = request.cookies.get('comparison_pairs')
        n_q = request.cookies.get('n_q')
        recom_count = request.cookies.get('recom_count')
        user_feedback = request.form

        print(answers)
        print(user_feedback)

        results_to_save_dict = user_feedback.to_dict(flat=True)
        results_to_save_dict['answers'] = json.loads(answers)
        results_to_save_dict['name_field'] = user_name
        results_to_save_dict['recom_count'] = int(recom_count)
        results_to_save_dict['recom_types'] = json.loads(recom_types_json)
        results_to_save_dict['comparison_pairs'] = json.loads(comparison_pairs)
        results_to_save_dict['n_q'] = int(n_q)

        output_filename = str(datetime.now())
        output_filename = output_filename.replace(' ', '_').replace(':','_').replace('.','_').replace('-','_')
        output_filename = output_filename + '_' + str(random.randint(0,200000))
        json.dump(results_to_save_dict, open(settings['output_dir']+output_filename+'.json', mode='w'))

        return render_template('thanks.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000)
