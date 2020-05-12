from datetime import date

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from elasticsearch_dsl.query import MoreLikeThis
import re
from elasticsearch_dsl import Q
from nltk.corpus import wordnet
from bs4 import BeautifulSoup
import collections


def _do_abstraction_query(s, abstraction_query, query_option):
    if len(abstraction_query) > 0:
        '''
        # if hypen is in the query, add double quotes around the term with hypen and then do simple_query_string query
        if "-" in abstraction_query:
            text = re.findall(r'\w+(?:-\w+)+', abstraction_query)
            t_query = abstraction_query.split(" ")
            print(t_query)
            for i, q in enumerate(t_query):
                if q in text:
                    t_query[i] = "\"" + q + "\""
            t_query = " ".join(t_query)
            print(t_query)
            s = s.query('simple_query_string', query=t_query, fields=['title^1.5', 'abstract'],
                        default_operator=query_option)
        '''
        phrases = process_abstraction_query(abstraction_query)

        if query_option == "or":
            q0 = phrases.pop()
            if '"' in q0:
                q = Q('multi_match', query=q0, type='phrase_prefix', fields=['title^2', 'abstract'])
            else:
                if len(q0) >= 4:
                    q = Q('multi_match', query=q0, fields=['title^2', 'abstract'], fuzziness=1, max_expansions=2)
                else:
                    q = Q('multi_match', query=q0, fields=['title^2', 'abstract'])
            while len(phrases) > 0:
                q0 = phrases.pop()
                if '"' in q0:
                    q |= Q('multi_match', query=q0, type='phrase_prefix', fields=['title^2', 'abstract'])
                else:
                    if len(q0) >= 4:
                        q |= Q('multi_match', query=q0, fields=['title^2', 'abstract'], fuzziness=1, max_expansions=2)
                    else:
                        q |= Q('multi_match', query=q0, fields=['title^2', 'abstract'])
            s = s.query(q)
        elif query_option == "and":
            while len(phrases) > 0:
                q0 = phrases.pop()
                if '"' in q0:
                    s = s.query('multi_match', query=q0, type='phrase_prefix', fields=['title^2', 'abstract'])
                else:
                    if len(q0) >= 4:
                        s = s.query('multi_match', query=q0, fields=['title^2', 'abstract'], fuzziness=1,
                                    max_expansions=2)
                    else:
                        s = s.query('multi_match', query=q0, fields=['title^2', 'abstract'])
    return s


def _do_author_query(s, author_query):
    if len(author_query) > 0:
        s = s.query('match', author=author_query)
    return s


def _extract_free_text_query_text(s: str) -> dict:
    """ Extract information from free query text, return a dict contains the information extracted.
    Take a string "<chem>alcohol</chem> <chem>isopropyl</chem> covid <phrase>test result</phrase>"
    Return a dict : {"chem": ["alcohol", "isopropyl"], "phrase": ["test result"], "normal": ["covid"]}
    """
    if type(s) is not str:
        raise TypeError("query text must be str")

    result_dict = {"chemical": [], "phrase": [], "normal": ""}
    soup = BeautifulSoup(s, features="lxml")

    for tag in soup.find_all('chem'):
        result_dict['chemical'].append(tag.text)
        tag.decompose()

    for tag in soup.find_all('phrase'):
        result_dict['phrase'].append(tag.text)
        tag.decompose()

    result_dict["normal"] = soup.get_text().strip()
    return result_dict


def _do_chemical_query(query_list: list, option):
    q = None
    for chem in query_list:
        new_q = Q('multi_match', query=chem, type='phrase_prefix', fields=['chemicals_title_abstract_whole^9',
                                                     "chemicals_body_whole^8",
                                                     "chemicals_title_abstract_ngram^3",
                                                     "chemicals_body_ngram^1"])
        if option == GeneralQueryService.CONJUNCTIVE_OPTION:
            q = new_q & q if q is not None else new_q
        elif option == GeneralQueryService.DISJUNCTIVE_OPTION:
            q = new_q | q if q is not None else new_q
        else:
            raise RuntimeError("No such query options")

    return q


