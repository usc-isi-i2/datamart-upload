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
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
from flask_cors import CORS, cross_origin
# When load spacy in a route, it will raise error. So do not remove "import spacy" here:
# import spacy

# sys.path.append(sys.path.append(os.path.join(os.path.dirname(__file__), '..')))
from d3m.base import utils as d3m_utils
from d3m.container import DataFrame as d3m_DataFrame
from d3m.container.dataset import Dataset as d3m_Dataset, D3MDatasetLoader
from d3m.metadata.base import ALL_ELEMENTS
from flask import Flask, request, render_template, send_file, Response
from datamart_isi.config import general_search_server, wikidata_server
from SPARQLWrapper import SPARQLWrapper, JSON, POST, URLENCODED
from datamart_isi.entries import Datamart, DatamartQuery, VariableConstraint, AUGMENT_RESOURCE_ID, DatamartSearchResult, DatasetColumn
from datamart_isi.upload.store import Datamart_isi_upload
from datamart_isi.utilities.utils import Utils


dataset_paths = ["/Users/minazuki/Desktop/studies/master/2018Summer/data/datasets/seed_datasets_data_augmentation", "/Users/minazuki/Desktop/studies/master/2018Summer/data/datasets/seed_datasets_current"]
WIKIDATA_QUERY_SERVER = wikidata_server
DATAMART_SERVER = general_search_server
datamart_upload_instance = Datamart_isi_upload(update_server="http://dsbox02.isi.edu:9001/blazegraph/namespace/datamart3/sparql")

app = Flask(__name__)
CORS(app, resources={r"/api": {"origins": "*"}})


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
                return pd.read_csv(files[key]).infer_objects()
            elif _type == 'json':
                return json.load(files[key])
        except:
            pass


def parse_search_result(search_res: DatamartSearchResult) -> str:
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
    res = " - " + title + \
          " -\n    * Datamart ID: " + datamart_id + \
          "\n    * Score: " + score + \
          "\n    * URL: " + url + "\n    " + "* Columns: "

    for i, each in enumerate(columns_result):
        res += "\n\t[" + str(i) + "] " + each

    res += "\n    * Recommend Join Columns: " + join_columns + "\n"

    print(res)
    sys.stdout.flush()
    return res


def load_d3m_dataset(path) -> typing.Optional[d3m_Dataset]:
    """
    Function used to load d3m datasets
    """
    # creat a dict which have reference for all dataset ids
    logger.debug("Trying to load dataset " + str(path))
    datasets_list = dict()
    for each_path in dataset_paths:
        temp = os.listdir(each_path)
        for each in temp:
            datasets_list[each] = each_path

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
    logger.debug(str(data[:100]))
    if type(data) is str:
        data = pd.read_csv(data, dtype=str)
    elif type(data) is pd.DataFrame:
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
        "location_uris":('file:///tmp/datasetDoc.json',),
        "digest":"",
        "description":"",
        "source":{'license': 'Other'},
    }
    return_ds.metadata = return_ds.metadata.update(metadata=metadata_all_level, selector=())
    logger.debug("Loading csv and transform to d3m dataset format success!")
    return return_ds

# def wrap_materializer(search_result):
#     output = {"info" : search_result.serialize(), "first_n_rows": 30}
#     return output


@app.route('/')
def hello():
    return 'Datamart(V2.0) Web Service!<a href="/gui">gui</a>'


@app.route('/search', methods=['POST'])
@cross_origin()
def search():
    try:
        query = read_file(request.files, 'query', 'json')
        # if not send the json via file
        if not query and request.form.get('query_json'):
            query = json.loads(request.form.get('query_json'))

        # if data is csv content
        data = read_file(request.files, 'data', 'csv')
        # if data is not a csv content but a str path
        if data is not None:
            logger.debug("csv file input detected!")
            loaded_dataset = load_csv_data(data)
        elif request.values.get('data'):
            path = request.values.get('data')

            if path.lower().endswith(".csv"):
                logger.debug("csv file path detected!")
                loaded_dataset = load_csv_data(path)
            else:
                logger.debug("d3m path input detected!")
                loaded_dataset = load_d3m_dataset(path)
        else:
            loaded_dataset = None

        if loaded_dataset is None:
            logger.debug("Unable to load the input file with")
            logger.debug(str(path))
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - Unable to load input supplied data',
                                 data=None)

        max_return_docs = int(request.args.get('max_return_docs')) if request.args.get('max_return_docs') else 20

        keywords: typing.List[str] = []
        variables: typing.List['VariableConstraint'] = []
        query_wrapped = DatamartQuery(keywords=keywords, variables=variables)
        logger.debug("Starting datamart search service...")
        datamart_instance = Datamart(connection_url=DATAMART_SERVER)
        res = datamart_instance.search_with_data(query=query_wrapped, supplied_data=loaded_dataset).get_next_page(
            limit=max_return_docs) or []
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
        return wrap_response(code='0000',
                                  msg='Success',
                                  data=results)
    except Exception as e:
        return wrap_response(code='1000', msg="FAIL SEARCH - %s \n %s" % (str(e), str(traceback.format_exc())))


