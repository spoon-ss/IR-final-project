import json
import re
import time

from elasticsearch import Elasticsearch
from elasticsearch import helpers
from elasticsearch_dsl import Index, Document, Text, Keyword, Integer, InnerDoc, Date, Completion
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.analysis import tokenizer, analyzer
from elasticsearch_dsl.query import MultiMatch, Match
from datetime import date, datetime

from model import Article
# Connect to local host server
connections.create_connection(hosts=['127.0.0.1'])

# Create elasticsearch object
es = Elasticsearch()

# Define analyzers appropriate for your data.
# You can create a custom analyzer by choosing among elasticsearch options
# or writing your own functions.
# Elasticsearch also has default analyzers that might be appropriate.


# Populate the index
def buildIndex():
    """
    buildIndex creates a new film index, deleting any existing index of
    the same name.
    It loads a json file containing the movie corpus and does bulk loading
    using a generator function.
    """

    covid_index = Index('covid_index')
    if covid_index.exists():
        covid_index.delete()  # Overwrite any previous version
    covid_index.document(Article)  # register the document mapping
    covid_index.create() # create index with specified mapping and document

    
    articles = list()
    # Open the json covid corpus
    with open('covid_comm_use_subset_meta.json', 'r', encoding='utf-8') as data_file:
        # load articles from json file into dictionary
        for line in data_file:
            try:
                articles.append(json.loads(line))
            except json.decoder.JSONDecodeError:
                continue   

    size = len(articles)

    # Action series for bulk loading with helpers.bulk function.
    # Implemented as a generator, to return one movie with each call.
    # Note that we include the index name here.
    # The Document type is always 'doc'.
    # Every item to be indexed must have a unique key.
    def actions():
        # mid is movie id (used as key into movies dictionary)
        for mid in range(size):
            # handle NaN in author field
            author = str(articles[mid]['authors'])
            if author == "NaN":
                author = ""
            # handle NaN and missing month and day in publish_time field
            time = str(articles[mid]['publish_time'])
            # if NaN in publish_time let publish time be the date when index is run
            if time == "NaN":
                publish_time = date.today()
            # if month and day are missing in publish_time
            elif time == "2020":
                publish_time = date(2020, 1, 1)
            else:
                try:
                    publish_time = datetime.strptime(time, '%Y %m %d').date()
                except Exception:
                    publish_time = date.today()
            yield {
                "_index": "covid_index", 
                "_type": '_doc',
                "_id": mid,
                "title": articles[mid]['title'],
                "abstract": articles[mid]['abstract'],
                "author": author,
                "publish_time": publish_time,
                "suggestion": articles[mid]['title']
            }

    helpers.bulk(es, actions())


# command line invocation builds index and prints the running time.
def main():
    start_time = time.time()
    buildIndex()
    print("=== Built index in %s seconds ===" % (time.time() - start_time))


if __name__ == '__main__':
    main()
