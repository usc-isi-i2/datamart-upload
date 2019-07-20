import memcache
import argparse
import subprocess
from collections import defaultdict
import traceback
import datetime
import logging
import time
import pickle
from datamart_isi import config
from SPARQLWrapper import SPARQLWrapper, JSON, POST, URLENCODED

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
# logging.basicConfig(format=FORMAT, stream=sys.stdout, level=logging.DEBUG)

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
MEMACHE_SERVER = config.memcache_server
WIKIDATA_QUERY_SERVER = config.wikidata_server

def update_wikidata_query(query_dict: dict, expire_time_length: int=CACHE_EXIPRE_TIME_LENGTH, client_ip: str=MEMACHE_SERVER) -> None:
    """
    The function used to check whether a query cache in memcache need to be run again to ensure the content are up-to-date
    It will check the timestamp of the query results uploaded to determine whether to update or not
    query_dict: adapted from function `load_all_wikidata_keys_from_file`
    """
    _logger.info("Start updating memcache queries!")
    start = time.time()
    mc = memcache.Client([client_ip], debug=True, server_max_value_length=1024*1024*100) 
    for query_key, query_value in query_dict.items():
        timestamp = query_value.get("timestamp")
        query = query_value.get("query")
        result = query_value.get("result")
        need_rerun_query = False
        if query is None:
            _logger.error("Query hash tag " + query_key + " do not have query content!")
            continue
        elif timestamp is None or datetime.datetime.now().timestamp() - float(timestamp) > expire_time_length:
            _logger.info("Query hash tag " + query_key + " is out-dated, will update.")
            need_rerun_query = True
        elif not result:
            _logger.warning("Query hash " + query_key + " do not have results, will update.")
            need_rerun_query = True

        if need_rerun_query:
            _logger.info("Start updating query for hash tag" + query_key)
            try:
                new_result = run_sparql_query(query)
            except:
                _logger.error("Running query for hash tag " + query_key + " failed!")
            if result and not new_result:
                _logger.error("Query return no results but old query have! Is that correct?")
                _logger.error("Not update query this time for query tag " + query_key)
            else:
                # update query results
                response_code = mc.set("results_" + query_key, pickle.dumps(new_result))
                if not response_code:
                    _logger.error("Update query results for hash tag " + query_key + " failed!")
                else:
                    _logger.info("Update query results for hash tag " + query_key + " success!")
                    response_code = mc.set("timestamp_" + query_key, str(datetime.datetime.now().timestamp()))
                    if not response_code:
                        _logger.error("Update timestamp for hash tag " + query_key + " failed!")
                    else:
                        _logger.info("Update timestamp for hash tag " + query_key + " success!")

    used_time = time.time() - start
    _logger.info("Updating all queries finished. Totally take {time_used} seconds.".format(time_used=str(used_time)))

def save_all_keys(client_ip: str="localhost", client_port:str="11211", maximum_key_amount=100000, file_loc:str="all_keys.out") -> None:
    """
    function to use shell command to save all keys from mecache
    Default setting will get all keys from local memcache server with default port, and maximum 100,000 keys will get
    """
    _logger.info("Starting saving all keys...")
    bash_command = "MEMCHOST=" + client_ip + """; printf "stats items\n" | nc $MEMCHOST """ + client_port + """ | grep ":number" | awk -F":" '{print $2}' | xargs -I % printf "stats cachedump % """ + str(maximum_key_amount) + """\r\n" | nc $MEMCHOST """ + client_port + " > " + file_loc #format(client_ip=client_ip, port=client_port, maximum_key_amount = maximum_key_amount, file_loc=file_loc)
    p = subprocess.Popen(bash_command, stdout=subprocess.PIPE, shell=True, stderr=subprocess.STDOUT)
    while p.poll() == None:
        out = p.stdout.readline().strip()
        if out:
            print (bytes.decode(out))
    _logger.info("All keys of memcache save finished at " + file_loc)

def load_all_wikidata_keys_from_file(file_loc:str="all_keys.out", client_ip: str=MEMACHE_SERVER):
    mc = memcache.Client([client_ip], debug=True)
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
        except:
            _logger.error("ERROR when processing " + each)
            traceback.print_exc()
    _logger.info("Following query hash tag found in memcache:")
    for i, each in enumerate(query_dict.keys()):
        _logger.info("No." + str(i) + " " + each)
    return query_dict

def run_sparql_query(sparql_query):
    sparql = SPARQLWrapper(WIKIDATA_QUERY_SERVER)
    sparql.setQuery(sparql_query)
    sparql.setReturnFormat(JSON)
    sparql.setMethod(POST)
    sparql.setRequestMethod(URLENCODED)
    result = sparql.query().convert()['results']['bindings']
    return result

def main(update_time:str):
    if update_time == "now":
        pass
    else:
        try:
            now = datetime.datetime.now()
            seconds_to_time_update = (now.replace(hour=0, minute=0, second=0, microsecond=0) - now).total_seconds() + 3600 * (24 + int(update_time))
            _logger.info("Specialize updating time given, will wait until then...")
            _logger.info("Will strat update on " + str(update_time) + ":00:00")
            time.sleep(seconds_to_time_update)
        except:
            _logger.error("Wrong update time format given, will update now!")
    while True:
        save_all_keys()
        memcache_keys = load_all_wikidata_keys_from_file()
        update_wikidata_query(memcache_keys)

        # sleep 24 hours to do next time running
        time.sleep(3600*24)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='The auto query updater service')
    parser.add_argument('update_time', help='The time of hour that want it to run update service.')
    args = parser.parse_args()
    update_time = args.update_time
    main(update_time=update_time)
        