import memcache
import argparse
import subprocess
import traceback
import datetime
import logging
import time
import json
import pickle
import wikifier
import pandas as pd
from collections import defaultdict
from datamart_isi import config
from datamart_isi.cache.materializer_cache import MaterializerCache
from SPARQLWrapper import SPARQLWrapper, JSON, POST, URLENCODED
from d3m.container import DataFrame as d3m_DataFrame
from d3m.container import Dataset as d3m_Dataset
from d3m.base import utils as d3m_utils
from datamart_isi.utilities import d3m_wikifier
from datamart_isi.utilities.utils import Utils
from datamart_isi.utilities import connection
from datamart_isi.cache.materializer_cache import MaterializerCache


# logging.basicConfig(format=FORMAT, stream=sys.stdout, level=logging.DEBUG)
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)s] %(name)s -- %(message)s",
                    datefmt='%m-%d %H:%M',
                    filename='memcache_updater.log',
                    filemode='w')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s -- %(message)s")
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

# set default update query each day
CACHE_EXIPRE_TIME_LENGTH = config.cache_expire_time
MEMACHE_SERVER = config.default_datamart_url
MEMACHE_SERVER_PORT = config.memcache_server_suffix[1:]
WIKIDATA_QUERY_SERVER = "http://" + config.default_datamart_url + config.wikidata_server_suffix