@app.route('/download', methods=['POST'])
@cross_origin()
def download():
    try:
        logger.debug("Start datamart downloading...")
        search_result = read_file(request.files, 'task', 'json')
        # if not send the json via file
        if not search_result and request.form.get('task'):
            search_result = json.loads(request.form.get('task'))
        if search_result is None:
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - Unable to get search result or input is a bad format!',
                                 data=None)

        # if data is csv content
        data = read_file(request.files, 'data', 'csv')
        # if data is not a csv content but a str path
        if data is not None:
            loaded_dataset = load_csv_data(data)
        elif request.values.get('data'):
            path = request.values.get('data')
            if path.lower().endswith("csv"):
                loaded_dataset = load_csv_data(path)
            else:
                loaded_dataset = load_d3m_dataset(data)
        else:
            loaded_dataset = None

        return_format = request.values.get('format')
        if not return_format or return_format.lower() == "csv":
            return_format = "csv"
        elif return_format.lower() == "d3m":
            return_format = "d3m"
        else:
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - Unknown return format: ' + str(return_format),
                                 data=None)

        # search without supplied data, not implement yet
        # TODO: implement this part!
        if loaded_dataset is None:
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - Unable to load input supplied data',
                                 data=None)
        # search with supplied data
        else:
            # preprocess on loaded_dataset
            logger.debug("Start running wikifier...")
            search_result_wikifier = DatamartSearchResult(search_result={}, supplied_data=None, query_json={}, search_type="wikifier")
            logger.debug("Wikifier finished, start running download...")
            loaded_dataset = search_result_wikifier.augment(supplied_data=loaded_dataset)
            search_result = DatamartSearchResult.deserialize(search_result['materialize_info'])
            download_result = search_result.download(supplied_data=loaded_dataset)
            logger.debug("Download finished.")
            res_id, result_df = d3m_utils.get_tabular_resource(dataset=download_result, resource_id=None)

            # print("--------------")
            # print(loaded_dataset['learningData'])
            # print("--------------")
            # print(result_df)
            # print("--------------")
            # sys.stdout.flush()

            non_empty_rows = []
            for i, v in result_df.iterrows():
                if len(v["joining_pairs"]) != 0:
                    non_empty_rows.append(i)

            if len(non_empty_rows) == 0:
                return wrap_response(code='1000',
                                     msg='FAIL DOWNLOAD - No joinable rows found!',
                                     data=None)
            logger.debug("Start saving the download results...")
            result_df = result_df.iloc[non_empty_rows ,:]
            result_df.reset_index(drop=True)
            # set all cells to be str so that we can save correctly
            download_result[res_id] = result_df.astype(str)
            # update structure type
            update_part = {"structural_type":str}
            for i in range(result_df.shape[1]):
                download_result.metadata = download_result.metadata.update(metadata = update_part, selector=(res_id, ALL_ELEMENTS, i))

            # update row length
            update_part = {"length":result_df.shape[0]}
            download_result.metadata = download_result.metadata.update(metadata = update_part, selector=(res_id,))

            result_id = str(hash(result_df.values.tobytes()))
            # save_dir = "/tmp/download_result" + result_id
            # if os.path.isdir(save_dir) or os.path.exists(save_dir):
            #     shutil.rmtree(save_dir)
            if return_format == "d3m":
                # save dataset
                with tempfile.TemporaryDirectory() as tmpdir:
                    absolute_path_part_length = len(str(tmpdir))
                    save_dir =os.path.join(str(tmpdir), result_id)
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
        return wrap_response(code='1000', msg="FAIL SEARCH - %s \n %s" %(str(e), str(traceback.format_exc())))


