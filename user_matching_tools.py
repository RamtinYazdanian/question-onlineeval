from networkx import from_numpy_array, max_weight_matching
import numpy as np

def max_pair_matching(weight_mat):
    gr = from_numpy_array(weight_mat)
    result = max_weight_matching(gr, maxcardinality=True, weight='weight')
    return result

def create_user_mat(answers_mat):
    adj_mat = np.zeros((answers_mat.shape[0], answers_mat.shape[0]))
    for i in range(adj_mat.shape[0]):
        for j in range(i+1, adj_mat.shape[0]):
            v = np.dot(answers_mat[i,:], answers_mat[j,:]) + answers_mat.shape[1]
            adj_mat[i, j] = v
            adj_mat[j, i] = v

    return adj_mat