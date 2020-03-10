import time
import requests
import hashlib
import logging
import base64
import os
import PyPDF2
import json

from .parser_base import ParserBase, PreParsedResult
from datetime import timedelta
from datamart_isi import config as config_datamart
from datamart_isi import config_services
from etk.wikidata.entity import *
from etk.wikidata.value import *
from io import BytesIO
from tika import parser
from wikifier.utils import remove_punctuation

SUPPORT_TYPE = ["pdf"]
MODULE_NAME = "PDFParser"


class PDFParser(ParserBase):
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def load_and_preprocess(self, **kwargs):
        input_dir = kwargs.get("input_dir")
        file_type = kwargs.get("file_type", "pdf")
        job = kwargs.get("job", None)
        start = time.time()
        if job is not None:
            job.meta['step'] = "materializing the dataset..."
            job.save_meta()
        requests_result = requests.get(input_dir)
        if requests_result.status_code // 100 != 2:
            raise ValueError("Reading file from {} failed.".format(str(input_dir)))
        metadata = dict()
        metadata['url'] = input_dir
        title_cleaned = input_dir.split("/")[-1]
        words_processed = remove_punctuation(title_cleaned)
        metadata['title'] = " ".join(words_processed)
        metadata['file_type'] = file_type
        all_metadata = [metadata]
        result = [requests_result.content]
        return PreParsedResult(result, all_metadata)

    def model_data(self, doc, inputs: PreParsedResult, **kwargs):
        self._logger.debug("Start modeling data into blazegraph format...")
        start = time.time()
        number = kwargs.get("number")
        job = kwargs.get("job", None)
        uploader_information = kwargs.get("uploader_information")
        each_content = inputs.content[number]
        each_metadata = inputs.metadata[number]
        hash_generator = hashlib.md5()
        hash_generator.update(str(each_content).encode('utf-8'))
        hash_url_key = hash_generator.hexdigest()
        modeled_data_id = hash_url_key
        node_id = 'D' + str(modeled_data_id)
        q = WDItem(node_id)
        try:
            parsed = parser.from_buffer(each_content, config_services.get_service_url("apache_tika"))
        except requests.exceptions.ConnectionError:
            raise ConnectionError("Apache Tika service is not up! Please check.")
        except Exception as e:
            self._logger.error("failed to parse the given pdf file.")
            self._logger.debug(e, exc_info=True)
            raise ValueError("Parsing PDF dataset ID = {} title = {} failed".format(modeled_data_id, each_metadata.get("title")))

        if parsed['status'] // 100 != 2:
            raise ValueError("Parsing PDF dataset ID = {} title = {} failed".format(modeled_data_id, each_metadata.get("title")))

        extra_information = dict()
        # because json require key to be string but not bytes,
        # we have to use b64 encoder to encoder the binary data and then decoded with utf-8 to store
        extra_information['first_10_rows'] = base64.b64encode(self.get_first_page(each_content)).decode("utf-8")
        extra_information["parsed_metadata"] = parsed["metadata"]
        # save a local backup
        hash_generator = hashlib.md5()
        hash_generator.update(each_metadata['url'].encode('utf-8'))
        hash_url_key = hash_generator.hexdigest()
        dataset_cache_loc = os.path.join(config_datamart.cache_file_storage_base_loc, "datasets_cache")
        if not os.path.exists(dataset_cache_loc):
            os.mkdir(dataset_cache_loc)
        cache_file_loc = os.path.join(dataset_cache_loc, hash_url_key + ".bin")
        with open(cache_file_loc, "wb") as f:
            f.write(each_content)

        q.add_label(node_id, lang='en')
        q.add_statement('P31', Item('Q1172284'))  # indicate it is subclass of a dataset
        q.add_statement('P2699', URLValue(each_metadata['url']))  # url
        q.add_statement('P2701', StringValue(each_metadata['file_type']))  # file type
        q.add_statement('P1476', MonolingualText(each_metadata['title'], lang='en'))  # title
        q.add_statement('C2001', StringValue(node_id))  # datamart identifier
        q.add_statement('C2004', StringValue(each_metadata.get('keywords', "")))  # keywords
        q.add_statement('C2010', StringValue(json.dumps(extra_information)))
        q.add_statement('C2014', StringValue(json.dumps(uploader_information)))
        end1 = time.time()
        if job is not None:
            job.meta['step'] = "Modeling abstract data finished."
            job.meta['modeling abstract'] = str(timedelta(seconds=end1 - start))
            job.save_meta()
        # model detail data
        self.model_details(parsed["content"], q)
        # add to doc
        doc.kg.add_subject(q)
        end2 = time.time()
        self._logger.info("Modeling detail data finished. Totally take " + str(end2 - end1) + " seconds.")
        if job is not None:
            job.meta['step'] = "Modeling finished. Start uploading..."
            job.meta['modeling'] = str(timedelta(seconds=end2 - end1))
            job.save_meta()
        # return the updated etc doc and corresponding dataset id
        return doc, node_id

    def model_details(self, parsed_data: str, item) -> None:
        """
        Model the details of the given parsed pdf files, currently we just get all words and save it
        :param parsed_data: parsed text from pdf file
        :param item: etk knowledge graph doc
        :return: None
        """
        statement = item.add_statement('C2005', StringValue("all_data"))
        all_value_str_set = set()
        words_processed = remove_punctuation(parsed_data)
        for word in words_processed:
            all_value_str_set.add(word)
        all_value_str = " ".join(all_value_str_set)
        self._logger.debug("Totally {} words added ".format(str(len(all_value_str_set))))
        statement.add_qualifier('C2006', StringValue(all_value_str))  # values
        statement.add_qualifier('C2007', Item("string"))  # data structure type
        statement.add_qualifier('C2008', URLValue('http://schema.org/Text'))  # semantic type identifier
        return item

    @staticmethod
    def get_first_page(input_pdf: bytes) -> bytes:
        """
        cut the first page of the given pdf bytes file
        :param input_pdf: a bytes object loaded from a pdf file
        :return: a bytes object contains the first page of the input pdf file
        """
        pdf_writer = PyPDF2.PdfFileWriter()
        pdf_file_obj = BytesIO(input_pdf)
        pdf_reader = PyPDF2.PdfFileReader(pdf_file_obj)
        page_obj = pdf_reader.getPage(0)
        pdf_writer.addPage(page_obj)
        with BytesIO() as f:
            pdf_writer.write(f)
            f.seek(0)
            result = f.read()
        return result