def _do_phrase_query(query_list: list, option):
    q = None
    for phrase in query_list:
        new_q = Q('multi_match', query=phrase, type='phrase_prefix', fields=['title^2', 'abstract'])
        if option == GeneralQueryService.CONJUNCTIVE_OPTION:
            q = new_q & q if q is not None else new_q
        elif option == GeneralQueryService.DISJUNCTIVE_OPTION:
            q = new_q | q if q is not None else new_q
        else:
            raise RuntimeError("No such query options")
    return q


def _do_text_query(query_str: str, option):
    if query_str == "":
        return None
    if option == GeneralQueryService.CONJUNCTIVE_OPTION:
        new_q = Q('multi_match', query=query_str, fields=['title^2', 'abstract', 'body^0.5'],
                  fuzziness=1, max_expansions=2, operator='and')
    elif option == GeneralQueryService.DISJUNCTIVE_OPTION:
        new_q = Q('multi_match', query=query_str, fields=['title^2', 'abstract', 'body^0.5'], fuzziness=1, max_expansions=2)
    else:
        raise RuntimeError("No such option")
    return new_q


def _do_free_text_query(s, query_str: str, option):
    extract_dict = _extract_free_text_query_text(query_str)
    # s = _do_abstraction_query(s, extract_dict['normal'], option)
    q_list = []
    q_list.append(_do_text_query(extract_dict['normal'], option))
    q_list.append(_do_chemical_query(extract_dict['chemical'], option))
    q_list.append(_do_phrase_query(extract_dict['phrase'], option))
    q = None
    for inner_q in q_list:
        if q is None:
            q = inner_q
            continue
        if inner_q is None:
            continue
        if option == GeneralQueryService.CONJUNCTIVE_OPTION:
            q &= inner_q
        elif option == GeneralQueryService.DISJUNCTIVE_OPTION:
            q |= inner_q
        else:
            raise RuntimeError("No such options")
    if q is not None:
        s = s.query(q)
    return s


def _do_highlight(s):
    s = s.highlight_options(pre_tags='<mark>', post_tags='</mark>')
    s = s.highlight('abstract', fragment_size=500, number_of_fragments=1)
    s = s.highlight('title', fragment_size=150, number_of_fragments=0)
    s = s.highlight('author', fragment_size=100, number_of_fragments=1)
    s = s.highlight('body', number_of_fragments=1, fragment_size=300)
    s = s.highlight('chemicals_title_abstract_whole', fragment_size=300, number_of_fragments=1)
    s = s.highlight('chemicals_title_abstract_ngram', fragment_size=300, number_of_fragments=1)
    s = s.highlight('chemicals_body_whole', fragment_size=300, number_of_fragments=1)
    s = s.highlight('chemicals_body_ngram', fragment_size=300, number_of_fragments=1)
    return s


def _do_pagination(s, page):
    s = s[(page - 1) * 10: 10 + (page - 1) * 10]
    return s


