import pandas as pd
import requests
import string
import wikifier
import typing
from requests.auth import HTTPBasicAuth
from etk.etk import ETK
from etk.knowledge_graph import KGSchema
from etk.etk_module import ETKModule
from etk.wikidata.entity import WDProperty, WDItem, change_recorder, serialize_change_record
from etk.wikidata.value import Datatype, Item, TimeValue, Precision, QuantityValue, StringValue, URLValue, MonolingualText
from etk.wikidata.statement import WDReference
# from etk.wikidata import serialize_change_record
from etk.wikidata.truthy import TruthyUpdater
from dsbox.datapreprocessing.cleaner.data_profile import Profiler, Hyperparams as ProfilerHyperparams
from dsbox.datapreprocessing.cleaner.cleaning_featurizer import CleaningFeaturizer, CleaningFeaturizerHyperparameter
from SPARQLWrapper import SPARQLWrapper, JSON, POST, URLENCODED
from datamart_isi.utilities.utils import Utils as datamart_utils
from datamart_isi.materializers.general_materializer import GeneralMaterializer
from datamart_isi.materializers.wikitables_materializer import WikitablesMaterializer
from wikifier import config
from io import StringIO
from collections import defaultdict
# WIKIDATA_QUERY_SERVER = config.endpoint_main
# WIKIDATA_UPDATE_SERVER = config.endpoint_update_main
# WIKIDATA_QUERY_SERVER = config.endpoint_query_test  # this is testing wikidata
# WIKIDATA_UPDATE_SERVER = config.endpoint_upload_test  # this is testing wikidata
DATAMRT_SERVER = "http://dsbox02.isi.edu:9001/blazegraph/namespace/datamart4/sparql"