@app.route('/download/id', methods=['GET'])
@cross_origin()
def download_by_id():
    """
    download the dataset with given id
    """
    logger.debug("Start downloading with id...")
    datamart_id = request.values.get('id')
    return_format = request.values.get('format')
    try:
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
                "digest":"",
                "description":"",
                "source":{'license': 'Other'},
            }
            return_ds.metadata = return_ds.metadata.update(metadata=metadata_all_level, selector=())

            with tempfile.TemporaryDirectory() as tmpdir:
                absolute_path_part_length = len(str(tmpdir))
                save_dir =os.path.join(str(tmpdir), result_id)
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
                    attachment_filename= datamart_id + '.zip'
                )

        else:
            data = io.StringIO()
            result_df.to_csv(data, index=False)
            return Response(data.getvalue(), mimetype="text/csv")

    except Exception as e:
        return wrap_response('1000', msg="FAIL MATERIALIZE - %s \n %s" %(str(e), str(traceback.format_exc())))


@app.route('/augment', methods=['POST'])
@cross_origin()
def augment():
    try:
        logger.debug("Start running augment...")
        search_result = read_file(request.files, 'task', 'json')
        # if not send the json via file
        if not search_result and request.form.get('task'):
            search_result = json.loads(request.form.get('task'))
        if search_result is None:
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - Unable to get search result',
                                 data=None)

        # if data is csv content
        data = read_file(request.files, 'data', 'csv')
        # if data is not a csv content but a str path
        if data is not None:
            loaded_dataset = load_csv_data(data)
        elif request.values.get('data'):
            path = request.values.get('data')
            if path.lower().endswith("csv"):
                loaded_dataset = load_csv_data(path)
            else:
                loaded_dataset = load_d3m_dataset(data)
        else:
            loaded_dataset = None

        return_format = request.values.get('format')
        if not return_format or return_format.lower() == "csv":
            return_format = "csv"
        elif return_format.lower() == "d3m":
            return_format = "d3m"
        else:
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - Unknown return format: ' + str(return_format),
                                 data=None)

        # search without supplied data, not implement yet
        # TODO: implement this part!
        if loaded_dataset is None:
            return wrap_response(code='1000',
                                 msg='FAIL SEARCH - Unable to load input supplied data',
                                 data=None)
        # search with supplied data
        else:
            columns = request.values.get('columns')
            if columns and type(columns) is not list:
                columns = columns.split(", ")
                logger.info("Required columns found as: "+ str(columns))
            columns_formated = []
            if columns:
                for each in columns:
                    columns_formated.append(DatasetColumn(resource_id=AUGMENT_RESOURCE_ID, column_index=int(each)))
            logger.debug("Start running wikifier...")
            # preprocess on loaded_dataset
            search_result_wikifier = DatamartSearchResult(search_result={}, supplied_data=None, query_json={}, search_type="wikifier")
            loaded_dataset = search_result_wikifier.augment(supplied_data=loaded_dataset)
            logger.debug("Wikifier running finished, start running augment...")
            search_result = DatamartSearchResult.deserialize(search_result['materialize_info'])
            augment_result = search_result.augment(supplied_data=loaded_dataset, augment_columns = columns_formated)
            res_id, result_df = d3m_utils.get_tabular_resource(dataset=augment_result, resource_id=None)
            augment_result[res_id] = result_df.astype(str)

            # update structural type
            update_part = {"structural_type": str}
            for i in range(result_df.shape[1]):
                augment_result.metadata = augment_result.metadata.update(metadata = update_part, selector=(res_id, ALL_ELEMENTS, i))

            result_id = str(hash(result_df.values.tobytes()))
            # if required to store in disk and return the path
            if request.values.get('destination'):
                logger.info("Saving to a given destination required.")
                save_dir = os.path.join(request.values.get('destination'), "augment_result" + result_id)
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
                with tempfile.TemporaryDirectory() as tmpdir:
                    absolute_path_part_length = len(str(tmpdir))
                    save_dir =os.path.join(str(tmpdir), result_id)
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

    except Exception as e:
        return wrap_response(code='1000', msg="FAIL SEARCH - %s \n %s" %(str(e), str(traceback.format_exc())))


