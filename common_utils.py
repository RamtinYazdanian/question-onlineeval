import os
import errno
from random import shuffle, sample, randint
import re

Q_BASED_STR = 'q_based'
VIEW_POP_STR = 'view_pop'
EDIT_POP_STR = 'edit_pop'
CF_BASED_STR = 'cf_based'

LIST_COMPARISON_DICT_WITH_CF = {0 : [Q_BASED_STR, CF_BASED_STR],
                                1 : [Q_BASED_STR, VIEW_POP_STR],
                                2 : [Q_BASED_STR, EDIT_POP_STR],
                                3 : [CF_BASED_STR, VIEW_POP_STR],
                                4 : [CF_BASED_STR, EDIT_POP_STR],
                                5 : [EDIT_POP_STR, VIEW_POP_STR]}

LIST_COMPARISON_DICT_NO_CF = {0 : [Q_BASED_STR, VIEW_POP_STR],
                              1 : [Q_BASED_STR, EDIT_POP_STR],
                              2 : [EDIT_POP_STR, VIEW_POP_STR]}

def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def add_slash_to_dir(dir_name):
    if dir_name[len(dir_name) - 1] != '/':
        return dir_name + '/'
    return dir_name

def invert_dict(d):
    return {d[k]: k for k in d}

"""
Assuming best_docs is a list of document indices or ids sorted in descending order of recommendation score, 
picks recom_count recommendations that are not members of documents_to_avoid, and returns a list of dictionaries 
containing doc ids and names. If doc_index_to_id is None, best_docs is assumed to contain ids; otherwise, it's assumed 
to contain indices.
The optional 'randomise' argument tells the function whether to provide a straight-up list of highest-scoring documents 
(when randomise == -1), or to first shuffle the top 'randomise' documents and then provide recommendations out of those. 
"""

def get_top_k_recommendations_by_id(best_docs, recom_count, doc_id_to_name, documents_to_avoid,
                                    doc_index_to_id=None, randomise=-1):
    # This check is to make sure that we don't end up with too few documents because some of them were in
    # documents_to_avoid.
    if randomise != -1:
        if randomise < recom_count * 2:
            randomise = recom_count * 2
        if randomise > len(best_docs):
            randomise = len(best_docs)
        docs_list = best_docs[:randomise]
        shuffle(docs_list)
    else:
        docs_list = best_docs

    recom_results = list()
    recoms_so_far = 0
    best_docs_counter = -1

    while recoms_so_far < recom_count and best_docs_counter < len(best_docs):
        best_docs_counter += 1
        if doc_index_to_id is not None:
            current_id = doc_index_to_id[docs_list[best_docs_counter]]
        else:
            current_id = docs_list[best_docs_counter]
        # Now we need to make sure to only recommend documents that were not present in the questions.
        if (current_id in documents_to_avoid):
            continue
        current_recom = dict()

        current_recom['id'] = current_id
        print(current_id)
        print(doc_id_to_name[current_id])
        current_recom['name'] = doc_id_to_name[current_id]
        recom_results.append(current_recom)
        recoms_so_far += 1

    return recom_results

def get_view_pop_recoms(view_pop_list, recom_count, documents_to_avoid=None):
    regexp = re.compile(r'(.+)(:)[^_]+.*')
    articles_list = [str(x['article'].encode('utf8')) for x in view_pop_list['items'][0]['articles']]
    articles_list = [x.replace('_', ' ') for x in articles_list
                     if not re.search(regexp, x)]
    if documents_to_avoid is not None:
        articles_list = [x for x in articles_list if x not in documents_to_avoid]
    result_list = sample(articles_list, recom_count)
    return result_list

def get_edit_pop_recoms(edit_pop_data, recom_count):
    regexp = re.compile(r'(.+)(:)[^_]+.*')
    articles_list = [str(x.split(',')[0].encode('utf8')) for x in edit_pop_data[1:]]
    articles_list = [x.replace('_', ' ') for x in articles_list if not re.search(regexp, x)]
    result_list = sample(articles_list, recom_count)
    return result_list

"""
Creates a shuffling dictionary for shuffling a dictionary without preserving the original key set.
"""

def dictionary_shuffler_creator(key_set):
    result_list = key_set.copy()
    shuffle(result_list)
    return dict(enumerate(result_list))

def shuffle_dict_using_shuffler(d, shuffler):
    return {x: d[shuffler[x]] for x in shuffler}

def invert_list_by_coin_flip(l):
    coin_flip = randint(0,1)
    if coin_flip == 0:
        return l
    else:
        return l[::-1]