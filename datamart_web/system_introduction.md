## Datamart System Introduction
### Hardware
Currently most of the service is running on dsbox02 machine. This machine has 
- 48 cores (2.2GHz for each core)
- 252GB physical memory
- One 4TB SSD(on sata interface)
- One 2TB SSD(on sata interface)
- Two 10TB HDD(in RAID1 mode) and the system is installed on this disk
- The port `9000` and `9001` are open to public network outside isi
- 9000 is the REST api service
- 9001 is the front end page for datamart (not implemented yet)
- The opearting system is CentOS 7

### Software
Following services is or will running on datamart service machine
All datamart related service should be ran on `datamart` account on `dsbox02.isi.edu`, it is a local account, can be loggin with `sudo su datamart`.
Currently all things that running on the datamart is under `tmux` system with 3 sessions.
- `datamart_backend`: It has the blazegraph running pannel and `datamart REST api` running pannel.
- `memcache`: It has the running `Upload Manager` system which update the wikidata query.
- `upload_workers`: It has 5 rq worker started for running upload.

#### Wikidata SPARQL Service
This is the main query service for any people that want to use our own wikidata query service (has a longer timeout limitation). Currently the query webpage service is running on `dsbox02.isi.edu:8888`. This service is running on user `wikidata`.
The data is stored on `/data02/wikidata`. There are totally 2 wikidata database:
- `/wikidata-query-rdf` stored on triple mode, same as wikidata official server
- `/wikidata-query-rdf-2` stored on quads mode, it will help in the condition with multiple graphs

It will take up to 128GB memories. So please ensure leave enough space for the server.

#### Wikifier Service (identifier)
This is the old version of wikifier. Basically it requires a Redis server, a data file(a large json) and a Flask server for POST interface. ~~Currenly it is running on minds03 machine,~~ the data has been copied to `dsbox02` server.
The following config is used to start the redis service in docker:
- `$ docker run --detach -m 50g --name wikifier-redis --publish 6379:6379 --volume=$HOME/data:/data --entrypoint redis-server redis --appendonly yes`
- ~~-The memory limit on this redis server is set to 50GB~~ No memory usage limit on redis now.
- The data file of redis is stored at `/data00/dsbox/datamart/data`

#### Wikifier Service (new)
This is the new version of wikifier. The codes are still under developing. Also need to run on dsbox02 later.

#### Wikidata Vector Service
This is the vector service adapted from facebook. It will generate a 200-dimension vector for each Q nodes. Currently it is running on sitaware.isi.edu. Should also be migrated to dsbox02 later.

#### Datamart Blazegraph Database
This is the database for storing datamart's datasets (like csvs, or wikipedia tables). Currently the service is running on `dsbox02.isi.edu:9002`. The main namespace used now is `datamart3`. This service is running on user `datamart`.
To restart the service, just login to the datamart user, there is a tmux session named `datamart_backend` and the service is running on that session.
Currently, the detail config used is `$ java -server -Xmx4g -Djetty.port=9002 -jar blazegraph.jar`.
The corresponding files are stored `/data00/dsbox/datamart`

#### Datamart REST Service
This is the backend service for datamart. There is a backand and a openAPI front end page running on `dsbox02.isi.edu:9000`. This service is running on user `datamart`. To run this backend service, need to be in the environment `datamart` for python.
Following packages are required to be installed:
 - D3M
 - common-primitives
 - dsbox-primitives
 - datamart-userend
 - datamart-upload
 - spacy web package (by running python -m spacy download en_core_web_sm)
 - gunicorn
 - `OWL-RL` package stored on `/data00/dsbox/datamart/datamart_new/OWL-RL` which support multi-processes


