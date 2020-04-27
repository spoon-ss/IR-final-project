class TranslateService:
    CHINESE_OPTION = "chinese"
    ENGLISH_OPTION = "english"

    def __init__(self):
        pass

    def translate(self, query_str: str, from_lang: str, to_lang: str) -> str:
        return query_str + " translated"
