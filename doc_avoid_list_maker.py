import sys
import pickle
import json
from common_utils import *

def main():
    input_questions = json.load(open(sys.argv[1], mode='r'))
    input_docid_docname = json.load(open(sys.argv[2], mode='r'))
    docid_to_docname = {int(x):input_docid_docname[x] for x in input_docid_docname}
    docname_docid = invert_dict(docid_to_docname)
    id_avoid_list = [docname_docid[x] for y in input_questions for z in input_questions[y] for x in input_questions[y][z]]
    id_avoid_list = set(id_avoid_list)
    name_avoid_list = {docid_to_docname[x] for x in id_avoid_list}
    pickle.dump(id_avoid_list, open('id_avoid_list.pkl', mode='wb'))
    pickle.dump(name_avoid_list, open('name_avoid_list.pkl', mode='wb'))

if __name__ == '__main__':
    main()