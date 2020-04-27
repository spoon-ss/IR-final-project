"""
This module implements a (partial, sample) query interface for elasticsearch movie search.
You will need to rewrite and expand sections to support the types of queries over the fields in your UI.
"""

from flask import *
from service import GeneralQueryService, TranslateService

app = Flask(__name__)


# display query page
@app.route("/")
def show_index_page():
    return render_template('index.html')


# display results page for first set of results and "next" sets.
@app.route("/results", defaults={'page': 1}, methods=['GET'])
@app.route("/results/<page>", methods=['GET'])
def results(page):
    query_str = request.args.get('query')
    author_str = request.args.get('author')
    min_time_str = request.args.get('mintime')
    max_time_str = request.args.get('maxtime')
    page_num = page

    query_option = None
    a = request.args.get('type')
    if request.args.get('type') == 'conjunctive':
        query_option = GeneralQueryService.CONJUNCTIVE_OPTION
    elif request.args.get('type') == 'disjunctive':
        query_option = GeneralQueryService.DISJUNCTIVE_OPTION
    else:
        raise RuntimeError("Illegal Request")

    translate_service = TranslateService()
    translated_query_str = translate_service.translate(query_str, TranslateService.CHINESE_OPTION,
                                                       TranslateService.ENGLISH_OPTION)

    query_service = GeneralQueryService("sample_covid_19_index")
    result = query_service.query(query_str, author_str, min_time_str, max_time_str, query_option, page_num)

    result_dict = result['result_dict']
    stops_words_included = result['stop_words_included']
    a = request.args.to_dict()
    return render_template('result.html', stop_len=len(stops_words_included), stops=stops_words_included,
                           results=result_dict, res_num=len(result_dict),
                           page_num=page, queries=request.args.to_dict())


# display suggestion for autocompletion
@app.route("/autocomplete", methods=['GET'])
def autocomplete():
    text = request.args.getlist('search[term]')
    general_query_service = GeneralQueryService()
    return jsonify(general_query_service.autocomplete(text))


# display a particular document given a result number
@app.route("/documents/<res>", methods=['GET'])
def documents(res):
    return render_template('article.html')


if __name__ == "__main__":
    app.config['ENV'] = 'development'
    app.config['DEBUG'] = True
    app.config['TESTING'] = True
    app.run()
