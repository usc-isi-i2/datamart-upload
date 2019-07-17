import typing
import pandas as pd
import copy
import random
import frozendict
import collections
import typing
import traceback
import logging
import datetime
import d3m.metadata.base as metadata_base
import json
import string
import wikifier
import time
import memcache
from ast import literal_eval
from SPARQLWrapper import SPARQLWrapper, JSON, POST, URLENCODED

from d3m import container
from d3m import utils
from d3m.container import DataFrame as d3m_DataFrame
from d3m.container import Dataset as d3m_Dataset
from d3m.base import utils as d3m_utils
from d3m.metadata.base import DataMetadata, ALL_ELEMENTS

from datamart_isi.augment import Augment
from datamart_isi.utilities.utils import Utils
from datamart_isi.joiners.rltk_joiner import RLTKJoinerGeneral
from datamart_isi.joiners.rltk_joiner import RLTKJoinerWikidata
from datamart_isi import config
from datamart_isi.utilities.timeout import Timeout, timeout_call

# from datamart_isi.joiners.join_result import JoinResult
# from datamart_isi.joiners.joiner_base import JoinerType


__all__ = ('DatamartQueryCursor', 'Datamart', 'DatasetColumn', 'DatamartSearchResult', 'AugmentSpec',
           'TabularJoinSpec', 'UnionSpec', 'TemporalGranularity', 'GeospatialGranularity', 'ColumnRelationship',
           'DatamartQuery',
           'VariableConstraint', 'NamedEntityVariable', 'TemporalVariable', 'GeospatialVariable', 'TabularVariable')

Q_NODE_SEMANTIC_TYPE = "http://wikidata.org/qnode"
AUGMENTED_COLUMN_SEMANTIC_TYPE = "https://metadata.datadrivendiscovery.org/types/Datamart_augmented_column"
MAX_ENTITIES_LENGTH = 10000
CONTAINER_SCHEMA_VERSION = 'https://metadata.datadrivendiscovery.org/schemas/v0/container.json'
P_NODE_IGNORE_LIST = {"P1549"}
SPECIAL_REQUEST_FOR_P_NODE = {"P1813": "FILTER(strlen(str(?P1813)) = 2)"}
AUGMENT_RESOURCE_ID = "learningData"
WIKIDATA_QUERY_SERVER = config.wikidata_server
MEMCACHE_SERVER = config.memcache_server
TIME_COLUMN_MARK = "%^&*SPECIAL_TIME_TYPE%^&*"
# initialize memcache system, if failed, just ignore
# try:
#     mc = memcache.Client([MEMCACHE_SERVER], debug=True)
# except:
mc = None


class DatamartQueryCursor(object):
    """
    Cursor to iterate through Datamarts search results.
    """

    def __init__(self, augmenter, search_query, supplied_data, need_run_wikifier=None):
        self._logger = logging.getLogger(__name__)
        self.augmenter = augmenter
        self.search_query = search_query
        self.supplied_data = supplied_data
        self.current_searching_query_index = 0

        self.remained_part = None
        if need_run_wikifier is None:
            self.need_run_wikifier = self._check_need_wikifier_or_not()
        else:
            self.need_run_wikifier = need_run_wikifier

    def get_next_page(self, *, limit: typing.Optional[int] = 20, timeout: int = None) \
            -> typing.Optional[typing.Sequence['DatamartSearchResult']]:
        """
        Return the next page of results. The call will block until the results are ready.

        Note that the results are not ordered; the first page of results can be returned first simply because it was
        found faster, but the next page might contain better results. The caller should make sure to check
        `DatamartSearchResult.score()`.

        Parameters
        ----------
        limit : int or None
            Maximum number of search results to return. None means no limit.
        timeout : int
            Maximum number of seconds before returning results. An empty list might be returned if it is reached.

        Returns
        -------
        Sequence[DatamartSearchResult] or None
            A list of `DatamartSearchResult's, or None if there are no more results.
        """
        if timeout is None:
            timeout = 1800
        self._logger.info("Set time limit to be " + str(timeout) + " seconds.")

        # if need to run wikifier, run it before any search
        if self.current_searching_query_index == 0 and self.need_run_wikifier:
            self._run_wikifier()

        # if already remained enough part
        current_result = self.remained_part or []
        if len(current_result) > limit:
            self.remained_part = current_result[limit:]
            current_result = current_result[:limit]
            return current_result

        # start searching
        while self.current_searching_query_index < len(self.search_query) and len(current_result) < limit:
            time_start = time.time()
            self._logger.debug("Start searching on query No." + str(self.current_searching_query_index))

            if self.search_query[self.current_searching_query_index].search_type == "wikidata":
                # TODO: now wikifier can only automatically search for all possible columns and do exact match
                search_res = timeout_call(timeout, self._search_wikidata, [])
            elif self.search_query[self.current_searching_query_index].search_type == "general":
                # search_res = timeout_call(timeout, self._search_datamart, [])
                search_res = self._search_datamart()
            else:
                raise ValueError("Unknown search query type for " +
                                 self.search_query[self.current_searching_query_index].search_type)

            time_used = (time.time() - time_start)
            timeout -= time_used
            if search_res is not None:
                self._logger.info("Running search on query No." + str(self.current_searching_query_index) + " used "
                                  + str(time_used) + " seconds and finished.")
                self._logger.info("Remained searching time: " + str(timeout) + " seconds.")
            elif timeout <= 0:
                self._logger.error(
                    "Running search on query No." + str(self.current_searching_query_index) + " timeouted!")
                break
            else:
                self._logger.error("Running search on query No." + str(self.current_searching_query_index) + " failed!")

            self.current_searching_query_index += 1
            if search_res is not None:
                current_result.extend(search_res)

        if len(current_result) == 0:
            return None
        else:
            if len(current_result) > limit:
                self.remained_part = current_result[limit:]
                current_result = current_result[:limit]
            return current_result

    def _check_need_wikifier_or_not(self) -> bool:
        """
        inner function used to check whether there already exist Q nodes in the supplied ata
        If not, will return True to indicate need to run wikifier
        If already exist Q nodes, return False to indicate no need to run wikifier
        :return: a bool value to indicate whether need to run wikifier or not
        """
        if self.supplied_data == None:
            return False
        if type(self.supplied_data) is d3m_Dataset:
            res_id, supplied_dataframe = d3m_utils.get_tabular_resource(dataset=self.supplied_data, resource_id=None)
            selector_base_type = "ds"
        else:
            supplied_dataframe = self.supplied_data
            selector_base_type = "df"

        for i in range(supplied_dataframe.shape[1]):
            if selector_base_type == "ds":
                metadata_selector = (res_id, metadata_base.ALL_ELEMENTS, i)
            else:
                metadata_selector = (metadata_base.ALL_ELEMENTS, i)
            each_metadata = self.supplied_data.metadata.query(metadata_selector)
            if Q_NODE_SEMANTIC_TYPE in each_metadata['semantic_types']:
                self._logger.info("Q nodes columns found in input data, will not run wikifier.")
                return False
        self._logger.info("No Q nodes columns found in input data, will run wikifier.")
        return True

    def _run_wikifier(self) -> None:
        """
        function used to run wikifier, will update self.supplied_data
        :return: None
        """
        self._logger.debug("Start running wikifier...")
        try:
            output_ds = copy.copy(self.supplied_data)
            specific_q_nodes = None
            res_id, supplied_dataframe = d3m_utils.get_tabular_resource(dataset=self.supplied_data, resource_id=None)
            target_columns = list(range(supplied_dataframe.shape[1]))
            wikifier_res = wikifier.produce(pd.DataFrame(supplied_dataframe), target_columns, specific_q_nodes)
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

            # update each column's metadata
            for i in range(old_column_length, wikifier_res.shape[1]):
                selector = (res_id, ALL_ELEMENTS, i)
                metadata = {"name": wikifier_res.columns[i],
                            "structural_type": str,
                            'semantic_types': (
                                "http://schema.org/Text",
                                "https://metadata.datadrivendiscovery.org/types/CategoricalData",
                                "https://metadata.datadrivendiscovery.org/types/Attribute",
                                "http://wikidata.org/qnode"
                            )}
                output_ds.metadata = output_ds.metadata.update(selector, metadata)
            # replace the old supplied_data
            self.supplied_data = output_ds
        except:
            traceback.print_exc()
            self._logger.error("Wikifier running failed.")

        self._logger.info("Wikifier running finished.")
        self.need_run_wikifier = False

    def _search_wikidata(self, query=None, supplied_data: typing.Union[d3m_DataFrame, d3m_Dataset] = None,
                         search_threshold=0.5) -> typing.List["DatamartSearchResult"]:
        """
        The search function used for wikidata search
        :param query: JSON object describing the query.
        :param supplied_data: the data you are trying to augment.
        :param search_threshold: the minimum appeared times of the properties
        :return: list of search results of DatamartSearchResult
        """
        self._logger.debug("Start running search on wikidata...")
        if supplied_data is None:
            supplied_data = self.supplied_data

        wikidata_results = []
        try:
            q_nodes_columns = []
            if type(supplied_data) is d3m_Dataset:
                res_id, supplied_dataframe = d3m_utils.get_tabular_resource(dataset=supplied_data, resource_id=None)
                selector_base_type = "ds"
            else:
                supplied_dataframe = supplied_data
                selector_base_type = "df"

            # check whether Qnode is given in the inputs, if given, use this to wikidata and search
            required_variables_names = None
            metadata_input = supplied_data.metadata

            if query is not None and 'required_variables' in query:
                required_variables_names = []
                for each in query['required_variables']:
                    required_variables_names.extend(each['names'])
            for i in range(supplied_dataframe.shape[1]):
                if selector_base_type == "ds":
                    metadata_selector = (res_id, metadata_base.ALL_ELEMENTS, i)
                else:
                    metadata_selector = (metadata_base.ALL_ELEMENTS, i)
                if Q_NODE_SEMANTIC_TYPE in metadata_input.query(metadata_selector)["semantic_types"]:
                    # if no required variables given, attach any Q nodes found
                    if required_variables_names is None:
                        q_nodes_columns.append(i)
                    # otherwise this column has to be inside required_variables
                    else:
                        if supplied_dataframe.columns[i] in required_variables_names:
                            q_nodes_columns.append(i)

            if len(q_nodes_columns) == 0:
                self._logger.warning("No wikidata Q nodes detected on corresponding required_variables!")
                self._logger.warning("Will skip wikidata search part")
                return wikidata_results
            else:
                self._logger.info("Wikidata Q nodes inputs detected! Will search with it.")
                self._logger.info("Totally " + str(len(q_nodes_columns)) + " Q nodes columns detected!")

                # do a wikidata search for each Q nodes column
                for each_column in q_nodes_columns:
                    self._logger.debug("Start searching on column " + str(each_column))
                    q_nodes_list = supplied_dataframe.iloc[:, each_column].tolist()
                    p_count = collections.defaultdict(int)
                    p_nodes_needed = []
                    # old method, the generated results are not very good
                    """
                    http_address = 'http://minds03.isi.edu:4444/get_properties'
                    headers = {"Content-Type": "application/json"}
                    requests_data = str(q_nodes_list)
                    requests_data = requests_data.replace("'", '"')
                    r = requests.post(http_address, data=requests_data, headers=headers)
                    results = r.json()
                    for each_p_list in results.values():
                        for each_p in each_p_list:
                            p_count[each_p] += 1
                    """
                    # TODO: temporary change here, may change back in the future
                    # TODO: add to use memcache to get results faster, memcache should run on dsbox server and let the backend the get the cache via internal
                    # Q node format (wd:Q23)(wd: Q42)
                    q_node_query_part = ""
                    unique_qnodes = set(q_nodes_list)
                    for each in unique_qnodes:
                        if len(each) > 0:
                            q_node_query_part += "(wd:" + each + ")"
                    sparql_query = "select distinct ?item ?property where \n{\n  VALUES (?item) {" + q_node_query_part \
                                   + "  }\n  ?item ?property ?value .\n  ?wd_property wikibase:directClaim ?property ." \
                                   + "  values ( ?type ) \n  {\n    ( wikibase:Quantity )\n" \
                                   + "    ( wikibase:Time )\n    ( wikibase:Monolingualtext )\n  }" \
                                   + "  ?wd_property wikibase:propertyType ?type .\n}\norder by ?item ?property "

                    if mc is not None:
                        # check whether we have cache or not
                        results = mc.get("results_" + str(hash(sparql_query)))
                    else:
                        results = None

                    if results is not None:
                        self._logger.info("Memcache hit in dsbox server! Will use cached results.")

                    else:
                        self._logger.info("Cache not hit, will run general query.")
                        try:
                            sparql = SPARQLWrapper(WIKIDATA_QUERY_SERVER)
                            sparql.setQuery(sparql_query)
                            sparql.setReturnFormat(JSON)
                            sparql.setMethod(POST)
                            sparql.setRequestMethod(URLENCODED)
                            results = sparql.query().convert()['results']['bindings']
                        except:
                            self._logger.error("Query on search_wikidata failed!")
                            traceback.print_exc()
                            continue

                        # add search result to cache
                        if mc is not None:
                            mc.set("results_" + str(hash(sparql_query)), results)
                            # add timestamp to let the system know when to update
                            mc.set("timestamp_" + str(hash(sparql_query)), str(datetime.datetime.now().timestamp()))
                            # add real query
                            mc.set("query_" + str(hash(sparql_query)), sparql_query)

                    self._logger.debug("Response from server for column " + str(each_column) +
                                       " received, start parsing the returned data from server.")
                    for each in results:
                        p_count[each['property']['value'].split("/")[-1]] += 1

                    for key, val in p_count.items():
                        if float(val) / len(unique_qnodes) >= search_threshold:
                            p_nodes_needed.append(key)
                    wikidata_search_result = {"p_nodes_needed": p_nodes_needed,
                                              "target_q_node_column_name": supplied_dataframe.columns[each_column]}
                    wikidata_results.append(DatamartSearchResult(search_result=wikidata_search_result,
                                                                 supplied_data=supplied_data,
                                                                 query_json=query,
                                                                 search_type="wikidata")
                                            )

                self._logger.debug("Running search on wikidata finished.")
            return wikidata_results

        except:
            self._logger.error("Searching with wikidata failed!")
            traceback.print_exc()
        finally:
            return wikidata_results

    def _search_datamart(self) -> typing.List["DatamartSearchResult"]:
        """
        function used for searching in datamart with blaze graph database
        :return: List[DatamartSearchResult]
        """
        self._logger.debug("Start searching on datamart...")
        search_result = []
        variables_search = self.search_query[self.current_searching_query_index].variables_search
        keywords_search = self.search_query[self.current_searching_query_index].keywords_search
        variables, title = dict(), dict()
        variables_temp = dict()  # this temp is specially used to store variable for time query
        for each_variable in self.search_query[self.current_searching_query_index].variables:
            if each_variable.key.startswith(TIME_COLUMN_MARK):
                variables_temp[each_variable.key.split("____")[1]] = each_variable.values
                start_time, end_time, granularity = each_variable.values.split("____")
                variables_search = {"temporal_variable": {
                                         "start": start_time,
                                         "end": end_time,
                                         "granularity": granularity
                                         }
                                    }
            else:
                variables[each_variable.key] = each_variable.values

        query = {"keywords": self.search_query[self.current_searching_query_index].keywords,
                 "variables": variables,
                 "keywords_search": keywords_search,
                 "variables_search": variables_search,
                 }

        query_results = self.augmenter.query_by_sparql(query=query, dataset=self.supplied_data)

        if len(variables_temp) != 0:
            query["variables"] = variables_temp

        for i, each_result in enumerate(query_results):
            self._logger.debug("Get returned No." + str(i) + " query result as ")
            self._logger.debug(str(each_result))
            if "start_time" in each_result.keys() and "end_time" in each_result.keys():
                tv = query["variables_search"]["temporal_variable"]
                start_date, end_date = pd.to_datetime(tv["start"]).timestamp(),\
                                       pd.to_datetime(tv["end"]).timestamp()  # query time
                start_time, end_time = pd.to_datetime(each_result['start_time']['value']).timestamp(), \
                                       pd.to_datetime(each_result['end_time']['value']).timestamp()  # dataset
                print("start_date {} end_date {} \n start_time {} end_time {}".format(start_date, end_date, start_time, end_time))

                # TODO: it seems the score calculation still have some problem here
                if  start_date >= start_time and end_time >= end_date:
                    time_score = 1.0
                elif start_time >= start_date and end_date >= end_time:
                    time_score = (end_time - start_time) / float(end_date - start_date)
                elif end_date >= end_time and start_time >= start_date and end_time >= end_date:
                    time_score = (end_date - start_time) / float(end_date - start_date)
                elif start_date >= start_time and end_time >= start_date and end_date >= end_time:
                    time_score = (end_time - start_date) / float(end_date - start_date)
                else:
                    time_score = 0.0

                if time_score != 0.0 and 'score' in each_result.keys():
                    old_score = float(each_result['score']['value'])
                    each_result['score']['value'] = (old_score + time_score) / 2
                else:
                    each_result['score'] = {"value": 0.0}

            temp = DatamartSearchResult(search_result=each_result, supplied_data=self.supplied_data, query_json=query,
                                        search_type="general")
            search_result.append(temp)

        search_result.sort(key=lambda x: x._score, reverse=True)

        self._logger.debug("Searching on datamart finished.")
        return search_result


