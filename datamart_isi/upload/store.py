import pandas as pd
import requests
import string
import wikifier
import typing
import uuid
import time
import datetime
import logging
import json
import os
import hashlib

from requests.auth import HTTPBasicAuth
from pandas.util import hash_pandas_object
from etk.etk import ETK
from etk.knowledge_graph import KGSchema
from etk.etk_module import ETKModule
from etk.wikidata.entity import WDProperty, WDItem, change_recorder, serialize_change_record
from etk.wikidata.value import Datatype, Item, TimeValue, Precision, QuantityValue, StringValue, URLValue, MonolingualText, Literal, LiteralType
from etk.wikidata.statement import WDReference
# from etk.wikidata import serialize_change_record
from etk.wikidata.truthy import TruthyUpdater
# from dsbox.datapreprocessing.cleaner.data_profile import Profiler, Hyperparams as ProfilerHyperparams
# from dsbox.datapreprocessing.cleaner.cleaning_featurizer import CleaningFeaturizer, CleaningFeaturizerHyperparameter
from SPARQLWrapper import SPARQLWrapper, JSON, POST, URLENCODED
from datamart_isi.utilities.utils import Utils as datamart_utils
from datamart_isi.materializers.general_materializer import GeneralMaterializer
from datamart_isi.materializers.wikitables_materializer import WikitablesMaterializer
from io import StringIO
from collections import defaultdict
from datamart_isi.utilities.timeout import Timeout, timeout_call
from datamart_isi.utilities import connection
from datamart_isi import config as config_datamart
from datamart_isi.cache.general_search_cache import GeneralSearchCache
from datamart_isi.utilities.d3m_wikifier import save_wikifier_choice

DATAMRT_SERVER = connection.get_general_search_server_url()


def remove_punctuation(input_str) -> typing.List[str]:
    translator = str.maketrans(string.punctuation, ' '*len(string.punctuation))
    words_processed = str(input_str).lower().translate(translator).split()
    return words_processed

