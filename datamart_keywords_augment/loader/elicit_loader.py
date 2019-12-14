from loader.loader import Loader
from common.wordlist import WordList, KeyedWordList

class ElicitLabelLoader(Loader):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.input_file = cfg['input_file']
        import json
        API_NER = []
        with open(self.input_file) as f:
            for line in f:
                API_NER.append(json.loads(line))
        label2ontology = {}
        for json in API_NER:
            if 'measure' in json:
                if 'label' in json['measure']:
                    if json['measure']['label'] not in label2ontology and '_reported_value' in json['measure']:
                        label2ontology[json['measure']['label']] = []
                        for ontology in json['measure']['_reported_value']:
                            label2ontology[json['measure']['label']].append(ontology.split('#',1)[1])

        for k, v in label2ontology.items():
            self.lines.append(k)

    def load(self):
        for line in self.lines:
            wordlist = WordList(line)
#             print ("Wordlist:" + wordlist.string)
#             for w in wordlist.words:
#                 print(str(w))
            self.word_lists.append(wordlist)
        return self.word_lists


class ElicitOntologyLoader(Loader):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.input_file = cfg['input_file']
        import json
        API_NER = []
        with open(self.input_file) as f:
            for line in f:
                API_NER.append(json.loads(line))
        label2ontology = {}
        for json in API_NER:
            if 'measure' in json:
                if 'label' in json['measure']:
                    if json['measure']['label'] not in label2ontology and '_reported_value' in json['measure']:
                        label2ontology[json['measure']['label']] = []
                        for ontology in json['measure']['_reported_value']:
                            label2ontology[json['measure']['label']].append(ontology.split('#',1)[1])
        for k, v in label2ontology.items():
            self.lines.append(', '.join(word for word in v))

    def load(self):
        self.unique_words_map = {}
        for line in self.lines:
            parts_line = line.split(",")
            temp = []
            for part_line in parts_line:
                wordlist = WordList(part_line.strip())
                self.unique_words_map[wordlist.string] = part_line.strip()
        self.word_lists = [KeyedWordList(item[1], item[0]) for item in self.unique_words_map.items()]
        return self.word_lists


class ElicitTruthLoader(Loader):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.input_file = cfg['input_file']
        import json
        API_NER = []
        with open(self.input_file) as f:
            for line in f:
                API_NER.append(json.loads(line))
        label2ontology = {}
        for json in API_NER:
            if 'measure' in json:
                if 'label' in json['measure']:
                    if json['measure']['label'] not in label2ontology and '_reported_value' in json['measure']:
                        label2ontology[json['measure']['label']] = []
                        for ontology in json['measure']['_reported_value']:
                            label2ontology[json['measure']['label']].append(ontology.split('#',1)[1])
        self.label_lines = []
        self.onto_lines = []
        for k, v in label2ontology.items():
            self.label_lines.append(k)
            self.onto_lines.append(', '.join(word for word in v))

    def load(self):
        _map = {}
        for index, onto_line in enumerate(self.onto_lines):
            parts_line = onto_line.split(",")
            temp = []
            for part_line in parts_line:
                wordlist = WordList(part_line.strip())
                key = wordlist.string
#                 for w in wordlist.words:
#                         print(str(w))
                temp.append((key,1))
            _map[self.label_lines[index].strip()] = temp
#             self.word_lists.append(temp)
        return _map