class Datamart(object):
    """
    ISI implement of datamart
    """

    def __init__(self, connection_url: str) -> None:
        self.connection_url = connection_url
        self._logger = logging.getLogger(__name__)
        # query_server = "http://dsbox02.isi.edu:9001/blazegraph/namespace/datamart3/sparql"
        self.augmenter = Augment(endpoint=self.connection_url)
        self.supplied_dataframe = None

    def set_test_mode(self) -> None:
        query_server = config.wikidata_server_test
        self.augmenter = Augment(endpoint=query_server)

    def search(self, query: 'DatamartQuery') -> DatamartQueryCursor:
        """This entry point supports search using a query specification.

        The query specification supports querying datasets by keywords, named entities, temporal ranges, and geospatial ranges.

        Datamart implementations should return a DatamartQueryCursor immediately.

        Parameters
        ----------
        query : DatamartQuery
            Query specification.

        Returns
        -------
        DatamartQueryCursor
            A cursor pointing to search results.
        """

        return DatamartQueryCursor(augmenter=self.augmenter, search_query=[query], supplied_data=None)

    def search_with_data(self, query: 'DatamartQuery', supplied_data: container.Dataset, need_wikidata=True) \
            -> DatamartQueryCursor:
        """
        Search using on a query and a supplied dataset.

        This method is a "smart" search, which leaves the Datamart to determine how to evaluate the relevance of search
        result with regard to the supplied data. For example, a Datamart may try to identify named entities and date
        ranges in the supplied data and search for companion datasets which overlap.

        To manually specify query constraints using columns of the supplied data, use the `search_with_data_columns()`
        method and `TabularVariable` constraints.

        Datamart implementations should return a DatamartQueryCursor immediately.

        Parameters
        ------_---
        query : DatamartQuery
            Query specification
        supplied_data : container.Dataset
            The data you are trying to augment.

        Returns
        -------
        DatamartQueryCursor
            A cursor pointing to search results containing possible companion datasets for the supplied data.
        """

        # first take a search on wikidata
        # add wikidata searching query at first position
        res_id = None
        if not need_wikidata:
            search_queries = []
            need_run_wikifier = False
        else:
            need_run_wikifier = None
            search_queries = [DatamartQuery(search_type="wikidata")]

        if type(supplied_data) is d3m_Dataset:
            res_id, self.supplied_dataframe = d3m_utils.get_tabular_resource(dataset=supplied_data, resource_id=None)
        else:
            self.supplied_dataframe = supplied_data

        # if query is None:
        # if not query given, try to find the Text columns from given dataframe and use it to find some candidates
        can_query_columns = []
        for each in range(len(self.supplied_dataframe.columns)):
            if type(supplied_data) is d3m_Dataset:
                selector = (res_id, ALL_ELEMENTS, each)
            else:
                selector = (ALL_ELEMENTS, each)
            each_column_meta = supplied_data.metadata.query(selector)
            if 'http://schema.org/Text' in each_column_meta["semantic_types"] \
                    or "http://schema.org/DateTime" in each_column_meta["semantic_types"]:
                can_query_columns.append(each)

        if len(can_query_columns) == 0:
            self._logger.warning("No columns can be augment with datamart!")

        for each_column_index in can_query_columns:
            column_formated = DatasetColumn(res_id, each_column_index)
            tabular_variable = TabularVariable(columns=[column_formated], relationship=ColumnRelationship.CONTAINS)
            each_search_query = self.generate_datamart_query_from_data(supplied_data=supplied_data,
                                                                       data_constraints=[tabular_variable])
            search_queries.append(each_search_query)

        return DatamartQueryCursor(augmenter=self.augmenter, search_query=search_queries, supplied_data=supplied_data,
                                   need_run_wikifier=need_run_wikifier)

    def search_with_data_columns(self, query: 'DatamartQuery', supplied_data: container.Dataset,
                                 data_constraints: typing.List['TabularVariable']) -> DatamartQueryCursor:
        """
        Search using a query which can include constraints on supplied data columns (TabularVariable).

        This search is similar to the "smart" search provided by `search_with_data()`, but caller must manually specify
        constraints using columns from the supplied data; Datamart will not automatically analyze it to determine
        relevance or joinability.

        Use of the query spec enables callers to compose their own "smart search" implementations.

        Datamart implementations should return a DatamartQueryCursor immediately.

        Parameters
        ------_---
        query : DatamartQuery
            Query specification
        supplied_data : container.Dataset
            The data you are trying to augment.
        data_constraints : list
            List of `TabularVariable` constraints referencing the supplied data.

        Returns
        -------
        DatamartQueryCursor
            A cursor pointing to search results containing possible companion datasets for the supplied data.
        """

        # put entities of all given columns from "data_constraints" into the query's variable part and run the query

        search_query = self.generate_datamart_query_from_data(supplied_data=supplied_data,
                                                              data_constraints=data_constraints)
        return DatamartQueryCursor(augmenter=self.augmenter, search_query=[search_query], supplied_data=supplied_data)

    def generate_datamart_query_from_data(self, supplied_data: container.Dataset,
                                          data_constraints: typing.List['TabularVariable']) -> "DatamartQuery":
        """
        Inner function used to generate the isi implemented datamart query from given dataset
        :param supplied_data: a Dataset format supplied data
        :param data_constraints:
        :return: a DatamartQuery can be used in isi datamart
        """
        all_query_variables = []
        keywords = []
        translator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
        TemporalGranularity = {'second': 14, 'minute': 13, 'hour': 12, 'day': 11, 'month': 10, 'year': 9}

        for each_constraint in data_constraints:
            for each_column in each_constraint.columns:
                each_column_index = each_column.column_index
                each_column_res_id = each_column.resource_id
                all_value_str_set = set()
                each_column_meta = supplied_data.metadata.query((each_column_res_id, ALL_ELEMENTS, each_column_index))
                if 'http://schema.org/DateTime' in each_column_meta["semantic_types"]:
                    try:
                        column_data = supplied_data[each_column_res_id].iloc[:, each_column_index]
                        column_data_datetime_format = pd.to_datetime(column_data)
                        start_date = min(column_data_datetime_format)
                        end_date = max(column_data_datetime_format)
                        if any(column_data_datetime_format.dt.second != 0):
                            time_granularity = 'second'
                        elif any(column_data_datetime_format.dt.minute != 0):
                            time_granularity = 'minute'
                        elif any(column_data_datetime_format.dt.hour != 0):
                            time_granularity = 'hour'
                        elif any(column_data_datetime_format.dt.day != 0):
                            time_granularity = 'day'
                        elif any(column_data_datetime_format.dt.month != 0):
                            time_granularity = 'month'
                        elif any(column_data_datetime_format.dt.year != 0):
                            time_granularity = 'year'
                        else:
                            self._logger.error("No usefully date information found for column No." + str(each_column_index))
                            continue
                    except:
                        self._logger.error("Can't parse current datetime for column No." + str(each_column_index))
                        continue
                    each_keyword = TIME_COLUMN_MARK + "____" + supplied_data[each_column_res_id].columns[each_column_index]
                    keywords.append(each_keyword)
                    all_value_str = str(start_date) + "____" + str(end_date) + "____" + time_granularity

                elif 'http://schema.org/Text' in each_column_meta["semantic_types"]:
                    column_values = supplied_data[each_column_res_id].iloc[:, each_column_index].astype(str)
                    query_column_entities = list(set(column_values.tolist()))
                    if len(query_column_entities) > MAX_ENTITIES_LENGTH:
                        query_column_entities = random.sample(query_column_entities, MAX_ENTITIES_LENGTH)
                    for each in query_column_entities:
                        words_processed = str(each).lower().translate(translator).split()
                        for word in words_processed:
                            all_value_str_set.add(word)
                    all_value_str = " ".join(all_value_str_set)
                    each_keyword = supplied_data[each_column_res_id].columns[each_column_index]
                    keywords.append(each_keyword)

                all_query_variables.append(VariableConstraint(key=each_keyword, values=all_value_str))

        search_query = DatamartQuery(keywords=keywords, variables=all_query_variables)

        return search_query


