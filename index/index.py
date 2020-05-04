import json
import re
import time
from elasticsearch import Elasticsearch
from elasticsearch import helpers
from elasticsearch_dsl import Index, Document, Text, Keyword, Integer, Nested, Date, Completion
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.analysis import tokenizer, analyzer
from elasticsearch_dsl.query import MultiMatch, Match
from elasticsearch_dsl import token_filter

# Connect to local host server
connections.create_connection(hosts=['127.0.0.1'])
'''
brit_spelling_tokenfilter = token_filter(
    'my_tokenfilter', # Any name for the filter
    'synonym', # Synonym filter type
    synonyms_path = "analysis/wn_s.pl"
    )
'''

# Create elasticsearch object
es = Elasticsearch()

# Define analyzers appropriate for your data.
# You can create a custom analyzer by choosing among elasticsearch options
# or writing your own functions.
# Elasticsearch also has default analyzers that might be appropriate.
text_analyzer = analyzer('custom',
                         tokenizer='standard',
                         filter=['lowercase', 'stop'])
# author_analyzer = analyzer('custom',
#                            tokenizer='standard',
#                            filter=['lowercase'])


# --- Add more analyzers here ---
# use stopwords... or not?
# use stemming... or not?

# Define document mapping (schema) by defining a class as a subclass of Document.
# This defines fields and their properties (type and analysis applied).
# You can use existing es analyzers or use ones you define yourself as above.
class Article(Document):
    sha = Text()
    title = Text(analyzer=text_analyzer)
    abstract = Text(analyzer=text_analyzer)
    authors = Text(analyzer='standard')
    publish_time = Date()
    suggestion = Completion()

    # --- Add more fields here ---
    # What data type for your field? List?
    # Which analyzer makes sense for each field?

    # override the Document save method to include subclass field definitions
    def save(self, *args, **kwargs):
        return super(Article, self).save(*args, **kwargs)


# Populate the index
def buildIndex():
    """
    buildIndex creates a new film index, deleting any existing index of
    the same name.
    It loads a json file containing the movie corpus and does bulk loading
    using a generator function.
    """
    covid_index = Index('sample_covid_19_index')
    if covid_index.exists():
        covid_index.delete()  # Overwrite any previous version
    # film_index.analyzer()  # register your customized analyzer
    covid_index.document(Article)  # register the document mapping
    covid_index.create()

    # Open the json film corpus
    data_dict = process_json("covid_comm.json")
    size = len(data_dict)

    # Action series for bulk loading with helpers.bulk function.
    # Implemented as a generator, to return one movie with each call.
    # Note that we include the index name here.
    # The Document type is always 'doc'.
    # Every item to be indexed must have a unique key.

    def actions():
        # mid is movie id (used as key into movies dictionary)
        for mid in range(1, size + 1):
            # print("document: " + str(mid))
            # print(convert_date(data_dict[str(mid)]['publish_time']))
            yield {
                "_index": "sample_covid_19_index",
                "_type": '_doc',
                "_id": mid,
                "sha": data_dict[str(mid)]['sha'],
                "title": data_dict[str(mid)]['title'],
                "abstract": data_dict[str(mid)]['abstract'],
                "author": data_dict[str(mid)]['authors'],
                "publish_time": convert_date(data_dict[str(mid)]['publish_time']),
                # movies[str(mid)]['runtime'] # You would like to convert runtime to integer (in minutes)
                # --- Add more fields here ---
                "suggestion": data_dict[str(mid)]['title']
            }

    helpers.bulk(es, actions())


def process_json(path):
    import json
    result_dict = {}
    with open(path) as f:
        i = 1
        for line in f.readlines():
            ob = json.loads(line)
            if type(ob["authors"]) != str:
                ob["authors"] = ""
            result_dict[str(i)] = ob
            i += 1
    return result_dict

def convert_date(date_ob):
    from datetime import date
    import math
    mon_dict = {"Jan": "1", "Feb": "2", "Mar": "3", "Apr": "4", "May": "5",  "Jun": "6", "Jul": "7", "Aug": "8",
                "Sep": "9", "Sept": "9", "Oct": "10", "Nov": "11", "Dec": "12"}
    date_result = date.min
    if date_ob is None:
        return date_result
    if type(date_ob) == float:
        if math.isnan(date_ob):
            return date_result
        return date.fromtimestamp(date_ob)
    if type(date_ob) == str:
        if len(date_ob) == 0 or date_ob == "NaN":
            return date_result
        date_param = [1, 1, 1]
        date_ob = date_ob.split()
        if len(date_ob) > 3:
            date_ob = date_ob[0:3]
        for i, s in enumerate(date_ob):
            if s in mon_dict:
                s = mon_dict[s]
            try:
                date_param[i] = int(s)
            except ValueError as err:
                date_param[1] = 1
        try:
            date_result = date(date_param[0], date_param[1], date_param[2])
        except ValueError:
            return date_result
    return date_result

# command line invocation builds index and prints the running time.
def main():
    start_time = time.time()
    buildIndex()
    print("=== Built index in %s seconds ===" % (time.time() - start_time))


if __name__ == '__main__':
    main()
