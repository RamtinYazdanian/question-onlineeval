from wordcloud import WordCloud
import json
from PIL import Image
import sys
import os
import errno

def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def main():
    if (len(sys.argv) != 3):
        print("Please give the input dir and output dir.")
        return
    input_filename = sys.argv[1]
    output_dir = sys.argv[2]
    make_sure_path_exists(output_dir+'clouds/')
    word_lists = json.load(open(input_filename, mode='r'))
    for i in word_lists:
        for indicator in word_lists[i]:
            print(i)
            current_str = ' '.join(word_lists[i][indicator])
            cloud = WordCloud(background_color="white", colormap="plasma").generate(current_str)
            #print(cloud)
            im = cloud.to_image()
            im.save(open(output_dir + 'clouds/' + i + '_' + indicator + '.png', mode='wb'))

if __name__ == '__main__':
    main()