class DatasetColumn:
    """
    Specify a column of a dataframe in a D3MDataset
    """

    def __init__(self, resource_id: str, column_index: int) -> None:
        self.resource_id = resource_id
        self.column_index = column_index


class DatamartSearchResult:
    """
    This class represents the search results of a datamart search.
    Different datamarts will provide different implementations of this class.
    """

    def __init__(self, search_result, supplied_data, query_json, search_type, connection_url=None):
        self._logger = logging.getLogger(__name__)
        self.search_result = search_result
        self.supplied_data = supplied_data
        if type(supplied_data) is d3m_Dataset:
            self.res_id, self.supplied_dataframe = d3m_utils.get_tabular_resource(dataset=supplied_data,
                                                                                  resource_id=None)
            self.selector_base_type = "ds"
        elif type(supplied_data) is d3m_DataFrame:
            self.supplied_dataframe = supplied_data
            self.selector_base_type = "df"
        else:
            self.supplied_dataframe = None
        if connection_url is None:
            self.connection_url = WIKIDATA_QUERY_SERVER
        self.query_json = query_json
        self.search_type = search_type
        self.pairs = None
        self._res_id = None  # only used for input is Dataset
        self.join_pairs = None
        self.right_df = None
        self.d3m_metadata = self._get_d3m_metadata()

        if self.search_type == "general":
            self._id = self.search_result['datasetLabel']['value']
            self._score = float(self.search_result['score']['value'])

        elif self.search_type == "wikidata":
            self._id = "wikidata search on " + str(self.search_result['p_nodes_needed']) + " with column " + \
                       self.search_result['target_q_node_column_name']
            self._id = self._id.replace(" ", "_")
            self._id = self._id.replace("[", "_")
            self._id = self._id.replace("]", "_")
            self._id = self._id.replace("'", "_")
            self._id = self._id.replace(",", "")
            self._score = 1
        else:
            self._id = "wikifier"
            self._score = 1

    def _get_d3m_metadata(self) -> DataMetadata:
        """
        function used to generate the d3m format metadata
        """
        self._logger.debug("Start getting d3m metadata...")
        if self.search_type == "wikidata":
            metadata = self._get_d3m_metadata_for_wikidata()
        elif self.search_type == "general":
            metadata = self._get_d3m_metadata_for_general()
        elif self.search_type == "wikifier":
            self._logger.warning("No metadata can provide for wikifier augment")
            metadata = DataMetadata()
        else:
            self._logger.error("Unknown search type as " + str(self.search_type))
            metadata = DataMetadata()
        self._logger.debug("Getting d3m metadata finished.")
        return metadata

    def _get_d3m_metadata_for_wikidata(self):
        """
        function used to generate the d3m format metadata - specified for wikidata search result
        because search results don't have value type of each P node, we have to query one sample to find
        """
        return_metadata = DataMetadata()
        if self.supplied_dataframe is not None:
            data_length = self.supplied_dataframe.shape[0]
        elif self.supplied_data is not None:
            res_id, self.supplied_dataframe = d3m_utils.get_tabular_resource(dataset=self.supplied_data,
                                                                             resource_id=None)
            data_length = self.supplied_dataframe.shape[0]
        else:
            self._logger.warning("Can't calculate the row length for wikidata search results without supplied data")
            data_length = None

        metadata_all = {"structural_type": d3m_DataFrame,
                        "semantic_types": ["https://metadata.datadrivendiscovery.org/types/Table"],
                        "dimension": {
                            "name": "rows",
                            "semantic_types": ["https://metadata.datadrivendiscovery.org/types/TabularRow"],
                            "length": data_length,
                        },
                        "schema": "https://metadata.datadrivendiscovery.org/schemas/v0/container.json"
                        }
        return_metadata = return_metadata.update(selector=(), metadata=metadata_all)
        metadata_all_elements = {
            "dimension": {
                "name": "columns",
                "semantic_types": ["https://metadata.datadrivendiscovery.org/types/TabularColumn"],
                "length": len(self.search_result['p_nodes_needed']),
            }
        }
        return_metadata = return_metadata.update(selector=(ALL_ELEMENTS,), metadata=metadata_all_elements)

        for i, each in enumerate(self.search_result['p_nodes_needed']):
            target_q_node_column_name = self.search_result['target_q_node_column_name']
            try:

                q_node_column_number = self.supplied_dataframe.columns.tolist().index(target_q_node_column_name)
                sample_row_number = 0
                q_node_sample = self.supplied_dataframe.iloc[sample_row_number, q_node_column_number]
                semantic_types = self._get_wikidata_column_semantic_types(q_node_sample, each)
                # if we failed with first test, repeat until we get success one
                while not semantic_types[0]:
                    sample_row_number += 1
                    q_node_sample = self.supplied_dataframe.iloc[sample_row_number, q_node_column_number]
                    semantic_types = self._get_wikidata_column_semantic_types(q_node_sample, each)
            except:
                semantic_types = (
                    'https://metadata.datadrivendiscovery.org/types/Attribute',
                    AUGMENTED_COLUMN_SEMANTIC_TYPE
                )
            each_metadata = {
                "name": self.get_node_name(
                    self.search_result['p_nodes_needed'][i]) + "_for_" + target_q_node_column_name,
                "structural_type": str,
                "semantic_types": semantic_types,
            }
            return_metadata = return_metadata.update(selector=(ALL_ELEMENTS, i), metadata=each_metadata)

            each_metadata = {
                "name": "q_node",
                "structural_type": str,
                "semantic_types": (
                    'http://schema.org/Text',
                    'https://metadata.datadrivendiscovery.org/types/Attribute',
                    Q_NODE_SEMANTIC_TYPE,
                    AUGMENTED_COLUMN_SEMANTIC_TYPE
                ),
            }
            return_metadata = return_metadata.update(selector=(ALL_ELEMENTS, i + 1), metadata=each_metadata)

            each_metadata = {
                "name": "joining_pairs",
                "structural_type": list,
                "semantic_types": (
                    'https://metadata.datadrivendiscovery.org/types/Attribute',
                    AUGMENTED_COLUMN_SEMANTIC_TYPE
                ),
            }
            return_metadata = return_metadata.update(selector=(ALL_ELEMENTS, i + 2), metadata=each_metadata)
        return return_metadata

    def _get_wikidata_column_semantic_types(self, q_node_sample, p_node_target):
        """
        Inner function used to get the semantic types for given wikidata column
        :return: a tuple, tuple[0] indicate success get semantic type or not, tuple[1] indicate the found semantic types
        """
        q_nodes_query = '(wd:' + q_node_sample + ') \n'
        p_nodes_query_part = ' ?' + p_node_target + '\n'
        p_nodes_optional_part = "  OPTIONAL { ?q wdt:" + p_node_target + " ?" + p_node_target + "}\n"
        sparql_query = "SELECT DISTINCT ?q " + p_nodes_query_part + \
                       "WHERE \n{\n  VALUES (?q) { \n " + q_nodes_query + "}\n" + \
                       p_nodes_optional_part + "}\n"
        try:
            sparql = SPARQLWrapper(WIKIDATA_QUERY_SERVER)
            sparql.setQuery(sparql_query)
            sparql.setReturnFormat(JSON)
            sparql.setMethod(POST)
            sparql.setRequestMethod(URLENCODED)
            p_val = sparql.query().convert()['results']['bindings'][0][p_node_target]
            if "datatype" in p_val.keys():
                semantic_types = (
                    self.get_semantic_type(p_val["datatype"]),
                    'https://metadata.datadrivendiscovery.org/types/Attribute', AUGMENTED_COLUMN_SEMANTIC_TYPE)
            else:
                semantic_types = (
                    "http://schema.org/Text", 'https://metadata.datadrivendiscovery.org/types/Attribute',
                    AUGMENTED_COLUMN_SEMANTIC_TYPE)
            return True, semantic_types
        except:
            return False, None

    def _get_d3m_metadata_for_general(self):
        """
        function used to generate the d3m format metadata - specified for general search result
        """
        return_metadata = DataMetadata()
        metadata_dict = literal_eval(self.search_result['extra_information']['value'])
        data_metadata = metadata_dict.pop('data_metadata')
        metadata_all = {"structural_type": d3m_DataFrame,
                        "semantic_types": ["https://metadata.datadrivendiscovery.org/types/Table"],
                        "dimension": {
                            "name": "rows",
                            "semantic_types": ["https://metadata.datadrivendiscovery.org/types/TabularRow"],
                            "length": int(data_metadata['shape_0']),
                        },
                        "schema": "https://metadata.datadrivendiscovery.org/schemas/v0/container.json"
                        }
        return_metadata = return_metadata.update(selector=(), metadata=metadata_all)
        metadata_all_elements = {
            "dimension": {
                "name": "columns",
                "semantic_types": ["https://metadata.datadrivendiscovery.org/types/TabularColumn"],
                "length": int(data_metadata['shape_1']),
            }
        }
        return_metadata = return_metadata.update(selector=(ALL_ELEMENTS,), metadata=metadata_all_elements)

        for each_key, each_value in metadata_dict.items():
            if each_key[:12] == 'column_meta_':
                each_metadata = {
                    "name": each_value['name'],
                    "structural_type": str,
                    "semantic_types": each_value['semantic_type'],
                }
                i = int(each_key.split("_")[-1])
                return_metadata = return_metadata.update(selector=(ALL_ELEMENTS, i), metadata=each_metadata)
        return return_metadata

    def display(self) -> pd.DataFrame:
        """
        function used to see what found inside this search result class in a human vision
        :return: a pandas DataFrame
        """
        if self.search_type == "wikidata":
            column_names = []
            for each in self.search_result["p_nodes_needed"]:
                each_name = self.get_node_name(each)
                column_names.append(each_name)
            column_names = ", ".join(column_names)
            required_variable = list()
            required_variable.append(self.search_result["target_q_node_column_name"])
            result = pd.DataFrame({"title": "wikidata search result for "
                                            + self.search_result["target_q_node_column_name"],
                                   "columns": column_names, "join columns": required_variable, "score": self._score},
                                  index=[0])

        elif self.search_type == "general":
            title = self.search_result['title']['value']
            column_names = []
            current_column_number = 0
            temp_selector = (ALL_ELEMENTS, current_column_number)
            temp_meta = self.d3m_metadata.query(selector=temp_selector)
            while len(temp_meta) != 0:
                column_names.append(temp_meta['name'])
                current_column_number += 1
                temp_selector = (ALL_ELEMENTS, current_column_number)
                temp_meta = self.d3m_metadata.query(selector=temp_selector)

            column_names = ", ".join(column_names)
            join_columns = self.search_result['variableName']['value']

            result = pd.DataFrame(
                {"title": title, "columns": column_names, "join columns": join_columns, "score": self._score},
                index=[0])

        elif self.search_type == "wikifier":
            title = "wikifier"
            result = pd.DataFrame({"title": title, "columns": "", "join columns": "", "score": self._score},
                                  index=[0])

        else:
            raise ValueError("Unknown search type with " + self.search_type)
        return result

    def download(self, supplied_data: typing.Union[d3m_Dataset, d3m_DataFrame] = None,
                 connection_url: str = None, generate_metadata=True, return_format="ds") -> container.Dataset:
        """
        Produces a D3M dataset (data plus metadata) corresponding to the search result.
        Every time the download method is called on a search result, it will produce the exact same columns
        (as specified in the metadata -- get_metadata), but the set of rows may depend on the supplied_data.
        Datamart is encouraged to return a dataset that joins well with the supplied data, e.g., has rows that match
        the entities in the supplied data. Datamarts may ignore the supplied_data and return the same data regardless.

        If the supplied_data is None, Datamarts may return None or a default dataset, based on the search query.

        Parameters
        ---------
        supplied_data : container.Dataset
            A D3M dataset containing the dataset that is the target for augmentation. Datamart will try to download data
            that augments the supplied data well.
        connection_url : str
            A connection string used to connect to a specific Datamart deployment. If not provided, the one provided to
            the `Datamart` constructor is used.
        generate_metadata: bool
            Whether need to get the auto-generated metadata or not, only valid in isi datamart
        return_format: str
            A control parameter to set which type of output should get, the default value is "ds" as dataset
            Optional choice is to get dataframe type output. Only valid in isi datamart
        """
        if connection_url:
            self.connection_url = connection_url
        if self.search_type == "general":
            res = self.download_general(supplied_data, generate_metadata, return_format)
        elif self.search_type == "wikidata":
            res = self.download_wikidata(supplied_data, generate_metadata, return_format)
        else:
            raise ValueError("Unknown search type with " + self.search_type)

        if return_format == "ds":
            # sometime the index will be not continuous after augment, need to reset to ensure the index is continuous
            res[AUGMENT_RESOURCE_ID].reset_index(drop=True)
        else:
            res.reset_index(drop=True)

        return res

    def download_general(self, supplied_data: typing.Union[d3m_Dataset, d3m_DataFrame] = None, generate_metadata=True,
                         return_format="ds", augment_resource_id=AUGMENT_RESOURCE_ID) -> typing.Union[
        d3m_Dataset, d3m_DataFrame]:
        """
        Specified download function for general datamart Datasets
        :param supplied_data: given supplied data
        :param generate_metadata: whether need to genreate the metadata or not
        :param return_format: set the required return format: d3m_Dataset or d3m_DataFrame
        :param augment_resource_id: the name of the output dataset's resource id, the default is "augmentData"
        :return: a dataset or a dataframe depending on the input
        """
        self._logger.debug("Start downloading for datamart...")
        res_id = None
        if type(supplied_data) is d3m_Dataset:
            res_id, supplied_dataframe = d3m_utils.get_tabular_resource(dataset=supplied_data, resource_id=None)
        elif type(supplied_data) is d3m_DataFrame:
            supplied_dataframe = supplied_data
        else:
            supplied_dataframe = self.supplied_dataframe

        join_pairs_result = []
        candidate_join_column_scores = []

        # start finding pairs
        left_df = copy.deepcopy(supplied_dataframe)
        if self.right_df is None:
            self.right_df = Utils.materialize(metadata=self.search_result)
            right_df = self.right_df
        else:
            self._logger.info("Find downloaded data from previous time, will use that.")
            right_df = self.right_df
        self._logger.debug("Download finished, start generating d3m metadata.")
        left_metadata = Utils.generate_metadata_from_dataframe(data=left_df, original_meta=None)
        right_metadata = Utils.generate_metadata_from_dataframe(data=right_df, original_meta=None)

        if self.join_pairs is None:
            candidate_join_column_pairs = self.get_join_hints(left_df=left_df, right_df=right_df, left_df_src_id=res_id)
        else:
            candidate_join_column_pairs = self.join_pairs
        if len(candidate_join_column_pairs) > 1:
            logging.warning("multiple joining column pairs found! Will only check first one.")
        elif len(candidate_join_column_pairs) < 1:
            logging.error("Getting joining pairs failed")

        is_time_query = True
        if "start_time" in self.search_result and "end_time" in self.search_result:
            for each in self.query_json['keywords']:
                if TIME_COLUMN_MARK in each:
                    is_time_query = True

        if is_time_query:
            # TODO: transfor format for both left df and right df so that we can run exact join
            pass

        pairs = candidate_join_column_pairs[0].get_column_number_pairs()
        # generate the pairs for each join_column_pairs
        for each_pair in pairs:
            left_columns = each_pair[0]
            right_columns = each_pair[1]
            try:
                # Only profile the joining columns, otherwise it will be too slow:
                left_metadata = Utils.calculate_dsbox_features(data=left_df, metadata=left_metadata,
                                                               selected_columns=set(left_columns))

                right_metadata = Utils.calculate_dsbox_features(data=right_df, metadata=right_metadata,
                                                                selected_columns=set(right_columns))

                self._logger.info(" - start getting pairs for " + str(each_pair))
                right_df_copy = copy.deepcopy(right_df)

                result, self.pairs = RLTKJoinerGeneral.find_pair(left_df=left_df, right_df=right_df_copy,
                                                                 left_columns=[left_columns],
                                                                 right_columns=[right_columns],
                                                                 left_metadata=left_metadata,
                                                                 right_metadata=right_metadata)

                join_pairs_result.append(result)
                # TODO: figure out some way to compute the joining quality
                candidate_join_column_scores.append(1)
            except:
                self._logger.error("failed when getting pairs for", each_pair)
                traceback.print_exc()

        # choose the best joining results
        all_results = []
        for i in range(len(join_pairs_result)):
            each_result = (pairs[i], candidate_join_column_scores[i], join_pairs_result[i])
            all_results.append(each_result)

        all_results.sort(key=lambda x: x[1], reverse=True)
        if len(all_results) == 0:
            raise ValueError("All join failed")

        if return_format == "ds":
            return_df = d3m_DataFrame(all_results[0][2], generate_metadata=False)
            resources = {augment_resource_id: return_df}
            return_result = d3m_Dataset(resources=resources, generate_metadata=False)
            if generate_metadata:
                metadata_shape_part_dict = self._generate_metadata_shape_part(value=return_result, selector=(),
                                                                              supplied_data=supplied_data)
                for each_selector, each_metadata in metadata_shape_part_dict.items():
                    return_result.metadata = return_result.metadata.update(selector=each_selector,
                                                                           metadata=each_metadata)
                return_result.metadata = self._generate_metadata_column_part_for_general(return_result,
                                                                                         return_result.metadata,
                                                                                         return_format,
                                                                                         augment_resource_id)

        elif return_format == "df":
            return_result = d3m_DataFrame(all_results[0][2], generate_metadata=False)
            if generate_metadata:
                metadata_shape_part_dict = self._generate_metadata_shape_part(value=return_result, selector=(),
                                                                              supplied_data=supplied_data)
                for each_selector, each_metadata in metadata_shape_part_dict.items():
                    return_result.metadata = return_result.metadata.update(selector=each_selector,
                                                                           metadata=each_metadata)
                return_result.metadata = self._generate_metadata_column_part_for_general(return_result,
                                                                                         return_result.metadata,
                                                                                         return_format,
                                                                                         augment_resource_id=None)
        else:
            raise ValueError("Invalid return format was given")
        self._logger.debug("download_general function finished.")
        return return_result

    def _generate_metadata_shape_part(self, value, selector, supplied_data=None) -> dict:
        """
        recursively generate all metadata for shape part, return a dict
        :param value: the input data
        :param selector: a tuple which indicate the selector
        :return: a dict with key as the selector, value as the metadata
        """
        if supplied_data is None:
            supplied_data = self.supplied_data
        generated_metadata = dict()
        generated_metadata['schema'] = CONTAINER_SCHEMA_VERSION
        if isinstance(value, d3m_Dataset):  # type: ignore
            generated_metadata['id'] = supplied_data.metadata.query(())['id']
            generated_metadata['name'] = supplied_data.metadata.query(())['name']
            generated_metadata['location_uris'] = supplied_data.metadata.query(())['location_uris']
            generated_metadata['digest'] = supplied_data.metadata.query(())['digest']
            generated_metadata['description'] = supplied_data.metadata.query(())['description']
            generated_metadata['source'] = supplied_data.metadata.query(())['source']
            generated_metadata['version'] = supplied_data.metadata.query(())['version']
            generated_metadata['structural_type'] = supplied_data.metadata.query(())['structural_type']
            generated_metadata['dimension'] = {
                'name': 'resources',
                'semantic_types': ['https://metadata.datadrivendiscovery.org/types/DatasetResource'],
                'length': len(value),
            }

            metadata_dict = collections.OrderedDict([(selector, generated_metadata)])

            for k, v in value.items():
                metadata_dict.update(self._generate_metadata_shape_part(v, selector + (k,)))

            # It is unlikely that metadata is equal across dataset resources, so we do not try to compact metadata here.

            return metadata_dict

        if isinstance(value, d3m_DataFrame):  # type: ignore
            generated_metadata['semantic_types'] = ['https://metadata.datadrivendiscovery.org/types/Table']
            generated_metadata['structural_type'] = d3m_DataFrame
            generated_metadata['dimension'] = {
                'name': 'rows',
                'semantic_types': ['https://metadata.datadrivendiscovery.org/types/TabularRow'],
                'length': value.shape[0],
            }

            metadata_dict = collections.OrderedDict([(selector, generated_metadata)])

            # Reusing the variable for next dimension.
            generated_metadata = {
                'dimension': {
                    'name': 'columns',
                    'semantic_types': ['https://metadata.datadrivendiscovery.org/types/TabularColumn'],
                    'length': value.shape[1],
                },
            }

            selector_all_rows = selector + (ALL_ELEMENTS,)
            metadata_dict[selector_all_rows] = generated_metadata
            return metadata_dict

    def _generate_metadata_column_part_for_general(self, data, metadata_return, return_format,
                                                   augment_resource_id) -> DataMetadata:
        """
        Inner function used to generate metadata for general search
        """
        # part for adding each column's metadata
        for i, each_column in enumerate(data[augment_resource_id]):
            if return_format == "ds":
                metadata_selector = (augment_resource_id, ALL_ELEMENTS, i)
            elif return_format == "df":
                metadata_selector = (ALL_ELEMENTS, i)
            structural_type = data[augment_resource_id][each_column].dtype.name
            if "int" in structural_type:
                structural_type = int
            elif "float" in structural_type:
                structural_type = float
            else:
                structural_type = str
            metadata_each_column = {"name": each_column, "structural_type": structural_type,
                                    'semantic_types': ('https://metadata.datadrivendiscovery.org/types/Attribute',)}
            metadata_return = metadata_return.update(metadata=metadata_each_column, selector=metadata_selector)

        if return_format == "ds":
            metadata_selector = (augment_resource_id, ALL_ELEMENTS, i + 1)
        elif return_format == "df":
            metadata_selector = (ALL_ELEMENTS, i + 1)
        metadata_joining_pairs = {"name": "joining_pairs", "structural_type": typing.List[int],
                                  'semantic_types': ("http://schema.org/Integer",)}
        metadata_return = metadata_return.update(metadata=metadata_joining_pairs, selector=metadata_selector)

        return metadata_return

    def download_wikidata(self, supplied_data: typing.Union[d3m_Dataset, d3m_DataFrame], generate_metadata=True,
                          return_format="ds", augment_resource_id=AUGMENT_RESOURCE_ID) \
            -> typing.Union[d3m_Dataset, d3m_DataFrame]:
        """
        :param supplied_data: input DataFrame
        :param generate_metadata: control whether to automatically generate metadata of the return DataFrame or not
        :param: return_format: the control parameter to set the return format
        :param: augment_resource_id: the returned dataset id for the augmented data, only valid when return format is "ds"
        :return: return_df: the materialized wikidata d3m_DataFrame,
                            with corresponding pairing information to original_data at last column
        """
        self._logger.debug("Start downloading for wikidata...")
        # prepare the query
        p_nodes_needed = self.search_result["p_nodes_needed"]
        target_q_node_column_name = self.search_result["target_q_node_column_name"]
        if type(supplied_data) is d3m_DataFrame:
            self.supplied_dataframe = copy.deepcopy(supplied_data)
            self.supplied_data = supplied_data
        elif type(supplied_data) is d3m_Dataset:
            self._res_id, supplied_dataframe = d3m_utils.get_tabular_resource(dataset=supplied_data,
                                                                              resource_id=None)
            self.supplied_dataframe = copy.deepcopy(supplied_dataframe)
            self.supplied_data = supplied_data

        q_node_column_number = self.supplied_dataframe.columns.tolist().index(target_q_node_column_name)
        q_nodes_list = set(self.supplied_dataframe.iloc[:, q_node_column_number].tolist())
        q_nodes_query = ""
        p_nodes_query_part = ""
        p_nodes_optional_part = ""
        special_request_part = ""

        for each in q_nodes_list:
            if each != "N/A":
                q_nodes_query += "(wd:" + each + ") \n"
        for each in p_nodes_needed:
            if each not in P_NODE_IGNORE_LIST:
                p_nodes_query_part += " ?" + each
                p_nodes_optional_part += "  OPTIONAL { ?q wdt:" + each + " ?" + each + "}\n"
            if each in SPECIAL_REQUEST_FOR_P_NODE:
                special_request_part += SPECIAL_REQUEST_FOR_P_NODE[each] + "\n"

        sparql_query = "SELECT DISTINCT ?q " + p_nodes_query_part + \
                       " \nWHERE \n{\n  VALUES (?q) { \n " + q_nodes_query + "}\n" + \
                       p_nodes_optional_part + special_request_part + "}\n"
        # if not self.connection_url:
        #     self.connection_url = WIKIDATA_QUERY_SERVER
        #     print("[INFO] Using default connection url: " + self.connection_url)
        # else:
        #     print("[INFO] User-defined connection url given as: " + self.connection_url)
        return_df = d3m_DataFrame()
        try:
            sparql = SPARQLWrapper(self.connection_url)
            self._logger.debug("Connection to datamart blazegraph server at" + self.connection_url)
            sparql.setQuery(sparql_query)
            sparql.setReturnFormat(JSON)
            sparql.setMethod(POST)

            sparql.setRequestMethod(URLENCODED)
            results = sparql.query().convert()
        except:
            self._logger.error("Getting query of wiki data failed!")
            return return_df
        self._logger.debug("Download data finished, start generating d3m metadata.")

        semantic_types_dict = {
            "q_node": ("http://schema.org/Text", 'https://metadata.datadrivendiscovery.org/types/PrimaryKey')}
        q_node_name_appeared = set()
        for result in results["results"]["bindings"]:
            each_result = {}
            q_node_name = result.pop("q")["value"].split("/")[-1]
            if q_node_name in q_node_name_appeared:
                continue
            q_node_name_appeared.add(q_node_name)
            each_result["q_node"] = q_node_name
            for p_name, p_val in result.items():
                each_result[p_name] = p_val["value"]
                # only do this part if generate_metadata is required
                if p_name not in semantic_types_dict:
                    if "datatype" in p_val.keys():
                        semantic_types_dict[p_name] = (
                            self.get_semantic_type(p_val["datatype"]),
                            'https://metadata.datadrivendiscovery.org/types/Attribute',
                            AUGMENTED_COLUMN_SEMANTIC_TYPE
                        )
                    else:
                        semantic_types_dict[p_name] = (
                            "http://schema.org/Text",
                            'https://metadata.datadrivendiscovery.org/types/Attribute',
                            AUGMENTED_COLUMN_SEMANTIC_TYPE
                        )

            return_df = return_df.append(each_result, ignore_index=True)

        p_name_dict = {"q_node": "q_node"}
        for each in return_df.columns.tolist():
            if each.lower().startswith("p") or each.lower().startswith("c"):
                p_name_dict[each] = self.get_node_name(each) + "_for_" + target_q_node_column_name

        # use rltk joiner to find the joining pairs
        joiner = RLTKJoinerWikidata()
        joiner.set_join_target_column_names((self.supplied_dataframe.columns[q_node_column_number], "q_node"))
        result, self.pairs = joiner.find_pair(left_df=self.supplied_dataframe, right_df=return_df)

        # if this condition is true, it means "id" column was added which should not be here
        if return_df.shape[1] == len(p_name_dict) + 2 and "id" in return_df.columns:
            return_df = return_df.drop(columns=["id"])

        metadata_new = DataMetadata()
        self.metadata = dict()
        # add remained attributes metadata
        for each_column in range(0, return_df.shape[1] - 1):
            current_column_name = p_name_dict[return_df.columns[each_column]]
            if return_format == "df":
                each_selector = (ALL_ELEMENTS, each_column)
            elif return_format == "ds":
                each_selector = (self._res_id, ALL_ELEMENTS, each_column)
            # here we do not modify the original data, we just add an extra "expected_semantic_types" to metadata
            metadata_each_column = {"name": current_column_name, "structural_type": str,
                                    'semantic_types': semantic_types_dict[return_df.columns[each_column]]}
            self.metadata[current_column_name] = metadata_each_column
            if generate_metadata:
                metadata_new = metadata_new.update(metadata=metadata_each_column, selector=each_selector)

        # special for joining_pairs column
        if return_format == "df":
            each_selector = (ALL_ELEMENTS, each_column + 1)
        elif return_format == "ds":
            each_selector = (self._res_id, ALL_ELEMENTS, each_column + 1)
        metadata_joining_pairs = {"name": "joining_pairs", "structural_type": typing.List[int],
                                  'semantic_types': ("http://schema.org/Integer",)}
        if generate_metadata:
            metadata_new = metadata_new.update(metadata=metadata_joining_pairs, selector=each_selector)

        # start adding shape metadata for dataset
        if return_format == "ds":
            return_df = d3m_DataFrame(return_df, generate_metadata=False)
            return_df = return_df.rename(columns=p_name_dict)
            resources = {augment_resource_id: return_df}
            return_result = d3m_Dataset(resources=resources, generate_metadata=False)
            if generate_metadata:
                return_result.metadata = metadata_new
                metadata_shape_part_dict = self._generate_metadata_shape_part(value=return_result, selector=(),
                                                                              supplied_data=self.supplied_data)
                for each_selector, each_metadata in metadata_shape_part_dict.items():
                    return_result.metadata = return_result.metadata.update(selector=each_selector,
                                                                           metadata=each_metadata)
            # update column names to be property names instead of number

        elif return_format == "df":
            return_result = d3m_DataFrame(return_df, generate_metadata=False)
            return_result = return_result.rename(columns=p_name_dict)
            if generate_metadata:
                return_result.metadata = metadata_new
                metadata_shape_part_dict = self._generate_metadata_shape_part(value=return_result, selector=(),
                                                                              supplied_data=self.supplied_data)
                for each_selector, each_metadata in metadata_shape_part_dict.items():
                    return_result.metadata = return_result.metadata.update(selector=each_selector,
                                                                           metadata=each_metadata)
        self._logger.debug("download_wikidata function finished.")
        return return_result

    def get_node_name(self, node_code) -> str:
        """
        Function used to get the properties(P nodes) names with given P node
        :param node_code: a str indicate the P node (e.g. "P123")
        :return: a str indicate the P node label (e.g. "inception")
        """
        sparql_query = "SELECT DISTINCT ?x WHERE \n { \n" + \
                       "wd:" + node_code + " rdfs:label ?x .\n FILTER(LANG(?x) = 'en') \n} "
        try:
            sparql = SPARQLWrapper(WIKIDATA_QUERY_SERVER)
            sparql.setQuery(sparql_query)
            sparql.setReturnFormat(JSON)
            sparql.setMethod(POST)
            sparql.setRequestMethod(URLENCODED)
            results = sparql.query().convert()
            return results['results']['bindings'][0]['x']['value']
        except:
            self._logger.error("Getting name of node " + node_code + " failed!")
            return node_code

    def get_semantic_type(self, datatype: str):
        """
        Inner function used to transfer the wikidata semantic type to D3M semantic type
        :param datatype: a str indicate the semantic type adapted from wikidata
        :return: a str indicate the semantic type for D3M
        """
        special_type_dict = {"http://www.w3.org/2001/XMLSchema#dateTime": "http://schema.org/DateTime",
                             "http://www.w3.org/2001/XMLSchema#decimal": "http://schema.org/Float",
                             "http://www.opengis.net/ont/geosparql#wktLiteral":
                                 "https://metadata.datadrivendiscovery.org/types/Location"
                             }
        default_type = "http://schema.org/Text"
        if datatype in special_type_dict:
            return special_type_dict[datatype]
        else:
            self._logger.warning("Not seen data type: ", datatype)
            return default_type

    def _do_wikifier(self, supplied_data):
        """
        Inner function to do wikifier type augment
        :param supplied_data:
        :return:
        """
        self._logger.debug("Start running wikifier.")
        if type(supplied_data) is d3m_Dataset:
            self._res_id, _ = d3m_utils.get_tabular_resource(dataset=supplied_data, resource_id=None,
                                                             has_hyperparameter=False)
            supplied_data_df = supplied_data[self._res_id]
        elif type(supplied_data) is d3m_DataFrame:
            supplied_data_df = supplied_data
        else:
            raise ValueError("Unknown input type for supplied data as: " + str(type(supplied_data)))
        import wikifier
        all_columns = list(range(supplied_data_df.shape[1]))
        can_wikifier_columns = []
        for each in all_columns:
            if type(supplied_data) is d3m_Dataset:
                selector = (self._res_id, ALL_ELEMENTS, each)
            elif type(supplied_data) is d3m_DataFrame:
                selector = (ALL_ELEMENTS, each)
            each_column_semantic_type = supplied_data.metadata.query(selector)['semantic_types']
            if 'http://schema.org/Integer' not in each_column_semantic_type and \
                    'http://schema.org/Float' not in each_column_semantic_type:
                can_wikifier_columns.append(each)

        output_ds = copy.deepcopy(supplied_data)
        wikifier_res = wikifier.produce(pd.DataFrame(supplied_data_df), can_wikifier_columns, None)
        output_ds[self._res_id] = d3m_DataFrame(wikifier_res, generate_metadata=False)
        # update metadata on column length
        selector = (self._res_id, ALL_ELEMENTS)
        old_meta = dict(output_ds.metadata.query(selector))
        old_meta_dimension = dict(old_meta['dimension'])
        old_column_length = old_meta_dimension['length']
        old_meta_dimension['length'] = wikifier_res.shape[1]
        old_meta['dimension'] = frozendict.FrozenOrderedDict(old_meta_dimension)
        new_meta = frozendict.FrozenOrderedDict(old_meta)
        output_ds.metadata = output_ds.metadata.update(selector, new_meta)

        # update each column's metadata
        for i in range(old_column_length, wikifier_res.shape[1]):
            selector = (self._res_id, ALL_ELEMENTS, i)
            metadata = {"name": wikifier_res.columns[i],
                        "structural_type": str,
                        'semantic_types': (
                            "http://schema.org/Text",
                            # "https://metadata.datadrivendiscovery.org/types/CategoricalData",
                            "https://metadata.datadrivendiscovery.org/types/Attribute",
                            "http://wikidata.org/qnode"
                        )}
            output_ds.metadata = output_ds.metadata.update(selector, metadata)
        self._logger.debug("Running wikifier finished.")
        return output_ds

    def augment(self, supplied_data, augment_columns=None, connection_url: str = None, augment_resource_id=AUGMENT_RESOURCE_ID):
        """
        Produces a D3M dataset that augments the supplied data with data that can be retrieved from this search result.
        The augment methods is a baseline implementation of download plus augment.

        Callers who want to control over the augmentation process should use the download method and use their own
        augmentation algorithm.

        Parameters
        ---------
        supplied_data : container.Dataset
            A D3M dataset containing the dataset that is the target for augmentation.
        augment_columns : typing.List[DatasetColumn]
            If provided, only the specified columns from the Datamart dataset that will be added to the supplied dataset.
        connection_url : str
            A connection string used to connect to a specific Datamart deployment. If not provided, a different
            deployment might be used.
        """
        if connection_url:
            self.connection_url = connection_url

        if self.search_type == "wikifier":
            result = self._do_wikifier(supplied_data)
            return result

        if type(supplied_data) is d3m_DataFrame:
            res = self._augment(supplied_data=supplied_data, augment_columns=augment_columns, generate_metadata=True,
                                return_format="df", augment_resource_id=augment_resource_id)
        elif type(supplied_data) is d3m_Dataset:
            self._res_id, self.supplied_data = d3m_utils.get_tabular_resource(dataset=supplied_data, resource_id=None,
                                                                              has_hyperparameter=False)
            res = self._augment(supplied_data=supplied_data, augment_columns=augment_columns, generate_metadata=True,
                                return_format="ds", augment_resource_id=augment_resource_id)
        else:
            raise ValueError("Unknown input type for supplied data as: " + str(type(supplied_data)))
        # res[augment_resource_id] = res[augment_resource_id].astype(str)
        # sometime the index will be not continuous after augment, need to reset to ensure the index is continuous
        res[AUGMENT_RESOURCE_ID].reset_index(drop=True)
        return res

    def _augment(self, supplied_data, augment_columns=None, generate_metadata=True, return_format="ds",
                 augment_resource_id=AUGMENT_RESOURCE_ID):
        """
        Inner detail function
        """
        self._logger.debug("Start running augment function.")
        if type(return_format) is not str or return_format != "ds" and return_format != "df":
            raise ValueError("Unknown return format as" + str(return_format))

        if type(supplied_data) is d3m_Dataset:
            supplied_data_df = supplied_data[self._res_id]
        elif type(supplied_data) is d3m_DataFrame:
            supplied_data_df = supplied_data
        else:
            supplied_data_df = self.supplied_dataframe

        if supplied_data_df is None:
            raise ValueError("Can't find supplied data!")

        download_result = self.download(supplied_data=supplied_data_df, generate_metadata=False, return_format="df")
        download_result = download_result.drop(columns=['joining_pairs'])
        column_names_to_join = None
        r1_paired = set()
        i = 0

        df_dict = dict()
        start = time.time()
        for r1, r2 in self.pairs:
            i += 1
            r1_int = int(r1)
            if r1_int in r1_paired:
                continue
            r1_paired.add(r1_int)
            left_res = supplied_data_df.loc[r1_int]
            right_res = download_result.loc[int(r2)]
            if column_names_to_join is None:
                column_names_to_join = right_res.index.difference(left_res.index)
                # if specified augment columns given, only append these columns
                if augment_columns:
                    augment_columns_with_column_names = []
                    max_length = self.d3m_metadata.query((ALL_ELEMENTS,))['dimension']['length']
                    for each in augment_columns:
                        if each.column_index < max_length:
                            each_column_meta = self.d3m_metadata.query((ALL_ELEMENTS, each.column_index))
                            augment_columns_with_column_names.append(each_column_meta["name"])
                        else:
                            print("[ERROR] Index out of range, will ignore: " + str(each.column_index))
                    column_names_to_join = column_names_to_join.intersection(augment_columns_with_column_names)

                columns_new = left_res.index.tolist()
                columns_new.extend(column_names_to_join.tolist())
            dcit_right = right_res[column_names_to_join].to_dict()
            dict_left = left_res.to_dict()
            dcit_right.update(dict_left)
            df_dict[i] = dcit_right

        df_joined = pd.DataFrame.from_dict(df_dict, "index")
        # add up the rows don't have pairs
        unpaired_rows = set(range(supplied_data_df.shape[0])) - r1_paired
        if len(unpaired_rows) > 0:
            unpaired_rows_list = [i for i in unpaired_rows]
            df_joined = df_joined.append(supplied_data_df.iloc[unpaired_rows_list, :], ignore_index=True)
        import pdb
        pdb.set_trace()
        # ensure that the original dataframe columns are at the first left part
        df_joined = df_joined[columns_new]
        # if search with wikidata, we can remove duplicate Q node column
        self._logger.info("Join finished, totally take " + str(time.time() - start) + " seconds.")
        if self.search_type == "wikidata" and 'q_node' in df_joined.columns:
            df_joined = df_joined.drop(columns=['q_node'])

        if 'id' in df_joined.columns:
            df_joined = df_joined.drop(columns=['id'])

        if generate_metadata:
            # put d3mIndex at first column
            columns_all = list(df_joined.columns)
            if 'd3mIndex' in df_joined.columns:
                oldindex = columns_all.index('d3mIndex')
                columns_all.insert(0, columns_all.pop(oldindex))
            else:
                self._logger.warning("No d3mIndex column found after data-mart augment!!!")
            df_joined = df_joined[columns_all]

        # start adding column metadata for dataset
        if generate_metadata:
            metadata_dict_left = {}
            metadata_dict_right = {}
            if self.search_type == "general":
                # if the search type is general, we need to generate the metadata dict here
                for i, each in enumerate(df_joined):
                    # description = each['description']
                    dtype = df_joined[each].dtype.name
                    if "float" in dtype:
                        semantic_types = (
                            "http://schema.org/Float",
                            "https://metadata.datadrivendiscovery.org/types/Attribute",
                            AUGMENTED_COLUMN_SEMANTIC_TYPE
                        )
                    elif "int" in dtype:
                        semantic_types = (
                            "http://schema.org/Integer",
                            "https://metadata.datadrivendiscovery.org/types/Attribute",
                            AUGMENTED_COLUMN_SEMANTIC_TYPE
                        )
                    else:
                        semantic_types = (
                            # "https://metadata.datadrivendiscovery.org/types/CategoricalData",
                            "https://metadata.datadrivendiscovery.org/types/Attribute",
                            AUGMENTED_COLUMN_SEMANTIC_TYPE
                        )

                    each_meta = {
                        "name": each,
                        "structural_type": str,
                        "semantic_types": semantic_types,
                        # "description": description
                    }
                    metadata_dict_right[each] = frozendict.FrozenOrderedDict(each_meta)
            else:
                # if from wikidata, we should have already generated it
                metadata_dict_right = self.metadata

            if return_format == "df":
                try:
                    left_df_column_length = supplied_data.metadata.query((metadata_base.ALL_ELEMENTS,))['dimension'][
                        'length']
                except Exception:
                    traceback.print_exc()
                    raise ValueError("Getting left metadata information failed!")
            elif return_format == "ds":
                left_df_column_length = \
                supplied_data.metadata.query((self._res_id, metadata_base.ALL_ELEMENTS,))['dimension'][
                    'length']

            # add the original metadata
            for i in range(left_df_column_length):
                if return_format == "df":
                    each_selector = (ALL_ELEMENTS, i)
                elif return_format == "ds":
                    each_selector = (self._res_id, ALL_ELEMENTS, i)
                each_column_meta = supplied_data.metadata.query(each_selector)
                metadata_dict_left[each_column_meta['name']] = each_column_meta

            metadata_new = metadata_base.DataMetadata()
            new_column_names_list = list(df_joined.columns)

            # update each column's metadata
            for i, current_column_name in enumerate(new_column_names_list):
                if return_format == "df":
                    each_selector = (metadata_base.ALL_ELEMENTS, i)
                elif return_format == "ds":
                    each_selector = (augment_resource_id, ALL_ELEMENTS, i)

                if current_column_name in metadata_dict_left:
                    new_metadata_i = metadata_dict_left[current_column_name]
                elif current_column_name in metadata_dict_right:
                    new_metadata_i = metadata_dict_right[current_column_name]
                else:
                    new_metadata_i = {
                        "name": current_column_name,
                        "structural_type": str,
                        "semantic_types": ("https://metadata.datadrivendiscovery.org/types/Attribute",),
                    }
                    self._logger.error("Please check!")
                    self._logger.error("No metadata found for column No." + str(i) + "with name " + current_column_name)

                metadata_new = metadata_new.update(each_selector, new_metadata_i)
            return_result = None

            # start adding shape metadata for dataset
            if return_format == "ds":
                return_df = d3m_DataFrame(df_joined, generate_metadata=False)
                resources = {augment_resource_id: return_df}
                return_result = d3m_Dataset(resources=resources, generate_metadata=False)
                if generate_metadata:
                    return_result.metadata = metadata_new
                    metadata_shape_part_dict = self._generate_metadata_shape_part(value=return_result,
                                                                                  selector=(),
                                                                                  supplied_data=supplied_data)
                    for each_selector, each_metadata in metadata_shape_part_dict.items():
                        return_result.metadata = return_result.metadata.update(selector=each_selector,
                                                                               metadata=each_metadata)
            elif return_format == "df":
                return_result = d3m_DataFrame(df_joined, generate_metadata=False)
                if generate_metadata:
                    return_result.metadata = metadata_new
                    metadata_shape_part_dict = self._generate_metadata_shape_part(value=return_result,
                                                                                  selector=(),
                                                                                  supplied_data=supplied_data)
                    for each_selector, each_metadata in metadata_shape_part_dict.items():
                        return_result.metadata = return_result.metadata.update(selector=each_selector,
                                                                               metadata=each_metadata)
            self._logger.debug("Augment finished")
            return return_result

    def score(self) -> float:
        return self._score

    def id(self) -> str:
        return self._id

    def get_metadata(self) -> DataMetadata:
        return self.d3m_metadata

    def set_join_pairs(self, join_pairs: typing.List["TabularJoinSpec"]) -> None:
        """
        manually set up the join pairs
        :param join_pairs: user specified TabularJoinSpec
        :return:
        """
        self.join_pairs = join_pairs

    def get_join_hints(self, left_df, right_df, left_df_src_id=None, right_src_id=None) -> typing.List[
        "TabularJoinSpec"]:
        """
        Returns hints for joining supplied data with the data that can be downloaded using this search result.
        In the typical scenario, the hints are based on supplied data that was provided when search was called.

        The optional supplied_data argument enables the caller to request recomputation of join hints for specific data.

        :return: a list of join hints. Note that datamart is encouraged to return join hints but not required to do so.
        """
        self._logger.debug("Start getting join hints.")
        right_join_column_name = self.search_result['variableName']['value']
        left_columns = []
        right_columns = []

        for each in self.query_json['variables'].keys():
            left_index = left_df.columns.tolist().index(each)
            right_index = right_df.columns.tolist().index(right_join_column_name)
            left_index_column = DatasetColumn(resource_id=left_df_src_id, column_index=left_index)
            right_index_column = DatasetColumn(resource_id=right_src_id, column_index=right_index)
            left_columns.append([left_index_column])
            right_columns.append([right_index_column])

        results = TabularJoinSpec(left_columns=left_columns, right_columns=right_columns)
        self._logger.debug("Get join hints finished, the join hints are:")
        self._logger.debug(str(left_index) + ", " + str(right_index))
        return [results]

    def serialize(self):
        result = dict()
        result['id'] = self._id
        result['score'] = self._score

        result['metadata'] = dict()
        result['metadata']['connection_url'] = self.connection_url
        result['metadata']['search_result'] = self.search_result
        result['metadata']['query_json'] = self.query_json
        result['metadata']['search_type'] = self.search_type
        augmentation = dict()
        augmentation['properties'] = "join"
        if self.search_type == "general":
            left_col_number = []
            right_col_number = None
            for each_key, each_value in literal_eval(self.search_result['extra_information']['value']).items():
                if 'name' in each_value.keys() and each_value['name'] == self.search_result['variableName']['value']:
                    right_col_number = int(each_key.split("_")[-1])
                    break
            augmentation['right_columns'] = [right_col_number]
            if self.supplied_dataframe is None:
                self._logger.error(
                    "Can't get supplied dataframe information, failed to find the left join column number")
            else:
                for each in self.query_json['variables'].keys():
                    left_col_number.append(self.supplied_dataframe.columns.tolist().index(each))
            augmentation['left_columns'] = left_col_number
        elif self.search_type == "wikidata":
            left_col_number = self.supplied_dataframe.columns.tolist().index(
                self.search_result['target_q_node_column_name'])
            augmentation['left_columns'] = [left_col_number]
            right_col_number = len(self.search_result['p_nodes_needed']) + 1
            augmentation['right_columns'] = [right_col_number]
        result['augmentation'] = augmentation
        result['datamart_type'] = 'isi'
        result_str = json.dumps(result)

        return result_str

    @classmethod
    def deserialize(cls, serialize_result_str):
        serialize_result = json.loads(serialize_result_str)
        if "datamart_type" not in serialize_result or serialize_result["datamart_type"] != "isi":
            raise ValueError("False datamart type found")
        supplied_data = None  # serialize_result['metadata']['supplied_data']
        search_result = serialize_result['metadata']['search_result']
        query_json = serialize_result['metadata']['query_json']
        search_type = serialize_result['metadata']['search_type']
        return DatamartSearchResult(search_result, supplied_data, query_json, search_type)

    def __getstate__(self) -> typing.Dict:
        """
        This method is used by the pickler as the state of object.
        The object can be recovered through this state uniquely.
        Returns:
            state: Dict
                dictionary of important attributes of the object
        """
        state = dict()
        state["search_result"] = self.__dict__["search_result"]
        state["query_json"] = self.__dict__["query_json"]
        state["search_type"] = self.__dict__["search_type"]

        return state

    def __setstate__(self, state: typing.Dict) -> None:
        """
        This method is used for unpickling the object. It takes a dictionary
        of saved state of object and restores the object to that state.
        Args:
            state: typing.Dict
                dictionary of the objects picklable state
        Returns:
        """
        self = self.__init__(search_result=state['search_result'],
                             supplied_data=None,
                             query_json=state['query_json'],
                             search_type=state['search_type'])