class Datamart_isi_upload:
    """
    Main class for uploading part
    """
    def __init__(self, query_server=None, update_server=None):
        self._logger = logging.getLogger(__name__)
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

        p = WDProperty('C2011', Datatype.TimeValue)
        p.add_label('start date', lang='en')
        p.add_description('The earlist time exist in this dataset, only valid when there exists time format data in this dataset', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        self.doc.kg.add_subject(p)

        p = WDProperty('C2012', Datatype.TimeValue)
        p.add_label('end date', lang='en')
        p.add_description('The latest time exist in this dataset, only valid when there exists time format data in this dataset', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        self.doc.kg.add_subject(p)

        p = WDProperty('C2013', Datatype.QuantityValue)
        p.add_label('time granularity', lang='en')
        p.add_description('time granularity in a dataset', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        self.doc.kg.add_subject(p)

        p = WDProperty('C2014', Datatype.StringValue)
        p.add_label('uploader information', lang='en')
        p.add_description('information about who uploaded and when uploaded', lang='en')
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
            self._logger.error("Getting query of wiki data failed!")
            raise ValueError("Unable to initialize the datamart query service on address " + query_server)
        # if not results:
        #     self._logger.warning("No starting source id found! Will initialize the starting source with D1000001")
        #     self.resource_id = 1000001
        # else:
        #     if len(results) != 1:
        #         self._logger.warning(str(results))
        #         self._logger.warning("Something wrong with the dataset counter! Totally " + str(len(results)) + " counter found instead of 1!")
        #     self.resource_id = int(results[0]['x']['value'])

    def load_and_preprocess(self, input_dir, file_type="csv", job=None, wikifier_choice="auto"):
        start = time.time()
        self._logger.debug("Start loading from " + input_dir)
        if job is not None:
            job.meta['step'] = "materializing the dataset..."
            job.save_meta()
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
            except Exception as e:
                _logger.debug(e, exc_info=True)
                raise ValueError("Loading online data from " + input_dir + " failed!")
                # remove last \n so that we will not get an extra useless row
            if result[-1] == "\n":
                result = result[:-1]
            loaded_data = StringIO(result)
            loaded_data = [pd.read_csv(loaded_data,dtype=str)]

        elif file_type=="wikitable":
            from_online_file = True
            materializer = WikitablesMaterializer()
            loaded_data, xpaths = materializer.get(input_dir)
        else:
            raise ValueError("Unsupported file type")
        end1 = time.time()
        self._logger.info("Loading finished. Totally take " + str(end1 - start) + " seconds.")
        if job is not None:
            job.meta['step'] = "materialization finished, start running wikifier..."
            job.meta['loading dataset used'] = str(datetime.timedelta(seconds=end1 - start))
            job.save_meta()

        all_wikifier_res = []
        all_metadata = []
        for df_count, each_df in enumerate(loaded_data):
            if wikifier_choice == "false":
                do_wikifier = False
            elif wikifier_choice == "true":
                do_wikifier = True
            else:
                do_wikifier = None

            do_wikifier = save_wikifier_choice(input_dataframe=each_df, choice=do_wikifier)
            
            if do_wikifier:
                self._logger.info("Will run wikifier!")
                wikifier_res = wikifier.produce(each_df)

            else:
                self._logger.info("Not run wikifier!")
                wikifier_res = each_df
                # we also need to let the cache system know not to do wikifier
                produce_config = {"target_columns": None, "target_p_nodes": None,
                                  "input_type": "pandas", "wikifier_choice": None, 
                                  "threshold": 0.7
                                  }
                
                CACHE_MANAGER = GeneralSearchCache()
                
                cache_key = CACHE_MANAGER.get_hash_key(each_df, json.dumps(produce_config))

                # add extra information after we calculate the correct hash tag
                produce_config["use_wikifier"] = False
                response = CACHE_MANAGER.add_to_memcache(supplied_dataframe=each_df,
                                                     search_result_serialized=json.dumps(produce_config),
                                                     augment_results=each_df,
                                                     hash_key=cache_key
                                                     )
                if not response:
                    self._logger.warning("Push wikifier results to results failed!")
                else:
                    self._logger.info("Push wikifier results to memcache success!")

            end2 = time.time()
            self._logger.info("Wikifier finished. Totally take " + str(end2 - end1) + " seconds.")
            if job is not None:
                job.meta['step'] = "wikifier running finished, start generating metadata..."
                job.meta['wikifier used'] = str(datetime.timedelta(seconds=end2 - end1))
                job.save_meta()

            # process datetime column to standard datetime
            for col_name in wikifier_res.columns.values.tolist():
                if 'date' in col_name.lower() or 'time' in col_name.lower():
                    try:
                        temp = pd.to_datetime(wikifier_res[col_name])
                        has_time_format_or_not = (pd.isnull(temp)==True).value_counts()
                        if False in has_time_format_or_not.keys() and has_time_format_or_not[False] >= wikifier_res.shape[0] * 0.7:
                            wikifier_res[col_name] = temp
                    except:
                        pass

            # TODO: need update profiler here to generate better semantic type
            metadata = datamart_utils.generate_metadata_from_dataframe(data=wikifier_res)
            self._logger.info("The uploaded data's shape is " + str(wikifier_res.shape))
            for i, each_column_meta in enumerate(metadata['variables']):
                self._logger.debug("Metadata for column No.{} is:".format(str(i)))
                self._logger.debug(str(each_column_meta))
                # if 'http://schema.org/Text' in each_column_meta['semantic_type']:
                    # self.columns_are_string[df_count].append(i)
                
            if from_online_file:
                metadata['url'] = input_dir
                title_cleaned = input_dir.split("/")[-1]
                words_processed = remove_punctuation(title_cleaned)
                metadata['title'] = " ".join(words_processed)
                metadata['file_type'] = file_type
            if file_type=="wikitable":
                metadata['xpath'] = xpaths[df_count]

            all_wikifier_res.append(wikifier_res)
            all_metadata.append(metadata)

        end2 = time.time()
        self._logger.info("Preprocess finished. Totally take " + str(end2 - end1) + " seconds.")
        if job is not None:
            job.meta['step'] = "metadata generating finished..."
            job.meta['metadata generating used'] = str(datetime.timedelta(seconds=end2 - end1))
            job.save_meta()
        return all_wikifier_res, all_metadata


    def model_data(self, input_dfs:typing.List[pd.DataFrame], metadata:typing.List[dict], number:int, uploader_information, **kwargs):
        self._logger.debug("Start modeling data into blazegraph format...")
        start = time.time()
        job = kwargs.get("job", None)
        need_process_columns = kwargs.get("need_process_columns", None)
        if need_process_columns is None:
            need_process_columns = list(range(input_dfs[number].shape[1]))
        else:
            for each_column_number in need_process_columns:
                if each_column_number >= input_dfs[number].shape[1]:
                    raise ValueError("The given column number {} exceed the dataset's column length as {}.".format(each_column_number, str(input_dfs[number].shape[1])))

        # updated v2019.12.5: now use the md5 value of dataframe hash as the dataset id
        pandas_id = str(hash_pandas_object(input_dfs[number]).sum())
        hash_generator = hashlib.md5()
        hash_generator.update(pandas_id.encode('utf-8'))
        hash_url_key = hash_generator.hexdigest()
        self.modeled_data_id = hash_url_key

        if metadata is None or metadata[number] is None:
            metadata = {}
        extra_information = {}
        title = metadata[number].get("title") or ""
        keywords = metadata[number].get("keywords") or ""
        file_type = metadata[number].get("file_type") or ""
        # TODO: if no url given?
        url = metadata[number].get("url") or "http://"

        # update v2019.12.6, now adapt special requirement from keywords
        if type(keywords) is str:
            keywords_list = keywords.split(",")
        else:
            keywords_list = keywords
        words_processed = []
        for each in keywords_list:
            if each.startswith("*&#") and each.endswith("*&#"):
                self._logger.info("Special requirement from keyword area detected as {}".format(each))
                special_requirement = json.loads(each[3: -3])
                extra_information['special_requirement'] = special_requirement
            else:
                words_processed.extend(remove_punctuation(each))
        keywords = " ".join(set(words_processed))

        node_id = 'D' + str(self.modeled_data_id)
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

        # updated v2019.10.14, add first 10 rows of each dataset in extra information for checking
        extra_information['first_10_rows'] = input_dfs[number].loc[:10].to_csv()
        # updated v2019.10.14, trying to save a local backup of the downloaded dataframe to increase the speed
        hash_generator = hashlib.md5()
        hash_generator.update(url.encode('utf-8'))
        hash_url_key = hash_generator.hexdigest()
        dataset_cache_loc = os.path.join(config_datamart.cache_file_storage_base_loc, "datasets_cache")
        cache_file_loc = os.path.join(dataset_cache_loc, hash_url_key + ".h5")
        if not os.path.exists(dataset_cache_loc):
            os.mkdir(dataset_cache_loc)

        input_dfs[number].to_hdf(cache_file_loc, key='df', mode='w', format='fixed')
        extra_information['local_storage'] = cache_file_loc

        # for each_key in ["", ]:
        #     if each_key not in uploader_information:
        #         uploader_information[each_key] = "None"

        # self.resource_id += 1
        q.add_label(node_id, lang='en')
        q.add_statement('P31', Item('Q1172284'))  # indicate it is subclass of a dataset
        q.add_statement('P2699', URLValue(url))  # url
        q.add_statement('P2701', StringValue(file_type)) # file type
        q.add_statement('P1476', MonolingualText(title, lang='en'))  # title
        q.add_statement('C2001', StringValue(node_id))  # datamart identifier
        q.add_statement('C2004', StringValue(keywords))  # keywords
        q.add_statement('C2010', StringValue(json.dumps(extra_information)))
        q.add_statement('C2014', StringValue(json.dumps(uploader_information)))

        end1 = time.time()
        if job is not None:
            job.meta['step'] = "Modeling abstarct data finished."
            job.meta['modeling abstarct'] = str(datetime.timedelta(seconds=end1 - start))
            job.save_meta()

        self._logger.info("Modeling abstarct data finished. Totally take " + str(end1 - start) + " seconds.")
        # each columns
        for i in need_process_columns:
            if job is not None:
                job.meta['step'] = "Modeling ({}/{}) column ...".format(str(i), str(input_dfs[number].shape[1]))
                job.save_meta()
            try: 
                semantic_type = metadata[number]['variables'][i]['semantic_type']
            except IndexError:
                semantic_type = 'http://schema.org/Text'
            model_column_time_limit = 600
            self._logger.info("Currently settting modeling each column maximum time as " + str(model_column_time_limit) + " seconds.")
            res = timeout_call(model_column_time_limit, self.process_one_column, [input_dfs[number].iloc[:,i], q, i, semantic_type])
            # res = self.process_one_column(column_data=input_dfs[number].iloc[:,i], item=q, column_number=i, semantic_type=semantic_type)
            if not res:
                self._logger.error("Error when modeling column " + str(i) + ". Maybe timeout? Will skip.")
        self.doc.kg.add_subject(q)
        end2 = time.time()
        self._logger.info("Modeling detail data finished. Totally take " + str(end2 - end1) + " seconds.")
        if job is not None:
            job.meta['step'] = "Modeling finished. Start uploading..."
            job.meta['modeling'] = str(datetime.timedelta(seconds=end2 - end1))
            job.save_meta()

    def process_one_column(self, column_data: pd.Series, item: WDItem, column_number: int, semantic_type: typing.List[str]) -> bool:
        """
        :param column_data: a pandas series data
        :param item: the target q node aimed to add on
        :param column_number: the column number
        :param semantic_type: a list indicate the semantic type of this column
        :return: a bool indicate succeeded or not
        """
        start = time.time()
        self._logger.debug("Start processing No." +str(column_number) + " column.")
        translator = str.maketrans(string.punctuation, ' '*len(string.punctuation))
        statement = item.add_statement('C2005', StringValue(column_data.name))  # variable measured
        try:
            import pdb
            pdb.set_trace()
            if 'http://schema.org/DateTime' in semantic_type or "datetime" in column_data.dtype.name:
                data_type = "datetime"
                semantic_type_url = "http://schema.org/DateTime"
                start_date = min(column_data)
                end_date = max(column_data)

                TemporalGranularity = {'second': 14, 'minute': 13, 'hour': 12, 'day': 11, 'month': 10, 'year': 9}
                # updated v2019.12.12: check details, only treat as the granularity if we found more than 1 values for this granularity
                if any(column_data.dt.second != 0) and len(column_data.dt.second.unique()) > 1:
                    time_granularity = TemporalGranularity['second']
                elif any(column_data.dt.minute != 0) and len(column_data.dt.minute.unique()) > 1:
                    time_granularity = TemporalGranularity['minute']
                elif any(column_data.dt.hour != 0) and len(column_data.dt.hour.unique()) > 1:
                    time_granularity = TemporalGranularity['hour']
                elif any(column_data.dt.day != 0) and len(column_data.dt.day.unique()) > 1:
                    time_granularity = TemporalGranularity['day']
                elif any(column_data.dt.month != 0) and len(column_data.dt.month.unique()) > 1:
                    time_granularity = TemporalGranularity['month']
                elif any(column_data.dt.year != 0) and len(column_data.dt.year.unique()) > 1:
                    time_granularity = TemporalGranularity['year']
                else:
                    raise Exception('Dates do not in a right format.')

                start_time = TimeValue(Literal(start_date.isoformat(), type_=LiteralType.dateTime), Item('Q1985727'), time_granularity, 0)
                end_time = TimeValue(Literal(end_date.isoformat(), type_=LiteralType.dateTime), Item('Q1985727'), time_granularity, 0)

                statement.add_qualifier('C2011', start_time)
                statement.add_qualifier('C2012', end_time)
                statement.add_qualifier('C2013', QuantityValue(time_granularity))
            else:
                all_data = set(column_data.tolist())
                all_value_str_set = set()
                for each in all_data:
                    # set to lower characters, remove punctuation and split by the space
                    words_processed = str(each).lower().translate(translator).split()
                    for word in words_processed:
                        all_value_str_set.add(word)
                all_value_str = " ".join(all_value_str_set)

                statement.add_qualifier('C2006', StringValue(all_value_str))  # values
                if 'http://schema.org/Float' in semantic_type:
                    semantic_type_url = 'http://schema.org/Float'
                    data_type = "float"
                elif 'http://schema.org/Integer' in semantic_type:
                    data_type = "int"
                    semantic_type_url = 'http://schema.org/Integer'
                else: # 'http://schema.org/Text' in semantic_type:
                    data_type = "string"
                    semantic_type_url = 'http://schema.org/Text'

            statement.add_qualifier('C2007', Item(data_type))  # data structure type
            statement.add_qualifier('C2008', URLValue(semantic_type_url))  # semantic type identifier
            statement.add_qualifier('P1545', QuantityValue(column_number))  # column index
            end1 = time.time()
            self._logger.info("Processing finished, totally take " + str(end1 - start) + " seconds.")
            return True
        except Exception as e:
            self._logger.error("[ERROR] processing column No." + str(column_number) + " failed!")
            self._logger.debug(e, exc_info=True)
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
        self._logger.info('Serialization completed!')

    def upload(self) -> str:
        """
            upload the dataset. If success, return the uploaded dataset's id
        """
        # # This special Q node is used to store the next count to store the new Q node
        start = time.time()
        self._logger.info("Start uploading...")
        # sparql_query = """
        #     prefix wdt: <http://www.wikidata.org/prop/direct/>
        #     prefix wdtn: <http://www.wikidata.org/prop/direct-normalized/>
        #     prefix wdno: <http://www.wikidata.org/prop/novalue/>
        #     prefix wds: <http://www.wikidata.org/entity/statement/>
        #     prefix wdv: <http://www.wikidata.org/value/>
        #     prefix wdref: <http://www.wikidata.org/reference/>
        #     prefix wd: <http://www.wikidata.org/entity/>
        #     prefix wikibase: <http://wikiba.se/ontology#>
        #     prefix p: <http://www.wikidata.org/prop/>
        #     prefix pqv: <http://www.wikidata.org/prop/qualifier/value/>
        #     prefix pq: <http://www.wikidata.org/prop/qualifier/>
        #     prefix ps: <http://www.wikidata.org/prop/statement/>
        #     prefix psn: <http://www.wikidata.org/prop/statement/value-normalized/>
        #     prefix prv: <http://www.wikidata.org/prop/reference/value/>
        #     prefix psv: <http://www.wikidata.org/prop/statement/value/>
        #     prefix prn: <http://www.wikidata.org/prop/reference/value-normalized/>
        #     prefix pr: <http://www.wikidata.org/prop/reference/>
        #     prefix pqn: <http://www.wikidata.org/prop/qualifier/value-normalized/>
        #     prefix skos: <http://www.w3.org/2004/02/skos/core#>
        #     prefix prov: <http://www.w3.org/ns/prov#>
        #     prefix schema: <http://schema.org/'>
        #     prefix bd: <http://www.bigdata.com/rdf#>
        #     prefix bds: <http://www.bigdata.com/rdf/search#>

        #     delete {
        #           wd:Z00000 wdt:P1114 ?x .
        #         }
        #         where {
        #             wd:Z00000 wdt:P1114 ?x .
        #         }
        #     """
        # try:
        #     sparql = SPARQLWrapper(self.update_server)
        #     sparql.setQuery(sparql_query)
        #     sparql.setReturnFormat(JSON)
        #     sparql.setMethod(POST)
        #     sparql.setRequestMethod(URLENCODED)
        #     results = sparql.query()  #.convert()['results']['bindings']
        # except:
        #     self._logger.error("Updating the count for datamart failed!")
        #     raise ValueError("Unable to connect to datamart server!")
        # # add datamart count to ttl
        # q = WDItem('Z00000')
        # q.add_label('Datamart datasets count', lang='en')
        # q.add_statement('P1114', QuantityValue(self.resource_id))  # title
        # self.doc.kg.add_subject(q)
        # upload
        extracted_data = self.doc.kg.serialize("ttl")
        headers = {'Content-Type': 'application/x-turtle',}
        response = requests.post(self.update_server, data=extracted_data.encode('utf-8'), headers=headers)
        self._logger.info('Upload file finished with status code: {}!'.format(response.status_code))

        if response.status_code//100 !=2:
            raise ValueError("Uploading file failed with code ", str(response.status_code))

        # upload truthy
        temp_output = StringIO()
        serialize_change_record(temp_output)
        temp_output.seek(0)
        tu = TruthyUpdater(self.update_server, False)
        np_list = []
        for l in temp_output.readlines():
            if not l: continue
            node, prop = l.strip().split('\t')
            np_list.append((node, prop))
        tu.build_truthy(np_list)
        self._logger.info('Update truthy finished!')
        end2 = time.time()
        self._logger.info("Upload finished. Totally take " + str(end2 - start) + " seconds.")
        return self.modeled_data_id
