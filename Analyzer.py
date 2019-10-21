import requests
from bs4 import BeautifulSoup
import pandas as pd
from time import sleep
import json
from pymorphy2 import MorphAnalyzer
import re
from collections import OrderedDict
from dictdiffer import diff, patch, swap, revert

class Analyzer:
    def __init__(self):
        self._analyzer = MorphAnalyzer()
        
    def get_morphems(self, word):
        """Получает морфемы слова
        Обращается по адресу и выдает морфемы в виде списка [(морфема1, название1),(морфема2, название2), ...]
        """
        url = "https://kartaslov.ru/разбор-слова-по-составу/{}".format(word)
        text = requests.get(url).text
        soup = BeautifulSoup(text, 'html.parser')
        
        # у сайта проблемы, например, со словом пять, парсит другое слово(пятить), поэтому чекаем на совпадение с желаемым
        # сейчас просто ингорим, но может стоит выкидывать то что лишнее добавляется - надо исследовать
        word_on_site = re.match(".*«(.*)»", soup.find('h1', class_='v2-h1').text)
        if word_on_site.group(1) != word:
            return {"error":"site parsing error"}

        table = soup.find('table', class_='morphemics-table')
        if table is None:
            return {"error":"not found on site"}
        
        rows = table.findAll('tr')
        info = []
        for row in rows:
            info.append((row.find('td', class_='td-morpheme-text').text, row.find('td', class_='td-morpheme-type').text))
         
        return info
    
    def get_POS(self, word, analyzer='pymorphy'):
        """Получает часть речи для слова
        Для многозначных берем первое что показывает анализатор, возмножны проблемы
        Заложен вариант для остальных анализаторов, пока не реализован
        """
        if analyzer=='pymorphy':
            return self._analyzer.parse(word)[0].tag.POS 
        else:
            raise NotImplementedError
    
    def _get_dd(self, m):
        """Переводит список морфем и их названий в упорядоченный словарь
        """
        d = OrderedDict()
        for v, k in m:
            if k in d:
                d[k].append(v)
            else:
                d[k] = [v]
        return d.copy()
    
    def _find(self, dif, action='add', morpheme='приставка'):
        """Ищет в dictdiffer различия определенного типа
        """
        for v in dif:
            if v[0]==action:
                if v[1]==morpheme: 
                    return True
                elif type(v[1])==list:
                    if v[1][0]==morpheme: 
                        return v[2]                  
                elif v[1]=='':
                    # thats in case [('add', '', [('приставка', ['при']), ('суффикс', ['ва'])])]
                    for i in v[2]:
                        if i[0]==morpheme:
                            return True
        return False

    def analyze(self, word1, word2, verbose=True):
        """Анализ слов на пердмет слообразования
        """
        #get morphemes
        m1_list = self.get_morphems(word1)
        m2_list = self.get_morphems(word2)
        
        #check if morphemes valid
        if 'error' in m1_list:
            if verbose: print('cant parse {}, error:'.format(word1, m1_list['error']))
            return 'UNKNOWN_PARSE_ERROR'       
        if 'error' in m2_list:
            if verbose: print('cant parse {}, error:'.format(word2, m2_list['error']))
            return 'UNKNOWN_PARSE_ERROR'    

        #revert morpheme list to ordered dict 
        m1 = self._get_dd(m1_list)
        m2 = self._get_dd(m2_list)
        
        #delete endings
        for v in ['глагольноеокончание', 'окончание', 'постфикс', 'нулевоеокончание']:
            m1[v] = []
            m2[v] = []

        #get POS
        pos_pair = (self.get_POS(word1), self.get_POS(word2))
        
        #find dif
        dif = list(diff(m1, m2))
        if verbose: print(dif)
        
        #actual methods
        p = self._find(dif, action='add', morpheme='приставка')
        s = self._find(dif, action='add', morpheme='суффикс')
        dk = self._find(dif, action='change', morpheme='корень')
        bs = self._find(dif, action='remove', morpheme='суффикс')
        
        ''' описание тегов из opencorpora
        NOUN	имя существительное	хомяк
        ADJF	имя прилагательное (полное)	хороший
        ADJS	имя прилагательное (краткое)	хорош
        COMP	компаратив	лучше, получше, выше
        VERB	глагол (личная форма)	говорю, говорит, говорил
        INFN	глагол (инфинитив)	говорить, сказать
        PRTF	причастие (полное)	прочитавший, прочитанная
        PRTS	причастие (краткое)	прочитана
        GRND	деепричастие	прочитав, рассказывая
        NUMR	числительное	три, пятьдесят
        ADVB	наречие	круто
        NPRO	местоимение-существительное	он
        PRED	предикатив	некогда
        PREP	предлог	в
        CONJ	союз	и
        PRCL	частица	бы, же, лишь
        INTJ	междометие	ой
        
        '''
        # приставочный
        p_set = {('VERB', 'VERB'), ('VERB', 'INFN'), ('INFN', 'VERB'), ('INFN', 'INFN'),
                 ('NOUN', 'NOUN'), 
                 ('ADJF', 'ADJF'), ('ADJF', 'ADJS'), ('ADJS', 'ADJF'), ('ADJS', 'ADJS'),
                 ('NPRO', 'NPRO'),
                 ('ADVB', 'ADVB')}
        # суффиксальный
        s_set = {('NOUN', 'NOUN'), ('NOUN', 'ADJS'), ('NOUN', 'ADJF'), ('NOUN', 'VERB'), ('NOUN', 'INFN'),
                 ('VERB', 'VERB'), ('VERB', 'INFN'), ('VERB', 'NOUN'), ('VERB', 'ADJS'), ('VERB', 'ADJF'),
                 ('INFN', 'VERB'), ('INFN', 'INFN'), ('INFN', 'NOUN'), ('INFN', 'ADJS'), ('INFN', 'ADJF'),
                 ('ADJF', 'ADVB'), ('ADJF', 'NOUN'), ('ADJF', 'VERB'), ('ADJF', 'INFN'), ('ADJF', 'ADJF'),
                 ('ADJS', 'ADVB'), ('ADJS', 'NOUN'), ('ADJS', 'VERB'), ('ADJS', 'INFN'), ('ADJS', 'ADJS')}
        # приставочно-суффиксальный       
        ps_set = {('NOUN', 'NOUN'), 
                  ('NOUN', 'ADJF'), ('NOUN', 'ADJS'), 
                  ('NOUN', 'VERB'), ('NOUN', 'INFN'), ('ADJF', 'VERB'), ('ADJF', 'INFN'), ('ADJS', 'VERB'), ('ADJS', 'INFN'),
                  ('ADJF', 'ADVB'), ('ADJS', 'ADVB'), ('NOUN', 'ADVB'), ('NUMR', 'ADVB'),
                  ('INFN', 'INFN'), ('VERB', 'VERB') # добавил я, надо чекать верно ли это
                 }
        bs_set = {('INFN', 'NOUN'), ('VERB', 'NOUN'), 
                 ('ADJF', 'NOUN'), ('ADJS', 'NOUN'),
                 ('NOUN', 'NOUN'), 
                 ('NOUN', 'ADJF'), ('NOUN', 'ADJS'),
                 ('INFN', 'ADJF'), ('INFN', 'ADJS'), ('VERB', 'ADJF'), ('VERB', 'ADJS'),
                 ('ADJF', 'ADJF'), ('ADJF', 'ADJS'), ('ADJS', 'ADJF'), ('ADJS', 'ADJS'),
                 ('ADVB', 'ADJF'), ('ADVB', 'ADJS'),
                 ('NUMR', 'NUMR')}# проверить количественное-качественное
                 
        ## все далльше при условии что у нас только один корень!!!
        ## два надо отдельно смотреть
        if dk:
            #return "DIFF_ROOT"
            #теперь проверим вдруг жто чередующаяся согласная
            if len(m1['корень'][0])==len(m2['корень'][0]):
                s = {m1['корень'][0][-1], m2['корень'][0][-1]}
                if verbose: print(s)
                # неоптимально при большом списке!
                if s not in [{'г', 'ж'}, {'a', 'a'}]:
                    return ("DIFF_ROOT", m1_list, m2_list)
            
        if (pos_pair in ps_set) and p and s:
            if verbose: print(word1, '->', word2, ': приставочно-суффиксальный')
            return ('PS', m1_list, m2_list)
        if (pos_pair in p_set) and  p:
            if verbose: print(word1, '->', word2, ': приставочный')
            return ('P', m1_list, m2_list)
        if (pos_pair in s_set) and s:
            if verbose: print(word1, '->', word2, ': суффиксальный')
            return ('S', m1_list, m2_list)
        if (pos_pair in bs_set) and s:
            if verbose: print(word1, '->', word2, ': ,безсуффиксный')
            return ('BS', m1_list, m2_list)
        return 'UNKNOWN'