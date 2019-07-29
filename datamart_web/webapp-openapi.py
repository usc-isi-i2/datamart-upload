import os
import json
import sys
import pandas as pd
import logging
import typing
import traceback
import shutil
import io
import zipfile
import tempfile
import pathlib
import logging
import requests
from flask_cors import CORS, cross_origin
# sys.path.append(sys.path.append(os.path.join(os.path.dirname(__file__), '..')))
from d3m.base import utils as d3m_utils
from d3m.container import DataFrame as d3m_DataFrame
from d3m.container.dataset import Dataset as d3m_Dataset, D3MDatasetLoader
from d3m.metadata.base import ALL_ELEMENTS
from flask import Flask, request, render_template, send_file, Response, redirect
from datamart_isi import config as config_datamart
from datamart_isi.utilities import connection
from SPARQLWrapper import SPARQLWrapper, JSON, POST, URLENCODED
from datamart_isi.entries import Datamart, DatamartQuery, VariableConstraint, AUGMENT_RESOURCE_ID, DatamartSearchResult, DatasetColumn
from datamart_isi.upload.store import Datamart_isi_upload
from datamart_isi.utilities.utils import Utils
from flasgger import Swagger

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

config = json.load(open('config.json'))
em_es_url = config['em_es_url']
em_es_index = config['em_es_index']
em_es_type = config['em_es_type']
wikidata_uri_template = '<http://www.wikidata.org/entity/{}>'

dataset_paths = ["/nfs1/dsbox-repo/data/datasets/seed_datasets_data_augmentation",  # for dsbox server using
                 "/nfs1/dsbox-repo/data/datasets/seed_datasets_current",  # for dsbox server using
                 "/data",  # for docker using
                 "/Users/minazuki/Desktop/studies/master/2018Summer/data/datasets/seed_datasets_data_augmentation"
                 ]
DATAMART_SERVER = connection.get_genearl_search_server_url(config_datamart.default_datamart_url)
datamart_upload_instance = Datamart_isi_upload(update_server=config['update_server'],
                                               query_server=config['update_server'])

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
        'message': msg or ('Success' if code == '0000' else 'Failed'),
        'data': data,
        **kwargs
    }, indent=2, default=lambda x: str(x))


def read_file(files, key, _type):
    if files and key in files:
        try:
            if _type == 'csv':
                return pd.read_csv(files[key], converters=StringConverter()).infer_objects()
            elif _type == 'json':
                return json.load(files[key])
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
    # if search_res.search_type == ""
    columns_result = columns_result.split(", ")
    score = str(search_res.score())
    # description = "test description"
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
    Function used to load d3m datasets
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
    Function used to load general csv file
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

def load_input_supplied_data(data_from_value, data_from_file):
    if data_from_file:
        logger.debug("Detected a file from post body!")
        data = pd.read_csv(data_from_file, converters=StringConverter()).infer_objects()
        loaded_dataset = load_csv_data(data)
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


@app.route('/')
def hello():
    return redirect('/apidocs')


