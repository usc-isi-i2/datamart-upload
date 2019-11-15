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
import socket
import inspect
import datetime
import frozendict
import rq
import bcrypt

from wikifier.wikifier import produce
from flask_cors import CORS, cross_origin
# sys.path.append(sys.path.append(os.path.join(os.path.dirname(__file__), '..')))
from d3m.base import utils as d3m_utils
from d3m.container import DataFrame as d3m_DataFrame
from d3m.container.dataset import Dataset as d3m_Dataset, D3MDatasetLoader
from d3m.metadata.base import ALL_ELEMENTS
from flask import Flask, request, send_file, Response, redirect
from datamart_isi import config as config_datamart
from datamart_isi.utilities import connection
from SPARQLWrapper import SPARQLWrapper, JSON, POST, URLENCODED
from datamart_isi import config_services
from datamart_isi.entries import Datamart, DatamartQuery, AUGMENT_RESOURCE_ID, DatamartSearchResult, DatasetColumn
from datamart_isi.upload.store import Datamart_isi_upload
from datamart_isi.utilities.utils import Utils
from datamart_isi.cache.metadata_cache import MetadataCache
from datamart_isi.upload.redis_manager import RedisManager
from datamart_isi.upload.dataset_upload_woker_process import upload_to_datamart
from flasgger import Swagger
from rq import Queue


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
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
# add the handler to the root logger
logging.getLogger('').addHandler(console)

em_es_url = connection.get_es_fb_embedding_server_url()
# em_es_url = config_datamart.em_es_url
# em_es_index = config_datamart.em_es_index
# em_es_type = config_datamart.em_es_type
wikidata_uri_template = '<http://www.wikidata.org/entity/{}>'
password_token_file = "../datamart_isi/upload/password_tokens.json"
password_record_file = "../datamart_isi/upload/upload_password_config.json"


dataset_paths = ["/data",  # for docker
                 "/nfs1/dsbox-repo/data/datasets/seed_datasets_data_augmentation",  # for dsbox server
                 "/nfs1/dsbox-repo/data/datasets/seed_datasets_current",  # for dsbox server
                 "/Users/minazuki/Desktop/studies/master/2018Summer/data/datasets/seed_datasets_data_augmentation"
                 ]
DATAMART_SERVER = connection.get_general_search_server_url()
DATAMART_TEST_SERVER = connection.get_general_search_test_server_url()
datamart_upload_instance = Datamart_isi_upload(update_server=DATAMART_SERVER,
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
    }, indent=2, default=lambda x: str(x))


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
    logger.debug("Trying to load dataset " + str(path))
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
    logger.debug("Load " + str(path) + " success!")
    return all_dataset


def load_csv_data(data) -> d3m_Dataset:
    """
    Function used to load general csv file to d3m format dataset
    :param data: a str or a pd.DataFrame
    :return: a d3m style Dataset
    """
    logger.debug("Trying to load csv data with first 100 characters as:")
    logger.debug(str(data[:10]))
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
        "version": "2.0",
        "name": "user given input from datamart userend",
        "location_uris": ('file:///tmp/datasetDoc.json',),
        "digest": "",
        "description": "",
        "source": {'license': 'Other'},
    }
    return_ds.metadata = return_ds.metadata.update(metadata=metadata_all_level, selector=())
    logger.debug("Loading csv and transform to d3m dataset format success!")
    return return_ds

def _load_file_with(read_format: str, tmpfile):
    try:
        if read_format == "zip": 
            # try to load as d3m dataset
            data = None
            destination = tempfile.mkdtemp(prefix='datamart_download_')
            zip = zipfile.ZipFile(tmpfile)
            zip.extractall(destination)
            loaded_dataset = d3m_Dataset.load('file://' + destination + '/datasetDoc.json')
            status = True

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

        logger.info("Loading {} as {} file success!".format(tmpfile, read_format))

    except Exception as e:
        loaded_dataset = None
        data = None
        logger.debug("Get error information " + str(e))
        logger.info("{} is not a valid {} file".format(tmpfile, read_format))
        status = False
    return status, data, loaded_dataset


