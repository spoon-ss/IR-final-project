from googletrans import Translator
import jieba


class TranslateService:
    
    def __init__(self, ser_url='translate.google.com', outpt='english', inpt='chinese'):
        self.translator = Translator(service_urls=[ser_url])
        self.inlan = inpt
        self.outlan = outpt
     
           
    def translate(self,txt):
        "Translate raw txt to English"   
        output = self.translator.translate(txt)
        return output.text.lower()
    
    def tokenizer_chn(self,txt):
        "Tokenize Chinese querty to Chinese query"
        result = list(jieba.cut_for_search(txt))
        return result
    
    def ctoks2Eng(self, chntoks):
        "covert chinese tokens to english token"
        result = []
        for wd in chntoks:
            result.append(self.translator.translate(wd).text.lower())
        return result
    
    def translateTokens(self,txt):
        "translate chinese raw text into enlgish tokens for searching purpose"
        chntoks = self.tokenizer_chn(txt)
        chntoks = self.ctoks2Eng(chntoks)
        translated = self.ctoks2Eng(chntoks)
        return translated
    
    
t = TranslateService()
print(t.translate('新冠 DNA病毒'))
    
    

  
  
    
    

        

    
    
    
    