@app.route('/load_and_process', methods=['POST'])
@cross_origin()
def load_and_process():
    logger.debug("Start loading and process the upload data")
    try:
        if request.values.get('input_dir'):
            input_dir = request.values.get('input_dir')
        if request.values.get('file_type'):
            file_type = request.values.get('file_type')

        df,meta = datamart_upload_instance.load_and_preprocess(input_dir=input_dir,file_type=file_type)
        df_returned = []
        for each in df:
            data = io.StringIO()
            each.to_csv(data, index=False)
            df_returned.append(data.getvalue())
        return wrap_response('0000', data=(df_returned, meta))
    except Exception as e:
        return wrap_response('1000', msg="FAIL LOAD/ PREPROCESS - %s \n %s" %(str(e), str(traceback.format_exc())))


@app.route('/upload', methods=['POST'])
@cross_origin()
def upload():
    logger.debug("Start uploading...")
    try:
        if request.values.get('metadata'):
            metadata = request.values.get('metadata')
            metadata_json = [json.loads(metadata)]
            print(metadata_json[0].keys())
        else:
            return wrap_response('1000', msg="FAIL UPLOAD - No metadata input found")
        if request.values.get('data_input'):
            data_input = request.values.get('data_input')
        else:
            return wrap_response('1000', msg="FAIL UPLOAD - No dataset input found")
        data_df = []
        if type(data_input) is list:
            for each in data_input:
                data_df.append(pd.read_csv(each, dtype="str"))

        else:
            # print(data_input)
            if data_input[-1] == "\n":
                data_input = data_input[:-1]
            loaded_data = io.StringIO(data_input)
            data_df = [pd.read_csv(loaded_data, dtype="str")]
            print(data_df[0].head())
            sys.stdout.flush()
        # for each in DataFrame:

        if request.values.get('dataset_number'):
            dataset_number = request.values.get('dataset_number')
        else:
            dataset_number = 0

        datamart_upload_instance.model_data(data_df, metadata_json, dataset_number)
        datamart_upload_instance.upload()

        return wrap_response('0000', msg="UPLOAD Success!")
    except Exception as e:
        return wrap_response('1000', msg="FAIL LOAD/ PREPROCESS - %s \n %s" %(str(e), str(traceback.format_exc())))



@app.route('/new/materialize_data', methods=['POST'])
@cross_origin()
def materialize_data():
    try:
        data = request.data
        materialize_info = json.loads(data)
        first_n_rows = None
        datamart_search_result = DatamartSearchResult.deserialize(materialize_info["info"])
        print("materialize_info is")
        print(materialize_info["info"])
        sys.stdout.flush()
        try:
            first_n_rows = int(materialize_info['first_n_rows'])
        except:
            pass
        df = Utils.materialize(metadata=datamart_search_result.search_result)
        if first_n_rows:
            df = df.iloc[:first_n_rows, :]
        csv = df.to_csv(index=False)
        return wrap_response('0000', data=csv)
    except Exception as e:
        return wrap_response('1000', msg="FAIL MATERIALIZE - %s \n %s" %(str(e), str(traceback.format_exc())))