class AugmentSpec:
    """
    Abstract class for D3M augmentation specifications
    """
    pass


class TabularJoinSpec(AugmentSpec):
    """
    A join spec specifies a possible way to join a left dataset with a right dataset. The spec assumes that it may
    be necessary to use several columns in each datasets to produce a key or fingerprint that is useful for joining
    datasets. The spec consists of two lists of column identifiers or names (left_columns, left_column_names and
    right_columns, right_column_names).

    In the simplest case, both left and right are singleton lists, and the expectation is that an appropriate
    matching function exists to adequately join the datasets. In some cases equality may be an appropriate matching
    function, and in some cases fuzz matching is required. The join spec does not specify the matching function.

    In more complex cases, one or both left and right lists contain several elements. For example, the left list
    may contain columns for "city", "state" and "country" and the right dataset contains an "address" column. The join
    spec pairs up ["city", "state", "country"] with ["address"], but does not specify how the matching should be done
    e.g., combine the city/state/country columns into a single column, or split the address into several columns.
    """

    def __init__(self, left_columns: typing.List[typing.List[DatasetColumn]],
                 right_columns: typing.List[typing.List[DatasetColumn]],
                 left_resource_id: str = None, right_resource_id: str = None) -> None:

        self.left_resource_id = left_resource_id
        self.right_resource_id = right_resource_id
        self.left_columns = left_columns
        self.right_columns = right_columns
        if len(self.left_columns) != len(self.right_columns):
            shorter_len = min(len(self.right_columns), len(self.left_columns))
            self.left_columns = self.left_columns[:shorter_len]
            self.right_columns = self.right_columns[:shorter_len]
            print("The join spec length on left and right are different! Part of them will be ignored")

        # we can have list of the joining column pairs
        # each list inside left_columns/right_columns is a candidate joining column for that dataFrame
        # each candidate joining column can also have multiple columns

    def get_column_number_pairs(self):
        """
            A simple function used to get the pairs of column numbers only
            For example, it will return a join pair like ([1,2], [1])
        """
        all_pairs = []
        for each in zip(self.left_columns, self.right_columns):
            left = []
            right = []
            for each_left_col in each[0]:
                left.append(each_left_col.column_index)
            for each_right_col in each[1]:
                right.append(each_right_col.column_index)
            all_pairs.append((left, right))
        return all_pairs


