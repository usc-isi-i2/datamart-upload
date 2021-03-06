import os
import json
import sys
import pandas as pd
import logging
import typing
import traceback
import shutil
import pickle
import io
import zipfile
import cgitb
import tempfile
import pathlib
import requests
import copy
import time
import redis
import hashlib
import socket
import inspect
import datetime
import frozendict
import rq
import bcrypt

from flask_cors import CORS, cross_origin
from flask import Flask, request, send_file, Response, redirect
from flasgger import Swagger
from rq import Queue
from werkzeug.contrib.fixers import ProxyFix
from SPARQLWrapper import SPARQLWrapper, JSON, POST, URLENCODED

# sys.path.append(sys.path.append(os.path.join(os.path.dirname(__file__), '..')))
from d3m.base import utils as d3m_utils
from d3m.container import DataFrame as d3m_DataFrame
from d3m.container.dataset import Dataset as d3m_Dataset, D3MDatasetLoader
from d3m.metadata.base import ALL_ELEMENTS

from wikifier.wikifier import produce
from wikifier.utils import wikifier_for_ethiopia_dataset
from datamart_isi import config as config_datamart
from datamart_isi import config_services
from datamart_isi.utilities import connection
from datamart_isi.entries import Datamart, DatamartQuery, AUGMENT_RESOURCE_ID, DatamartSearchResult, DatasetColumn
from datamart_isi.upload.store import DatamartISIUpload
from datamart_isi.utilities.download_manager import DownloadManager
from datamart_isi.utilities.utils import Utils
from datamart_isi.cache.materializer_cache import MaterializerCache
from datamart_isi.cache.metadata_cache import MetadataCache
from datamart_isi.upload.redis_manager import RedisManager
from datamart_isi.upload.dataset_upload_woker_process import upload_to_datamart
from datamart_isi.augment import Augment


_logger = logging.getLogger()
_logger.setLevel(logging.DEBUG)
# logging.basicConfig(format=FORMAT, stream=sys.stdout, level=logging.DEBUG)
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)s] %(name)s %(lineno)d -- %(message)s",
                    datefmt='%m-%d %H:%M:%S',
                    filename='datamart_openapi.log',
                    filemode='w')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s %(lineno)d -- %(message)s", '%m-%d %H:%M:%S')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root _logger
logging.getLogger('').addHandler(console)

em_es_url = connection.get_es_fb_embedding_server_url()
# em_es_url = config_datamart.em_es_url
# em_es_index = config_datamart.em_es_index
# em_es_type = config_datamart.em_es_type
wikidata_uri_template = '<http://www.wikidata.org/entity/{}>'
password_token_file = "../datamart_isi/upload/password_tokens.json"
password_record_file = "../datamart_isi/upload/upload_password_config.json"


dataset_paths = ["/data",  # for docker
                 "/data00/dsbox/dataset/datasets/seed_datasets_data_augmentation",  # for dsbox02 server
                 "/data00/dsbox/dataset/datasets/seed_datasets_current",  # for dsbox02 server
                 "/Users/minazuki/Desktop/studies/master/2018Summer/data/datasets/seed_datasets_data_augmentation"
                 ]

def load_keywords_augment_resources():
    sys.path.append(os.path.join(os.getcwd(), '..', "datamart_keywords_augment"))
    if os.path.exists("fuzzy_search_core.pkl"):
        try:
            with open("fuzzy_search_core.pkl","rb") as f:
                FUZZY_SEARCH_CORE = pickle.load(f)
        except ModuleNotFoundError:
            _logger.error("Can't load keywords augment core model! Please check the path!")
            FUZZY_SEARCH_CORE = None
    else:
        FUZZY_SEARCH_CORE = None
    return FUZZY_SEARCH_CORE

hostname = socket.gethostname()
_logger.info("Current hostname is: {}".format(hostname))
_logger.info("Loading for keywords augmentation!!")
FUZZY_SEARCH_CORE = load_keywords_augment_resources()
_logger.info("Loading finished!!")
DATAMART_SERVER = connection.get_general_search_server_url()
DATAMART_TEST_SERVER = connection.get_general_search_test_server_url()
datamart_upload_instance = DatamartISIUpload(update_server=DATAMART_SERVER,
                                               query_server=DATAMART_SERVER)
Q_NODE_SEMANTIC_TYPE = config_datamart.q_node_semantic_type
REDIS_MANAGER = RedisManager()

app = Flask(__name__)

CORS(app, resources={r"/api": {"origins": "*"}})
app.config['SWAGGER'] = {
    'title': 'Datamart Link Panel',
    'openapi': '3.0.2'
}

# swagger-UI configuration
swagger_config = Swagger.DEFAULT_CONFIG
swagger_config['swagger_ui_bundle_js'] = '//unpkg.com/swagger-ui-dist@3/swagger-ui-bundle.js'
swagger_config['jquery_js'] = '//unpkg.com/jquery@2.2.4/dist/jquery.min.js'
swagger_config['swagger_ui_css'] = '//unpkg.com/swagger-ui-dist@3/swagger-ui.css'
Swagger(app, template_file='api.yaml', config=swagger_config)


class StringConverter(dict):
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return str

    def get(self, default=None):
        return str


def is_redis_available(redis_conn):
    # for debugging condition, should not run on redis
    if "dsbox" not in hostname:
        return False

    try:
        redis_conn.get(None)  # getting None returns None or throws an exception
    except (redis.exceptions.ConnectionError, redis.exceptions.BusyLoadingError):
        _logger.debug("Redis is still loading or not ready yet.")
        return False
    except redis.exceptions.DataError:
        _logger.warn("Redis is ready for connection.")
        return True
    _logger.warn("Redis is ready for connection (2).")
    return True


def retrieve_file_paths(dirName):
    # setup file paths variable
    filePaths = []
    # Read all directory, subdirectories and file lists
    for root, directories, files in os.walk(dirName):
        for filename in files:
            # Create the full filepath by using os module.
            filePath = os.path.join(root, filename)
            filePaths.append(filePath)
    # return all paths
    return filePaths


def wrap_response(code, msg='', data=None, **kwargs):
    return json.dumps({
        'code': code,
        'message': msg or ('Success' if code == '200' else 'Failed'),
        'data': data,
        **kwargs
    }, indent=2, default=lambda x: str(x)), code


def read_file(files, key, _type):
    if files and key in files:
        try:
            if _type == 'csv':
                return pd.read_csv(files[key], converters=StringConverter()).infer_objects()
            elif _type == 'json':
                return json.loads(files[key])
        except:
            pass


def parse_search_result(search_res: DatamartSearchResult) -> dict:
    """
    function to parse the search result into a str for better display
    :param search_res: a DatamartSearchResult
    :return: a str with multiple lines
    """
    display_df = search_res.display()
    title = str(display_df['title'][0])
    datamart_id = str(search_res.id())
    columns_result = display_df['columns'][0]
    columns_result = columns_result.split(", ")
    score = str(search_res.score())
    join_columns = display_df['join columns'][0]
    try:
        url = search_res.search_result['url']['value']
    except:
        url = "None"

    res = {"title": title, "Datamart ID": datamart_id, "Score": score, "URL": url, 'Columns': []}
    for i, each in enumerate(columns_result):
        res['Columns'].append("[" + str(i) + "] " + each)
    res['Recommend Join Columns'] = join_columns
    if 'number_of_vectors' in display_df.columns.tolist():
        res['Number of Vectors'] = display_df['number_of_vectors'][0]

    return res


def load_d3m_dataset(path) -> typing.Optional[d3m_Dataset]:
    """
    Function used to load exist d3m datasets
    """
    # creat a dict which have reference for all dataset ids
    _logger.debug("Trying to load dataset " + str(path))
    datasets_list = dict()
    for each_path in dataset_paths:
        try:
            temp = os.listdir(each_path)
            for each in temp:
                datasets_list[each] = each_path
        except:
            pass
    if path not in datasets_list.keys():
        return None
    loader = D3MDatasetLoader()
    dataset_path = os.path.join(datasets_list[path], path, path + "_dataset", "datasetDoc.json")
    json_file = os.path.abspath(dataset_path)
    all_dataset_uri = 'file://{}'.format(json_file)
    all_dataset = loader.load(dataset_uri=all_dataset_uri)
    _logger.debug("Load " + str(path) + " success!")
    return all_dataset


