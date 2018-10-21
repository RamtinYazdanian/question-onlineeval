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
    question_mode = '1'
    questions = json.load(open(settings['modes'][question_mode]['questions'], mode='r'))
    questions = {str(k):questions[str(k)] for k in range(n_q)}
    resp = make_response(render_template('questions_form.html', questions = questions, n_q = n_q, cloud_dir = settings['modes'][question_mode]['cloud_dir']))
    resp.set_cookie('question_mode', question_mode)
    return resp


@app.route('/result', methods=['POST'])
def recom_result():
    if request.method == 'POST':
        settings = json.load(open('static/settings.json', mode='r'))
        recom_count = settings['recom_count']
        n_q = settings['n_q']
        answer_levels = settings['answer_levels']
        max_answer = (answer_levels - 1)/2
        #editor_count = settings['editor_count']
        result = request.form
        question_mode = request.cookies.get('question_mode')
        print(result)
        answers = {int(x.strip('u').strip('\'').strip('q_group_')):int(result[x].strip('u').strip('\''))
                                                                    for x in result if 'q_group_' in x}
        user_name = result['name_field']

        answers_vector = np.zeros((n_q, 1))
        for x in answers:
            answers_vector[x, 0] = 1.0*answers[x] / max_answer
        print(answers_vector)

        doc_latent_filename = settings['modes'][question_mode]['doc_latent']

        if sys.version_info[0] < 3:
            doc_latent = pickle.load(open(doc_latent_filename, mode='rb'))
        else:
            doc_latent = pickle.load(open(doc_latent_filename, mode='rb'), encoding='latin1')

        # The assumption is that the doc_latent file is already column-normalised and has n_q columns.
        # Here, we calculate the dot product of the topic matrix and the answer vector, resulting in the
        # document-space representation of the user. Then, we sort it in descending order to get the highest-weighted
        # documents.
        doc_scores = (doc_latent.dot(answers_vector)).flatten()
        best_docs = np.argsort(doc_scores)
        best_docs = best_docs[::-1]

        # The dictionaries needed for pretty much every set of documents
        doc_id_to_index = json.load(open('static/doc_id_index.json'))
        doc_index_to_id = {int(doc_id_to_index[x]):int(x) for x in doc_id_to_index}
        doc_id_to_name = json.load(open('static/docid_docname.json', mode='r'))
        doc_id_to_name = {int(x):doc_id_to_name[x] for x in doc_id_to_name}

        # The set (as in Python 'set') of documents that appear in the questions and should be avoided in the
        # recommendations.

        # TODO: remove 'modes' from the settings.json file
        documents_to_avoid = pickle.load(open(settings['question_doc_ids'], mode='rb'))

        # Both of the following lists are assumed to be lists of ids of top-ranking documents (in each one's
        # respective department).
        edit_pop_list = pickle.load(open(settings['edit_pop_list'], mode='rb'), encoding='latin1')
        view_pop_list = pickle.load(open(settings['view_pop_list'], mode='rb'), encoding='latin1')

        q_based_recommendations = get_top_k_recommendations_by_id(best_docs, recom_count, doc_id_to_name,
                                                                  documents_to_avoid, doc_index_to_id=doc_index_to_id,
                                                                  randomise=-1)
        # Need to shuffle this one because it's not randomised. The viewpop and editpop recoms are already randomised
        # so we don't shuffle them.
        random.shuffle(q_based_recommendations)

        edit_pop_recommendations = get_top_k_recommendations_by_id(edit_pop_list, recom_count, doc_id_to_name,
                                                                   documents_to_avoid, doc_index_to_id=None,
                                                                   randomise=100)

        view_pop_recommendations = get_top_k_recommendations_by_id(view_pop_list, recom_count, doc_id_to_name,
                                                                   documents_to_avoid, doc_index_to_id=None,
                                                                   randomise=100)

        # TODO calculating the personal CF recommendations and saving them in a file (won't be done here though)
        all_cf_personal_recommendations = json.load(open(settings['cf_recoms'], mode='rb'), encoding='latin1')
        if user_name in all_cf_personal_recommendations:
            cf_personal_recoms = get_top_k_recommendations_by_id(all_cf_personal_recommendations[user_name],
                                                                 recom_count, doc_id_to_name, documents_to_avoid,
                                                                 doc_index_to_id=None, randomise=100)
            random.shuffle(cf_personal_recoms)
        else:
            cf_personal_recoms = None

        final_recoms = dict()

        for i in range(recom_count):
            if cf_personal_recoms is not None:
                final_recoms[i] = {'q_based': q_based_recommendations[i],
                                   'view_pop': view_pop_recommendations[i],
                                   'edit_pop': edit_pop_recommendations[i],
                                   'cf_based': cf_personal_recoms[i]}
            else:
                final_recoms[i] = {'q_based': q_based_recommendations[i],
                                   'view_pop': view_pop_recommendations[i],
                                   'edit_pop': edit_pop_recommendations[i]}

        resp = make_response(render_template("recom_results.html", recoms_dict = final_recoms))
        resp.set_cookie('answers', json.dumps(answers))
        resp.set_cookie('question_mode', question_mode)
        return resp


# @app.route('/thankyou', methods=['POST'])
# def thank_you_page():
#     if request.method == 'POST':
#         #Saving the results
#         settings = json.load(open('static/settings.json', mode='r'))
#         answers = request.cookies.get('answers')
#         question_mode = request.cookies.get('question_mode')
#         user_eval = request.form
#         user_eval = {int(x.strip('u').strip('\'').strip('group')):int(user_eval[x].strip('u').strip('\'')) for x in user_eval}
#
#         print(answers)
#         print(question_mode)
#         print(user_eval)
#
#         result_to_save = {}
#         result_to_save['user_eval'] = user_eval
#         result_to_save['question_mode'] = question_mode
#         result_to_save['question_mode_name'] = settings['modes'][question_mode]['mode_name']
#         result_to_save['answers'] = answers
#
#         output_filename = str(datetime.now())
#         output_filename = output_filename.replace(' ', '_').replace(':','_').replace('.','_').replace('-','_')
#         output_filename = output_filename + '_' + str(random.randint(0,20000))
#         json.dump(result_to_save, open(settings['output_dir']+output_filename+'.json', mode='w'))
#
#         return render_template('thanks.html')

@app.route('/thankyou', methods=['POST'])
def thank_you_page():
    if request.method == 'POST':
        settings = json.load(open('static/settings.json', mode='r'))
        result = request.form
        question_mode = request.cookies.get('question_mode')
        user_name = result['name_field']
        result = {x:result[x] for x in result if x != 'name_field'}
        answers = {int(x.strip('u').strip('\'').strip('group')):int(result[x].strip('u').strip('\'')) for x in result}

        print(answers)
        print(question_mode)

        result_to_save = {}
        result_to_save['question_mode'] = question_mode
        result_to_save['question_mode_name'] = settings['modes'][question_mode]['mode_name']
        result_to_save['answers'] = answers
        result_to_save['username'] = user_name

        output_filename = str(datetime.now())
        output_filename = output_filename.replace(' ', '_').replace(':','_').replace('.','_').replace('-','_')
        output_filename = output_filename + '_' + str(random.randint(0,200000))

        make_sure_path_exists(settings['output_dir'])
        json.dump(result_to_save, open(settings['output_dir']+output_filename+'.json', mode='w'))

        return render_template('thanks.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000)