class UnionSpec(AugmentSpec):
    """
    A union spec specifies how to combine rows of a dataframe in the left dataset with a dataframe in the right dataset.
    The dataframe after union should have the same columns as the left dataframe.

    Implementation: TBD
    """
    pass


class TemporalGranularity(utils.Enum):
    YEAR = 1
    MONTH = 2
    DAY = 3
    HOUR = 4
    SECOND = 5


class GeospatialGranularity(utils.Enum):
    COUNTRY = 1
    STATE = 2
    COUNTY = 3
    CITY = 4
    POSTAL_CODE = 5


class ColumnRelationship(utils.Enum):
    CONTAINS = 1
    SIMILAR = 2
    CORRELATED = 3
    ANTI_CORRELATED = 4
    MUTUALLY_INFORMATIVE = 5
    MUTUALLY_UNINFORMATIVE = 6


class DatamartQuery:
    """
    A Datamart query consists of two parts:

    * A list of keywords.

    * A list of required variables. A required variable specifies that a matching dataset must contain a variable
      satisfying the constraints provided in the query. When multiple required variables are given, the matching
      dataset should contain variables that match each of the variable constraints.

    The matching is fuzzy. For example, when a user specifies a required variable spec using named entities, the
    expectation is that a matching dataset contains information about the given named entities. However, due to name,
    spelling, and other differences it is possible that the matching dataset does not contain information about all
    the specified entities.

    In general, Datamart will do a best effort to satisfy the constraints, but may return datasets that only partially
    satisfy the constraints.
    """

    def __init__(self, keywords: typing.List[str] = list(), variables: typing.List['VariableConstraint'] = list(),
                 search_type: str = "general", keywords_search: typing.List[str] = list(), title_search: str = "",
                 variables_search: dict() = dict()) -> None:
        self.search_type = search_type
        self.keywords = keywords
        self.variables = variables
        self.keywords_search = keywords_search
        self.title_search = title_search
        self.variables_search = variables_search


