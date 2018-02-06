import sys
import pickle
import json

def main():
    input_questions = json.load(open(sys.argv[1], mode='r'))
    input_docid_docname = json.load(open(sys.argv[2], mode='r'))
    docname_docid = {input_docid_docname[x]:int(x) for x in input_docid_docname}
    avoid_list = [docname_docid[x] for y in input_questions for z in input_questions[y] for x in input_questions[y][z]]
    avoid_list = set(avoid_list)
    pickle.dump(avoid_list, open(sys.argv[3], mode='wb'))

if __name__ == '__main__':
    main()