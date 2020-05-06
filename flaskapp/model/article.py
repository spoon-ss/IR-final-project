
from elasticsearch_dsl import Index, Document, Text, Keyword, Integer, InnerDoc, Date, Completion, analyzer


# Define document mapping (schema) by defining a class as a subclass of Document.
# This defines fields and their properties (type and analysis applied).
# You can use existing es analyzers or use ones you define yourself as above.
class Article(Document):
    my_analyzer = analyzer('custom',
                           tokenizer='standard',
                           filter=['lowercase', 'stop', 'porter_stem'])

    title = Text(analyzer=my_analyzer)
    abstract = Text(analyzer=my_analyzer)
    author = Text(analyzer="standard")
    publish_time = Date()
    suggestion = Completion()

    # override the Document save method to include subclass field definitions
    def save(self, *args, **kwargs):
        return super(Article, self).save(*args, **kwargs)