def load_csv_data(data) -> d3m_Dataset:
    """
    Function used to load general csv file to d3m format dataset
    :param data: a str or a pd.DataFrame
    :return: a d3m style Dataset
    """
    _logger.debug("Trying to load csv data with first 100 characters as:")

    if isinstance(data, str):
        _logger.debug(str(data))
    else:
        _logger.debug(str(data[:10]))

    if type(data) is str:
        data = pd.read_csv(data, converters=StringConverter())
    elif type(data) is pd.DataFrame:
        data.fillna("",inplace=True)
        data = data.astype(str)
    else:
        raise ValueError("Unknown input type.")
    # transform pd.DataFrame to d3m.Dataset

    d3m_df = d3m_DataFrame(data, generate_metadata=False)
    resources = {AUGMENT_RESOURCE_ID: d3m_df}
    return_ds = d3m_Dataset(resources=resources, generate_metadata=False)
    return_ds.metadata = return_ds.metadata.clear(source="", for_value=return_ds, generate_metadata=True)
    for i, each_column in enumerate(return_ds[AUGMENT_RESOURCE_ID]):
        metadata_selector = (AUGMENT_RESOURCE_ID, ALL_ELEMENTS, i)
        structural_type = str
        metadata_each_column = {"name": each_column,
                                "structural_type": structural_type,
                                'semantic_types': ('https://metadata.datadrivendiscovery.org/types/Attribute',
                                                   "http://schema.org/Text")}
        return_ds.metadata = return_ds.metadata.update(metadata=metadata_each_column, selector=metadata_selector)
    metadata_all_level = {
        "id": "datamart_search_" + str(hash(data.values.tobytes())),
        "version": "4.0.0",
        "name": "user given input from datamart userend",
        "location_uris": ('file:///tmp/datasetDoc.json',),
        "digest": "",
        "description": "",
        "source": {'license': 'Other'},
    }
    return_ds.metadata = return_ds.metadata.update(metadata=metadata_all_level, selector=())
    _logger.debug("Loading csv and transform to d3m dataset format success!")
    return return_ds

def _load_file_with(read_format: str, tmpfile):
    """
    Inner function used for `load_input_supplied_data`
    """
    try:
        if read_format == "zip": 
            # try to load as d3m dataset
            data = None
            destination = tempfile.mkdtemp(prefix='datamart_download_')
            zip = zipfile.ZipFile(tmpfile)
            zip.extractall(destination)
            loaded_dataset = d3m_Dataset.load('file://' + destination + '/datasetDoc.json')
            status = True
            # remove unzipped files
            shutil.rmtree(destination)

        elif read_format == "pkl":
            # pkl format
            data = None
            with open(tmpfile,"rb") as f:
                loaded_dataset = pickle.load(f)
            status = True

        elif read_format == "csv":
            # csv format
            data = pd.read_csv(tmpfile)
            loaded_dataset = load_csv_data(data)
            status = True
        else:
            raise ValueError("Unknown read format!")

        _logger.info("Loading {} as {} file success!".format(tmpfile, read_format))

    except Exception as e:
        loaded_dataset = None
        data = None
        _logger.debug("Get error information " + str(e))
        _logger.info("{} is not a valid {} file".format(tmpfile, read_format))
        status = False
    return status, data, loaded_dataset


def load_input_supplied_data(data_from_value, data_from_file):
    """
    function used to load the input data from different methods
    """
    if data_from_file:
        _logger.debug("Detected a file from post body!")

        fd, tmpfile = tempfile.mkstemp(prefix='datamart_download_', suffix='.d3m.tmp')
        destination = None
        data_from_file.save(tmpfile)

        status, data, loaded_dataset = _load_file_with("zip", tmpfile)
        if not status:
            status, data, loaded_dataset = _load_file_with("pkl", tmpfile)
        if not status:
            status, data, loaded_dataset = _load_file_with("csv", tmpfile)
        if not status:
            _logger.error("Loading dataset failed with all attempts!")

        # remove temp files
        os.close(fd)
        os.remove(tmpfile)
        if destination:
            shutil.rmtree(destination) 
                   
    elif data_from_value:
        data = None
        if data_from_value.lower().endswith(".csv"):
            _logger.debug("csv file path detected!")
            loaded_dataset = load_csv_data(data_from_value)
        else:
            _logger.debug("d3m path maybe?")
            loaded_dataset = load_d3m_dataset(data_from_value)
    else:
        data = None
        loaded_dataset = None
    return data, loaded_dataset


def check_return_format(format_):
    if format_ is None:
        return None
    if format_.lower() == "csv":
        return_format = "csv"
    elif format_.lower() == "d3m":
        return_format = "d3m"
    else:
        return None
    return return_format


def record_error_to_file(e, function_from):
    """
    function used to make records on the errors
    """
    with open("datamart_error_records.log", "a") as f:
        f.write("*"*100 + "\n")
        f.write(str(datetime.datetime.now()) + "\n")
        error_message = """Errror happened on function "{}" \n""".format(str(function_from))
        f.write(error_message)
        f.write(str(e))
        f.write(str(traceback.format_exc()))
        info = sys.exc_info()
        f.write(str(cgitb.text(info)))
    # also show on _logger
    _logger.error(error_message)
    _logger.error(str(e))
    _logger.error(str(traceback.format_exc()))


@app.before_request
def before_request():
    hostname = socket.gethostname()
    if hostname == "dsbox02" and not request.is_secure:
        url = request.url.replace("http://", "https://", 1)
        code = 301
        return redirect(url, code=code)


@app.route('/')
def hello():
    return redirect('/apidocs')


