from flask import Flask, render_template, request, make_response
#import flask_bootstrap
import json
import pickle
import os
import sys
import numpy as np
import random
from datetime import datetime

app = Flask(__name__, static_folder='static')

@app.route('/')
def q_form():
    settings = json.load(open('static/settings.json', mode='r'))
    n_q = settings['n_q']
    question_mode = str(random.randint(0,1))
    questions = json.load(open(settings['modes'][question_mode]['questions'], mode='r'))
    questions = {str(k):questions[str(k)] for k in range(n_q)}
    word_clouds = json.load(open(settings['modes'][question_mode]['word_cloud'], mode='r'))
    resp = make_response(render_template('questions_form.html', questions = questions, word_clouds = word_clouds, n_q = n_q, cloud_dir = settings['modes'][question_mode]['cloud_dir']))
    resp.set_cookie('question_mode', question_mode)
    return resp


@app.route('/result', methods=['POST'])
def recom_result():
    if request.method == 'POST':
        settings = json.load(open('static/settings.json', mode='r'))
        recom_count = settings['recom_count']
        editor_count = settings['editor_count']
        result = request.form
        question_mode = request.cookies.get('question_mode')
        print(result)
        answers = {int(x.strip('u').strip('\'').strip('group')):int(result[x].strip('u').strip('\'')) for x in result}

        answers_standard = {}
        for x in answers:
            if answers[x] in {-1,0,1}:
                answers_standard[x] = answers[x]
            else:
                answers_standard[x] = 0

        doc_latent_filename = settings['modes'][question_mode]['doc_latent']
        centroids_filename = settings['modes'][question_mode]['centroids']


        if sys.version_info[0] < 3:
            question_centroids = pickle.load(open(centroids_filename, mode='rb'))
            doc_latent = pickle.load(open(doc_latent_filename, mode='rb'))
        else:
            question_centroids = pickle.load(open(centroids_filename, mode='rb'), encoding='latin1')
            doc_latent = pickle.load(open(doc_latent_filename, mode='rb'), encoding='latin1')

        answer_rows = []
        for x in answers_standard:
            if (answers_standard[x] == 1):
                answer_rows.append(2*x)
            elif (answers_standard[x] == -1):
                answer_rows.append(2*x+1)

        this_user_latent_profile = np.zeros((question_centroids.shape[1]))
        if (len(answer_rows) > 0):
            this_user_latent_profile += np.mean(question_centroids[answer_rows, :],axis=0)

        doc_dot_products = (doc_latent.dot(
                    np.reshape(this_user_latent_profile, (this_user_latent_profile.size,1)))).flatten()

        doc_index_to_index = json.load(open('static/doc_index_index.json', mode='r'))
        doc_index_to_index = {int(k):int(doc_index_to_index[k]) for k in doc_index_to_index}
        best_docs = np.argsort(doc_dot_products)
        best_docs = best_docs[::-1]
        best_docs = [doc_index_to_index[x] for x in best_docs]
        doc_id_to_index = json.load(open('static/doc_id_index.json'))
        doc_index_to_id = {int(doc_id_to_index[x]):int(x) for x in doc_id_to_index}
        doc_id_to_name = json.load(open('static/docid_docname.json', mode='r'))
        doc_id_to_name = {int(x):doc_id_to_name[x] for x in doc_id_to_name}
        user_id_to_username = json.load(open('static/userid_username.json', mode='r'))
        user_id_to_username = {int(x):user_id_to_username[x] for x in user_id_to_username}
        docs_fervent_editors = json.load(open('static/docs_fervent_editors.json', mode='r'))
        docs_fervent_editors = {int(x):docs_fervent_editors[x] for x in docs_fervent_editors}

        recommendations = {}
        recoms_so_far = 0
        best_docs_counter = -1
        documents_to_avoid = pickle.load(open(settings['modes'][question_mode]['question_doc_ids'], mode='rb'))
        #documents_to_avoid = {}
        while recoms_so_far < recom_count:
            best_docs_counter += 1
            #Now we need to make sure to only recommend documents that were not present in the questions.
            if (doc_index_to_id[best_docs[best_docs_counter]] in documents_to_avoid):
                continue
            current_recom = {}
            current_id = doc_index_to_id[best_docs[best_docs_counter]]
            current_recom['id'] = current_id
            print(current_id)
            print(doc_id_to_name[current_id])
            current_recom['name'] = doc_id_to_name[current_id]
            doc_fervent_editor_count = min([len(docs_fervent_editors[best_docs[best_docs_counter]]), editor_count])
            current_recom['fervent_editors'] = [user_id_to_username[int(x)] for x in
                                                docs_fervent_editors[best_docs[best_docs_counter]][:doc_fervent_editor_count]]
            recommendations[recoms_so_far] = current_recom
            recoms_so_far += 1

        resp = make_response(render_template("recom_results.html", recommendations = recommendations))
        resp.set_cookie('answers', json.dumps(answers))
        resp.set_cookie('question_mode', question_mode)
        return resp


@app.route('/thankyou', methods=['POST'])
def thank_you_page():
    if request.method == 'POST':
        #Saving the results
        settings = json.load(open('static/settings.json', mode='r'))
        answers = request.cookies.get('answers')
        question_mode = request.cookies.get('question_mode')
        user_eval = request.form
        user_eval = {int(x.strip('u').strip('\'').strip('group')):int(user_eval[x].strip('u').strip('\'')) for x in user_eval}

        print(answers)
        print(question_mode)
        print(user_eval)

        result_to_save = {}
        result_to_save['user_eval'] = user_eval
        result_to_save['question_mode'] = question_mode
        result_to_save['question_mode_name'] = settings['modes'][question_mode]['mode_name']
        result_to_save['answers'] = answers

        output_filename = str(datetime.now())
        output_filename = output_filename.replace(' ', '_').replace(':','_').replace('.','_').replace('-','_')
        output_filename = output_filename + '_' + str(random.randint(0,20000))
        json.dump(result_to_save, open(settings['output_dir']+output_filename+'.json', mode='w'))

        return render_template('thanks.html')


if __name__ == '__main__':
    app.run(port=5000)
