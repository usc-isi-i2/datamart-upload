from common import preprocessing


# Read dataset from an address

# # Each line in the dataset or ontology is a Wordlist object
class WordList(object):
    def __init__(self, string):
        self.orig_string = string.strip()
        self.string = preprocessing.clean_text(string)
        self.words = preprocessing.clean_word_list(self.string)
        self.string = ' '.join(self.words)

    def get_key(self):
        return None

    def get_original_string(self):
        return self.orig_string

class KeyedWordList(WordList):
    def __init__(self, string, key):
        super().__init__(string)
        self.key = key

    def get_key(self):
        return self.key

class DerivedWordList(WordList):
    def __init__(self, wl, words):
        self.parent = wl
        self.words = list(words)
        self.string = ' '.join(self.words)

    def get_key(self):
        parent = self.parent
        try:
            while parent.parent:
                parent = parent.parent
        except AttributeError:
            if isinstance(parent, KeyedWordList):
                return parent.get_key()
            return None

    def get_original_string(self):
        parent = self.parent
        try:
            while parent.parent:
                parent = parent.parent
        except AttributeError:
            return parent.get_original_string()

class CamelCaseWordList(WordList):
    def __init__(self, string):
        import re
        self.words = [word.lower() for word in re.findall('[A-Z][^A-Z]*', string)]
        self.orig_string = string
        self.string = ' '.join(self.words)

    def get_original_string(self):
        return self.orig_string


class WeightedWordList(DerivedWordList):
    def __init__(self, wl, wordMap):
        super().__init__(wl,wordMap.keys())
        self.word_map = wordMap

def unweighted_to_weighted(data):
    rv = list()
    for wl in data:
        if isinstance(wl, WeightedWordList):
            return data
        wmap = dict()
        for w in wl.words:
            wmap[w]=1
        rv.append(WeightedWordList(wl, wmap))
    return rv


def print_op(self,data):
    v = []
    for wl in data:
        x = dict()
        x['variable'] = wl.get_original_string()
        x['words'] = wl.words
        v.append(x)
    print(v)
