import collections
from common.wordlist import DerivedWordList, WeightedWordList
from configurator import configurator
from sklearn.feature_extraction.text import TfidfVectorizer


# Input is a Dataset object
class WordListFilter(object):
    def __init__(self, config=None):
        self.filtered_data = []
        self.config = config
        
    def filter_words(self, word_lists):
        self.filtered_data = word_lists
        return self.filtered_data
        

class Tfidf_Filter(WordListFilter):
    def __init__(self, config):
        super().__init__(config)
        self.min_weight = configurator.set_with_default(self.config, 'min_weight', 0.1)
        self.top_n = configurator.set_with_default(self.config, 'top_n', 10)
        
    def filter_words(self, word_lists):
        label_clean_list = []
        for word_list in word_lists:
            line = word_list.string
            label_clean_list.append(line)
        tfidf_vec = TfidfVectorizer()
        transformed = tfidf_vec.fit_transform(raw_documents=label_clean_list)
        index_value={i[1]:i[0] for i in tfidf_vec.vocabulary_.items()}
        weighted_word_list = []
        for wl in word_lists:
            twords = tfidf_vec.transform([wl.string])
            tdict = {index_value[column]:value for (column,value) in zip(twords.indices,twords.data)}
            sorted_item_map_list = sorted(tdict.items(), key=lambda kv: float(kv[1]), reverse=True)
            min_weight_items = [word for word in sorted_item_map_list if float(word[1]) >= self.min_weight]
            min_weight_items = min_weight_items[:self.top_n]
            new_word_list = WeightedWordList(wl,
                                             {w[0]: w[1] for w in min_weight_items})
            self.filtered_data.append(new_word_list)
        return self.filtered_data
"""
        for row in transformed:
            weighted_word_list.append({index_value[column]:value for (column,value) in zip(row.indices,row.data)})
        print(weighted_word_list)
        counter=0
        for word_list in weighted_word_list:
            sorted_item_map_list = sorted(word_list.items(), key=lambda kv: float(kv[1]), reverse=True)
            min_weight_items = [word for word in sorted_item_map_list if float(word[1]) >= self.min_weight]
            min_weight_items = min_weight_items[:self.top_n]
            self.word_weights.append({w[0]: w[1] for w in min_weight_items})
            new_word_list = WeightedWordList(word_lists[counter], 
                                             {w[0]: w[1] for w in min_weight_items})
            counter+=1
            print(word_lists[counter].string,'ORIG', ' '.join(word_list.keys()))
            self.filtered_data.append(new_word_list)
"""


        
class Freq_Filter(WordListFilter):
    def __init__(self, config):
        super().__init__(config)
        self.min_weight = configurator.set_with_default(self.config, 'min_weight', 0.1)
        self.top_n = configurator.set_with_default(self.config, 'top_n', 10)
        
    def filter_words(self, word_lists):
        for word_list in word_lists:
            counts = collections.Counter(word_list.words)
            top_counts = counts.most_common(self.top_n)
            new_word_list = DerivedWordList(word_list, 
                                            [w for w in [word[0] for word in top_counts if word[1] >= self.min_weight]])
            self.filtered_data.append(new_word_list)
        return self.filtered_data
    