class Datamart_isi_upload:
    def __init__(self, query_server=None, update_server=None):
        self.punctuation_table = str.maketrans(dict.fromkeys(string.punctuation))
        if query_server and update_server:
            self.query_server = query_server
            self.update_server = update_server
        else:
            self.query_server = DATAMRT_SERVER
            self.update_server = DATAMRT_SERVER

        # initialize
        kg_schema = KGSchema()
        kg_schema.add_schema('@prefix : <http://isi.edu/> .', 'ttl')
        etk = ETK(kg_schema=kg_schema, modules=ETKModule)
        self.doc = etk.create_document({}, doc_id="http://isi.edu/default-ns/projects")

        # bind prefixes
        self.doc.kg.bind('wikibase', 'http://wikiba.se/ontology#')
        self.doc.kg.bind('wd', 'http://www.wikidata.org/entity/')
        self.doc.kg.bind('wdt', 'http://www.wikidata.org/prop/direct/')
        self.doc.kg.bind('wdtn', 'http://www.wikidata.org/prop/direct-normalized/')
        self.doc.kg.bind('wdno', 'http://www.wikidata.org/prop/novalue/')
        self.doc.kg.bind('wds', 'http://www.wikidata.org/entity/statement/')
        self.doc.kg.bind('wdv', 'http://www.wikidata.org/value/')
        self.doc.kg.bind('wdref', 'http://www.wikidata.org/reference/')
        self.doc.kg.bind('p', 'http://www.wikidata.org/prop/')
        self.doc.kg.bind('pr', 'http://www.wikidata.org/prop/reference/')
        self.doc.kg.bind('prv', 'http://www.wikidata.org/prop/reference/value/')
        self.doc.kg.bind('prn', 'http://www.wikidata.org/prop/reference/value-normalized/')
        self.doc.kg.bind('ps', 'http://www.wikidata.org/prop/statement/')
        self.doc.kg.bind('psv', 'http://www.wikidata.org/prop/statement/value/')
        self.doc.kg.bind('psn', 'http://www.wikidata.org/prop/statement/value-normalized/')
        self.doc.kg.bind('pq', 'http://www.wikidata.org/prop/qualifier/')
        self.doc.kg.bind('pqv', 'http://www.wikidata.org/prop/qualifier/value/')
        self.doc.kg.bind('pqn', 'http://www.wikidata.org/prop/qualifier/value-normalized/')
        self.doc.kg.bind('skos', 'http://www.w3.org/2004/02/skos/core#')
        self.doc.kg.bind('prov', 'http://www.w3.org/ns/prov#')
        self.doc.kg.bind('schema', 'http://schema.org/')

        # give definition of the nodes we definied
        p = WDProperty('C2001', Datatype.MonolingualText)
        p.add_label('keywords', lang='en')
        p.add_description('identifier of a dataset in the Datamart system', lang='en')
        p.add_statement('P31', Item('Q19847637'))
        p.add_statement('P1629', Item('Q1172284'))
        self.doc.kg.add_subject(p)

        p = WDProperty('C2004', Datatype.StringValue)
        p.add_label('datamart identifier', lang='en')
        p.add_description('keywords associated with an item to facilitate finding the item using text search', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        self.doc.kg.add_subject(p)

        p = WDProperty('C2005', Datatype.StringValue)
        p.add_label('variable measured', lang='en')
        p.add_description('the variables measured in a dataset', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        p.add_statement('P1628', URLValue('http://schema.org/variableMeasured'))
        self.doc.kg.add_subject(p)

        p = WDProperty('C2006', Datatype.StringValue)
        p.add_label('values', lang='en')
        p.add_description('the values of a variable represented as a text document', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        self.doc.kg.add_subject(p)

        p = WDProperty('C2007', Datatype.Item)
        p.add_label('data type', lang='en')
        p.add_description('the data type used to represent the values of a variable, integer (Q729138), Boolean (Q520777), '
                          'Real (Q4385701), String (Q184754), Categorical (Q2285707)', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        self.doc.kg.add_subject(p)

        p = WDProperty('C2008', Datatype.URLValue)
        p.add_label('semantic type', lang='en')
        p.add_description('a URL that identifies the semantic type of a variable in a dataset', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        self.doc.kg.add_subject(p)

        p = WDProperty('C2010', Datatype.StringValue)
        p.add_label('extra information', lang='en')
        p.add_description('some extra information that may needed for this dataset', lang='en')
        self.doc.kg.add_subject(p)
        # get the starting source id
        sparql_query = """
            prefix wdt: <http://www.wikidata.org/prop/direct/>
            prefix wd: <http://www.wikidata.org/entity/>
            prefix wikibase: <http://wikiba.se/ontology#>
            PREFIX p: <http://www.wikidata.org/prop/>
            PREFIX pqv: <http://www.wikidata.org/prop/qualifier/value/>
            PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
            PREFIX ps: <http://www.wikidata.org/prop/statement/>
            prefix bd: <http://www.bigdata.com/rdf#>
            prefix bds: <http://www.bigdata.com/rdf/search#>

            select ?x where {
              wd:Z00000 wdt:P1114 ?x .
            }
            """
        try:
            sparql = SPARQLWrapper(self.query_server)
            sparql.setQuery(sparql_query)
            sparql.setReturnFormat(JSON)
            sparql.setMethod(POST)
            sparql.setRequestMethod(URLENCODED)
            results = sparql.query().convert()['results']['bindings']
        except:
            print("Getting query of wiki data failed!")
            raise ValueError("Unable to initialize the datamart query service")
        if not results:
            print("[WARNING] No starting source id found! Will initialize the starting source with D1000001")
            self.resource_id = 1000001
        else:
            if len(results) != 1:
                print(str(results))
                raise ValueError("Something wrong with the dataset counter!")
            self.resource_id = int(results[0]['x']['value'])

    def load_and_preprocess(self, input_dir, file_type="csv"):
        from_online_file = False
        if file_type=="csv":
            try:
                loaded_data = [pd.read_csv(input_dir,dtype=str)]
            except:
                raise ValueError("Reading csv from" + input_dir + "failed.")

            # TODO: how to upload to the online server afterwards?
        elif len(file_type) > 7 and file_type[:7]=="online_":
            from_online_file = True
            general_materializer = GeneralMaterializer()
            file_type = file_type[7:]
                # example: "csv"
            file_metadata = {
                "materialization": {
                    "arguments": {
                        "url": input_dir,
                        # one example here: "url": "http://insight.dev.schoolwires.com/HelpAssets/C2Assets/C2Files/C2ImportFamRelSample.csv",
                        "file_type": file_type
                    }
                }
            }
            try:
                result = general_materializer.get(metadata=file_metadata).to_csv(index=False)
            except:
                raise ValueError("Loading online data from " + input_dir + "failed!")
                # remove last \n so that we will not get an extra useless row
            if result[-1] == "\n":
                result = result[:-1]
            loaded_data = StringIO(result)
            loaded_data = [pd.read_csv(loaded_data,dtype="str")]

        elif file_type=="wikitable":
            from_online_file = True
            materializer = WikitablesMaterializer()
            loaded_data, xpaths = materializer.get(input_dir)
        else:
            raise ValueError("Unsupported file type")

        # loaded_data = loaded_data.fillna("")

        # run dsbox's profiler and cleaner
        hyper1 = ProfilerHyperparams.defaults()
        hyper2 = CleaningFeaturizerHyperparameter.defaults()
        self.columns_are_string = defaultdict(list)
        all_wikifier_res = []
        all_metadata = []
        for df_count, each in enumerate(loaded_data):
            clean_f = CleaningFeaturizer(hyperparams=hyper2)
            profiler = Profiler(hyperparams=hyper1)
            profiled_df = profiler.produce(inputs=each).value            
            clean_f.set_training_data(inputs=profiled_df)
            clean_f.fit()
            cleaned_df = pd.DataFrame(clean_f.produce(inputs=profiled_df).value)
            # wikifier_res = wikifier.produce(loaded_data, target_columns=self.columns_are_string)

            # TODO: It seems fill na with "" will change the column type!
            # cleaned_df = cleaned_df.fillna("")
            wikifier_res = wikifier.produce(cleaned_df)
            # TODO: need update profiler here to generate better semantic type
            metadata = datamart_utils.generate_metadata_from_dataframe(data=wikifier_res)
            
            for i, each_column_meta in enumerate(metadata['variables']):
                if 'http://schema.org/Text' in each_column_meta['semantic_type']:
                    self.columns_are_string[df_count].append(i)
                
            if from_online_file:
                metadata['url'] = input_dir
                metadata['title'] = input_dir.split("/")[-1]
                metadata['file_type'] = file_type
            if file_type=="wikitable":
                metadata['xpath'] = xpaths[df_count]

            all_wikifier_res.append(wikifier_res)
            all_metadata.append(metadata)

        return all_wikifier_res, all_metadata


    def model_data(self, input_dfs:typing.List[pd.DataFrame], metadata:typing.List[dict], number:int):
        if metadata is None or metadata[number] is None:
            metadata = {}
        extra_information = {}
        title = metadata[number].get("title") or ""
        keywords = metadata[number].get("keywords") or ""
        file_type = metadata[number].get("file_type") or ""
        # TODO: if no url given?
        url = metadata[number].get("url") or "https://"
        if type(keywords) is list:
            keywords = " ".join(keywords)
        node_id = 'D' + str(self.resource_id)
        q = WDItem(node_id)
        if 'xpath' in metadata[number]:
            extra_information['xpath'] = metadata[number]['xpath']

        data_metadata = {}
        data_metadata['shape_0'] = input_dfs[number].shape[0]
        data_metadata['shape_1'] = input_dfs[number].shape[1]
        for i, each in enumerate(metadata[number]['variables']):
            each_column_meta = {}
            each_column_meta['semantic_type'] = each['semantic_type']
            each_column_meta['name'] = input_dfs[number].columns[i]
            extra_information['column_meta_' + str(i)] = each_column_meta
        extra_information['data_metadata'] = data_metadata

        self.resource_id += 1
        q.add_label(node_id, lang='en')
        q.add_statement('P31', Item('Q1172284'))  # indicate it is subclass of a dataset
        q.add_statement('P2699', URLValue(url))  # url
        q.add_statement('P2701', StringValue(file_type)) # file type
        q.add_statement('P1476', MonolingualText(title, lang='en'))  # title
        q.add_statement('C2001', StringValue(node_id))  # datamart identifier
        q.add_statement('C2004', StringValue(keywords))  # keywords
        q.add_statement('C2010', StringValue(str(extra_information)))
        # each columns
        for i in self.columns_are_string[number]:
            try: 
                semantic_type = metadata[number]['variables'][i]['semantic_type']
            except IndexError:
                semantic_type = 'http://schema.org/Text'
            res = self.process_one_column(column_data=input_dfs[number].iloc[:,i], item=q, column_number=i, semantic_type=semantic_type)
            if not res:
                print("Error when adding column " + str(i))
        self.doc.kg.add_subject(q)

    def process_one_column(self, column_data: pd.Series, item: WDItem, column_number: int, semantic_type: typing.List[str]) -> bool:
        """
        :param column_data: a pandas series data
        :param item: the target q node aimed to add on
        :param column_number: the column number
        :param semantic_type: a list indicate the semantic tpye of this column
        :return: a bool indicate succeeded or not
        """
        translator = str.maketrans(string.punctuation, ' '*len(string.punctuation))
        try:
            all_data = set(column_data.tolist())
            all_value_str_set = set()
            for each in all_data:
                # set to lower characters, remove punctuation and split by the space
                words_processed = str(each).lower().translate(translator).split()
                for word in words_processed:
                    all_value_str_set.add(word)
            all_value_str = " ".join(all_value_str_set)

            statement = item.add_statement('C2005', StringValue(column_data.name))  # variable measured
            statement.add_qualifier('C2006', StringValue(all_value_str))  # values
            if 'http://schema.org/Float' in semantic_type:
                semantic_type_url = 'http://schema.org/Float'
                data_type = "float"
            elif 'http://schema.org/Integer' in semantic_type:
                data_type = "int"
                semantic_type_url = 'http://schema.org/Integer'
            elif 'http://schema.org/Text' in semantic_type:
                data_type = "string"
                semantic_type_url = 'http://schema.org/Text'

            statement.add_qualifier('C2007', Item(data_type))  # data structure type
            statement.add_qualifier('C2008', URLValue(semantic_type_url))  # semantic type identifier
            statement.add_qualifier('P1545', QuantityValue(column_number))  # column index
            return True
        except:
            print("[ERROR] processing column No." + str(column_number) + " failed!")
            return False

    def output_to_ttl(self, file_path: str, file_format="ttl"):                        
        """
            output the file only but not upload
        """
        f = open(file_path + ".ttl", 'w')
        f.write(self.doc.kg.serialize(file_format))
        f.close()
        with open(file_path + 'changes.tsv', 'w') as fp:
            serialize_change_record(fp)
        print('Serialization completed!')

    def upload(self):
        """
            upload the dataset
        """
        # This special Q node is used to store the next count to store the new Q node
        sparql_query = """
            prefix wdt: <http://www.wikidata.org/prop/direct/>
            prefix wdtn: <http://www.wikidata.org/prop/direct-normalized/>
            prefix wdno: <http://www.wikidata.org/prop/novalue/>
            prefix wds: <http://www.wikidata.org/entity/statement/>
            prefix wdv: <http://www.wikidata.org/value/>
            prefix wdref: <http://www.wikidata.org/reference/>
            prefix wd: <http://www.wikidata.org/entity/>
            prefix wikibase: <http://wikiba.se/ontology#>
            prefix p: <http://www.wikidata.org/prop/>
            prefix pqv: <http://www.wikidata.org/prop/qualifier/value/>
            prefix pq: <http://www.wikidata.org/prop/qualifier/>
            prefix ps: <http://www.wikidata.org/prop/statement/>
            prefix psn: <http://www.wikidata.org/prop/statement/value-normalized/>
            prefix prv: <http://www.wikidata.org/prop/reference/value/>
            prefix psv: <http://www.wikidata.org/prop/statement/value/>
            prefix prn: <http://www.wikidata.org/prop/reference/value-normalized/>
            prefix pr: <http://www.wikidata.org/prop/reference/>
            prefix pqn: <http://www.wikidata.org/prop/qualifier/value-normalized/>
            prefix skos: <http://www.w3.org/2004/02/skos/core#>
            prefix prov: <http://www.w3.org/ns/prov#>
            prefix schema: <http://schema.org/'>
            prefix bd: <http://www.bigdata.com/rdf#>
            prefix bds: <http://www.bigdata.com/rdf/search#>

            delete {
                  wd:Z00000 wdt:P1114 ?x .
                }
                where {
                    wd:Z00000 wdt:P1114 ?x .
                }
            """
        try:
            sparql = SPARQLWrapper(self.update_server)
            sparql.setQuery(sparql_query)
            sparql.setReturnFormat(JSON)
            sparql.setMethod(POST)
            sparql.setRequestMethod(URLENCODED)
            sparql.setCredentials(config.user, config.password)
            results = sparql.query()  #.convert()['results']['bindings']
        except:
            print("Updating the count for datamart failed!")
            raise ValueError("Unable to connect to datamart query service")
        # add datamart count to ttl
        q = WDItem('Z00000')
        q.add_label('Datamart datasets count', lang='en')
        q.add_statement('P1114', QuantityValue(self.resource_id))  # title
        self.doc.kg.add_subject(q)
        # upload
        extracted_data = self.doc.kg.serialize("ttl")
        headers = {'Content-Type': 'application/x-turtle',}
        response = requests.post(self.update_server, data=extracted_data.encode('utf-8'), headers=headers,
                                 auth=HTTPBasicAuth(config.user, config.password))
        print('Upload file finished with status code: {}!'.format(response.status_code))

        if response.status_code!=200:
            raise ValueError("Uploading file failed")
        else:
            # upload truthy
            temp_output = StringIO()
            serialize_change_record(temp_output)
            temp_output.seek(0)
            tu = TruthyUpdater(self.update_server, False, config.user, config.password)
            np_list = []
            for l in temp_output.readlines():
                if not l: continue
                node, prop = l.strip().split('\t')
                np_list.append((node, prop))
            tu.build_truthy(np_list)
            print('Update truthy finished!')
