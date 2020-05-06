"""
This module implements a (partial, sample) query interface for elasticsearch movie search.
You will need to rewrite and expand sections to support the types of queries over the fields in your UI.
"""

from flask import *
from flaskapp.service import GeneralQueryService, TranslateService
from datetime import date

app = Flask(__name__)


# display query page
@app.route("/")
def show_index_page():
    return render_template('index.html')


# display results page for first set of results and "next" sets.
@app.route("/results", methods=['GET'])
def results():
    query_str = request.args.get('query')
    author_str = request.args.get('author')
    min_time_str = request.args.get('mintime')
    max_time_str = request.args.get('maxtime')
    page_num = int(request.args.get('page'))

    query_option = None
    if request.args.get('type') == 'conjunctive':
        query_option = GeneralQueryService.CONJUNCTIVE_OPTION
    elif request.args.get('type') == 'disjunctive':
        query_option = GeneralQueryService.DISJUNCTIVE_OPTION
    else:
        raise RuntimeError("Illegal Request")

    max_date = date.max
    if len(max_time_str) != 0:
        max_date = date.fromisoformat(max_time_str)

    min_date = date.min
    if len(min_time_str) != 0:
        min_date = date.fromisoformat(min_time_str)

    translate_service = TranslateService()
    translated_query_str = translate_service.translate(query_str, TranslateService.CHINESE_OPTION,
                                                       TranslateService.ENGLISH_OPTION)

    query_service = GeneralQueryService("sample_covid_19_index")
    result = query_service.query(query_str, author_str, min_date, max_date, query_option, page_num)

    result_dict = result['result_dict']
    stops_words_included = result['stop_words_included']
    total_hits = result['total_hits']

    queries = request.args.to_dict()
    queries.pop('page')
    return render_template('result.html', stop_len=len(stops_words_included), stops=stops_words_included,
                           results=result_dict, res_num=total_hits,
                           page_num=page_num, queries=queries)


# display suggestion for autocompletion
@app.route("/autocomplete", methods=['GET'])
def autocomplete():
    text = request.args.getlist('search[term]')
    general_query_service = GeneralQueryService("sample_covid_19_index").autocomplete(text)
    return jsonify(general_query_service)


# display a particular document given a result number
@app.route("/documents/<res>", methods=['GET'])
def documents(res):
    article_dic, more_like_this_dic = GeneralQueryService("sample_covid_19_index").doc_result(res)
    return render_template('article.html', article=article_dic, more_like_this=more_like_this_dic)


if __name__ == "__main__":
    app.config['ENV'] = 'development'
    app.config['DEBUG'] = True
    app.config['TESTING'] = True
    app.run()