@app.route('/search', methods=['POST'])
@cross_origin()
def search():
    try:
        # check that each parameter meets the requirements
        query = read_file(request.files, 'query', 'json')
        # if not send the json via file
        if not query and request.form.get('query_json'):
            query = json.loads(request.form.get('query_json'))
        max_return_docs = int(request.values.get('max_return_docs')) if request.values.get('max_return_docs') else 20

        try:
            data_file = request.files.get('data')
        except:
            data_file = None
        data, loaded_dataset = load_input_supplied_data(request.values.get('data'), data_file)

        if loaded_dataset is None:
            if data is None:
                logger.error("No path given")
                return wrap_response(code='1000',
                                     msg='FAIL SEARCH - data is not given, please run "/search_without_data" instead',
                                     data=None)
            else:
                logger.error("Unable to load the input file with")
                logger.error(str(data))
                return wrap_response(code='1000',
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
        keywords: typing.List[str] = []
        variables: typing.List['VariableConstraint'] = []
        query_wrapped = DatamartQuery(keywords=keywords, variables=variables)
        logger.debug("Starting datamart search service...")

        datamart_instance = Datamart(connection_url=config_datamart.default_datamart_url)
        if need_wikifier:
            logger.debug("Start running wikifier...")
            search_result_wikifier = DatamartSearchResult(search_result={}, supplied_data=None, query_json={},
                                                          search_type="wikifier")
            loaded_dataset = search_result_wikifier.augment(supplied_data=loaded_dataset)
            logger.debug("Wikifier finished, start running download...")
        else:
            logger.debug("Wikifier skipped, start running download...")

        res = datamart_instance.search_with_data(query=query_wrapped, supplied_data=loaded_dataset).get_next_page(
            limit=max_return_docs) or []
        logger.debug("Search finished, totally find " + str(len(res)) + " results.")
        results = []
        for r in res:
            cur = {
                'augmentation': {'type': 'join', 'left_columns': [[]], 'right_columns': [[]]},
                'summary': parse_search_result(r),
                'score': r.score(),
                'metadata': r.get_metadata().to_json_structure(),
                'id': r.id(),
                'materialize_info': r.serialize()
            }
            results.append(cur)
        json_return = dict()
        json_return["results"] = results
        # return wrap_response(code='0000',
        #                       msg='Success',
        #                       data=json.dumps(json_return, indent=2)
        #                       )
        return json.dumps(json_return, indent=2)

    except Exception as e:
        return wrap_response(code='1000', msg="FAIL SEARCH - %s \n %s" % (str(e), str(traceback.format_exc())))


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
            return wrap_response(code='0000', msg="FAIL SEARCH - did not find the results")
        else:
            json_return = dict()
            json_return["results"] = results
            return json.dumps(json_return, indent=2)

    except Exception as e:
        return wrap_response(code='1000', msg="FAIL SEARCH - %s \n %s" % (str(e), str(traceback.format_exc())))


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
            return wrap_response(code='1000',
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
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - Unknown return format: ' + str(return_format),
                                 data=None)

        try:
            data_file = request.files.get('data')
        except:
            data_file = None
        data, loaded_dataset = load_input_supplied_data(request.values.get('data'), data_file)

        if loaded_dataset is None:
            return wrap_response(code='1000',
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
        download_result = search_result.download(supplied_data=loaded_dataset)
        logger.debug("Download finished.")
        res_id, result_df = d3m_utils.get_tabular_resource(dataset=download_result, resource_id=None)

        non_empty_rows = []
        for i, v in result_df.iterrows():
            if len(v["joining_pairs"]) != 0:
                non_empty_rows.append(i)

        if len(non_empty_rows) == 0:
            return wrap_response(code='1000',
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
        return wrap_response(code='1000', msg="FAIL SEARCH - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/download/<id>', methods=['GET'])
@cross_origin()
def download_by_id(id):
    datamart_id = id
    logger.debug("Start downloading with id " + str(datamart_id))
    return_format = check_return_format(request.values.get('format'))
    if return_format is None:
        return wrap_response(code='1000',
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
                return wrap_response('1000', msg="Can't find corresponding dataset with given id.")
            logger.debug("Start materialize the dataset...")
            result_df = Utils.materialize(metadata=results[0])

        # else:
        # return wrap_response('1000', msg="FAIL MATERIALIZE - Unknown input id format.")

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
        return wrap_response('1000', msg="FAIL MATERIALIZE - %s \n %s" % (str(e), str(traceback.format_exc())))


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
            p_nodes = p_nodes[1: -1]
            materialize_info = {"p_nodes_needed": p_nodes}
            logger.debug("Start materialize the dataset for wikidata...")
            result_df = Utils.materialize(materialize_info)
        else:
            #  len(datamart_id) == 8 and datamart_id[0] == "D":
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
                return wrap_response('1000', msg="Can't find corresponding dataset with given id.")
            logger.debug("Start materialize the dataset for general..")
            result_df = Utils.materialize(metadata=results[0])

        logger.debug("Materialize finished, start generating metadata...")

        # generate metadata
        d3m_df = d3m_DataFrame(result_df, generate_metadata=False)
        resources = {AUGMENT_RESOURCE_ID: d3m_df}
        return_ds = d3m_Dataset(resources=resources, generate_metadata=False)
        return_ds.metadata = return_ds.metadata.clear(source="", for_value=return_ds, generate_metadata=True)
        logger.debug("Updating metadata...")
        metadata_all_level = {
            "id": datamart_id,
            "version": "2.0",
            "name": "datamart_dataset_" + datamart_id,
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
        logger.debug("Generating metadata finished...")
        return json.dumps(return_ds.metadata.to_json_structure(), indent=2)
    except Exception as e:
        return wrap_response('1000', msg="FAIL MATERIALIZE - %s \n %s" % (str(e), str(traceback.format_exc())))


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
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - Unable to get search result or input is a bad format!',
                                 data=None)

        return_format = request.values.get('format')
        # if not get return format, set defauld as csv
        if return_format is None:
            return_format = "d3m"
        else:
            return_format = check_return_format(return_format)
        if not return_format:
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - Unknown return format: ' + str(return_format),
                                 data=None)

        logger.info("The requested download format is " + return_format)

        try:
            data_file = request.files.get('data')
        except:
            data_file = None
        data, loaded_dataset = load_input_supplied_data(request.values.get('data'), data_file)

        if loaded_dataset is None:
            return wrap_response(code='1000',
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
            loaded_dataset = search_result_wikifier.augment(supplied_data=loaded_dataset)
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

            return wrap_response(code='0000',
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
        return wrap_response(code='1000', msg="FAIL SEARCH - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/upload', methods=['POST'])
@cross_origin()
def upload():
    logger.debug("Start uploading in one step...")
    try:
        url = request.values.get('url')
        if url is None:
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - Url can not be None',
                                 data=None)

        file_type = request.values.get('file_type')
        if file_type is None:
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - file_type can not be None',
                                 data=None)

        title = request.values.get('title').split("||") if request.values.get('title') else None
        description = request.values.get('description').split("||") if request.values.get('description') else None
        keywords = request.values.get('keywords').split("||") if request.values.get('keywords') else None

        df, meta = datamart_upload_instance.load_and_preprocess(input_dir=url, file_type=file_type)
        try:
            for i in range(len(df)):
                if title:
                    meta[i]['title'] = title[i]
                if description:
                    meta[i]['description'] = description[i]
                if keywords:
                    meta[i]['keywords'] = keywords[i]
        except:
            msg = "ERROR set the user defined title / description / keywords: " + str(
                len(meta)) + " tables detected but only "
            if title:
                msg += str(len(title)) + " title, "
            if description:
                msg += str(len(description)) + " description, "
            if keywords:
                msg += str(len(keywords)) + "keywords"
            msg += " given."
            return wrap_response('1000', msg=msg)

        for i in range(len(df)):
            datamart_upload_instance.model_data(df, meta, i)
            response_id = datamart_upload_instance.upload()
        return wrap_response('0000', msg="UPLOAD Success! The uploadted dataset id is:" + response_id)
    except Exception as e:
        return wrap_response('1000', msg="FAIL UPLOAD - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/upload/test', methods=['POST'])
@cross_origin()
def upload_test():
    logger.debug("Start uploading(test version) in one step...")
    datamart_upload_test_instance = Datamart_isi_upload(update_server=config['update_test_server'],
                                                        query_server=config['update_test_server'])
    try:
        url = request.values.get('url')
        if url is None:
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - Url can not be None',
                                 data=None)

        file_type = request.values.get('file_type')
        if file_type is None:
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - file_type can not be None',
                                 data=None)

        title = request.values.get('title').split("||") if request.values.get('title') else None
        description = request.values.get('description').split("||") if request.values.get('description') else None
        keywords = request.values.get('keywords').split("||") if request.values.get('keywords') else None

        df, meta = datamart_upload_test_instance.load_and_preprocess(input_dir=url, file_type=file_type)
        try:
            for i in range(len(df)):
                if title:
                    meta[i]['title'] = title[i]
                if description:
                    meta[i]['description'] = description[i]
                if keywords:
                    meta[i]['keywords'] = keywords[i]
        except:
            msg = "ERROR set the user defined title / description / keywords: " + str(
                len(meta)) + " tables detected but only "
            if title:
                msg += str(len(title)) + " title, "
            if description:
                msg += str(len(description)) + " description, "
            if keywords:
                msg += str(len(keywords)) + "keywords"
            msg += " given."
            return wrap_response('1000', msg=msg)

        for i in range(len(df)):
            datamart_upload_test_instance.model_data(df, meta, i)
            datamart_upload_test_instance.upload()
        return wrap_response('0000', msg="UPLOAD TEST Success!")
    except Exception as e:
        return wrap_response('1000', msg="FAIL UPLOAD TEST - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/upload/generateWD+Metadata', methods=['POST'])
@cross_origin()
def load_and_process():
    logger.debug("Start loading and process the upload data")
    try:
        url = request.values.get('url')
        if url is None:
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - Url can not be None',
                                 data=None)

        file_type = request.values.get('file_type')
        if file_type is None:
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - file_type can not be None',
                                 data=None)

        df, meta = datamart_upload_instance.load_and_preprocess(input_dir=url, file_type=file_type)
        df_returned = []
        for each in df:
            data = io.StringIO()
            each.to_csv(data, index=False)
            df_returned.append(data.getvalue())
        # return wrap_response('0000', data=(df_returned, meta))
        return json.dumps({"data": df_returned, "metadata": meta}, indent=2)
    except Exception as e:
        return wrap_response('1000', msg="FAIL LOAD/ PREPROCESS - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/upload/uploadWD+Metadata', methods=['POST'])
@cross_origin()
def upload_metadata():
    logger.debug("Start uploading...")
    try:
        if request.values.get('metadata'):
            metadata = request.values.get('metadata')
            metadata_json = json.loads(metadata)
        else:
            return wrap_response('1000', msg="FAIL UPLOAD - No metadata input found")

        if request.values.get('data_input'):
            data_input = request.values.get('data_input')
            data_input = json.loads(data_input)
        else:
            return wrap_response('1000', msg="FAIL UPLOAD - No dataset input found")

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

        return wrap_response('0000', msg="UPLOAD Success! The uploadted dataset id is:" + response_id)
    except Exception as e:
        return wrap_response('1000', msg="FAIL LOAD/ PREPROCESS - %s \n %s" % (str(e), str(traceback.format_exc())))


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

    url = '{}/{}/{}/_search'.format(em_es_url, em_es_index, em_es_type)
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


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=9000, debug=False, threaded=True)
