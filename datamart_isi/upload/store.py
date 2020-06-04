import requests
import typing
import sys
import time
import logging
import urllib

from .file_parsers.parser_base import PreParsedResult
from .file_parsers.pdf_parser import PDFParser
from .file_parsers.csv_parser import CSVParser
from .file_parsers.image_parser import ImageParser
from .file_parsers.other_parser import OtherParser
from .file_parsers import *
from etk.etk import ETK
from etk.knowledge_graph import KGSchema
from etk.etk_module import ETKModule
from etk.wikidata.entity import WDProperty, serialize_change_record
from etk.wikidata.value import *
from etk.wikidata.truthy import TruthyUpdater
from SPARQLWrapper import SPARQLWrapper, JSON, POST, URLENCODED
from io import StringIO
from datamart_isi.utilities import connection


DATAMART_SERVER = connection.get_general_search_server_url()


class DatamartISIUpload:
    """
    Main class for uploading part
    """
    def __init__(self, query_server=DATAMART_SERVER, update_server=DATAMART_SERVER):
        self._logger = logging.getLogger(__name__)
        self.query_server = query_server
        self.update_server = update_server
        self.modeled_data_id = ""
        self.parser = None
        # test server is working or not
        sparql_query = """
            select ?s ?p ?o where {?s ?p ?o} LIMIT 1
            """
        try:
            sparql = SPARQLWrapper(self.query_server)
            sparql.setQuery(sparql_query)
            sparql.setReturnFormat(JSON)
            sparql.setMethod(POST)
            sparql.setRequestMethod(URLENCODED)
            _ = sparql.query().convert()['results']['bindings']
        except urllib.error.URLError:
            self._logger.error("Can't connect to blazegraph satellite!")
            raise ValueError("Unable to initialize the datamart query service on address " + query_server)
        except Exception:
            raise
        # load all parsers
        self.all_parsers = dict()
        self.support_types = dict()
        for each_module_name in sys.modules.keys():
            if each_module_name.startswith("datamart_isi.upload.file_parsers.") and "parser_base" not in each_module_name:
                self._logger.debug("{} loaded.".format(str(each_module_name)))
                class_name = each_module_name.replace("datamart_isi.upload.file_parsers.", "").split("_")[0]
                each_module = sys.modules[each_module_name]
                parser_class_name = getattr(each_module, "MODULE_NAME")
                each_parser_class = getattr(each_module, parser_class_name)
                self.support_types[class_name] = getattr(each_module, "SUPPORT_TYPE")
                self.all_parsers[class_name] = each_parser_class
        self.doc = self._init_etk()

    @staticmethod
    def _init_etk():
        # initialize for etk
        kg_schema = KGSchema()
        kg_schema.add_schema('@prefix : <http://isi.edu/> .', 'ttl')
        etk = ETK(kg_schema=kg_schema, modules=ETKModule)
        doc = etk.create_document({}, doc_id="http://isi.edu/default-ns/projects")

        # bind prefixes
        doc.kg.bind('wikibase', 'http://wikiba.se/ontology#')
        doc.kg.bind('wd', 'http://www.wikidata.org/entity/')
        doc.kg.bind('wdt', 'http://www.wikidata.org/prop/direct/')
        doc.kg.bind('wdtn', 'http://www.wikidata.org/prop/direct-normalized/')
        doc.kg.bind('wdno', 'http://www.wikidata.org/prop/novalue/')
        doc.kg.bind('wds', 'http://www.wikidata.org/entity/statement/')
        doc.kg.bind('wdv', 'http://www.wikidata.org/value/')
        doc.kg.bind('wdref', 'http://www.wikidata.org/reference/')
        doc.kg.bind('p', 'http://www.wikidata.org/prop/')
        doc.kg.bind('pr', 'http://www.wikidata.org/prop/reference/')
        doc.kg.bind('prv', 'http://www.wikidata.org/prop/reference/value/')
        doc.kg.bind('prn', 'http://www.wikidata.org/prop/reference/value-normalized/')
        doc.kg.bind('ps', 'http://www.wikidata.org/prop/statement/')
        doc.kg.bind('psv', 'http://www.wikidata.org/prop/statement/value/')
        doc.kg.bind('psn', 'http://www.wikidata.org/prop/statement/value-normalized/')
        doc.kg.bind('pq', 'http://www.wikidata.org/prop/qualifier/')
        doc.kg.bind('pqv', 'http://www.wikidata.org/prop/qualifier/value/')
        doc.kg.bind('pqn', 'http://www.wikidata.org/prop/qualifier/value-normalized/')
        doc.kg.bind('skos', 'http://www.w3.org/2004/02/skos/core#')
        doc.kg.bind('prov', 'http://www.w3.org/ns/prov#')
        doc.kg.bind('schema', 'http://schema.org/')

        # give definition of the nodes we definied
        p = WDProperty('C2001', Datatype.MonolingualText)
        p.add_label('datamart identifier', lang='en')
        p.add_description('identifier of a dataset in the Datamart system', lang='en')
        p.add_statement('P31', Item('Q19847637'))
        p.add_statement('P1629', Item('Q1172284'))
        doc.kg.add_subject(p)

        p = WDProperty('C2004', Datatype.StringValue)
        p.add_label('keywords', lang='en')
        p.add_description('keywords associated with an item to facilitate finding the item using text search', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        doc.kg.add_subject(p)

        p = WDProperty('C2005', Datatype.StringValue)
        p.add_label('variable measured', lang='en')
        p.add_description('the variables measured in a dataset', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        p.add_statement('P1628', URLValue('http://schema.org/variableMeasured'))
        doc.kg.add_subject(p)

        p = WDProperty('C2006', Datatype.StringValue)
        p.add_label('values', lang='en')
        p.add_description('the values of a variable represented as a text document', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        doc.kg.add_subject(p)

        p = WDProperty('C2007', Datatype.Item)
        p.add_label('data type', lang='en')
        p.add_description('the data type used to represent the values of a variable, integer (Q729138), Boolean (Q520777), '
                          'Real (Q4385701), String (Q184754), Categorical (Q2285707)', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        doc.kg.add_subject(p)

        p = WDProperty('C2008', Datatype.URLValue)
        p.add_label('semantic type', lang='en')
        p.add_description('a URL that identifies the semantic type of a variable in a dataset', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        doc.kg.add_subject(p)

        p = WDProperty('C2010', Datatype.StringValue)
        p.add_label('extra information', lang='en')
        p.add_description('some extra information that may needed for this dataset', lang='en')
        doc.kg.add_subject(p)

        p = WDProperty('C2011', Datatype.TimeValue)
        p.add_label('start date', lang='en')
        p.add_description('The earlist time exist in this dataset, only valid when there exists time format data in this dataset',
                          lang='en')
        p.add_statement('P31', Item('Q18616576'))
        doc.kg.add_subject(p)

        p = WDProperty('C2012', Datatype.TimeValue)
        p.add_label('end date', lang='en')
        p.add_description('The latest time exist in this dataset, only valid when there exists time format data in this dataset',
                          lang='en')
        p.add_statement('P31', Item('Q18616576'))
        doc.kg.add_subject(p)

        p = WDProperty('C2013', Datatype.QuantityValue)
        p.add_label('time granularity', lang='en')
        p.add_description('time granularity in a dataset', lang='en')
        p.add_statement('P31', Item('Q18616576'))
        doc.kg.add_subject(p)

        p = WDProperty('C2014', Datatype.StringValue)
        p.add_label('uploader information', lang='en')
        p.add_description('information about who uploaded and when uploaded', lang='en')
        doc.kg.add_subject(p)
        return doc

    def load_and_preprocess(self, **kwargs) -> PreParsedResult:
        """
            check the file type and use corresponding parser to load and preprocess the given data
            add codes like if statement here for further updates
        """
        file_type = kwargs.get("file_type")
        if file_type == "csv" or file_type == "online_csv":
            self.parser = CSVParser()
        if file_type == "pdf":
            self.parser = PDFParser()
        elif file_type == "image":
            self.parser = ImageParser()
        elif file_type == "other":
            self.parser = OtherParser()
        elif file_type == "auto":
            input_dir = kwargs.get("input_dir")
            input_file_type = input_dir.split(".")[-1]
            for parser_name, support_type in self.support_types.items():
                if input_file_type in support_type:
                    self.parser = self.all_parsers[parser_name]()
                    file_type = parser_name

        # if no parser found, use "other" as type
        if self.parser is None:
            self.parser = OtherParser()
            file_type = "other"

        # update file type
        kwargs['file_type'] = file_type

        # load different parser by file type
        self._logger.debug("The upload file type is {}".format(file_type))

        return self.parser.load_and_preprocess(**kwargs)

    def model_data(self, **kwargs) -> None:
        """
        call parser's function to finish modeling process
        """
        if self.parser is None:
            raise ValueError("Have to call function `load_and_preprocess` first!")
        self.doc, self.modeled_data_id = self.parser.model_data(self.doc, **kwargs)

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
        start = time.time()
        self._logger.info("Start uploading...")
        # upload
        extracted_data = self.doc.kg.serialize("ttl")
        headers = {'Content-Type': 'application/x-turtle', }
        response = requests.post(self.update_server, data=extracted_data.encode('utf-8'), headers=headers)
        self._logger.info('Upload file finished with status code: {}!'.format(response.status_code))

        if response.status_code // 100 != 2:
            raise ValueError("Uploading file failed with code ", str(response.status_code))

        # upload truthy
        temp_output = StringIO()
        serialize_change_record(temp_output)
        temp_output.seek(0)
        tu = TruthyUpdater(self.update_server, False)
        np_list = []
        for l in temp_output.readlines():
            if not l:
                continue
            node, prop = l.strip().split('\t')
            np_list.append((node, prop))
        tu.build_truthy(np_list)
        self._logger.info('Update truthy finished!')
        end2 = time.time()
        self._logger.info("Upload finished. Totally take " + str(end2 - start) + " seconds.")
        return self.modeled_data_id
