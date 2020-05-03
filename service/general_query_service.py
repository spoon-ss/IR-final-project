from datetime import date

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from elasticsearch_dsl.query import MoreLikeThis
import re


def _do_abstraction_query(s, abstraction_query, query_option):
    if len(abstraction_query) > 0:
        # if hypen is in the query, add double quotes around the term with hypen and then do simple_query_string query
        if "-" in abstraction_query:
            text = re.findall(r'\w+(?:-\w+)+', abstraction_query)
            t_query = abstraction_query.split(" ")
            # print(t_query)
            for i, q in enumerate(t_query):
                if q in text:
                    t_query[i] = "\"" + q + "\""
            t_query = " ".join(t_query)
            s = s.query('simple_query_string', query=t_query, fields=['title^1.5', 'abstract'],
                        default_operator=query_option)
        else:
            s = s.query('multi_match', query=abstraction_query, type='cross_fields', fields=['title^3', 'abstract'],
                        operator=query_option)
    return s


def _do_author_query(s, author_query):
    if len(author_query) > 0:
        s = s.query('match', author=author_query)
    return s


def _do_highlight(s):
    s = s.highlight_options(pre_tags='<mark>', post_tags='</mark>')
    s = s.highlight('abstract', fragment_size=999999999, number_of_fragments=1)
    s = s.highlight('title', fragment_size=999999999, number_of_fragments=1)
    s = s.highlight('author', fragment_size=999999999, number_of_fragments=1)
    return s


def _do_pagination(s, page):
    s = s[(page - 1) * 10: 10 + (page - 1) * 10]
    return s


def _extract_response(response):
    result_dict = {}
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

        result_dict[hit.meta.id] = result
    return result_dict


def get_stop_words():
    stop_words = ["a", "an", "and", "are", "as", "at", "be", "but", "by",
                  "for", "if", "in", "into", "is", "it",
                  "no", "not", "of", "on", "or", "such",
                  "that", "the", "their", "then", "there", "these",
                  "they", "this", "to", "was", "will", "with"]
    return stop_words


def extract_stop_words(query_text):
    stop_words = get_stop_words()
    stops = [term for term in query_text.lower().split() if term in stop_words]
    return stops

def get_more_like_this(s, query_text):
    
    s = s.query(MoreLikeThis(like=query_text, fields=['title', 'abstract']))
    # get first top 10 similar articles
    response = s[1:11].execute()   
    return _extract_response(response)

class GeneralQueryService:
    CONJUNCTIVE_OPTION = "and"
    DISJUNCTIVE_OPTION = "or"

    def __init__(self, index_path):
        client = Elasticsearch()
        self.search = Search(using=client, index=index_path)

    def query(self, query_text="", author_query="",
              min_time_query=date.min,
              max_time_query=date.max,
              query_option=DISJUNCTIVE_OPTION,
              page=1) -> dict:


        # search for runtime using a range query
        s = self.search.query('range', publish_time={'gte': min_time_query, 'lte': max_time_query})
        s = _do_abstraction_query(s, query_text, query_option)
        s = _do_author_query(s, author_query)
        s = _do_highlight(s)
        s = _do_pagination(s, page)

        response = s.execute()
        result_dict = _extract_response(response)
        return {"result_dict": result_dict, "total_hits": response.hits.total['value'], "stop_words_included": extract_stop_words(query_text)}

    def autocomplete(self, text):
        search = Search(index='covid_index')
        # do suggest on the query term
        s = search.suggest('autocomplete', text=text, completion={'field': 'suggestion'})
        response = s.execute()
        options = response.suggest.autocomplete[0].options
        results = list()
        for option in options:
            if option['_source']['title'] not in results:
                results.append(option['_source']['title'])
        return results

    def doc_result(self, query_id):
        # get article detail and the 'more like this' result
        response = self.search.query('ids', values=query_id).execute()
        article_dic = dict()
        article_dic['Title'] = response.hits[0].title
        article_dic['Abstract'] = response.hits[0].abstract
        article_dic['Author'] = response.hits[0].author
        article_dic['Publish Time'] = response.hits[0].publish_time
        text = article_dic['Title'] +article_dic['Abstract']
        more_like_this_dic = get_more_like_this(self.search, text)
        return article_dic, more_like_this_dic