class VariableConstraint(object):
    """
    Abstract class for all variable constraints.
    """

    def __init__(self, key: str, values: str):
        self.key = key
        self.values = values


class NamedEntityVariable(VariableConstraint):
    """
    Specifies that a matching dataset must contain a variable including the specified set of named entities.

    For example, if the entities are city names, the expectation is that a matching dataset must contain a variable
    (column) with the given city names. Due to spelling differences and incompleteness of datasets, the returned
    results may not contain all the specified entities.

    Parameters
    ----------
    entities : List[str]
        List of strings that should be contained in the matched dataset column.
    """

    def __init__(self, entities: typing.List[str]) -> None:
        self.entities = entities


class TemporalVariable(VariableConstraint):
    """
    Specifies that a matching dataset should contain a variable with temporal information (e.g., dates) satisfying
    the given constraint.

    The goal is to return a dataset that covers the requested temporal interval and includes
    data at a requested level of granularity.

    Datamart will return best effort results, including datasets that may not fully cover the specified temporal
    interval or whose granularity is finer or coarser than the requested granularity.

    Parameters
    ----------
    start : datetime
        A matching dataset should contain a variable with temporal information that starts earlier than the given start.
    end : datetime
        A matching dataset should contain a variable with temporal information that ends after the given end.
    granularity : TemporalGranularity
        A matching dataset should provide temporal information at the requested level of granularity.
    """

    def __init__(self, start: datetime.datetime, end: datetime.datetime,
                 granularity: TemporalGranularity = None) -> None:
        self.start = start
        self.end = end
        self.granularity = granularity


