
import string
import nltk
from nltk.corpus import stopwords 
from nltk.stem.wordnet import WordNetLemmatizer
import re
nltk.download('stopwords')
stop = set(stopwords.words("english"))
def clean_text(string):
    cleaned = re.sub(r'[^\w]', ' ', string.lower())
    cleaned = cleaned.replace('\n','').replace("'",'').replace(',','').replace('"','').replace('+','').replace('(','').replace(')','').replace('of','').replace('_',' ').replace('.',' ').replace('~',' ').replace('-',' ')
    return cleaned

def clean_word_list(string):
    # Create a clean list of words from a string with stopwords removed
    cleaned_words = string.split()
    returned = []
    for word in cleaned_words:
        if len(word) <= 1 or word in stop:
            continue
        digit_flag = False
        for char in word:
            if char.isdigit():
                digit_flag = True
                break
        if digit_flag == True:
            continue
        else:
            returned.append(word)
    return list(set(returned))

def lda_clean(doc):
    #nltk.download('stopwords')
    #nltk.download('wordnet')
    stop = set(stopwords.words('english'))
    stop.add('said')
    stop.add('the')
    stop.add('would')
    stop.add('new')
    stop.add('year')
    stop.add('world')
    stop.add('it')
    stop.add('one')
    stop.add('say')
    stop.add('also')
    stop.add('cnn')
    stop.add('city')
    stop.add('time')
    stop.add('i')
    stop.add('group')
    stop.add('u')
    stop.add('like')
    stop.add('people')
    stop.add('study')
    stop.add('told')
    stop.add('officer')
    stop.add('report')
    stop.add('two')
    stop.add('according')
    exclude = set(string.punctuation) 
    lemma = WordNetLemmatizer()
    stop_free = " ".join([i for i in doc.lower().split() if i not in stop])
    punc_free = ''.join(ch for ch in stop_free if ch not in exclude)
    normalized = " ".join(lemma.lemmatize(word) for word in punc_free.split())
    return normalized


