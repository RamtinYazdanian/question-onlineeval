import os
import errno
from random import shuffle, sample, randint
from sklearn.cluster import KMeans
from collections import Counter
import re
import operator
import numpy as np

Q_BASED_STR = 'q_based'
VIEW_POP_STR = 'view_pop'
EDIT_POP_STR = 'edit_pop'
CF_BASED_STR = 'cf_based'
N_RECOM_GROUPS = 6

MINIMUM_MEM = 7 * (2**30)

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

def get_top_k_q_based(best_docs, recom_count, doc_id_to_name, documents_to_avoid,
                      doc_index_to_id, diversify=-1, doc_latent=None):
    """
    Assuming best_docs is a list of document indices or ids sorted in descending order of recommendation score,
    picks recom_count recommendations that are not members of documents_to_avoid, and returns a list of dictionaries
    containing doc ids and names. If doc_index_to_id is None, best_docs is assumed to contain ids; otherwise, it's assumed
    to contain indices.
    The optional 'diversify' argument tells the function whether to provide a straight-up list of highest-scoring documents
    (when diversify == -1), or to perform diversification by taking a larger set of articles, clustering them, and then
    returning the top-scoring ones from each cluster.
    """

    # This check is to make sure that we don't end up with too few documents because some of them were in
    # documents_to_avoid.
    if diversify != -1 and doc_latent is not None:
        if diversify < recom_count * 5:
            diversify = recom_count * 2
        if diversify > len(best_docs):
            diversify = len(best_docs)
        docs_list = best_docs[:800 + diversify + recom_count]
    else:
        docs_list = best_docs[:800 + recom_count]

    docs_list = [x for x in docs_list if doc_index_to_id[x] not in documents_to_avoid]
    if (diversify != -1 and doc_latent is not None):
        docs_list = docs_list[:diversify]
        docs_list = diversity_based_clustering(docs_list, doc_latent, recom_count)
    else:
        docs_list = docs_list[:recom_count]

    recom_results = [doc_id_to_name[doc_index_to_id[x]] for x in docs_list]

    return recom_results


def get_top_k_cf(best_docs, recom_count, doc_id_to_name, documents_to_avoid, doc_id_to_index, doc_latent):
    """
    Assumes that the best_docs list consists of ids, unlike the q-based one which assumed indices.
    Uses the diversification scheme.
    """
    doc_index_to_id = invert_dict(doc_id_to_index)
    # Converting the ids to indices for the diversification function.
    docs_list = [doc_id_to_index[x] for x in best_docs if x not in documents_to_avoid]
    # Diversifying...
    docs_list = diversity_based_clustering(docs_list, doc_latent, recom_count)
    # Now converting the indices back into ids and then names.
    recom_results = [doc_id_to_name[doc_index_to_id[x]] for x in docs_list]
    return recom_results

def diversity_based_clustering(docs_list, doc_latent, recom_count, n_per_cluster = 1):
    docs_list = np.array(docs_list)
    n_clusters = int(np.ceil(recom_count / n_per_cluster))
    kmeans_model = KMeans(n_clusters=n_clusters)
    data_subset = doc_latent[docs_list, :]
    cluster_indices = np.array(kmeans_model.fit_predict(data_subset))

    cluster_counts = dict(Counter(cluster_indices))
    largest_cluster_index = max(cluster_counts.items(), key=operator.itemgetter(1))[0]
    cluster_count_to_get = {x: n_per_cluster for x in cluster_counts}
    for i in cluster_counts:
        if cluster_counts[i] < n_per_cluster:
            cluster_count_to_get[largest_cluster_index] += n_per_cluster - cluster_counts[i]
            cluster_count_to_get[i] = cluster_counts[i]

    result_indices_list = []
    for ind in cluster_count_to_get:
        current_list = docs_list[np.where(cluster_indices==ind)].tolist()
        result_indices_list.extend(sample(current_list, cluster_count_to_get[ind]))

    result_indices_list = result_indices_list[:recom_count]
    shuffle(result_indices_list)
    return result_indices_list

"""
Samples recom_count articles from the view pop JSON file. The articles will be in namespace 0 (and the method used 
to detect articles outside ns=0 is to see if they begin with "SOMETHING:STH ELSE").
"""

def get_view_pop_recoms(view_pop_list, recom_count, documents_to_avoid=None, docname_to_index=None, doc_latent=None):
    regexp = re.compile(r'(.+)(:)[^_]+.*')
    articles_list = [str(x['article']) for x in view_pop_list['items'][0]['articles']]
    articles_list = [x.replace('_', ' ') for x in articles_list
                     if not re.search(regexp, x)]

    if documents_to_avoid is not None:
        articles_list = [x for x in articles_list if x not in documents_to_avoid]
    if docname_to_index is None or doc_latent is None:
        result_list = sample(articles_list, recom_count)
    else:
        docindex_to_docname = invert_dict(docname_to_index)
        # Converting the article names to their indices in our matrix, filtering out the documents that don't have
        # such an index.
        article_indices_list = [docname_to_index[article_name] for article_name in articles_list
                                if article_name in docname_to_index]
        # Diversifying
        result_indices_list = diversity_based_clustering(article_indices_list, doc_latent, recom_count)
        # Back to names
        result_list = [docindex_to_docname[doc_index] for doc_index in result_indices_list]
    print('Viewpop recoms')
    print(result_list)
    return result_list

"""
Samples recom_count articles from the view pop CSV file. The articles will be in namespace 0 (and the method used 
to detect articles outside ns=0 is to see if they begin with "SOMETHING:STH ELSE").
"""

def get_edit_pop_recoms(edit_pop_data, recom_count, documents_to_avoid=None, docname_to_index=None, doc_latent=None):
    regexp = re.compile(r'(.+)(:)[^_]+.*')
    articles_list = [str(','.join(x.split(',')[:x.count(',')-2])).strip('"') for x in edit_pop_data[1:]]
    articles_list = [x.replace('_', ' ') for x in articles_list if not re.search(regexp, x)]

    if documents_to_avoid is not None:
        articles_list = [x for x in articles_list if x not in documents_to_avoid]
    if docname_to_index is None or doc_latent is None:
        result_list = sample(articles_list, recom_count)
    else:
        docindex_to_docname = invert_dict(docname_to_index)
        # Converting the article names to their indices in our matrix, filtering out the documents that don't have
        # such an index.
        article_indices_list = [docname_to_index[article_name] for article_name in articles_list
                                if article_name in docname_to_index]
        # Diversifying
        result_indices_list = diversity_based_clustering(article_indices_list, doc_latent, recom_count)
        # Back to names
        result_list = [docindex_to_docname[doc_index] for doc_index in result_indices_list]
    print('Editpop recoms')
    print(result_list)
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