@app.route('/wikifier', methods=['POST'])
@cross_origin()
def wikifier():
    try:
        _logger.debug("Start running wikifier...")
        # check that each parameter meets the requirements
        try:
            data_file = request.files.get('data')
        except:
            data_file = None
        data, loaded_dataset = load_input_supplied_data(request.values.get('data'), data_file)

        if loaded_dataset is None:
            return wrap_response(code='400',
                                 msg='FAIL SEARCH - Unable to load input supplied data',
                                 data=None)

        return_format = request.values.get('format')
        # if not get return format, set defauld as csv
        if return_format is None:
            return_format = "csv"
        else:
            return_format = check_return_format(return_format)
        if not return_format:
            return wrap_response(code='400',
                                 msg='FAIL SEARCH - Unknown return format: ' + str(return_format),
                                 data=None)

        _logger.info("The requested download format is " + return_format)

        columns_formated, choice = [], []

        try:
            if request.data:
                col_cho = json.loads(str(request.data, "utf-8"))
                for x in col_cho:
                    if "column" in x.keys() and "wikifier_choice" in x.keys():
                        columns_formated.append(int(x['column']))
                        if x['wikifier_choice'] in ["identifier", "new_wikifier", "automatic"]:
                            choice.append(x['wikifier_choice'])
                        else:
                            return wrap_response(code='400',
                                                 msg='FAIL SEARCH - Unknown wikifier choice, please follow the examples!!! ' + str(x['wikifier_choice']),
                                                 data=None)
                    else:
                        return wrap_response(code='400',
                                             msg='FAIL SEARCH - Missed column or wikifier_choice, please follow the examples!!! ' + str(x),
                                             data=None)
            else:
                columns_formated = None
                choice = ['automatic']
        except:
            return wrap_response(code='400',
                                 msg='FAIL SEARCH - Unknown json format, please follow the examples!!! ' + str(request.data),
                                 data=None)
        _logger.info("Required columns found as: " + str(columns_formated))
        _logger.info("Wikifier choice is: " + str(choice))

        threshold = request.values.get("threshold")
        if not threshold:
            threshold = 0.7
        else:
            try:
                threshold = float(threshold)
            except:
                threshold = 0.7
        _logger.info("Threshold for coverage is: " + str(threshold))

        _logger.debug("Start changing dataset to dataframe...")
        # DA = load_d3m_dataset("DA_poverty_estimation")
        # MetadataCache.save_metadata_from_dataset(DA)
        # try to update with more correct metadata if possible
        updated_result = MetadataCache.check_and_get_dataset_real_metadata(loaded_dataset)
        if updated_result[0]:  # [0] store whether it success find the metadata
            loaded_dataset = updated_result[1]
        res_id, supplied_dataframe = d3m_utils.get_tabular_resource(dataset=loaded_dataset,
                                                                    resource_id=None, has_hyperparameter=False)
        output_ds = copy.copy(loaded_dataset)
        _logger.debug("Start running wikifier...")
        wikifier_res = produce(inputs=supplied_dataframe, target_columns=columns_formated, target_p_nodes=None,
                               wikifier_choice=choice, threshold=threshold)
        _logger.debug("Wikifier finished, Start to update metadata...")
        output_ds[res_id] = d3m_DataFrame(wikifier_res, generate_metadata=False)

        # update metadata on column length
        selector = (res_id, ALL_ELEMENTS)
        old_meta = dict(output_ds.metadata.query(selector))
        old_meta_dimension = dict(old_meta['dimension'])
        old_column_length = old_meta_dimension['length']
        old_meta_dimension['length'] = wikifier_res.shape[1]
        old_meta['dimension'] = frozendict.FrozenOrderedDict(old_meta_dimension)
        new_meta = frozendict.FrozenOrderedDict(old_meta)
        output_ds.metadata = output_ds.metadata.update(selector, new_meta)

        # update new column's metadata
        for i in range(old_column_length, wikifier_res.shape[1]):
            selector = (res_id, ALL_ELEMENTS, i)
            metadata = {"name": wikifier_res.columns[i],
                        "structural_type": str,
                        'semantic_types': (
                            "http://schema.org/Text",
                            'https://metadata.datadrivendiscovery.org/types/Attribute',
                            Q_NODE_SEMANTIC_TYPE
                        )}
            output_ds.metadata = output_ds.metadata.update(selector, metadata)

        _logger.info("Return the wikifier result.")
        result_id = str(hash(wikifier_res.values.tobytes()))
        if return_format == "d3m":
            with tempfile.TemporaryDirectory() as tmpdir:
                save_dir = os.path.join(str(tmpdir), result_id)
                absolute_path_part_length = len(str(save_dir))
                output_ds.save("file://" + save_dir + "/datasetDoc.json")
                base_path = pathlib.Path(save_dir + '/')
                data = io.BytesIO()
                filePaths = retrieve_file_paths(save_dir)

                zip_file = zipfile.ZipFile(data, 'w')
                with zip_file:
                    # write each file seperately
                    for fileName in filePaths:
                        shorter_path = fileName[absolute_path_part_length:]
                        zip_file.write(fileName, shorter_path)
                data.seek(0)

                return send_file(
                    data,
                    mimetype='application/zip',
                    as_attachment=True,
                    attachment_filename='download_result' + result_id + '.zip'
                )
        else:
            data = io.StringIO()
            wikifier_res.to_csv(data, index=False)
            return Response(data.getvalue(), mimetype="text/csv")

    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response(code='400', msg="FAIL WIKIFIER - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/search', methods=['POST'])
@cross_origin()
def search():
    try:
        # check that each parameter meets the requirements
        query = read_file(request.values, 'query', 'json')
        # if not send the json via file
        if not query and request.form.get('query_json'):
            query = json.loads(request.form.get('query_json'))
        if not query and request.files.get("query"):
            query = json.load(request.files.get('query'))
        max_return_docs = int(request.values.get('max_return_docs')) if request.values.get('max_return_docs') else 20

        try:
            data_file = request.files.get('data')
        except:
            data_file = None

        data, loaded_dataset = load_input_supplied_data(request.values.get('data'), data_file)

        if loaded_dataset is None:
            if data is None:
                _logger.error("Search failed! No path given or can't load dataset")
                return wrap_response(code='400',
                                     msg="""FAIL SEARCH - data is not given or can't load dataset, please run "/search_without_data" instead""",
                                     data=None)
            else:
                _logger.error("Unable to load the input file with")
                _logger.error(str(data))
                return wrap_response(code='400',
                                     msg='FAIL SEARCH - Unable to load input supplied data',
                                     data=None)
        if request.values.get('run_wikifier'):
            need_wikifier = request.values.get('run_wikifier')
            if need_wikifier.lower() == "false":
                need_wikifier = False
            elif need_wikifier.lower() == "true":
                need_wikifier = True
            else:
                _logger.error("Unknown value for need_wikifier as " + str(need_wikifier))
                _logger.error("Will set need_wikifier with default value as True.")
                need_wikifier = True
        else:
            need_wikifier = True
        
        if request.values.get('consider_wikifier_columns_only'):
            consider_wikifier_columns_only = request.values.get('consider_wikifier_columns_only')
            if consider_wikifier_columns_only.lower() == "false":
                consider_wikifier_columns_only = False
            elif consider_wikifier_columns_only.lower() == "true":
                consider_wikifier_columns_only = True
        else:
            consider_wikifier_columns_only = False
        if consider_wikifier_columns_only:
            _logger.warning("Will only consider wikifier columns only for augmenting!")

        if request.values.get('augment_with_time'):
            augment_with_time = request.values.get('augment_with_time')
            if augment_with_time.lower() == "false":
                augment_with_time = False
            elif augment_with_time.lower() == "true":
                augment_with_time = True
        else:
            augment_with_time = False
        if augment_with_time:
            _logger.warning("Will consider augment with time columns!")

        if request.values.get('consider_time'):
            consider_time = request.values.get('consider_time')
            if consider_time.lower() == "false":
                consider_time = False
            elif consider_time.lower() == "true":
                consider_time = True
        else:
            consider_time = True

        if not consider_time:
            if augment_with_time is True:
                _logger.warning("Augment with time is set to be true! consider_time parameter will be useless.")
            else:
                _logger.warning("Will not consider time columns augmentation from datamart!")

        # start to search
        _logger.debug("Starting datamart search service...")
        datamart_instance = Datamart(connection_url=config_datamart.default_datamart_url)

        if need_wikifier:
            meta_for_wikifier = None
            if query and "keywords" in query.keys():
                for i, kw in enumerate(query["keywords"]):
                    if kw and config_datamart.wikifier_column_mark in kw:
                        meta_for_wikifier = json.loads(query["keywords"].pop(i))[config_datamart.wikifier_column_mark]
                        break
                if meta_for_wikifier:
                    _logger.info(
                        "Get specific column<->p_nodes relationship from user. Will only wikifier those columns!")
                    _logger.info("The detail relationship is: {}".format(str(meta_for_wikifier)))
                    _, supplied_dataframe = d3m_utils.get_tabular_resource(dataset=loaded_dataset, resource_id=None)
                    MetadataCache.save_specific_wikifier_targets(supplied_dataframe, meta_for_wikifier)

            search_result_wikifier = DatamartSearchResult(search_result={}, supplied_data=None, query_json={},
                                                          search_type="wikifier")
            loaded_dataset = search_result_wikifier.augment(supplied_data=loaded_dataset)
            _logger.debug("Wikifier finished, start running search...")

        else:
            _logger.debug("Wikifier skipped, start running search...")

        if query:
            keywords = query.get("keywords", [])
            variables = query.get("variables", [])
        else:
            keywords: typing.List[str] = []
            variables: typing.List['VariableConstraint'] = []

        _logger.debug("The search's keywords are: {}".format(str(keywords)))
        _logger.debug("The search's variables are: {}".format(str(variables)))

        query_wrapped = DatamartQuery(keywords=keywords, variables=variables)
        res = datamart_instance.search_with_data(
                query=query_wrapped, 
                supplied_data=loaded_dataset,
                consider_wikifier_columns_only=consider_wikifier_columns_only,
                augment_with_time=augment_with_time,
                consider_time=consider_time
                ).get_next_page(limit=max_return_docs) or []
        
        _logger.debug("Search finished, totally find " + str(len(res)) + " results.")
        results = []
        for i, each_res in enumerate(res):
            try:
                file_type = each_res.search_result['file_type']['value']
                materialize_info = each_res.serialize()
                materialize_info_decoded = json.loads(materialize_info)
                augmentation_part = materialize_info_decoded['augmentation']
                search_type = materialize_info_decoded["metadata"]['search_type']
                sample_data = DownloadManager.get_sample_dataset(each_res)
                # if returned false from `sample_data`, we should skip this result because it is useless
                if sample_data == False:
                    _logger.info("No.{} search result is useless, skipped.".format(str(i)))
                    continue
                # updated v2020.3.17, now we can't do download/augment operation for non csv format
                # this extra parameter can let the frontend know if this search result can be used for augment or not
                if file_type != "csv":
                    preview_only = True
                else:
                    metadata = DownloadManager.get_metadata(each_res)
                    preview_only = False
                cur = {
                    'augmentation': {
                        'type': augmentation_part['properties'], 
                        'left_columns': augmentation_part['left_columns'], 
                        'right_columns': augmentation_part['right_columns'],
                        },
                    'all_column_names': materialize_info_decoded['dataframe_column_names'],
                    'summary': parse_search_result(each_res),
                    'score': each_res.score(),
                    'metadata': metadata,
                    'id': each_res.id(),
                    'sample': sample_data,
                    'file_type': file_type,
                    'preview_only': preview_only,
                    'materialize_info': materialize_info
                }
                results.append(cur)

            except Exception as e:
                _logger.error("Feteching No.{} result failed!".format(str(i)))
                _logger.debug(e, exc_info=True)
            
        json_return = dict()
        json_return["results"] = results
        # return wrap_response(code='200',
        #                       msg='Success',
        #                       data=json.dumps(json_return, indent=2)
        #                       )
        return json.dumps(json_return, indent=2)

    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response(code='400', msg="FAIL SEARCH - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/search_without_data', methods=['POST'])
@cross_origin()
def search_without_data():
    try:
        _logger.debug("Start running search_without_data...")
        # check that each parameter meets the requirements
        query = read_file(request.values, 'query', 'json')
        # if not send the json via file
        if not query and request.form.get('query_json'):
            query = json.loads(request.form.get('query_json'))
        if not query and request.files.get("query"):
            query = json.load(request.files.get('query'))
        if not query and request.json:
            query = request.json
        max_return_docs = int(request.values.get('max_return_docs')) if request.values.get('max_return_docs') else 20

        if query:
            keywords = query.get("keywords", [])
            variables = query.get("variables", {})
            if variables is None:
                variables = {}
        else:
            return wrap_response(code='400', msg="FAIL SEARCH - No query given, can't search.")

        # remove empty and duplicate keywords
        keywords_set = set(keywords)
        if "" in keywords_set:
            keywords_set.remove("")
        if " " in keywords_set:
            keywords_set.remove(" ")
        keywords = list(keywords_set)
        keywords.sort()

        _logger.debug("The search's keywords are: {}".format(str(keywords)))
        _logger.debug("The search's variables are: {}".format(str(variables)))
        _logger.debug("The search's return docs amount is: {}".format(str(max_return_docs)))

        # query_wrapped = DatamartQuery(keywords=keywords, variables=variables)

        # keywords = request.values.get("keywords").strip(',') if request.values.get("keywords") else None
        # keywords_search: typing.List[str] = keywords.split(',') if keywords != None else []
        # if request.data:
        #     variables = json.loads(str(request.data, "utf-8"))
        #     variables_search: dict() = variables['variables'] if variables != None else {}
        # else:
        #     query_wrapped = DatamartQuery(keywords_search=keywords_search)

        query_wrapped = DatamartQuery(keywords_search=keywords, variables_search=variables)

        _logger.debug("Starting datamart search service...")
        datamart_instance = Datamart(connection_url=config_datamart.default_datamart_url)
        res = datamart_instance.search(query=query_wrapped).get_next_page(limit=max_return_docs) or []
        _logger.debug("Search finished, totally find " + str(len(res)) + " results.")
        results = []
        for each_res in res:
            materialize_info = each_res.serialize()
            materialize_info_decoded = json.loads(materialize_info)
            sample_data = DownloadManager.get_sample_dataset(each_res)
            metadata = DownloadManager.get_metadata(each_res)
            file_type = each_res.search_result['file_type']['value']
            cur = {
                'augmentation': {'type': "", 'left_columns': [], 'right_columns':[]},
                'summary': parse_search_result(each_res),
                'score': each_res.score(),
                'metadata': metadata,
                'id': each_res.id(),
                'sample': sample_data,
                'materialize_info': materialize_info,
                'file_type': file_type
            }
            results.append(cur)

        json_return = dict()
        json_return["results"] = results
        return json.dumps(json_return, indent=2)

    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response(code='400', msg="FAIL SEARCH - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/download', methods=['POST'])
@cross_origin()
def download():
    try:
        _logger.debug("Start datamart downloading...")
        # check that each parameter meets the requirements
        search_result = read_file(request.files, 'task', 'json')
        # if not send the json via file
        if not search_result and request.values.get('task'):
            search_result = json.loads(request.values.get('task'))
        if search_result is None:
            return wrap_response(code='400',
                                 msg='FAIL SEARCH - Unable to get search result or input is a bad format!',
                                 data=None)
        try:
            request.files['format'].read().decode('UTF-8')
        except:
            return_format = check_return_format(request.values.get('format'))
        # if not get return format, set defauld as csv
        if return_format is None:
            return_format = "csv"
        if return_format != "csv" and return_format != "d3m":
            return wrap_response(code='400',
                                 msg='FAIL SEARCH - Unknown return format: ' + str(return_format),
                                 data=None)

        try:
            data_file = request.files.get('data')
        except:
            data_file = None
        data, loaded_dataset = load_input_supplied_data(request.values.get('data'), data_file)

        if loaded_dataset is None:
            return wrap_response(code='400',
                                 msg='FAIL SEARCH - Unable to load input supplied data',
                                 data=None)
        if request.values.get('run_wikifier'):
            need_wikifier = request.values.get('run_wikifier')
            if need_wikifier.lower() == "false":
                need_wikifier = False
            elif need_wikifier.lower() == "true":
                need_wikifier = True
            else:
                _logger.error("Unknown value for need_wikifier as " + str(need_wikifier))
                _logger.error("Will set need_wikifier with default value as True.")
                need_wikifier = True
        else:
            need_wikifier = True

        # search with supplied data
        # preprocess on loaded_dataset
        if need_wikifier:
            _logger.debug("Start running wikifier...")
            search_result_wikifier = DatamartSearchResult(search_result={}, supplied_data=None, query_json={},
                                                          search_type="wikifier")
            loaded_dataset = search_result_wikifier.augment(supplied_data=loaded_dataset)
            _logger.debug("Wikifier finished, start running download...")
        else:
            _logger.debug("Wikifier skipped, start running download...")

        search_result = DatamartSearchResult.deserialize(search_result['materialize_info'])
        download_result = search_result.download(supplied_data=loaded_dataset, run_wikifier=need_wikifier)
        _logger.debug("Download finished.")
        res_id, result_df = d3m_utils.get_tabular_resource(dataset=download_result, resource_id=None)

        non_empty_rows = []
        for i, v in result_df.iterrows():
            if len(v["joining_pairs"]) != 0:
                non_empty_rows.append(i)

        if len(non_empty_rows) == 0:
            return wrap_response(code='400',
                                 msg='FAIL DOWNLOAD - No joinable rows found!',
                                 data=None)
        _logger.debug("Start saving the download results...")
        result_df = result_df.iloc[non_empty_rows, :]
        result_df.reset_index(drop=True)
        # set all cells to be str so that we can save correctly
        download_result[res_id] = result_df.astype(str)
        # update structure type
        update_part = {"structural_type": str}
        for i in range(result_df.shape[1]):
            download_result.metadata = download_result.metadata.update(metadata=update_part,
                                                                       selector=(res_id, ALL_ELEMENTS, i))

        # update row length
        update_part = {"length": result_df.shape[0]}
        download_result.metadata = download_result.metadata.update(metadata=update_part, selector=(res_id,))

        result_id = str(hash(result_df.values.tobytes()))
        # save_dir = "/tmp/download_result" + result_id
        # if os.path.isdir(save_dir) or os.path.exists(save_dir):
        #     shutil.rmtree(save_dir)
        if return_format == "d3m":
            # save dataset
            with tempfile.TemporaryDirectory() as tmpdir:
                save_dir = os.path.join(str(tmpdir), result_id)
                absolute_path_part_length = len(str(save_dir))
                # print(save_dir)
                # sys.stdout.flush()
                download_result.save("file://" + save_dir + "/datasetDoc.json")
                # zip and send to client
                base_path = pathlib.Path(save_dir + '/')
                data = io.BytesIO()
                filePaths = retrieve_file_paths(save_dir)

                zip_file = zipfile.ZipFile(data, 'w')
                with zip_file:
                    # write each file seperately
                    for fileName in filePaths:
                        shorter_path = fileName[absolute_path_part_length:]
                        zip_file.write(fileName, shorter_path)
                data.seek(0)

                return send_file(
                    data,
                    mimetype='application/zip',
                    as_attachment=True,
                    attachment_filename='download_result' + result_id + '.zip'
                )

        else:
            data = io.StringIO()
            result_df.to_csv(data, index=False)
            return Response(data.getvalue(), mimetype="text/csv")

    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response(code='400', msg="FAIL SEARCH - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/download/<id>', methods=['GET'])
@cross_origin()
def download_by_id(id):
    datamart_id = id
    _logger.debug("Start downloading with id " + str(datamart_id))
    return_format = check_return_format(request.values.get('format'))
    if return_format is None:
        return_format = "original"
        # return wrap_response(code='400',
        #                      msg='FAIL SEARCH - Unknown return format: ' + str(return_format),
        #                      data=None)
    try:
        # general format datamart id
        if datamart_id.startswith("wikidata_search_on"):
            # wikidata search
            # wikidata_search_on___P1082___P2046___P571___with_column_FIPS_wikidata
            p_nodes = datamart_id.split("___")
            p_nodes = p_nodes[1: -1]
            materialize_info = {"p_nodes_needed": p_nodes}
            result_df = MaterializerCache.materialize(materialize_info, run_wikifier=False)

        else:  # len(datamart_id) == 8 and datamart_id[0] == "D":
            sparql_query = '''
                prefix ps: <http://www.wikidata.org/prop/statement/>
                prefix pq: <http://www.wikidata.org/prop/qualifier/>
                prefix p: <http://www.wikidata.org/prop/>
                SELECT distinct ?dataset ?title ?url ?file_type ?extra_information
                WHERE
                {
                  ?dataset p:C2001/ps:C2001 ?title .
                 filter regex(str(?title), "''' + datamart_id + '''").
                 ?dataset p:P2699/ps:P2699 ?url.
                 ?dataset p:P2701/ps:P2701 ?file_type.
                 ?dataset p:C2010/ps:C2010 ?extra_information.
                }
            '''
            sparql = SPARQLWrapper(DATAMART_SERVER)
            sparql.setQuery(sparql_query)
            sparql.setReturnFormat(JSON)
            sparql.setMethod(POST)
            sparql.setRequestMethod(URLENCODED)
            results = sparql.query().convert()['results']['bindings']
            _logger.debug("Totally " + str(len(results)) + " results found with given id.")
            if len(results) == 0:
                return wrap_response('400', msg="Can't find corresponding dataset with given id.")
            _logger.debug("Start materialize the dataset...")
            result = MaterializerCache.materialize(metadata=results[0], run_wikifier=False)
            original_file_type = results[0]['file_type']['value']
            original_file_name = results[0]['url']['value'].split("/")[-1]
            _logger.debug("result original format is {}".format(original_file_type))
        # else:
        # return wrap_response('400', msg="FAIL MATERIALIZE - Unknown input id format.")

        _logger.debug("Materialize finished, start sending...")
        if isinstance(result, pd.DataFrame):
            result_id = str(hash(result.values.tobytes()))
        else:
            hash_generator = hashlib.md5()
            hash_generator.update(str(result).encode('utf-8'))
            result_id = hash_generator.hexdigest()

        save_dir = "/tmp/download_result" + result_id
        if os.path.isdir(save_dir) or os.path.exists(save_dir):
            shutil.rmtree(save_dir)

        if "csv" in original_file_type:
            if return_format == "d3m":
                # save dataset
                d3m_df = d3m_DataFrame(result, generate_metadata=False)
                resources = {AUGMENT_RESOURCE_ID: d3m_df}
                return_ds = d3m_Dataset(resources=resources, generate_metadata=False)
                return_ds.metadata = return_ds.metadata.clear(source="", for_value=return_ds, generate_metadata=True)
                metadata_all_level = {
                    "id": datamart_id,
                    "version": "2.0",
                    "name": "datamart_dataset_" + datamart_id,
                    # "location_uris":('file:///tmp/datasetDoc.json',),
                    "digest": "",
                    "description": "",
                    "source": {'license': 'Other'},
                }
                return_ds.metadata = return_ds.metadata.update(metadata=metadata_all_level, selector=())
                # update structure type
                update_part = {"structural_type": str}
                for i in range(result.shape[1]):
                    return_ds.metadata = return_ds.metadata.update(metadata=update_part,
                                                                   selector=(AUGMENT_RESOURCE_ID, ALL_ELEMENTS, i))

                with tempfile.TemporaryDirectory() as tmpdir:
                    save_dir = os.path.join(str(tmpdir), result_id)
                    absolute_path_part_length = len(str(save_dir))
                    # print(save_dir)
                    # sys.stdout.flush()
                    return_ds.save("file://" + save_dir + "/datasetDoc.json")
                    # zip and send to client
                    base_path = pathlib.Path(save_dir + '/')
                    data = io.BytesIO()
                    filePaths = retrieve_file_paths(save_dir)

                    zip_file = zipfile.ZipFile(data, 'w')
                    with zip_file:
                        # write each file seperately
                        for fileName in filePaths:
                            shorter_path = fileName[absolute_path_part_length:]
                            zip_file.write(fileName, shorter_path)
                    data.seek(0)

                    return send_file(
                        data,
                        mimetype='application/zip',
                        as_attachment=True,
                        attachment_filename=datamart_id + '.zip'
                    )

            elif return_format == "csv":
                data = io.StringIO()
                result.to_csv(data, index=False)
                return Response(data.getvalue(), mimetype="text/csv")
        else:
            _logger.warning("Non csv file detected, will only return the original content.")
            return send_file(io.BytesIO(result), 
                             mimetype="application/x-binary", 
                             as_attachment=True,
                             attachment_filename=original_file_name)

    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response('400', msg="FAIL MATERIALIZE - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/download_metadata/<id>', methods=['GET'])
@cross_origin()
def download_metadata_by_id(id):
    datamart_id = id
    _logger.debug("Start downloading metadata with id " + str(datamart_id))
    try:
        # general format datamart id
        if datamart_id.startswith("wikidata_search_on"):
            # wikidata search
            # wikidata_search_on___P1082___P2046___P571___with_column_FIPS_wikidata
            p_nodes = datamart_id.split("___")
            target_q_node = "_".join(p_nodes[-1].split('_')[2:])
            p_nodes = p_nodes[1: -1]
            search_result = {"p_nodes_needed": p_nodes, "target_q_node_column_name": target_q_node}
            _logger.debug("Start searching the metadata for wikidata...")
            metadata = DatamartSearchResult(search_result=search_result, supplied_data=None, query_json={},
                                                          search_type="wikidata").get_metadata()

        else:
            #  len(datamart_id) == 8 and datamart_id[0] == "D":
            sparql_query = '''
                prefix ps: <http://www.wikidata.org/prop/statement/>
                prefix pq: <http://www.wikidata.org/prop/qualifier/>
                prefix p: <http://www.wikidata.org/prop/>
                SELECT distinct ?dataset ?datasetLabel ?title ?url ?file_type ?extra_information
                WHERE
                {
                 ?dataset rdfs:label ?datasetLabel.
                 ?dataset p:C2001/ps:C2001 ?title .
                 filter regex(str(?title), "''' + datamart_id + '''").
                 ?dataset p:P2699/ps:P2699 ?url.
                 ?dataset p:P2701/ps:P2701 ?file_type.
                 ?dataset p:C2010/ps:C2010 ?extra_information.
                }
            '''
            sparql = SPARQLWrapper(DATAMART_SERVER)
            sparql.setQuery(sparql_query)
            sparql.setReturnFormat(JSON)
            sparql.setMethod(POST)
            sparql.setRequestMethod(URLENCODED)
            results = sparql.query().convert()['results']['bindings']
            _logger.debug("Totally " + str(len(results)) + " results found with given id.")
            if len(results) == 0:
                return wrap_response('400', msg="Can't find corresponding dataset with given id.")
            _logger.debug("Start searching the metadata for general..")
            results[0]['score'] = {"value": 0}
            metadata = DatamartSearchResult(search_result=results[0], supplied_data=None, query_json={},
                                            search_type="general").get_metadata()

        _logger.debug("Searching metadata finished...")
        # update metadata
        metadata_all_level = {
            "id": datamart_id,
            "version": "2.0",
            "name": "datamart_dataset_" + datamart_id,
            "digest": "",
            "description": "",
            "source": {'license': 'Other'},
        }
        metadata = metadata.update(metadata=metadata_all_level, selector=())
        return json.dumps(metadata.to_json_structure(), indent=2)
    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response('400', msg="FAIL MATERIALIZE - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/augment', methods=['POST'])
@cross_origin()
def augment():
    try:
        _logger.debug("Start running augment...")
        # check that each parameter meets the requirements
        try:
            search_result = json.loads(request.files['task'].read().decode('UTF-8'))
        except:
            search_result = json.loads(request.values.get('task')) if request.values.get('task') else None
        if search_result is None:
            return wrap_response(code='400',
                                 msg='FAIL SEARCH - Unable to get search result or input is a bad format!',
                                 data=None)

        if request.values.get('use_cache'):
            use_cache = request.values.get('use_cache')
            if use_cache.lower() == "false":
                use_cache = False
            elif use_cache.lower() == "true":
                use_cache = True
            else:
                use_cache = None
                _logger.warning("Unknown value for use_cache as " + str(use_cache))
        else:
            use_cache = None
            _logger.info("use_cache value not detected")

        return_format = request.values.get('format')
        # if not get return format, set defauld as csv
        if return_format is None:
            return_format = "d3m"
        else:
            return_format = check_return_format(return_format)
        if not return_format:
            return wrap_response(code='400',
                                 msg='FAIL SEARCH - Unknown return format: ' + str(return_format),
                                 data=None)

        _logger.info("The requested download format is " + return_format)

        try:
            data_file = request.files.get('data')
        except:
            data_file = None
        data, loaded_dataset = load_input_supplied_data(request.values.get('data'), data_file)

        if loaded_dataset is None:
            return wrap_response(code='400',
                                 msg='FAIL SEARCH - Unable to load input supplied data',
                                 data=None)

        try:
            columns = request.files['columns'].read().decode('UTF-8')
            if columns == "" or columns == "[]":
                columns = None
        except:
            columns = request.values.get('columns')
        if columns and type(columns) is not list:
            columns = columns.split(",")
            _logger.info("Required columns found as: " + str(columns))
        columns_formated = []
        if columns:
            for each in columns:
                columns_formated.append(DatasetColumn(resource_id=AUGMENT_RESOURCE_ID, column_index=int(each)))

        destination = request.values.get('destination')

        if request.values.get('run_wikifier'):
            need_wikifier = request.values.get('run_wikifier')
            if need_wikifier.lower() == "false":
                need_wikifier = False
            elif need_wikifier.lower() == "true":
                need_wikifier = True
            else:
                _logger.error("Unknown value for need_wikifier as " + str(need_wikifier))
                _logger.error("Will set need_wikifier with default value as True.")
                need_wikifier = True
        else:
            need_wikifier = True

        if need_wikifier:
            _logger.debug("Start running wikifier...")
            search_result_wikifier = DatamartSearchResult(search_result={}, 
                                                          supplied_data=None, 
                                                          query_json={},
                                                          search_type="wikifier")
            loaded_dataset = search_result_wikifier.augment(supplied_data=loaded_dataset, 
                                                            use_cache=use_cache)
            _logger.debug("Wikifier finished, start running download...")
        else:
            _logger.debug("Wikifier skipped, start running download...")

        search_result = DatamartSearchResult.deserialize(search_result['materialize_info'])
        augment_result = search_result.augment(supplied_data=loaded_dataset, 
                                               augment_columns=columns_formated, 
                                               use_cache=use_cache)

        # if get string here, it means augment failed
        if isinstance(augment_result, str):
            return wrap_response(code='400',
                                 msg=augment_result)

        res_id, result_df = d3m_utils.get_tabular_resource(dataset=augment_result, resource_id=None)
        augment_result[res_id] = result_df.astype(str)

        # update structural type
        update_part = {"structural_type": str}
        for i in range(result_df.shape[1]):
            augment_result.metadata = augment_result.metadata.update(metadata=update_part,
                                                                     selector=(res_id, ALL_ELEMENTS, i))

        result_id = str(hash(result_df.values.tobytes()))
        # if required to store in disk and return the path
        if destination:
            _logger.info("Saving to a given destination required.")
            save_dir = os.path.join(destination, "augment_result" + result_id)
            if os.path.isdir(save_dir) or os.path.exists(save_dir):
                shutil.rmtree(save_dir)
            # save dataset
            augment_result.save("file://" + save_dir + "/datasetDoc.json")
            # zip and send to client
            base_path = pathlib.Path(save_dir + '/')
            data = io.BytesIO()
            filePaths = retrieve_file_paths(save_dir)
            # print('The following list of files will be zipped:')
            for fileName in filePaths:
                # print(fileName)
                zip_file = zipfile.ZipFile(data, 'w')
            with zip_file:
                # write each file seperately
                for file in filePaths:
                    zip_file.write(file)
            data.seek(0)

            return wrap_response(code='200',
                                 msg='Success',
                                 data=save_dir)
        else:
            # save dataset in temp directory
            _logger.info("Return the augment result directly required.")
            if return_format == "d3m":
                with tempfile.TemporaryDirectory() as tmpdir:
                    save_dir = os.path.join(str(tmpdir), result_id)
                    absolute_path_part_length = len(str(save_dir))
                    # print(save_dir)
                    # sys.stdout.flush()
                    augment_result.save("file://" + save_dir + "/datasetDoc.json")
                    # zip and send to client
                    base_path = pathlib.Path(save_dir + '/')
                    data = io.BytesIO()
                    filePaths = retrieve_file_paths(save_dir)

                    zip_file = zipfile.ZipFile(data, 'w')
                    with zip_file:
                        # write each file seperately
                        for fileName in filePaths:
                            shorter_path = fileName[absolute_path_part_length:]
                            zip_file.write(fileName, shorter_path)
                    data.seek(0)

                    return send_file(
                        data,
                        mimetype='application/zip',
                        as_attachment=True,
                        attachment_filename='download_result' + result_id + '.zip'
                    )
            else:
                data = io.StringIO()
                result_df.to_csv(data, index=False)
                return Response(data.getvalue(), mimetype="text/csv")

    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response(code='400', msg="FAIL SEARCH - %s \n %s" % (str(e), str(traceback.format_exc())))

# get_identifiers and get_properties are wrapped original from minds03.isi.edu:4444's wikifier
@app.route('/get_identifiers', methods=['POST'])
@cross_origin()
def get_identifiers():
    _logger.debug("Start running wikifier identifier...")
    request_data = json.loads(request.data)
    ids = request_data['ids'] if 'ids' in request_data.keys() else {}
    _logger.info("Totally " + str(len(ids)) + " ids received.")
    # Check empty
    if not ids:
        return {}
    start_time = time.time()
    data = REDIS_MANAGER.getKeys(keys=ids, prefix="identifiers:")
    _logger.debug("Identifier totally running used " + str(time.time() - start_time) + " seconds.")
    return_data = dict()
    for key in data:
        return_data[key] = list(data[key])

    response = app.response_class(
        response=json.dumps(return_data),
        status=200,
        mimetype='application/json'
    )
    return response


@app.route('/get_properties', methods=['POST'])
@cross_origin()
def get_properties():
    request_data = json.loads(request.data)
    property_map = REDIS_MANAGER.getKeys(request_data, "propall:")
    data = dict()
    for key in property_map:
        data[key] = list(property_map[key])
    response = app.response_class(
        response = json.dumps(data),
        status=200,
        mimetype='application/json'
    )   
    return response


@app.route('/upload/add_upload_user', methods=['POST'])
@cross_origin()
def add_upload_user():
    _logger.debug("Start adding upload user")
    try:
        token = request.values.get('token')
        username = request.values.get('username')
        password = request.values.get('password')
        if username is None or password is None:
            return wrap_response(code='400',
                                 msg="FAIL ADD USER - username and password can't be empty!",
                                 data=None)

        if not os.path.exists(password_token_file):
            _logger.error("No password config file found!")
            return wrap_response(code='400',
                                 msg="FAIL ADD USER - can't load token file!, please contact the adiministrator!",
                                 data=None)
        with open(password_token_file, 'r') as f:
            password_tokens = json.load(f)

        if token not in password_tokens:
            return wrap_response(code='400',
                                 msg='FAIL ADD USER - invalid token!',
                                 data=None)

        if not os.path.exists(password_record_file):
            _logger.error("No password config file found!")
            return wrap_response(code='400',
                                 msg="FAIL ADD USER - can't load the password config file, please contact the adiministrator!",
                                 data=None)

        with open(password_record_file, "r") as f:
            user_passwd_pairs = json.load(f)

        if username in user_passwd_pairs:
            return wrap_response(code='400',
                                 msg="FAIL ADD USER - username already exist!",
                                 data=None)

        current_group_information = password_tokens[token]
        # user_information['username'] = username
        user_information = dict()
        user_information['password_token'] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user_information['group'] = current_group_information['group']
        user_passwd_pairs[username] = user_information
        with open(password_record_file, 'w') as f:
            password_tokens = json.dump(user_passwd_pairs, f)

        return wrap_response('200', msg="Add user {} success!".format(username))

    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response('400', msg="FAIL ADD USER - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/upload', methods=['POST'])
@cross_origin()
def upload():
    return upload_function(request, test_mode=False)


@app.route('/upload/test', methods=['POST'])
@cross_origin()
def upload_test():
    # same as upload function, only difference is it will 
    # upload the dataset to a testing blazegraph namespace
    return upload_function(request, test_mode=True)


def upload_function(request, test_mode=False):
    """
    detail upload function,
    """
    _logger.debug("Start uploading in one step...")
    # start_time = time.time()
    try:
        url = request.values.get('url')
        upload_body = request.files.get("upload_file")

        if url is None and upload_body is None:
            return wrap_response(code='400',
                                 msg='FAIL UPLOAD - Url and upload file cannot both be None',
                                 data=None)

        if upload_body is not None and url is not None:
            return wrap_response(code='400',
                                 msg='FAIL UPLOAD - cannot send both url and upload file',
                                 data=None)
        
        file_type = request.values.get('file_type')
        if file_type is None:
            return wrap_response(code='400',
                                 msg='FAIL UPLOAD - file_type can not be None',
                                 data=None)

        upload_username = request.values.get('username')
        upload_password = request.values.get('password')
        if upload_username is None or upload_password is None:
            return wrap_response(code='400',
                                 msg='FAIL UPLOAD - upload username and password can not be None',
                                 data=None)

        # check username and password
        password_record_file = "../datamart_isi/upload/upload_password_config.json"
        if not os.path.exists(password_record_file):
            _logger.error("No password config file found!")
            return wrap_response(code='400',
                                 msg="FAIL UPLOAD - can't load the password config file, please contact the adiministrator!",
                                 data=None)

        with open(password_record_file ,"r") as f:
            user_passwd_pairs = json.load(f)

        if upload_username not in user_passwd_pairs:
            return wrap_response(code='400',
                                 msg='FAIL UPLOAD - username does not exist',
                                 data=None)
        else:
            is_correct_password = bcrypt.checkpw(upload_password.encode(), user_passwd_pairs[upload_username]["password_token"].encode())
            if not is_correct_password:
                return wrap_response(code='400',
                                     msg='FAIL UPLOAD - wrong password',
                                     data=None)

        if request.values.get('upload_async'):
            upload_async = request.values.get('upload_async')
            if upload_async.lower() == "false":
                upload_async = False
            elif upload_async.lower() == "true":
                upload_async = True
            else:
                upload_async = True
                _logger.warning("Unknown value for upload_async as {}, use default as True" + str(upload_async))
        else:
            upload_async = True
            _logger.info("upload_async value not detected, use default as True")

        need_process_columns_parsed = []
        need_process_columns = request.values.get('need_process_columns')
        if need_process_columns is not None:
            need_process_columns_all = need_process_columns.split("||")
            for each in need_process_columns_all:
                each_need_process_columns = each.split(",")
                if len(each_need_process_columns) == 1 and each_need_process_columns[0].lower() == "none":
                    each_need_process_columns = None
                else:
                    for i in range(len(each_need_process_columns)):
                        each_need_process_columns[i] = int(each_need_process_columns[i].lstrip())
                need_process_columns_parsed.append(each_need_process_columns)

        if upload_body is not None:
            datasets_store_loc = os.path.join(config_datamart.cache_file_storage_base_loc, "datasets_uploads")
            if not os.path.exists(datasets_store_loc):
                os.mkdir(datasets_store_loc)
            _logger.debug("Start saving the dataset {} from post body to {}...".format(upload_body.filename, datasets_store_loc))
            file_loc = os.path.join(datasets_store_loc, upload_body.filename)
            upload_body.save(file_loc)
            service_path = config_services.get_host_port_path("isi_datamart")
            url = os.path.join(service_path[0] + "://" + service_path[1] + ":" + str(service_path[2]), "upload/local_datasets", upload_body.filename)
            _logger.debug("Save the dataset finished at {} with url {}".format(datasets_store_loc, url))

        wikifier_choice = request.values.get('run_wikifier')
        if wikifier_choice is None:
            wikifier_choice = "auto"

        user_passwd_pairs[upload_username]["username"] = upload_username
        user_passwd_pairs[upload_username].pop("password_token")
        title = request.values.get('title').split("||") if request.values.get('title') else None
        description = request.values.get('description').split("||") if request.values.get('description') else None
        keywords = request.values.get('keywords').split("||") if request.values.get('keywords') else None

        # start uploading processes
        if not test_mode:
            server_address = DATAMART_SERVER
        else:
            server_address = DATAMART_TEST_SERVER
            
        dataset_information = {"url": url, 
                               "file_type": file_type, 
                               "title": title,
                               "description": description, 
                               "keywords": keywords,
                               "user_information": user_passwd_pairs[upload_username],
                               "wikifier_choice": wikifier_choice, 
                               "need_process_columns": need_process_columns_parsed,
                               }

        redis_host, redis_server_port = connection.get_redis_host_port()
        pool = redis.ConnectionPool(db=0, host=redis_host, port=redis_server_port)
        redis_conn = redis.Redis(connection_pool=pool)

        # if not get redis server, try to run locally
        if not upload_async or not is_redis_available(redis_conn):
            _logger.warning("Redis server not respond! Can't run in asyn mode!!")
            response_msg = upload_to_datamart(server_address, dataset_information)
            if response_msg.startswith("FAIL"):
                return wrap_response('400', msg=response_msg)
            else:
                return wrap_response('200', msg=response_msg)

        else:
            # use rq to schedule a job running asynchronously
            rq_queue = Queue(connection=redis_conn)
            job = rq_queue.enqueue(upload_to_datamart,
                                   args=(server_address, dataset_information,),
                                   # no timeout for job, result expire after 1 day
                                   job_timeout=-1, result_ttl=86400
                                   )
            job_id = job.get_id()
            # waif for 1 seconds to ensure the initialization finished
            time.sleep(1)
            job.refresh()
            job_status = job.get_status()
            return wrap_response('200', msg="UPLOAD job schedule succeed! The job id is: " + str(job_id) + " Current status is: " + str(job_status))
        # END uploading codes

    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response('400', msg="FAIL UPLOAD job - %s \n %s" % (str(e), str(traceback.format_exc())))



@app.route('/upload/local_datasets/<dataset_name>', methods=['GET'])
@cross_origin()
def get_local_datasets(dataset_name):
    """
    This function is used to work as a dummy http server that enable to generate a url for the dataset in local disks
    can also used for supporting the datasets user uploaded directly (in the future)
    """
    try:
        datasets_store_loc = os.path.join(config_datamart.cache_file_storage_base_loc, "datasets_uploads")
        if not os.path.exists(datasets_store_loc):
            os.mkdir(datasets_store_loc)
        _logger.debug("Start getting the dataset from local storage {}...".format(datasets_store_loc))

        datasets_loc = os.path.join(datasets_store_loc, dataset_name)
        if not os.path.exists(datasets_loc):
            _logger.error("File {} not exists!".format(dataset_name))
            return wrap_response('400', msg="File {} not exists!".format(dataset_name))

        with open(datasets_loc, 'rb') as f:
            file_content = f.read()
        return Response(file_content, mimetype="multipart/form-data")

    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response('400', msg="FAIL get local datasets - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/upload/generateWD+Metadata', methods=['POST'])
@cross_origin()
def load_and_process():
    _logger.debug("Start loading and process the upload data")
    try:
        url = request.values.get('url')
        if url is None:
            return wrap_response(code='400',
                                 msg='FAIL SEARCH - Url can not be None',
                                 data=None)

        file_type = request.values.get('file_type')
        if file_type is None:
            return wrap_response(code='400',
                                 msg='FAIL SEARCH - file_type can not be None',
                                 data=None)

        df, meta = datamart_upload_instance.load_and_preprocess(input_dir=url, file_type=file_type)
        df_returned = []
        for each in df:
            data = io.StringIO()
            each.to_csv(data, index=False)
            df_returned.append(data.getvalue())
        # return wrap_response('200', data=(df_returned, meta))
        return json.dumps({"data": df_returned, "metadata": meta}, indent=2)
    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response('400', msg="FAIL LOAD/ PREPROCESS - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/upload/uploadWD+Metadata', methods=['POST'])
@cross_origin()
def upload_metadata():
    _logger.debug("Start uploading...")
    try:
        if request.values.get('metadata'):
            metadata = request.values.get('metadata')
            metadata_json = json.loads(metadata)
        else:
            return wrap_response('400', msg="FAIL UPLOAD - No metadata input found")

        if request.values.get('data_input'):
            data_input = request.values.get('data_input')
            data_input = json.loads(data_input)
        else:
            return wrap_response('400', msg="FAIL UPLOAD - No dataset input found")

        data_df = []
        for di in data_input:
            if di[-1] == "\n":
                di = di[:-1]
            loaded_data = io.StringIO(di)
            data_df.append(pd.read_csv(loaded_data, converters=StringConverter()))

        if request.values.get('dataset_number'):
            dataset_number = request.values.get('dataset_number')
        else:
            dataset_number = 0

        datamart_upload_instance.model_data(data_df, metadata_json, dataset_number)
        response_id = datamart_upload_instance.upload()

        return wrap_response('200', msg="UPLOAD Success! The uploadted dataset id is:" + response_id)
    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response('400', msg="FAIL LOAD/ PREPROCESS - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/upload/check_upload_status', methods=['POST'])
@cross_origin()
def check_upload_status():
    try:
        _logger.debug("Start checking upload status...")
        redis_host, redis_server_port = connection.get_redis_host_port()
        pool = redis.ConnectionPool(db=0, host=redis_host, port=redis_server_port)
        redis_conn = redis.Redis(connection_pool=pool)
        job_ids = request.values.get("job_ids") if request.values.get("job_ids") else None

        # if user specify the job id
        if job_ids:
            job_status = {}
            job_ids = job_ids.replace(" ","").split(",")
            for each_job_id in job_ids:
                if rq.job.Job.exists(each_job_id, redis_conn):
                    current_job = rq.job.Job(each_job_id, redis_conn)
                    current_job.refresh()
                    current_status = current_job.meta
                    job_status[each_job_id] = current_status
                else:
                    job_status[each_job_id] = "Job does not exist!"

        # if not job id given, get all status of the workers
        else:
            job_status = {}
            workers = rq.Worker.all(connection=redis_conn)
            job_status['worker amount'] = len(workers)
            for i, each_worker in enumerate(workers):
                each_worker_status = {}
                each_worker_status['state'] = each_worker.state
                if each_worker_status['state'] != "idle":
                    current_job = each_worker.get_current_job()
                    each_worker_status['running_job_id'] = str(current_job.id)
                    each_worker_status['started_at'] = str(current_job.started_at)
                    current_job.refresh()
                    each_worker_status['meta'] = current_job.meta
                job_status["worker_" + str(i)] = each_worker_status
        return wrap_response(code='200',
                             msg='Success',
                             data=json.dumps(job_status, indent=2)
        )
    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response(code='400', msg="FAIL SEARCH - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/embeddings/fb/<qnode>', methods=['GET'])
@cross_origin()
def fetch_fb_embeddings(qnode):
    qnodes = qnode.split(',')
    qnode_uris = [wikidata_uri_template.format(qnode.upper().strip()) for qnode in qnodes]

    query = {
        'query': {
            'terms': {
                'key.keyword': qnode_uris
            }
        },
        "size": len(qnode_uris)
    }

    url = '{}/_search'.format(em_es_url)
    resp = requests.get(url, json=query)
    result_csv = ""
    if resp.status_code == 200:
        result = resp.json()
        hits = result['hits']['hits']
        for hit in hits:
            source = hit['_source']
            _qnode = source['key'].split('/')[-1][:-1]
            result_csv += '{}'.format(_qnode)

            for i in range(len(source['value'])):
                if i % 20 == 0:
                    result_csv += '\n'
                if i == len(source['value']) - 1:
                    result_csv += '{}'.format(source['value'][i])
                else:
                    result_csv += '{},'.format(source['value'][i])
            result_csv += '\n\n'

        return Response(result_csv, mimetype="text/csv")

    return None


@app.route('/keywords_augmentation/<string:keywords>', methods=['GET'])
@cross_origin()
def keywords_augmentation(keywords):
    """
        (original project link: https://github.com/usc-isi-i2/data-label-augmentation/tree/mint-fuzzy)
        use fuzzy search to augment input keywords to increase the possiblity to hit
        inputs: a list of keywords, separate by comma ","
        returns: a list of augmented keywords, separate by comma ","
    """
    try:
        keywords = list(map(lambda x: x.strip(), keywords.split(',')))
        _logger.info("Original keywords are: {}".format(str(keywords)))
        if FUZZY_SEARCH_CORE is not None:
            augmented_res = FUZZY_SEARCH_CORE.get_word_map(keywords)
            new_keywords = []
            for original_keywords, v in augmented_res.items():
                new_keywords.append(original_keywords)
                for extra_keywords in v.keys():
                    new_keywords.append(extra_keywords)
            _logger.info("Augmented keywords are: {}".format(str(new_keywords)))

        else:
            _logger.warning("Keywords augmentation core not loaded! Can't augment.")
            new_keywords = keywords
        return wrap_response(code='200', msg=",".join(new_keywords))

    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response(code='400', msg="FAIL SEARCH - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/fuzzy_search/search', methods=['POST'])
@cross_origin()
def fyzzy_search_without_data():
    try:
        _logger.debug("Start running fuzzy search without supplied data...")
        # check that each parameter meets the requirements
        query = read_file(request.values, 'query', 'json')
        # if not send the json via file
        if not query and request.form.get('query_json'):
            query = json.loads(request.form.get('query_json'))
        if not query and request.files.get("query"):
            query = json.load(request.files.get('query'))
        if not query and request.json:
            query = request.json
        max_return_docs = int(request.values.get('max_return_docs')) if request.values.get('max_return_docs') else 20

        if query:
            keywords = query.get("keywords", [])
            geospatial_names = query.get("geospatial_names", [])
            if geospatial_names is None:
                geospatial_names = []
        else:
            return wrap_response(code='400', msg="FAIL SEARCH - No query given, can't search.")

        keywords = clean_list_of_words(keywords)
        geospatial_names = clean_list_of_words(geospatial_names)

        _logger.debug("The search's keywords are: {}".format(str(keywords)))
        _logger.debug("The search's geospatial_names are: {}".format(str(geospatial_names)))
        _logger.debug("The search's return docs amount is: {}".format(str(max_return_docs)))
        # END processing inputs

        # start query in datamart
        query_wrapped = {"keywords_search": keywords, "variables": {"values": " ".join(geospatial_names)}}
        _logger.debug("Starting datamart search service...")
        datamart_search_unit = Augment()
        res = datamart_search_unit.query_by_sparql(query=query_wrapped, dataset="dummy")
        _logger.debug("Search finished, totally find " + str(len(res)) + " results.")

        # parse the search results
        results = []
        for each_res in res:
            extra_information = json.loads(each_res['extra_information']['value'])
            metadata = {}
            for k, v in extra_information.items():
                if "meta" in k:
                    metadata[k] = v
            data_metadata = extra_information
            file_type = each_res['file_type']['value']
            if file_type != "other":
                sample_data = extra_information['first_10_rows']
            else:
                sample_data = ""
            cur = {
                'id': each_res['datasetLabel']['value'],
                'score': float(each_res['score']['value']),
                'type': each_res['file_type']['value'],
                'metadata': metadata,
                'sample_data': sample_data,
            }
            results.append(cur)

        json_return = dict()
        json_return["results"] = results
        return json.dumps(json_return, indent=2)

    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response(code='400', msg="FAIL SEARCH - %s \n %s" % (str(e), str(traceback.format_exc())))


def clean_list_of_words(input_words: typing.List[str]) -> typing.List[str]:
    # remove empty and duplicate keywords, then return the sorted result
    words_set = set(input_words)
    if "" in words_set:
        words_set.remove("")
    if " " in words_set:
        words_set.remove(" ")
    output_words = [str(each) for each in words_set]
    output_words.sort()
    return output_words

def generate_dataset_metadata():
    '''
    Add D3M dataset metadata to cache
    '''
    print('Running generate_dataset_metadata')
    from datamart_isi.cache import metadata_cache
    import os
    import pathlib

    memcache_dir = pathlib.Path(config_datamart.cache_file_storage_base_loc) / 'datasets_cache'
    if not memcache_dir.exists():
        os.makedirs(memcache_dir)

    for path in dataset_paths:
        path = pathlib.Path(path)
        if path.exists:
            metadata_cache.MetadataCache.generate_real_metadata_files([str(path).lower()])
    print('Done generate_dataset_metadata')


if __name__ == '__main__':
    # generate_dataset_metadata()
    if hostname == "dsbox02":
        context = ('./certs/wildcard_isi.crt', './certs/wildcard_isi.key')
        app.run(host="0.0.0.0", port=9000, debug=False, ssl_context=context) 
    else:
        app.run(host="0.0.0.0", port=9000, debug=False)