def load_input_supplied_data(data_from_value, data_from_file):
    """
    function used to load the input data from different methods
    """
    if data_from_file:
        logger.debug("Detected a file from post body!")

        fd, tmpfile = tempfile.mkstemp(prefix='datamart_download_', suffix='.d3m.tmp')
        destination = None
        data_from_file.save(tmpfile)

        status, data, loaded_dataset = _load_file_with("zip", tmpfile)
        if not status:
            status, data, loaded_dataset = _load_file_with("pkl", tmpfile)
        if not status:
            status, data, loaded_dataset = _load_file_with("csv", tmpfile)
        if not status:
            logger.error("Loading dataset failed with all attempts!")

        # remove temp files
        os.close(fd)
        os.remove(tmpfile)
        if destination:
            shutil.rmtree(destination) 
                   
    elif data_from_value:
        data = None
        if data_from_value.lower().endswith(".csv"):
            logger.debug("csv file path detected!")
            loaded_dataset = load_csv_data(data_from_value)
        else:
            logger.debug("d3m path maybe?")
            loaded_dataset = load_d3m_dataset(data_from_value)
    else:
        data = None
        loaded_dataset = None
    return data, loaded_dataset


def check_return_format(format_):
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
    # also show on logger
    logger.error(error_message)
    logger.error(str(e))
    logger.error(str(traceback.format_exc()))


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
        logger.debug("Start running wikifier...")
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

        logger.info("The requested download format is " + return_format)

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
        logger.info("Required columns found as: " + str(columns_formated))
        logger.info("Wikifier choice is: " + str(choice))

        threshold = request.values.get("threshold")
        if not threshold:
            threshold = 0.7
        else:
            try:
                threshold = float(threshold)
            except:
                threshold = 0.7
        logger.info("Threshold for coverage is: " + str(threshold))

        logger.debug("Start changing dataset to dataframe...")
        # DA = load_d3m_dataset("DA_poverty_estimation")
        # MetadataCache.save_metadata_from_dataset(DA)
        # try to update with more correct metadata if possible
        updated_result = MetadataCache.check_and_get_dataset_real_metadata(loaded_dataset)
        if updated_result[0]:  # [0] store whether it success find the metadata
            loaded_dataset = updated_result[1]
        res_id, supplied_dataframe = d3m_utils.get_tabular_resource(dataset=loaded_dataset,
                                                                    resource_id=None, has_hyperparameter=False)
        output_ds = copy.copy(loaded_dataset)
        logger.debug("Start running wikifier...")
        wikifier_res = produce(inputs=supplied_dataframe, target_columns=columns_formated, target_p_nodes=None,
                               wikifier_choice=choice, threshold=threshold)
        logger.debug("Wikifier finished, Start to update metadata...")
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

        logger.info("Return the wikifier result.")
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
        return wrap_response(code='400', msg="FAIL SEARCH - %s \n %s" % (str(e), str(traceback.format_exc())))


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
                logger.error("Search failed! No path given or can't load dataset")
                return wrap_response(code='400',
                                     msg="""FAIL SEARCH - data is not given or can't load dataset, please run "/search_without_data" instead""",
                                     data=None)
            else:
                logger.error("Unable to load the input file with")
                logger.error(str(data))
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
                logger.error("Unknown value for need_wikifier as " + str(need_wikifier))
                logger.error("Will set need_wikifier with default value as True.")
                need_wikifier = True
        else:
            need_wikifier = True

        # start to search
        logger.debug("Starting datamart search service...")
        datamart_instance = Datamart(connection_url=config_datamart.default_datamart_url)

        if need_wikifier:
            meta_for_wikifier = None
            logger.debug("Start running wikifier...")
            # if a specific list of wikifier targets was sent (usually generated from ta2 system)
            if query and "keywords" in query.keys():
                for i, kw in enumerate(query["keywords"]):
                    if config_datamart.wikifier_column_mark in kw:
                        meta_for_wikifier = json.loads(query["keywords"].pop(i))[config_datamart.wikifier_column_mark]
                        break
                if meta_for_wikifier:
                    logger.info(
                        "Get specific column<->p_nodes relationship from user. Will only wikifier those columns!")
                    logger.info("The detail relationship is: {}".format(str(meta_for_wikifier)))
                    _, supplied_dataframe = d3m_utils.get_tabular_resource(dataset=loaded_dataset, resource_id=None)
                    MetadataCache.save_specific_wikifier_targets(supplied_dataframe, meta_for_wikifier)

            search_result_wikifier = DatamartSearchResult(search_result={}, supplied_data=None, query_json={},
                                                          search_type="wikifier")
            loaded_dataset = search_result_wikifier.augment(supplied_data=loaded_dataset)
            logger.debug("Wikifier finished, start running download...")
        else:
            logger.debug("Wikifier skipped, start running download...")

        if query:
            keywords = query.get("keywords", [])
            variables = query.get("variables", [])
        else:
            keywords: typing.List[str] = []
            variables: typing.List['VariableConstraint'] = []

        logger.debug("The search's keywords are: {}".format(str(keywords)))
        logger.debug("The search's variables are: {}".format(str(variables)))

        query_wrapped = DatamartQuery(keywords=keywords, variables=variables)
        res = datamart_instance.search_with_data(query=query_wrapped, supplied_data=loaded_dataset).get_next_page(
            limit=max_return_docs) or []
        logger.debug("Search finished, totally find " + str(len(res)) + " results.")
        results = []
        for i, r in enumerate(res):
            try:
                materialize_info = r.serialize()
                materialize_info_decoded = json.loads(materialize_info)
                augmentation_part = materialize_info_decoded['augmentation']
                cur = {
                    'augmentation': {'type': augmentation_part['properties'], 'left_columns': [augmentation_part['left_columns']], 'right_columns': [augmentation_part['right_columns']]},
                    'summary': parse_search_result(r),
                    'score': r.score(),
                    'metadata': r.get_metadata().to_json_structure(),
                    'id': r.id(),
                    'materialize_info': materialize_info
                }
                results.append(cur)

            except Exception as e:
                logger.error("Feteching No.{} result failed!".format(str(i)))
                self._logger.debug(e, exc_info=True)
            
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
        logger.debug("Start running search_without_data...")
        keywords = request.values.get("keywords").strip(',') if request.values.get("keywords") else None
        keywords_search: typing.List[str] = keywords.split(',') if keywords != None else []
        if request.data:
            variables = json.loads(str(request.data, "utf-8"))
            variables_search: dict() = variables['variables'] if variables != None else {}
            query_wrapped = DatamartQuery(keywords_search=keywords_search, variables_search=variables_search)
        else:
            query_wrapped = DatamartQuery(keywords_search=keywords_search)

        logger.debug("Starting datamart search service...")
        datamart_instance = Datamart(connection_url=config_datamart.default_datamart_url)
        res = datamart_instance.search(query=query_wrapped).get_next_page() or []
        logger.debug("Search finished, totally find " + str(len(res)) + " results.")
        results = []
        for r in res:
            cur = {
                "summary": parse_search_result(r),
                'score': r.score(),
                'metadata': r.get_metadata().to_json_structure(),
                'datamart_id': r.id(),
                'materialize_info': r.serialize()
            }
            results.append(cur)
        if not results:
            return wrap_response(code='200', msg="FAIL SEARCH - did not find the results")
        else:
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
        logger.debug("Start datamart downloading...")
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
                logger.error("Unknown value for need_wikifier as " + str(need_wikifier))
                logger.error("Will set need_wikifier with default value as True.")
                need_wikifier = True
        else:
            need_wikifier = True

        # search with supplied data
        # preprocess on loaded_dataset
        if need_wikifier:
            logger.debug("Start running wikifier...")
            search_result_wikifier = DatamartSearchResult(search_result={}, supplied_data=None, query_json={},
                                                          search_type="wikifier")
            loaded_dataset = search_result_wikifier.augment(supplied_data=loaded_dataset)
            logger.debug("Wikifier finished, start running download...")
        else:
            logger.debug("Wikifier skipped, start running download...")

        search_result = DatamartSearchResult.deserialize(search_result['materialize_info'])
        download_result = search_result.download(supplied_data=loaded_dataset, run_wikifier=need_wikifier)
        logger.debug("Download finished.")
        res_id, result_df = d3m_utils.get_tabular_resource(dataset=download_result, resource_id=None)

        non_empty_rows = []
        for i, v in result_df.iterrows():
            if len(v["joining_pairs"]) != 0:
                non_empty_rows.append(i)

        if len(non_empty_rows) == 0:
            return wrap_response(code='400',
                                 msg='FAIL DOWNLOAD - No joinable rows found!',
                                 data=None)
        logger.debug("Start saving the download results...")
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
    logger.debug("Start downloading with id " + str(datamart_id))
    return_format = check_return_format(request.values.get('format'))
    if return_format is None:
        return wrap_response(code='400',
                             msg='FAIL SEARCH - Unknown return format: ' + str(return_format),
                             data=None)
    try:
        # general format datamart id
        if datamart_id.startswith("wikidata_search_on"):
            # wikidata search
            # wikidata_search_on___P1082___P2046___P571___with_column_FIPS_wikidata
            p_nodes = datamart_id.split("___")
            p_nodes = p_nodes[1: -1]
            materialize_info = {"p_nodes_needed": p_nodes}
            result_df = Utils.materialize(materialize_info)

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
            logger.debug("Totally " + str(len(results)) + " results found with given id.")
            if len(results) == 0:
                return wrap_response('400', msg="Can't find corresponding dataset with given id.")
            logger.debug("Start materialize the dataset...")
            result_df = Utils.materialize(metadata=results[0])

        # else:
        # return wrap_response('400', msg="FAIL MATERIALIZE - Unknown input id format.")

        logger.debug("Materialize finished, start sending...")
        result_id = str(hash(result_df.values.tobytes()))
        save_dir = "/tmp/download_result" + result_id
        if os.path.isdir(save_dir) or os.path.exists(save_dir):
            shutil.rmtree(save_dir)

        if return_format == "d3m":
            # save dataset
            d3m_df = d3m_DataFrame(result_df, generate_metadata=False)
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
            for i in range(result_df.shape[1]):
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

        else:
            data = io.StringIO()
            result_df.to_csv(data, index=False)
            return Response(data.getvalue(), mimetype="text/csv")

    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response('400', msg="FAIL MATERIALIZE - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/download_metadata/<id>', methods=['GET'])
@cross_origin()
def download_metadata_by_id(id):
    datamart_id = id
    logger.debug("Start downloading metadata with id " + str(datamart_id))
    try:
        # general format datamart id
        if datamart_id.startswith("wikidata_search_on"):
            # wikidata search
            # wikidata_search_on___P1082___P2046___P571___with_column_FIPS_wikidata
            p_nodes = datamart_id.split("___")
            target_q_node = "_".join(p_nodes[-1].split('_')[2:])
            p_nodes = p_nodes[1: -1]
            search_result = {"p_nodes_needed": p_nodes, "target_q_node_column_name": target_q_node}
            logger.debug("Start searching the metadata for wikidata...")
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
            logger.debug("Totally " + str(len(results)) + " results found with given id.")
            if len(results) == 0:
                return wrap_response('400', msg="Can't find corresponding dataset with given id.")
            logger.debug("Start searching the metadata for general..")
            results[0]['score'] = {"value": 0}
            metadata = DatamartSearchResult(search_result=results[0], supplied_data=None, query_json={},
                                            search_type="general").get_metadata()

        logger.debug("Searching metadata finished...")
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
        logger.debug("Start running augment...")
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
                logger.warning("Unknown value for use_cache as " + str(use_cache))
        else:
            logger.info("use_cache value not detected")

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

        logger.info("The requested download format is " + return_format)

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
            logger.info("Required columns found as: " + str(columns))
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
                logger.error("Unknown value for need_wikifier as " + str(need_wikifier))
                logger.error("Will set need_wikifier with default value as True.")
                need_wikifier = True
        else:
            need_wikifier = True

        if need_wikifier:
            logger.debug("Start running wikifier...")
            search_result_wikifier = DatamartSearchResult(search_result={}, supplied_data=None, query_json={},
                                                          search_type="wikifier")
            loaded_dataset = search_result_wikifier.augment(supplied_data=loaded_dataset, use_cache=use_cache)
            logger.debug("Wikifier finished, start running download...")
        else:
            logger.debug("Wikifier skipped, start running download...")

        search_result = DatamartSearchResult.deserialize(search_result['materialize_info'])
        augment_result = search_result.augment(supplied_data=loaded_dataset, augment_columns=columns_formated)

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
            logger.info("Saving to a given destination required.")
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
            logger.info("Return the augment result directly required.")
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


@app.route('/get_identifiers', methods=['POST'])
@cross_origin()
def get_identifiers():
    logger.debug("Start running wikifier identifier...")
    request_data = json.loads(request.data)
    ids = request_data['ids'] if 'ids' in request_data.keys() else {}
    logger.info("Totally " + str(len(ids)) + " ids received.")
    # Check empty
    if not ids:
        return {}
    start_time = time.time()
    data = REDIS_MANAGER.getKeys(keys=ids, prefix="identifiers:")
    logger.debug("Identifier totally running used " + str(time.time() - start_time) + " seconds.")
    return_data = dict()
    for key in data:
        return_data[key] = list(data[key])

    response = app.response_class(
        response=json.dumps(return_data),
        status=200,
        mimetype='application/json'
    )
    return response


@app.route('/upload/add_upload_user', methods=['POST'])
@cross_origin()
def add_upload_user():
    logger.debug("Start adding upload user")
    try:
        token = request.values.get('token')
        username = request.values.get('username')
        password = request.values.get('password')
        if username is None or password is None:
            return wrap_response(code='400',
                                 msg="FAIL ADD USER - username and password can't be empty!",
                                 data=None)

        if not os.path.exists(password_token_file):
            logger.error("No password config file found!")
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
            logger.error("No password config file found!")
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
    upload_function(request, test_mode=False)


@app.route('/upload/test', methods=['POST'])
@cross_origin()
def upload_test():
    # save as upload function, only difference is it will upload the dataset to a testing blazegraph namespace
    upload_function(request, test_mode=True)


def upload_function(request, test_mode=False):
    """
    detail upload function,
    """
    logger.debug("Start uploading in one step...")
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
            logger.error("No password config file found!")
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

        if upload_body is not None:
            datasets_store_loc = os.path.join(config_datamart.cache_file_storage_base_loc, "datasets_uploads")
            if not os.path.exists(datasets_store_loc):
                os.mkdir(datasets_store_loc)
            logger.debug("Start saving the dataset {} from post body to {}...".format(upload_body.filename, datasets_store_loc))
            file_loc = os.path.join(datasets_store_loc, upload_body.filename)
            upload_body.save(file_loc)
            service_path = config_services.get_host_port_path("isi_datamart")
            url = os.path.join("http://" + service_path[0] + ":" + str(service_path[1]), "upload/local_datasets", upload_body.filename)
            logger.debug("Save the dataset finished at {}".format(url))

        wikifier_choice = request.values.get('run_wikifier')
        if wikifier_choice is None:
            wikifier_choice = "auto"

        user_passwd_pairs[upload_username]["username"] = upload_username
        user_passwd_pairs[upload_username].pop("password_token")
        title = request.values.get('title').split("||") if request.values.get('title') else None
        description = request.values.get('description').split("||") if request.values.get('description') else None
        keywords = request.values.get('keywords').split("||") if request.values.get('keywords') else None

        redis_host, redis_server_port = connection.get_redis_host_port()
        pool = redis.ConnectionPool(db=0, host=redis_host, port=redis_server_port)
        redis_conn = redis.Redis(connection_pool=pool)
        rq_queue = Queue(connection=redis_conn)
        dataset_information = {"url": url, "file_type": file_type, "title": title,
                               "description": description, "keywords": keywords,
                               "user_information": user_passwd_pairs[upload_username],
                               "wikifier_choice": wikifier_choice
                               }

        if not test_mode:
            server_address = DATAMART_SERVER
        else:
            server_address = DATAMART_TEST_SERVER

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
    except Exception as e:
        record_error_to_file(e, inspect.stack()[0][3])
        return wrap_response('400', msg="FAIL UPLOAD job schedule - %s \n %s" % (str(e), str(traceback.format_exc())))



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
        logger.debug("Start getting the dataset from local storage {}...".format(datasets_store_loc))

        datasets_loc = os.path.join(datasets_store_loc, dataset_name)
        if not os.path.exists(datasets_loc):
            logger.error("File {} not exists!".format(dataset_name))
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
    logger.debug("Start loading and process the upload data")
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
    logger.debug("Start uploading...")
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
        logger.debug("Start checking upload status...")
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
            metadata_cache.MetadataCache.generate_real_metadata_files([str(path)])
    print('Done generate_dataset_metadata')


if __name__ == '__main__':
    generate_dataset_metadata()
    hostname = socket.gethostname()
    if hostname == "dsbox02":
        context = ('./certs/wildcard_isi.crt', './certs/wildcard_isi.key')
        app.run(host="0.0.0.0", port=9000, debug=False, ssl_context=context) 
    else:
        app.run(host="0.0.0.0", port=9000, debug=False)
