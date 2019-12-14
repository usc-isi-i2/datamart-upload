from augmenter import augmentation_methods
from common.wordlist import DerivedWordList
import gensim
from gensim import corpora
from common import preprocessing

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation as LDA


class Augmenter(object):
    def __init__(self, config=None):
        self.augmented_data = []
        self.config = config

    @staticmethod
    def required_resources():
        return []

    def augment_word_lists(self, word_lists):
        pass

def load_word2vec_model(*args, **kwargs):
    return gensim.models.KeyedVectors.load_word2vec_format(*args, **kwargs)

class W2V_Augmenter(Augmenter):
    def __init__(self, config, GNews_SLIM_model):
        super().__init__(config)
        self.GNews_SLIM_model = GNews_SLIM_model

    @staticmethod
    def required_resources():
        return ['GNews_SLIM_model']

    def augment_word_lists(self, word_lists):
        counter = 0
        for string in word_lists:
            word_list = string.words
            w2v_augmentation = []+word_list
            for word in word_list:
                if word in self.GNews_SLIM_model.wv.vocab:
                    w2v_augmentation += augmentation_methods.get_w2v_augmented_list(word, self.GNews_SLIM_model, 10)
            new_word_list = DerivedWordList(string, [w for w in list(w2v_augmentation)])
            self.augmented_data.append(new_word_list)
            counter += 1
#            print(counter)
        return self.augmented_data


def load_elicit_corpus(path):
    ELICIT_corpus = []
    with open(path, 'r') as file:
        lines = file.readlines()
        for line in lines:
            ELICIT_corpus.append(line[:len(line)-1])
    return ELICIT_corpus


class LDA_Gensim_Augmenter(Augmenter):
    def __init__(self, config, ELICIT_Corpus):
        super().__init__(config)

        doc_clean = [preprocessing.lda_clean(doc).split() for doc in ELICIT_corpus]
        topic_num = 250
        print("Training LDA, current number of topics "+str(topic_num)+" ...")

        # Creating the term dictionary of our courpus, where every unique term is assigned an index. 
        self.dictionary = corpora.Dictionary(doc_clean)

        # Converting list of documents (corpus) into Document Term Matrix using dictionary prepared above.
        doc_term_matrix = [self.dictionary.doc2bow(doc) for doc in doc_clean] # Term Document Frequency = corpus

        # Creating the object for LDA model using gensim library
        Lda = gensim.models.ldamodel.LdaModel

        # Running and Trainign LDA model on the document term matrix.
        self.lda_gensim_model = Lda(doc_term_matrix, num_topics=topic_num, id2word = self.dictionary, iterations=2500)

    @staticmethod
    def required_resources():
        return ['ELICIT_Corpus']

    def augment_word_lists(self, word_lists):
        counter = 0
        for string in word_lists:
            word_list = string.words
#             print ("words: " + str(word_list))
            lda_augmentation= []+word_list
            augementation_list = augmentation_methods.get_LDA_gensim_doc_augmentation(word_list, self.lda_gensim_model, self.dictionary)
            #print (augementation_list)
            lda_augmentation += augementation_list
            new_word_list = DerivedWordList(string, [w for w in list(lda_augmentation)])
            self.augmented_data.append(new_word_list)
            counter +=1
            #print (counter)
            
        return self.augmented_data


class LDA_sklearn_Augmenter(Augmenter):
    def __init__(self, config, ELICIT_Corpus):
        super().__init__(config)

        doc_clean = [preprocessing.lda_clean(doc).split() for doc in ELICIT_corpus]
        intext = doc_clean
        topic_num = 250
        print("Training LDA, current number of topics "+str(topic_num)+" ...")
        self.sklearn_cvect = CountVectorizer(input='content', decode_error='ignore', strip_accents='ascii', analyzer='word', ngram_range=(1,1), max_df=0.9, min_df=1, max_features=2500, stop_words='english', lowercase=True)

        corpus_tokens = self.sklearn_cvect.fit_transform(intext)
        self.sklearn_lda_model = LDA(n_topics=topic_num, max_iter=50)
        self.vocab = self.sklearn_cvect.get_feature_names()
        lda_Z = self.sklearn_lda_model.fit_transform(corpus_tokens)

    @staticmethod
    def required_resources():
        return ['ELICIT_Corpus']
        
    def augment_word_lists(self, word_lists):
        counter = 0
        top_n = 100

        for string in word_lists:
            word_list = string.words
            lda_augmentation= []+word_list
            x = self.sklearn_lda_model.transform(self.sklearn_cvect.transform(word_list))[0]
            top_index = x.argsort()[::-1][0]
            topic_words = self.sklearn_lda_model.components_[top_index]
            topic_words = topic_words.argsort()[len(topic_words)-top_n:len(topic_words)][::-1]
            

            lda_augmentation += list(set([self.vocab[i] for i in topic_words]))
            new_word_list = DerivedWordList(string, [w for w in list(lda_augmentation)])
            self.augmented_data.append(new_word_list)
            counter +=1
        return self.augmented_data
    

class Web_Augmenter(Augmenter):
    def __init__(self, config):
        pass 


class WN_Augmenter(Augmenter):
    def __init__(self, config):
        super().__init__(config)
         
    def augment_word_lists(self, word_lists):   
        label_wn_lists = []
        counter = 0
        for string in word_lists:
            word_list = string.words
            wn_augmentation = []+word_list
            for word in word_list:
                wn_augmentation += augmentation_methods.get_WordNet_augmentation(word)
                
            new_word_list = DerivedWordList(string, [w for w in list(wn_augmentation)])
            self.augmented_data.append(new_word_list)
            counter += 1
            print(counter)
        return self.augmented_data