Currently, the detail config used is `gunicorn webapp-openapi:app -b 0.0.0.0:8999 -w 20 --preload --timeout 1800 --certfile=./certs/wildcard_isi.crt --keyfile=./certs/wildcard_isi.key`
 - `-b`: where the service should be running. Currenly it is running on local port 8999 (to ensure we can redirect both http and https). The access from outside (both `http://dsbox02.isi.edu:9000` and `https://dsbox02.isi.edu:9000`) will be redirected to `https://dsbox02.isi.edu:8999` as configured on `nginx`.
 - `-w`: How many processes(cores) that can be maximum used. Currenly it is 20 processes
 - `--timeout`: it will automatically kill the connection session after 1800 seconds. Which means any join attempt tooks larger than 30 minutes will be killed.
 - `preload`: load the whole module before starting, this can ensure no critical bug which cause system down will happened.
 - `--keyfile/certfile`: Now on dsbox02, we use https link instead of http, those certification / key file only existed on dsbox02 machine. 
 - If run on locally for testing purpose, you can run `python webapp-openapi.py` to start the rest service directly.

#### Memcache Service
This is the cache system used for datamart. For details, please refer to [here](https://github.com/usc-isi-i2/datamart-userend/tree/d3m/datamart_isi/cache "here")
To run the cache system, it is required to install mecache service. Currently  memcached version is 1.5.16, with dependency package libevent as 2.1.10.
The config file for memcache is stored at `/data00/dsbox/datamart/redis/src/memcached.conf` Currently it is running on `dsbox02.isi.edu:11211`.The maximum allowed cached value size is 100MB.
To start the memcache, run `./memcached.conf start`

#### Memcache Updater
There is also a memcache updater program that used to update the wikidata queries to ensure the cached results of the wikidata quries are up-to-date. The detail codes are over [here](https://github.com/usc-isi-i2/datamart-upload/tree/rest_api_test/datamart_web "here")
To run the updater, `nc` (NetCat) is required to be installed. For cent os, just need to run `yum install nc`
Currently, the system is scheduled to run the query updater on 2:00 AM each day(run with `python cache_query_updater.py 2 24`).

#### Upload Manager
~~This is a service that can do upload service on background so that user don't have to keep connection to datamart webpage until the upload finished. This is a `rq`(Redis queue) service running based on redis server.
To run the service, `supervisor` is required. Need to run `sudo yum install supervisor` for installation.
For detail introudction, please refer to [here](https://srijithr.gitlab.io/post/rq/ "here")
Currently the config file is stored at `/etc/supervisord.conf `
To start/stop the manager, run `sudo supervisorctl start all` or `sudo supervisorctl stop all`
To check the status of the manager on shell, run `rq info` (python enviroment and package `rq-dashboard` , `rq` required)~~ (Using supervisor seems have some bug)
Currently all worker are started by hand in one of the tmux session of user `datamart` on dsbox02.

#### Upload users management
Now upload required to provide user identification. To upload, a user must provide corresponding username and password combiniation. The username, its group information and the upload job scheduled time will be recorded in datamart blaze graph for further traceback.
Two files named `password_tokens.json` (used for saving password tokens) and `upload_password_config.json` (used for saving username and password combinations) are stored in `datamart-upload/datamart_isi/upload` (not exist on git hub). 
To add a user, there is an API named `/upload/add_upload_user`, by providing a token(which is generated by the administrator), with the username and password, a user can be created. The group information is stored in token. Currently only the group name is stored in the group information. The username and password config file will then be updated with this new information.
To add a token, just copy a exist pair from the `password_tokens.json` and create a new token according to the exist format. For example, `"sample_token": {"group": "isi"}` is one valid token with its token key is `sample_token` and could then used for creating new users with this token.

#### cache files
There are also some other files that stored some extra information.
- The wikifier choice file. This is currently stored on `/data00/dsbox/datamart/memcache_storage/other_cache/wikifier_choice.json`. This file contains the option on whether a given dataset need to be wikified or not. Basically it is only required to be copied by hand if migrating the system, otherwise the information will be automatically added to the file during uploading the dataset.
- The general augment cache. This is used for memorizing the augment results.The cache files are currently stored on `/data00/dsbox/datamart/memcache_storage/general_search_cache`.
- The wikifier target cache. This is used for memorizing the corresponding wikifier. The cache files are currently stored on `/data00/dsbox/datamart/memcache_storage/wikifier_cache`.
- The datasets cache. This is used for memorizing the metadata for the supplied data as if sent from NYU'S rest api service, metadata will not be sent (only a csv file will received). The cache files are currently stored on `/data00/dsbox/datamart/memcache_storage/datasets_cache`.