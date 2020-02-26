from common.wordlist import WordList


class Loader(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.word_lists = []
        self.lines = []
        self.global_names = []
        self.global_word_lists = []

    def load(self):
        pass


class CA_Samples_Loader(Loader):
    def __init__(self, input_file):
        super().__init__(input_file)
        with open(input_file) as f:
            index = 0
            for line in f:
                if index == 0:
                    index +=1
                    continue
                index+=1
                parts = line.split(';')
                sentence = parts[15] + " " + parts[16]
#                 print ("sentence is: " + sentence)
                self.lines.append(sentence)

    def load(self):
        for line in self.lines:
            wordlist = WordList(line)
            self.word_lists.append(wordlist)
        return self.word_lists


class KeywordLoader(Loader):
    def __init__(self, cfg):
        pass

    def load(self, keywords):
        return [ WordList(keyword) for keyword in keywords ]