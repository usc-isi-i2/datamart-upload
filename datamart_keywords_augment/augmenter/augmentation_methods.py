
import nltk
from nltk.corpus import wordnet as wn
import string
from nltk.corpus import stopwords

def get_WordNet_augmentation(word):
    # Given a word, returns a list of hypernyms, synonyms, meronyms, and troponyms (not found in wordnet)
    stops = set(stopwords.words("english"))
    syns = wn.synsets(word)
    returned_list = []
    for syn in syns:
        # Add synonyms
        returned_list += syn.lemma_names()
        hypers = syn.hypernyms()
        mero_parts = syn.part_meronyms()
        mero_subs = syn.substance_meronyms()
        for hyper in hypers:
            # Add hypernyms
            returned_list += hyper.lemma_names()
        for mero_part in mero_parts:
            # Add mero_parts
            returned_list += mero_part.lemma_names()
        for mero_sub in mero_subs:
            # Add mero_sub
            returned_list += mero_sub.lemma_names()
    final_list = []
    for word in returned_list:
        if '_' in word:
            final_list += [w for w in word.lower().split('_') if w not in stops]
        else:
            if word.lower() not in stops:
                final_list.append(word.lower())
    return list(set(final_list))


def get_w2v_augmented_list(word, GNews_SLIM_model, topn=50):
    return [x[0].lower() for x in GNews_SLIM_model.wv.most_similar(positive=[word], topn=topn)]

def get_LDA_gensim_doc_augmentation(doc_list, ldamodel, dictionary):
    # Given a doc as a list of word, get the top words from the topic with the highest probability
    aug_list = []
    bow = ldamodel.id2word.doc2bow(doc_list)
    topic_id_list = ldamodel.get_document_topics(bow)
    #topic_id_list = ldamodel.get_document_topics(bow)
#     print ("topic_id_list " + topic_id_list)
    for topic_id in topic_id_list:
        word_id_list = ldamodel.get_topic_terms(topic_id[0])
        for tup in word_id_list:
            aug_list.append(dictionary[tup[0]])
    return list(set(aug_list))
        
        
def get_LDA_gensim_word_augmentation(word, ldamodel, dictionary):
    # Given a word, get the top words from the topic with the highest probability
    aug_list = []
    topic_id = max(ldamodel.get_term_topics(word), key=lambda x: x[1])[0]
    word_id_list = ldamodel.get_topic_terms(topic_id)
    for tup in word_id_list:
        aug_list.append(dictionary[tup[0]])
    return list(set(aug_list))
