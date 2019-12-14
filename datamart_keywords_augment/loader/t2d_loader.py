import pandas as pd

from src.loader import Loader


class T2D_Label_Loader(Loader):

    def __init__(self, cfg):
        super().__init__(cfg)
        self.instance_folder = cfg['instance_folder']
        self.input_file = cfg['input_file']
        print ("Label Loader File is:" + self.input_file)
        df = pd.read_csv(self.input_file, sep=',', engine='python')
        self.lines = []
        for index, row in df.iterrows():
            self.lines.append(row['Table_ID'][:len(row['Table_ID'])-7])

    def get_table_word_list(self, file_address, table_address):
        df = pd.read_csv(file_address, error_bad_lines=False, engine='python')
        #print(df.columns)
        word_list = []
        col_names = list(df.columns.values)
        word_list += col_names
        for index, row in df.iterrows():
            for col_name in col_names:
                if row[col_name] is not '' and type(row[col_name]) is str:
                    if type(row[col_name]) is float and math.isnan(row[col_name]):
                        continue
                    word_list.append(row[col_name])
        wordlist = WordList(' '.join(word for word in word_list))
        wordlist.orig_string = table_address
        return wordlist

    def load(self):
        import collections
        self.word_lists = []
        for table_address in self.lines:
            address = self.instance_folder + '/' + table_address+'.csv'
            lst = self.get_table_word_list(address, table_address.strip())
            #print ("lst: " + str(lst))
            #self.word_lists.append(lst)
            counts = collections.Counter(lst.words)
            lst.words = [word[0] for word in counts.most_common()]
            self.word_lists.append(lst)
        return self.word_lists


class T2D_Ontology_Loader(Loader):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.input_file = cfg['input_file']
        print ("Ontology File is:" + self.input_file)
        df = pd.read_csv(self.input_file, sep=',', engine='python')
        self.lines = []
        for index, row in df.iterrows():
            self.lines.append(row['Class'])

    def load(self):
        self.unique_words_map = {}
        for line in self.lines:
            wordlist = CamelCaseWordList(line.strip())
            self.unique_words_map[wordlist.string] = line.strip()
        self.word_lists = [KeyedWordList(item[1], item[0]) for item in self.unique_words_map.items()]
        return self.word_lists


class T2D_Truth_Loader(Loader):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.input_file = cfg['input_file']
        df = pd.read_csv(self.input_file, sep=',', engine='python')
        self.classes = []
        self.table_addresses = []
        for index, row in df.iterrows():
            self.classes.append(row['Class'])
            self.table_addresses.append(row['Table_ID'][:len(row['Table_ID'])-7])

    def load(self):
        _map = {}
        for index, _class in enumerate(self.classes):
            parts_line = _class.split(",")
            temp = []
            for part_line in parts_line:
                wordlist = WordList(part_line.strip())
                key = wordlist.string
                temp.append((key,1))
            _map[self.table_addresses[index].strip()] = temp
        return _map