def _extract_highlight_str(s: str):
    if type(s) is not str:
        raise TypeError("query text must be str")

    result = ""
    soup = BeautifulSoup(s, features="lxml")

    for tag in soup.find_all('mark'):
        result = result + str(tag) + ", "

    return result


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

            if 'body' in hit.meta.highlight:
                result['body'] = hit.meta.highlight.body[0]
            else:
                result['body'] = ""

            if 'author' in hit.meta.highlight:
                result['author'] = hit.meta.highlight.author[0]
            else:
                result['author'] = hit.author[0:100]

            if 'chemicals_title_abstract_whole' in hit.meta.highlight:
                result['chemicals'] = _extract_highlight_str(hit.meta.highlight.chemicals_title_abstract_whole[0])
            elif 'chemicals_title_abstract_ngram' in hit.meta.highlight:
                result['chemicals'] = _extract_highlight_str(hit.meta.highlight.chemicals_title_abstract_ngram[0])
            elif 'chemicals_body_whole' in hit.meta.highlight:
                result['chemicals'] = _extract_highlight_str(hit.meta.highlight.chemicals_body_whole[0])
            elif 'chemicals_body_ngram' in hit.meta.highlight:
                result['chemicals'] = _extract_highlight_str(hit.meta.highlight.chemicals_body_ngram[0])
            else:
                result['chemicals'] = ""

        else:
            if len(hit.title) > 60:
                result['title'] = hit.title[:60] + '...'
            else:
                result['title'] = hit.title
            result['abstract'] = hit.abstract
            result['chemicals'] = ""
            result['author'] = hit.author
            result['body'] = ""
        publish_time = hit.publish_time
        result['publish_time'] = "" if publish_time == str(date.min) else publish_time
        result_dict[hit.meta.id] = result
    return result_dict


def process_abstraction_query(abstraction_query):
    # find all phrases with " "
    pattern = re.compile(r'(?:\B\")(.*?)(?:\b\")')
    phrases = pattern.findall(abstraction_query)
    abstraction_query = pattern.sub('', abstraction_query).strip()
    phrases = phrases + abstraction_query.split()
    # find all hyphen
    text = re.findall(r'\w+(?:-\w+)+', abstraction_query)
    for i in range(len(phrases)):
        if phrases[i] in text:
            phrases[i] = "\"" + phrases[i] + "\""
    return phrases


def get_stop_words():
    stop_words = ["a", "an", "and", "are", "as", "at", "be", "but", "by",
                  "for", "if", "in", "into", "is", "it",
                  "no", "not", "of", "on", "or", "such",
                  "that", "the", "their", "then", "there", "these",
                  "they", "this", "to", "was", "will", "with"]
    return stop_words


def get_synonyms(abstraction_query):
    phrases = process_abstraction_query(abstraction_query)
    d = collections.defaultdict(list)
    for p in phrases:
        synonyms = []

        for syn in wordnet.synsets(p):
            for l in syn.lemmas():
                if '_' not in l.name():
                    synonyms.append(l.name())

        d[p] = list(set(synonyms))
        if p.lower() in d[p]:
            d[p].sort(key=p.lower().__eq__)
        elif len(d[p]) > 0:
            d[p].append(p)
    for key in d:
        tmp = []
        for i in range(len(phrases)):
            if phrases[i] == key:
                tmp.append(i)
        d[key].append(tmp)
    return d


def extract_stop_words(query_text):
    stop_words = get_stop_words()
    stops = [term for term in query_text.lower().split() if term in stop_words]
    return stops


def get_more_like_this(s, query_text):
    s = s.query(MoreLikeThis(like=query_text, fields=['title', 'abstract', 'body^3'], stop_words=get_stop_words()))
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
        s = _do_free_text_query(s, query_text, query_option)
        s = _do_author_query(s, author_query)
        s = _do_highlight(s)
        s = _do_pagination(s, page)

        response = s.execute()
        result_dict = _extract_response(response)
        return {"result_dict": result_dict, "total_hits": response.hits.total['value'],
                "stop_words_included": extract_stop_words(query_text), "synonyms": get_synonyms(query_text)}

    def autocomplete(self, text):
        # do suggest on the query term
        s = self.search.suggest('autocomplete', text=text, completion={'field': 'suggestion'})
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
        article_dic['Body'] = response.hits[0].body.replace("\n", "</br></br>")
        article_dic['Author'] = response.hits[0].author
        article_dic['Publish Time'] = response.hits[0].publish_time
        text = article_dic['Title'] + article_dic['Abstract']
        more_like_this_dic = get_more_like_this(self.search, text)
        return article_dic, more_like_this_dic
