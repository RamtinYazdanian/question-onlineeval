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
    resp.set_cookie('n_q', n_q)
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

        documents_to_avoid = pickle.load(open(settings['question_doc_ids'], mode='rb'))
        doc_names_to_avoid = pickle.load(open(settings['question_doc_names'], mode='rb'))

        # Both of the following lists are assumed to be lists of ids of top-ranking documents (in each one's
        # respective department).
        edit_pop_file = settings['edit_pop_list']
        edit_pop_list = pickle.load(open(edit_pop_file, mode='rb'), encoding='latin1')
        view_pop_file = settings['view_pop_list']
        view_pop_list = json.load(open(view_pop_file, mode='r'))


        q_based_recommendations = get_top_k_recommendations_by_id(best_docs, recom_count, doc_id_to_name,
                                                                  documents_to_avoid, doc_index_to_id=doc_index_to_id,
                                                                  randomise=-1)
        q_based_recommendations = [x['name'] for x in q_based_recommendations]
        # Need to shuffle this one because it's not randomised. The viewpop and editpop recoms are already randomised
        # so we don't shuffle them.
        random.shuffle(q_based_recommendations)

        edit_pop_recommendations = get_top_k_recommendations_by_id(edit_pop_list, recom_count, doc_id_to_name,
                                                                   documents_to_avoid, doc_index_to_id=None,
                                                                   randomise=100)

        view_pop_recommendations = get_view_pop_recoms(view_pop_list, recom_count, doc_names_to_avoid)

        if settings.get('cf_recoms', None) is not None:
            all_cf_personal_recommendations = json.load(open(settings['cf_recoms'], mode='rb'), encoding='latin1')
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

        final_recoms = dict()
        recom_field_names = dict()

        for i in range(recom_count):
            if cf_personal_recoms is not None:
                final_recoms[i] = {0: q_based_recommendations[i],
                                   1: view_pop_recommendations[i],
                                   2: edit_pop_recommendations[i],
                                   3: cf_personal_recoms[i]}
                recom_field_names = {0: 'q_based', 1 :'view_pop', 2: 'edit_pop', 3: 'cf_based'}
            else:
                final_recoms[i] = {0: q_based_recommendations[i],
                                   1: view_pop_recommendations[i],
                                   2: edit_pop_recommendations[i]}
                recom_field_names = {0: 'q_based', 1: 'view_pop', 2: 'edit_pop'}


        resp = make_response(render_template("recom_results.html", recoms_dict = final_recoms, recom_count=recom_count,
                                                        field_names = recom_field_names, type_count = recom_type_count))
        resp.set_cookie('answers', json.dumps(answers))
        resp.set_cookie('name_field', user_name)
        resp.set_cookie('type_count', str(recom_type_count))
        resp.set_cookie('n_q', n_q)

        return resp


@app.route('/thankyou', methods=['POST'])
def thank_you_page():
    if request.method == 'POST':
        #Saving the results
        settings = json.load(open('static/settings.json', mode='r'))
        answers = request.cookies.get('answers')
        user_name = request.cookies.get('name_field')
        recom_type_count = request.cookies.get('type_count')
        n_q = request.cookies.get('n_q')
        user_feedback = request.form

        print(answers)
        print(user_feedback)

        results_to_save_dict = user_feedback.to_dict(flat=True)
        results_to_save_dict['answers'] = answers
        results_to_save_dict['name_field'] = user_name
        results_to_save_dict['recom_count'] = settings['recom_count']
        results_to_save_dict['type_count'] = recom_type_count
        results_to_save_dict['n_q'] = n_q

        output_filename = str(datetime.now())
        output_filename = output_filename.replace(' ', '_').replace(':','_').replace('.','_').replace('-','_')
        output_filename = output_filename + '_' + str(random.randint(0,200000))
        json.dump(results_to_save_dict, open(settings['output_dir']+output_filename+'.json', mode='w'))

        return render_template('thanks.html')

# @app.route('/thankyou', methods=['POST'])
# def thank_you_page():
#     if request.method == 'POST':
#         settings = json.load(open('static/settings.json', mode='r'))
#         result = request.form
#         question_mode = request.cookies.get('question_mode')
#         user_name = result['name_field']
#         result = {x:result[x] for x in result if x != 'name_field'}
#         answers = {int(x.strip('u').strip('\'').strip('group')):int(result[x].strip('u').strip('\'')) for x in result}
#
#         print(answers)
#         print(question_mode)
#
#         result_to_save = {}
#         result_to_save['question_mode'] = question_mode
#         result_to_save['question_mode_name'] = settings['modes'][question_mode]['mode_name']
#         result_to_save['answers'] = answers
#         result_to_save['username'] = user_name
#
#         output_filename = str(datetime.now())
#         output_filename = output_filename.replace(' ', '_').replace(':','_').replace('.','_').replace('-','_')
#         output_filename = output_filename + '_' + str(random.randint(0,200000))
#
#         make_sure_path_exists(settings['output_dir'])
#         json.dump(result_to_save, open(settings['output_dir']+output_filename+'.json', mode='w'))
#
#         return render_template('thanks.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000)