class DatamartCacheUpdater:
    def __init__(self, client_ip: str = MEMACHE_SERVER, client_port=MEMACHE_SERVER_PORT):
        self.client_ip = client_ip
        self.mc = memcache.Client([client_ip], debug=True, server_max_value_length=1024*1024*100)
        self.expire_time_length = CACHE_EXIPRE_TIME_LENGTH
        self.maximum_key_amount = 100000
        self.client_port = client_port
        self._logger = logging.getLogger(__name__)

    def update_wikidata_query(self, query_dict: dict) -> None:
        """
        The function used to check whether a query cache in memcache need to be run again to ensure the content are up-to-date
        It will check the timestamp of the query results uploaded to determine whether to update or not
        query_dict: adapted from function `load_all_cache_keys_from_file`
        """
        self._logger.info("Start updating memcache queries!")
        start = time.time()

        for cache_key, cache_value in query_dict.items():
            # if it has supplied_data as a key, it means it is a augment cache, skip
            if "supplied_data" in cache_value.keys():
                continue
            timestamp = cache_value.get("timestamp")
            query = cache_value.get("query")
            result = cache_value.get("result")
            need_rerun_query = False
            if query is None:
                self._logger.error("Query hash tag " + cache_key + " do not have query content!")
                continue
            elif timestamp is None or datetime.datetime.now().timestamp() - float(timestamp) > self.expire_time_length:
                self._logger.info("Query hash tag " + cache_key + " is out-dated, will update.")
                need_rerun_query = True
            elif not result:
                self._logger.warning("Query hash " + cache_key + " do not have results, will update.")
                need_rerun_query = True

            if need_rerun_query:
                self._logger.info("Start updating query for hash tag" + cache_key)
                try:
                    new_result = self.run_sparql_query(query)
                except:
                    self._logger.error("Running query for hash tag " + cache_key + " failed!")
                    # if query failed, skip
                    continue
                if result and not new_result:
                    self._logger.error("Query return no results but old query have! Is that correct?")
                    self._logger.error("Not update query this time for query tag " + cache_key)
                else:
                    # update query results
                    response_code = self.mc.set("results_" + cache_key, pickle.dumps(new_result))
                    if not response_code:
                        self._logger.error("Update query results for hash tag " + cache_key + " failed!")
                    else:
                        self._logger.info("Update query results for hash tag " + cache_key + " success!")
                        response_code = self.mc.set("timestamp_" + cache_key, str(datetime.datetime.now().timestamp()))
                        if not response_code:
                            self._logger.error("Update timestamp for hash tag " + cache_key + " failed!")
                        else:
                            self._logger.info("Update timestamp for hash tag " + cache_key + " success!")

        used_time = time.time() - start
        self._logger.info("Updating all queries finished. Totally take {time_used} seconds.".format(time_used=str(used_time)))

    def update_wikifier_query(self, query_dict: dict) -> None:
        """
        The function used to check whether a query cache in memcache need to be run again to ensure the content are up-to-date
        It will check the timestamp of the query results uploaded to determine whether to update or not
        query_dict: adapted from function `load_all_cache_keys_from_file`
        """
        self._logger.info("Start updating memcache queries!")
        start = time.time()

        for cache_key, cache_value in query_dict.items():
            # if it has query as a key, it means it is a wikidata cache, skip
            if "query" in cache_value.keys():
                continue
            timestamp = cache_value.get("timestamp")
            supplied_data = cache_value.get("supplied_data")
            search_result = cache_value.get("search_result")
            augment = cache_value.get("augment")
            need_rerun_query = False

            if supplied_data is None or search_result is None:
                self._logger.error("Query hash tag " + cache_key + " do not have supplied data or search result part!")
                continue
            elif timestamp is None or datetime.datetime.now().timestamp() - float(timestamp) > self.expire_time_length:
                self._logger.info("Query hash tag " + cache_key + " is out-dated, will update.")
                need_rerun_query = True
            elif not augment:
                self._logger.warning("Query hash " + cache_key + " do not have results, maybe a bad augment cache. skip")
                need_rerun_query = False

            if need_rerun_query:
                self._logger.info("Start updating query for hash tag" + cache_key)
                try:
                    search_result_loaded = json.loads(search_result)
                    if "datamart_type" in search_result_loaded:
                        if search_result_loaded["id"] == "wikifier":
                            self._logger.info("Datamart augmentation wikifier type found: " + cache_key)
                            self.update_wikifier_result(supplied_data, cache_key)
                    elif "target_columns" in search_result_loaded:
                        self._logger.info("Direct calling wikifier type cache found: " + cache_key)
                        self.update_wikifier_result(supplied_data, cache_key)
                    else:
                        self._logger.info("Currently do not update for this type of general search:")
                        self._logger.info(search_result)
                except:
                    self._logger.error("Running query for hash tag " + cache_key + " failed!")
                    # if query failed, skip
                    continue

    def update_wikifier_for_datasets_in_datamart(self):
        query_get_all_datasets = """
            prefix ps: <http://www.wikidata.org/prop/statement/> 
            prefix pq: <http://www.wikidata.org/prop/qualifier/> 
            prefix p: <http://www.wikidata.org/prop/>
            
            SELECT ?dataset ?url ?file_type ?extra_information
            WHERE 
            {
              ?dataset p:P2699/ps:P2699 ?url.
              ?dataset p:P2701/ps:P2701 ?file_type.
              ?dataset p:C2010/ps:C2010 ?extra_information.
            
            }
            """
        blaze_graph_server_address = config.default_datamart_url + config.general_search_server_suffix
        if not blaze_graph_server_address.startswith("http://"):
            blaze_graph_server_address = "http://" + blaze_graph_server_address
        update_cache_manager = MaterializerCache("http://dsbox02.isi.edu:9000")
        result = self.run_sparql_query(query_get_all_datasets, blaze_graph_server_address)
        for each_dataset_info in result:
            df_without_wikifier = MaterializerCache.materialize(metadata=each_dataset_info, run_wikifier=False)
            df_with_wikifier = wikifier.produce(df_without_wikifier)
            key_not_run_wikifier = update_cache_manager.get_hash_key(each_dataset_info, run_wikifier=False)
            key_run_wikifier = update_cache_manager.get_hash_key(each_dataset_info, run_wikifier=True)
            update_cache_manager.add_to_memcache(df_without_wikifier, key_not_run_wikifier)
            update_cache_manager.add_to_memcache(df_with_wikifier, key_run_wikifier)

    def save_all_keys(self, file_loc: str = "all_keys.out") -> None:
        """
        function to use shell command to save all keys from mecache
        Default setting will get all keys from local memcache server with default port, and maximum 100,000 keys will get
        """
        self._logger.info("Starting saving all keys...")
        bash_command = "MEMCHOST=" + self.client_ip + """; printf "stats items\n" | nc $MEMCHOST """ + self.client_port\
                       + """ | grep ":number" | awk -F":" '{print $2}' | xargs -I % printf "stats cachedump % """ \
                       + str(self.maximum_key_amount) + """\r\n" | nc $MEMCHOST """ + self.client_port + " > " \
                       + file_loc

        p = subprocess.Popen(bash_command, stdout=subprocess.PIPE, shell=True, stderr=subprocess.STDOUT)
        while p.poll() is None:
            out = p.stdout.readline().strip()
            if out:
                print (bytes.decode(out))
        self._logger.info("All keys of memcache save finished at " + file_loc)

    def save_all_values_from_key_file(self, key_file_loc: str = "all_keys.out", save_loc: str = "memcache_backup.pkl"):
        mc = memcache.Client([self.client_ip], debug=True)
        save_dict = dict()
        with open(key_file_loc) as f:
            content = [line.rstrip('\n') for line in f]
        for each in content:
            try:
                if each.startswith("ITEM"):
                    each_key = each.split(" ")[1]
                    each_value = mc.get(each_key)
                    save_dict[each_key] = each_value
            except:
                self._logger.error("ERROR when processing " + each)
                traceback.print_exc()
        with open(save_loc, 'wb') as f:
            pickle.dump(save_dict, f)

    def load_all_saved_key_value_pairs(self, save_loc: str = "memcache_backup.pkl"):
        mc = memcache.Client([self.client_ip], debug=True)
        save_dict = dict()
        with open(save_loc, 'rb') as f:
            loaded_dict = pickle.load(f)
        for each_key, each_value in loaded_dict.items():
            try:
                mc.set(each_key, each_value)
            except:
                self._logger.error("ERROR when loading " + each_key)
                traceback.print_exc()

    def load_all_cache_keys_from_file(self, file_loc: str = "all_keys.out"):
        mc = memcache.Client([self.client_ip], debug=True)
        query_dict = defaultdict(dict)
        seen_items = set()
        with open(file_loc) as f:
            content = [line.rstrip('\n') for line in f]
        for each in content:
            try:
                if each.startswith("ITEM"):
                    each_key = each.split(" ")[1]
                    if each_key in seen_items:
                        continue
                    seen_items.add(each_key)
                    if each_key.startswith("results"):
                        hash_part = each_key.split("results_")[1]
                        query_dict[hash_part]["results"] = mc.get(each_key)
                    elif each_key.startswith("query"):
                        hash_part = each_key.split("query_")[1]
                        query_dict[hash_part]["query"] = mc.get(each_key)
                    elif each_key.startswith("timestamp"):
                        hash_part = each_key.split("timestamp_")[1]
                        query_dict[hash_part]["timestamp"] = mc.get(each_key)
                    elif each_key.startswith("augment"):
                        hash_part = each_key.split("augment_")[1]
                        query_dict[hash_part]["augment"] = mc.get(each_key)
                    elif each_key.startswith("supplied_data"):
                        hash_part = each_key.split("supplied_data")[1]
                        query_dict[hash_part]["supplied_data"] = mc.get(each_key)
                    elif each_key.startswith("search_result"):
                        hash_part = each_key.split("search_result")[1]
                        query_dict[hash_part]["search_result"] = mc.get(each_key)

            except:
                self._logger.error("ERROR when processing " + each)
                traceback.print_exc()
        self._logger.debug("Following query hash tag found in memcache:")
        for i, each in enumerate(query_dict.keys()):
            self._logger.debug("No." + str(i) + " " + each)
        return query_dict

    @staticmethod
    def run_sparql_query(sparql_query, server=WIKIDATA_QUERY_SERVER):
        sparql = SPARQLWrapper(server)
        sparql.setQuery(sparql_query)
        sparql.setReturnFormat(JSON)
        sparql.setMethod(POST)
        sparql.setRequestMethod(URLENCODED)
        result = sparql.query().convert()['results']['bindings']
        return result

    def update_wikifier_result(self, supplied_data_value, cache_key):
        with open(supplied_data_value, 'rb') as f:
            loaded_supplied_data = pickle.load(f)
        if type(loaded_supplied_data) is d3m_Dataset:
            wikifier_result = d3m_wikifier.run_wikifier(supplied_data=loaded_supplied_data)
        elif type(loaded_supplied_data) is pd.DataFrame:
            wikifier_result = wikifier.produce(loaded_supplied_data, use_cache=False)
        else:  # if type(loaded_supplied_data) is d3m_DataFrame:
            raise ValueError("Not support type of supplied_data as " + str(type(supplied_data_value)))

        # save new results to original location
        with open(supplied_data_value, 'wb') as f:
            pickle.dump(wikifier_result, f)
        # update timestamp
        response_code = self.mc.set("timestamp_" + cache_key, str(datetime.datetime.now().timestamp()))
        if not response_code:
            self._logger.error("Update timestamp for hash tag " + cache_key + " failed!")
        else:
            self._logger.debug("Update timestamp for hash tag " + cache_key + " success!")
        self._logger.debug("Update wikifier cache success!")


