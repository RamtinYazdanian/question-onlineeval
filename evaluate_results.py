import json
import pandas as pd
from common_utils import *
from collections import Counter
import sys
import os

QUESTION_GROUP_TYPES = ['read_group','edit_group','uninterested_group']
N_PAIRS = 6
GLOBAL_MISSING_FIELD_COUNT = 0

def order_q_based_first(name_and_value):
    pair_name = name_and_value[0]
    current_value = name_and_value[1]
    q_based_position = pair_name.find(Q_BASED_STR)
    if q_based_position == 0:
        return name_and_value
    else:
        new_name = '_vs_'.join((pair_name.split('_vs_'))[::-1])
        new_value = -current_value
        return [new_name, new_value]

def convert_json_to_results(json_file):
    global GLOBAL_MISSING_FIELD_COUNT
    print(json_file)
    recorded_data = json.load(open(json_file, mode='r', encoding='utf8'))

    # Maps recom list index to its name (type)
    types_dict = recorded_data['recom_types']
    types_dict = {int(x): types_dict[x] for x in types_dict}

    # Maps comparison index to a list of the two
    comparison_pairs = recorded_data['comparison_pairs']
    comparison_pairs = {int(x): comparison_pairs[x] for x in comparison_pairs}
    comparison_pair_names = {x: '_vs_'.join([types_dict[y] for y in comparison_pairs[x]]) for x in comparison_pairs}

    results_dict = dict()
    for question_type_name in QUESTION_GROUP_TYPES:
        # Get only the responses for one question type
        subfields = {x: int(recorded_data[x]) for x in recorded_data if question_type_name in x}
        # Get the number of that question
        subfields = {int(x.strip(question_type_name)): subfields[x] for x in subfields}
        # Now create a list of lists with the name of the recom type pair to the value,
        # inverting the list (and negating the value) if q_based hasn't come first.
        GLOBAL_MISSING_FIELD_COUNT += N_PAIRS - len(subfields)
        if len(subfields) < N_PAIRS:
            return None
        subfields = [order_q_based_first([comparison_pair_names[x], subfields[x]]) for x in range(N_PAIRS) if x in subfields]
        results_dict[question_type_name] = subfields

    return results_dict

def get_all_results(list_of_files):
    result_list = []
    count = 0
    for filename in list_of_files:
        current_result = convert_json_to_results(filename)
        if current_result is not None:
            result_list.append(current_result)
        count += 1
        if count % 10 == 0 and count != 0:
            print(GLOBAL_MISSING_FIELD_COUNT)
    return result_list

def data_to_dataframe(results_list):
    list_of_lists = []
    for result_index in range(len(results_list)):
        current_result = results_list[result_index]
        for i in range(N_PAIRS):
            current_list = [current_result['edit_group'][i][0]]
            for question_type in QUESTION_GROUP_TYPES:
                current_list.append(current_result[question_type][i][1])
            list_of_lists.append(current_list)
    column_names = ['comparison_name']
    column_names.extend(QUESTION_GROUP_TYPES)
    return pd.DataFrame(list_of_lists, columns=column_names)

def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0

def get_descriptive_stats(df):
    print(df.describe())
    for question_type in QUESTION_GROUP_TYPES:
        df[question_type] = df[question_type].apply(sign)
    print('Number of "wins", "draws" and "losses" vs each baseline:')
    for question_type in QUESTION_GROUP_TYPES:
        df_agg = df.pivot_table(index=['comparison_name'], columns=question_type, aggfunc='size', fill_value=0)
        print(df_agg)


def main():
    global GLOBAL_MISSING_FIELD_COUNT
    input_dir = sys.argv[1]
    starting_day = 12
    filenames_list = os.listdir(input_dir)
    filenames_list = [x for x in filenames_list if int(x.split('_')[2]) >= starting_day]
    filenames_list = [os.path.join(input_dir, x) for x in filenames_list]
    get_descriptive_stats(data_to_dataframe(get_all_results(filenames_list)))
    print('Number of JSON files with missing values:')
    print(GLOBAL_MISSING_FIELD_COUNT)

if __name__ == '__main__':
    main()

