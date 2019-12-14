import pandas as pd
import csv
from loader.loader import Loader
from common.wordlist import KeyedWordList


class MINT_Loader(Loader):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.input_file = cfg['input_file']

    def load(self):
        with open(self.input_file) as fp:
            lines = fp.readlines()
            for line in lines:
                parts = line.split(',',2)
                wordlist = KeyedWordList(parts[1].replace('_',' '), parts[0])
#                wordlist = WordList(line)
                self.word_lists.append(wordlist)
        return self.word_lists

class MINT_CSV_Loader(Loader):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.input_file = cfg['input_file']

    def load(self):
        with open(self.input_file) as fp:
            lines = csv.reader(fp,  delimiter=',', quotechar='"', skipinitialspace=True)
            for line in lines:
                wordlist = KeyedWordList(line[1].replace('_',' '), line[0])
#                wordlist = WordList(line)
                self.word_lists.append(wordlist)
        return self.word_lists



class GSN_Label_Loader(Loader):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.input_file = cfg['input_file']
        df = pd.read_csv(self.input_file)
        df = df.dropna(subset=['Descriptions']).dropna(subset=['GSNs'])
        for index, row in df.iterrows():
            self.lines.append(row['Descriptions'])

    def load(self):
        for line in self.lines:
            wordlist = WordList(line)
#             print ("Wordlist:" + wordlist.string)
#             for w in wordlist.words:
#                 print(str(w))
            self.word_lists.append(wordlist)
        return self.word_lists


class GSN_Ontology_Loader(Loader):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.input_file = cfg['input_file']
        with open(self.input_file, 'r') as f:
            self.lines = f.readlines()

    def load(self):
        self.unique_words_map = {}
        for line in self.lines:
            parts_line = line.split(",")
            temp = []
            for part_line in parts_line:
                wordlist = WordList(part_line.strip())
                self.unique_words_map[wordlist.string] = part_line.strip()
        self.word_lists = [KeyedWordList(item[1], item[0]) for item in self.unique_words_map.items()]
        #print (str(self.unique_words_map.items()))
        return self.word_lists


class GSN_Truth_Loader(Loader):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.input_file = cfg['input_file']
        df = pd.read_csv(self.input_file)
        df = df.dropna(subset=['Descriptions']).dropna(subset=['GSNs'])
        self.label_lines = []
        self.onto_lines = []
        for index, row in df.iterrows():
            self.label_lines.append(row['Descriptions'])
            self.onto_lines.append(row['GSNs'])

    def load(self):
        _map = {}
        for index, onto_line in enumerate(self.onto_lines):
            parts_line = onto_line.split(",")
            temp = []
            for part_line in parts_line:
                #print ("part_line: " + str(parts_line))
                wordlist = WordList(part_line.strip())
                key = wordlist.string
#                 for w in wordlist.words:
#                         print(str(w))
                temp.append((key,1))
            _map[self.label_lines[index].strip()] = temp
#             self.word_lists.append(temp)

        return _map