#
# @app.route('/new/join_data', methods=['POST'])
# @cross_origin()
# def join_data():
#     try:
#         left_df = read_file(request.files, 'left_data', 'csv')
#         right_id = int(request.form.get('right_data'))
#         left_columns = json.loads(request.form.get('left_columns'))
#         right_columns = json.loads(request.form.get('right_columns'))
#         left_meta = json.loads(request.form.get('left_meta')) if request.form.get('left_meta') else None
#         exact_match = request.args.get('exact_match') or request.form.get('exact_match')
#         if exact_match and exact_match.lower() == 'true':
#             joiner = JoinerType.EXACT_MATCH
#         else:
#             joiner = JoinerType.RLTK
#         join_res = join(left_data=left_df,
#                          right_data=right_id,
#                          left_columns=left_columns,
#                          right_columns=right_columns,
#                          left_meta=left_meta,
#                          joiner=joiner)
#         if join_res.df is not None:
#             join_res.df.rename(columns=Renamer(), inplace=True)
#             joined_csv = join_res.df.to_csv(index=False)
#             return wrap_response('0000', data=joined_csv,
#                                       matched_rows=join_res.matched_rows,
#                                       cover_ratio=join_res.cover_ratio)
#         else:
#             return wrap_response('2000', msg="Failed, invalid inputs")
#     except Exception as e:
#         return wrap_response('1000', msg="FAIL JOIN - %s \n %s" %(str(e), str(traceback.format_exc())))
#
# @app.route('/new/get_metadata_single_file', methods=['POST'])
# @cross_origin()
# def get_metadata_single_file():
#     try:
#         description = request.json
#         enable_two_ravens_profiler = False
#         if request.args.get('enable_two_ravens_profiler') and request.args.get(
#                 'enable_two_ravens_profiler').lower() != "false":
#             enable_two_ravens_profiler = True
#         metadata_list = generate_metadata(description, enable_two_ravens_profiler=enable_two_ravens_profiler)
#         return wrap_response('0000', data=metadata_list)
#     except Exception as e:
#         return wrap_response('1000', msg="FAIL GENERATE DATA FOR SINGLE FILE - %s \n %s" %(str(e), str(traceback.format_exc())))
#
# @app.route('/new/get_multiple_dataset_metadata', methods=['POST'])
# @cross_origin()
# def get_multiple_dataset_metadata():
#     try:
#         url = request.json.get('url')
#         if 'wikipedia.org' in url:
#             metadata_lists = [[dataset_meta] for dataset_meta in wikipedia_tables_metadata(url)]
#         else:
#             enable_two_ravens_profiler = False
#             if request.args.get('enable_two_ravens_profiler') and request.args.get(
#                     'enable_two_ravens_profiler').lower() != "false":
#                 enable_two_ravens_profiler = True
#             url = request.json.get('url')
#             description = request.json.get('description')
#             metadata_lists = bulk_generate_metadata(html_page=url, description=description,
#                                                     enable_two_ravens_profiler=enable_two_ravens_profiler)
#         return wrap_response('0000', data=metadata_lists)
#     except Exception as e:
#         return wrap_response('1000', msg="FAIL GENERATE META FROM LINKS - %s \n %s" %(str(e), str(traceback.format_exc())))
#
# # @app.route('/new/get_metadata_extract_links', methods=['POST'])
# # def get_metadata_extract_links():
# #     try:
# #         enable_two_ravens_profiler = False
# #         if request.args.get('enable_two_ravens_profiler') and request.args.get(
# #                 'enable_two_ravens_profiler').lower() != "false":
# #             enable_two_ravens_profiler = True
# #         url = request.json.get('url')
# #         description = request.json.get('description')
# #         metadata_lists = bulk_generate_metadata(html_page=url, description=description,
# #                                                 enable_two_ravens_profiler=enable_two_ravens_profiler)
# #         return wrap_response('0000', data=metadata_lists)
# #     except Exception as e:
# #         return wrap_response('1000', msg="FAIL GENERATE META FROM LINKS - %s \n %s" %(str(e), str(traceback.format_exc())))
#
# @app.route('/new/upload_metadata_list', methods=['POST'])
# @cross_origin()
# def upload_list_of_metadata():
#     try:
#         all_metadata = request.json.get('metadata')
#         for_test = request.json.get('for_test')
#         allow_duplicates = request.json.get('allow_duplicates')
#         es_index = TEST_ES_INDEX if for_test else PRODUCTION_ES_INDEX
#         deduplicate = not allow_duplicates
#         succeed = []
#         if isinstance(all_metadata, dict):
#             succeed = upload(meta_list=[all_metadata],
#                    es_index=es_index,
#                    deduplicate=deduplicate)
#         elif all_metadata and isinstance(all_metadata[0], dict):
#             succeed = upload(meta_list=all_metadata,
#                    es_index=es_index,
#                    deduplicate=deduplicate)
#         elif all_metadata and isinstance(all_metadata[0], list):
#             succeed = bulk_upload(list_of_meta_list=all_metadata,
#                         es_index=es_index,
#                         deduplicate=deduplicate)
#         return wrap_response('0000', data=succeed)
#     except Exception as e:
#         return wrap_response('1000', msg="FAIL UPLOAD - %s \n %s" %(str(e), str(traceback.format_exc())))

# ----- gui for upload -----
@app.route('/gui', methods=['GET'])
def gui_index():
    return render_template("index.html")

# def get_metadata_extract_links():
#     try:
#         url = request.json.get('url')
#         description = request.json.get('description')
#         metadata_lists = bulk_generate_metadata(html_page=url, description=description)
#         return wrap_response('0000', data=metadata_lists)
#     except Exception as e:
#         return self.wrap_response('1000', msg="FAIL METADATA GENERATION - " + str(e))



if __name__ == '__main__':
    #app.run(host="0.0.0.0", port=9000, debug=False, ssl_context=('cert.pem', 'key.pem'), threaded=True)
    app.run(host="0.0.0.0", port=9000, debug=False, threaded=True)