class GeospatialVariable(VariableConstraint):
    """
    Specifies that a matching dataset should contain a variable with geospatial information that covers the given
    bounding box.

    A matching dataset may contain variables with latitude and longitude information (in one or two columns) that
    cover the given bounding box.

    Alternatively, a matching dataset may contain a variable with named entities of the given granularity that provide
    some coverage of the given bounding box. For example, if the bounding box covers a 100 mile square in Southern
    California, and the granularity is City, the result should contain Los Angeles, and other cities in Southern
    California that intersect with the bounding box (e.g., Hawthorne, Torrance, Oxnard).

    Parameters
    ----------
    latitude1 : float
        The latitude of the first point
    longitude1 : float
        The longitude of the first point
    latitude2 : float
        The latitude of the second point
    longitude2 : float
        The longitude of the second point
    granularity : GeospatialGranularity
        Requested geospatial values are well matched with the requested granularity
    """

    def __init__(self, latitude1: float, longitude1: float, latitude2: float, longitude2: float,
                 granularity: GeospatialGranularity = None) -> None:
        self.latitude1 = latitude1
        self.longitude1 = longitude1
        self.latitude2 = latitude2
        self.longitude2 = longitude2
        self.granularity = granularity


class TabularVariable(object):
    """
    Specifies that a matching dataset should contain variables related to given columns in the supplied_dataset.

    The relation ColumnRelationship.CONTAINS specifies that string values in the columns overlap using the string
    equality comparator. If supplied_dataset columns consists of temporal or spatial values, then
    ColumnRelationship.CONTAINS specifies overlap in temporal range or geospatial bounding box, respectively.

    The relation ColumnRelationship.SIMILAR specifies that string values in the columns overlap using fuzzy string matching.

    The relations ColumnRelationship.CORRELATED and ColumnRelationship.ANTI_CORRELATED specify the columns are
    correlated and anti-correlated, respectively.

    The relations ColumnRelationship.MUTUALLY_INFORMATIVE and ColumnRelationship.MUTUALLY_UNINFORMATIVE specify the columns
    are mutually and anti-correlated, respectively.

    Parameters:
    -----------
    columns : typing.List[int]
        Specify columns in the dataframes of the supplied_dataset
    relationship : ColumnRelationship
        Specifies how the the columns in the supplied_dataset are related to the variables in the matching dataset.
    """

    def __init__(self, columns: typing.List[DatasetColumn], relationship: ColumnRelationship) -> None:
        self.columns = columns
        self.relationship = relationship
