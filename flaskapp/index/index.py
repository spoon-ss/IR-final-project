import time
from elasticsearch import Elasticsearch
from elasticsearch import helpers
from elasticsearch_dsl import Index, Document, Text, Keyword, Integer, Nested, Date, Completion
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.analysis import tokenizer, analyzer
from elasticsearch_dsl.query import MultiMatch, Match
from elasticsearch_dsl import token_filter
# Connect to local host server
from .index_utils import process_json


INDEX_NAME = "sample_covid_19_index"

connections.create_connection(hosts=['127.0.0.1'])
'''
brit_spelling_tokenfilter = token_filter(
    'my_tokenfilter', # Any name for the filter
    'synonym', # Synonym filter type
    synonyms_path = "analysis/wn_s11.pl"
    )
'''


# Create elasticsearch object
es = Elasticsearch()

# Define analyzers appropriate for your data.
# You can create a custom analyzer by choosing among elasticsearch options
# or writing your own functions.
# Elasticsearch also has default analyzers that might be appropriate.
text_analyzer = analyzer('my_tokenfilter',
                         type='custom',
                         tokenizer='standard',
                         filter=['lowercase', 'stop'])

# n-gram tokenizer for chemical name;
three_gram_filter = token_filter('3-gram-filter', type='ngram', min_gram=5, max_gram=5)
chemical_ngram_analyzer = analyzer('chem_ngram_analyzer',
                             tokenizer=tokenizer('chem_tokenizer', type='char_group', tokenize_on_chars=['$']),
                             filter=["lowercase", "stop", three_gram_filter]
                             )
chemical_whole_analyzer = analyzer('chem_whole_analyzer',
                             tokenizer=tokenizer('chem_tokenizer', type='char_group', tokenize_on_chars=['$']),
                             filter=["lowercase", "stop", "trim"]
                             )
# --- Add more analyzers here ---
# use stopwords... or not?
# use stemming... or not?

# Define document mapping (schema) by defining a class as a subclass of Document.
# This defines fields and their properties (type and analysis applied).
# You can use existing es analyzers or use ones you define yourself as above.
class Article(Document):

    title = Text(analyzer=text_analyzer)
    abstract = Text(analyzer=text_analyzer)
    body = Text(analyzer=text_analyzer)
    authors = Text(analyzer='standard')
    publish_time = Date()
    url = Keyword()
    suggestion = Completion()
    chemicals_title_abstract_whole = Text(analyzer=chemical_whole_analyzer)
    chemicals_title_abstract_ngram = Text(analyzer=chemical_ngram_analyzer)
    chemicals_body_whole = Text(analyzer=chemical_whole_analyzer)
    chemicals_body_ngram = Text(analyzer=chemical_ngram_analyzer)

    # --- Add more fields here ---
    # What data type for your field? List?
    # Which analyzer makes sense for each field?

    # override the Document save method to include subclass field definitions
    def save(self, *args, **kwargs):
        return super(Article, self).save(*args, **kwargs)


# Populate the index
def buildIndex(file_path, size=None):
    """
    buildIndex creates a new film index, deleting any existing index of
    the same name.
    It loads a json file containing the movie corpus and does bulk loading
    using a generator function.
    """
    covid_index = Index(INDEX_NAME)
    if covid_index.exists():
        covid_index.delete()  # Overwrite any previous version
    # film_index.analyzer()  # register your customized analyzer
    covid_index.document(Article)  # register the document mapping
    covid_index.create()

    # Open the json film corpus
    data_dict = process_json(file_path, size)

    # Action series for bulk loading with helpers.bulk function.
    # Implemented as a generator, to return one movie with each call.
    # Note that we include the index name here.
    # The Document type is always 'doc'.
    # Every item to be indexed must have a unique key.

    def actions():
        # mid is movie id (used as key into movies dictionary)
        for mid in range(0, len(data_dict)):
            yield {
                "_index": INDEX_NAME,
                "_type": '_doc',
                "_id": mid,
                "title": data_dict[str(mid)]['title'],
                "abstract": data_dict[str(mid)]['abstract'],
                "body": data_dict[str(mid)]['body'],
                "author": data_dict[str(mid)]['authors'],
                "publish_time": data_dict[str(mid)]['publish_time'],
                "chemicals_title_abstract_whole": data_dict[str(mid)]['chemicals_title_abstract'],
                "chemicals_title_abstract_ngram": data_dict[str(mid)]['chemicals_title_abstract'],
                "chemicals_body_whole": data_dict[str(mid)]['chemicals_body'],
                "chemicals_body_ngram": data_dict[str(mid)]['chemicals_body'],
                "suggestion": data_dict[str(mid)]['title']
            }

    helpers.bulk(es, actions())