def main(update_time: str, update_frequency: str):
    if update_time == "now":
        pass
    else:
        try:
            now = datetime.datetime.now()
            seconds_to_time_update = (now.replace(hour=0, minute=0, second=0, microsecond=0) - now).total_seconds() + 3600 * (24 + int(update_time))
            _logger.info("Specialize updating time given, will wait until then...")
            _logger.info("Will start update on " + str(update_time) + ":00:00")
            time.sleep(seconds_to_time_update)
        except:
            _logger.error("Wrong update time format given, will update now!")

    try:
        update_frequency = float(update_frequency)
    except:
        _logger.error("Wrong update frequency format given, will use default value as 24 hours")
        update_frequency = 24

    cache_updater = DatamartCacheUpdater()
    while True:
        _logger.info("-"*50 + "Start updating" + "-" * 50)
        cache_updater.save_all_keys()
        memcache_keys = cache_updater.load_all_cache_keys_from_file()
        cache_updater.update_wikidata_query(memcache_keys)
        cache_updater.update_wikifier_query(memcache_keys)
        # cache_updater.update_wikifier_for_datasets_in_datamart()
        cache_updater.save_all_values_from_key_file()
        _logger.info("-"*50 + "End of update!" + "-" * 50)
        _logger.info("Start waiting for " + str(update_frequency) + " hours.")
        # sleep 24 hours to do next time running
        time.sleep(3600 * update_frequency)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='The auto query updater service')
    parser.add_argument('update_time', help='The time of hour that want it to run update service. Default is running update now')
    parser.add_argument('update_frequency', help='The update frequency, how long in hour should the system to update the query. Default is running each 24 hours')
    args = parser.parse_args()
    update_time = args.update_time
    update_frequency = args.update_frequency
    main(update_time=update_time, update_frequency=update_frequency)
