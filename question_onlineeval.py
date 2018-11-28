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
        user_name = result['name_field']

        answers_vector = np.zeros((n_q, 1))
        for x in answers:
            answers_vector[x, 0] = 1.0*answers[x] / max_answer
        print(answers_vector)

        doc_latent_filename = settings['doc_latent']

        if sys.version_info[0] < 3:
            doc_latent = pickle.load(open(doc_latent_filename, mode='rb'))
        else:
            doc_latent = pickle.load(open(doc_latent_filename, mode='rb'), encoding='latin1')

        # The assumption is that the doc_latent file is already column-normalised. We make sure that it has exactly
        # n_q columns, just in case.
        # Here, we calculate the dot product of the topic matrix and the answer vector, resulting in the
        # document-space representation of the user. Then, we sort it in descending order to get the highest-weighted
        # documents.
        doc_latent = doc_latent[:, :n_q]
        doc_scores = (doc_latent.dot(answers_vector)).flatten()
        best_docs = np.argsort(doc_scores)
        best_docs = best_docs[::-1]

        # The dictionaries needed for pretty much every set of documents
        doc_id_to_index = json.load(open(settings['article_id_to_index'], 'r'))
        doc_index_to_id = {int(doc_id_to_index[x]):int(x) for x in doc_id_to_index}
        # The following file is generated using get_id_name_dict in common_utils.py of the original repo.
        doc_id_to_name = json.load(open(settings['article_id_to_name'], 'r'))
        doc_id_to_name = {int(x):doc_id_to_name[x] for x in doc_id_to_name}

        # The set (as in Python 'set') of documents that appear in the questions and should be avoided in the
        # recommendations.

        documents_to_avoid = pickle.load(open(settings['question_doc_ids'], mode='rb'), encoding='latin1')
        doc_names_to_avoid = pickle.load(open(settings['question_doc_names'], mode='rb'), encoding='latin1')

        # Both of the following lists are assumed to be lists of ids of top-ranking documents (in each one's
        # respective department).
        edit_pop_file = settings['edit_pop_list']
        edit_pop_list = open(edit_pop_file, mode='r').readlines()
        view_pop_file = settings['view_pop_list']
        view_pop_list = json.load(open(view_pop_file, mode='r', encoding='utf8'))


        q_based_recommendations = get_top_k_recommendations_by_id(best_docs, recom_count, doc_id_to_name,
                                                                  documents_to_avoid, doc_index_to_id=doc_index_to_id,
                                                                  randomise=-1)
        q_based_recommendations = [x['name'] for x in q_based_recommendations]
        # Need to shuffle this one because it's not randomised. The viewpop and editpop recoms are already randomised
        # so we don't shuffle them.
        random.shuffle(q_based_recommendations)

        edit_pop_recommendations = get_edit_pop_recoms(edit_pop_list, recom_count)

        view_pop_recommendations = get_view_pop_recoms(view_pop_list, recom_count)

        if settings.get('cf_recoms', None) is not None:
            all_cf_personal_recommendations = json.load(open(settings['cf_recoms'], mode='r'), encoding='latin1')
            if user_name in all_cf_personal_recommendations:
                cf_personal_recoms = get_top_k_recommendations_by_id(all_cf_personal_recommendations[user_name],
                                                                     recom_count, doc_id_to_name, documents_to_avoid,
                                                                     doc_index_to_id=None, randomise=100)
                random.shuffle(cf_personal_recoms)
                recom_type_count = 4
            else:
                cf_personal_recoms = None
                recom_type_count = 3
        else:
            cf_personal_recoms = None
            recom_type_count = 3

        if cf_personal_recoms is not None:
            recom_field_types = {0: Q_BASED_STR, 1: VIEW_POP_STR, 2: EDIT_POP_STR, 3: CF_BASED_STR}
            final_recoms = {0: q_based_recommendations,
                            1: view_pop_recommendations,
                            2: edit_pop_recommendations,
                            3: cf_personal_recoms}
            comparison_pairs = LIST_COMPARISON_DICT_WITH_CF
        else:
            recom_field_types = {0: Q_BASED_STR, 1: VIEW_POP_STR, 2: EDIT_POP_STR}
            final_recoms = {0: q_based_recommendations,
                            1: view_pop_recommendations,
                            2: edit_pop_recommendations}
            comparison_pairs = LIST_COMPARISON_DICT_NO_CF

        # Here, we convert the list of pairwise list comparisons into their actual indices in the recommendations
        # dictionary, randomly (with a 50% chance) flip the order of lists in each pair, and the shuffle the whole
        # list of pairs such that both the ordering of the feedback questions and the ordering of the pair within
        # each question is randomised. We put all the information about these questions into the cookie so that
        # we know what was what afterwards.

        inverted_field_types = invert_dict(recom_field_types)
        comparison_pairs = {x:
                    invert_list_by_coin_flip([inverted_field_types[y] for y in comparison_pairs[x]])
                    for x in comparison_pairs}
        shuffler = dictionary_shuffler_creator(list(comparison_pairs.keys()))
        comparison_pairs = shuffle_dict_using_shuffler(comparison_pairs, shuffler)

        print(comparison_pairs)

        resp = make_response(render_template("recom_results.html", recoms_dict = final_recoms, recom_count=recom_count,
                            comparison_pairs = comparison_pairs, pairwise_comparison_count = len(comparison_pairs)))
        resp.set_cookie('answers', json.dumps(answers))
        resp.set_cookie('name_field', user_name)
        resp.set_cookie('recom_types', json.dumps(recom_field_types))
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
