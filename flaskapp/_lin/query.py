"""
This module implements a (partial, sample) query interface for elasticsearch movie search. 
You will need to rewrite and expand sections to support the types of queries over the fields in your UI.
"""

import re
from flask import *
from index import Article
from elasticsearch_dsl.utils import AttrList
from elasticsearch_dsl import Search
from datetime import date, datetime

app = Flask(__name__)

# Initialize global variables for rendering page
tmp_text = ""
tmp_title = ""
tmp_author = ""
tmp_min = ""
tmp_max = ""
tmp_opt = ""
gresults = {}


# display query page
@app.route("/")
def search():
    return render_template('index.html')


# display results page for first set of results and "next" sets.
@app.route("/results", defaults={'page': 1}, methods=['GET', 'POST'])
@app.route("/results/<page>", methods=['GET', 'POST'])
def results(page):
    global tmp_text
    global tmp_title
    global tmp_author
    global tmp_min
    global tmp_max
    global tmp_opt
    global gresults

    # convert the <page> parameter in url to integer.
    if type(page) is not int:
        page = int(page.encode('utf-8'))
        # if the method of request is post (for initial query), store query in local global variables
    # if the method of request is get (for "next" results), extract query contents from client's global variables  
    if request.method == 'POST':
        text_query = request.form['query']
        author_query = request.form['author']
        mintime_query = request.form['mintime']
        # min date will be min date if not specified
        if len(mintime_query) is 0:
            mintime = date.min
        else:
            mintime = datetime.strptime(mintime_query, '%Y-%m-%d').date()
        maxtime_query = request.form['maxtime']
        # max date will be max date if not specified
        if len(maxtime_query) is 0:
            maxtime = date.max
        else:
            # if max time is specified
            maxtime = datetime.strptime(maxtime_query, '%Y-%m-%d').date()
        
        # operation will be and for conjunctive and or for disjunctive
        if request.form['type'] == "conjunctive":
            operation = 'and'
        else:
            operation = 'or'

        # update global variable templates data
        tmp_text = text_query
        tmp_author = author_query
        tmp_min = mintime
        tmp_max = maxtime
        tmp_opt = operation
    else:
        # use the current values stored in global variables.
        text_query = tmp_text
        author_query = tmp_author
        mintime = tmp_min

        if tmp_min > date.min:
            mintime_query = tmp_min
        else:
            mintime_query = date.min
        maxtime = tmp_max

        if tmp_max < date.max:
            maxtime_query = tmp_max
        else:
            maxtime_query = date.max
        operation = tmp_opt

    # store query values to display in search boxes in UI
    shows = {}
    shows['text'] = text_query
    shows['author'] = author_query
    shows['maxtime'] = maxtime_query
    shows['mintime'] = mintime_query
    shows['type'] = False

    # Create a search object to query our index 
    search = Search(index='covid_index')

    # Build up your elasticsearch query in piecemeal fashion based on the user's parameters passed in.
    # The search API is "chainable".
    # Each call to search.query method adds criteria to our growing elasticsearch query.
    # You will change this section based on how you want to process the query data input into your interface.

    # search for runtime using a range query
    s = search.query('range', publish_time={'gte': mintime, 'lte': maxtime})

    # Conjunctive search over multiple fields (title and text) using the text_query passed in
    phrase = ""
    if len(text_query) > 0:
        # if hypen is in the query, add double quotes around the term with hypen and then do simple_query_string query 
        if "-" in text_query:
            text = re.findall(r'\w+(?:-\w+)+',text_query)
            t_query = text_query.split(" ")
            # print(t_query)
            for i, q in enumerate(t_query):
                if q in text:
                    t_query[i] = "\"" + q + "\""
            t_query = " ".join(t_query)
            s = s.query('simple_query_string', query=t_query, fields=['title^1.5', 'abstract'], default_operator=operation)
        else:
            s = s.query('multi_match', query=text_query, type='cross_fields', fields=['title^3', 'abstract'], operator=operation)

    # search for matching authors
    # You should support multiple values (list)
    if len(author_query) > 0:
        s = s.query('match', author=author_query)

    # highlight
    s = s.highlight_options(pre_tags='<mark>', post_tags='</mark>')
    s = s.highlight('abstract', fragment_size=999999999, number_of_fragments=1)
    s = s.highlight('title', fragment_size=999999999, number_of_fragments=1)
    s = s.highlight('author', fragment_size=999999999, number_of_fragments=1)

    # determine the subset of results to display (based on current <page> value)
    start = 0 + (page - 1) * 10
    end = 10 + (page - 1) * 10
    
    # execute search and return results in specified range.
    response = s[start:end].execute()
    # insert data into response
    resultList = {}
    for hit in response.hits:
        result = {}
        result['score'] = hit.meta.score

        if 'highlight' in hit.meta:
            if 'title' in hit.meta.highlight:
                result['title'] = hit.meta.highlight.title[0]
            else:
                result['title'] = hit.title

            if 'abstract' in hit.meta.highlight:
                result['abstract'] = hit.meta.highlight.abstract[0]
            else:
                result['abstract'] = hit.abstract
        else:
            result['title'] = hit.title
            result['abstract'] = hit.abstract

        resultList[hit.meta.id] = result

    # make the result list available globally
    gresults = resultList

    # get the total number of matching results
    result_num = response.hits.total['value']

    # list of stop words used in Elastic Search
    stop_words = ["a", "an", "and", "are", "as", "at", "be", "but", "by",
                    "for", "if", "in", "into", "is", "it",
                    "no", "not", "of", "on", "or", "such",
                    "that", "the", "their", "then", "there", "these",
                    "they", "this", "to", "was", "will", "with"]

    stops = [term for term in text_query.lower().split() if term in stop_words]

    # if we find the results, extract title and text information from doc_data, else do nothing
    if result_num > 0:
        return render_template('result.html', stop_len=len(stops), stops=stops, results=resultList, res_num=result_num, page_num=page, queries=shows)
    else:
        message = []
        if len(text_query) > 0:
            message.append('Unknown search term: ' + text_query)
        if len(author_query) > 0:
            message.append('Cannot find author: ' + author_query)

        return render_template('result.html', stop_len=len(stops), stops=stops, results=message, res_num=result_num, page_num=page, queries=shows)

# display suggestion for autocompletion
@app.route("/autocomplete", methods=['GET'])
def autocomplete():
    # get search term entered by user
    text = request.args.getlist('search[term]')
    search = Search(index='covid_index')
    # do suggest on the query term
    s = search.suggest('autocomplete', text=text, completion={'field': 'suggestion'})
    response = s.execute()
    options = response.suggest.autocomplete[0].options
    results = list()
    for option in options:
        if option['_source']['title'] not in results:
            results.append(option['_source']['title'])
    return jsonify(results)

# display a particular document given a result number
@app.route("/documents/<res>", methods=['GET'])
def documents(res):
    global gresults
    article = gresults[res]
    articletitle = article['title']
    for term in article:
        if type(article[term]) is AttrList:
            print("___181____")
            s = "\n"
            for item in article[term]:
                s += item + ",\n "
            article[term] = s
    # fetch the movie from the elasticsearch index using its id
    doc = Article.get(id=res, index='covid_index')
    articledic = doc.to_dict()
    article['author'] = str(articledic['author'])
    article['publish_time'] = str(articledic['publish_time'])
    return render_template('article.html', article=article, title=articletitle)


if __name__ == "__main__":
    app.run()
    app.debug = True