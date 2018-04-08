# Online Wikipedia experiment for user matching based on a questionnaire

## How to run

Simply run the file question-onlineeval.py, and the server will start.

## Which are the relevant files?

The two python files 'question-onlineeval.py' and 'common_utils.py', the templates 'base.html', 'questions_form.html' and 'thanks.html', all of the css and js files, and the files in the folder static/joint. The latter folder contains the questions json file and the word clouds.

The results will be saved in a new folder called results, located at the main directory. Each result will be a json file, containing the answers of the user and their username (email address) and some additional, unimportant information.

The settings (number of questions, locations of files and output directory) are located in the file static/settings.json.

## What about the matching?

It's not in this repository. It'll be done separately since it had pretty much nothing to do (temporally as well as logically) with this repo.
