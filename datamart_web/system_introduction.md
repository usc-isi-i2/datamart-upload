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
All datamart related service should be ran on `datamart` account on `dsbox02.isi.edu`, it is a local account.

#### Wikidata SPARQL Service
This is the main query service for any people that want to use our own wikidata query service (has a longer timeout limitation). Currently the query webpage service is running on `dsbox02.isi.edu:8888`. This service is running on user `wikidata`.
The data is stored on `/data02/wikidata`. There are totally 2 wikidata database:
- `/wikidata-query-rdf` stored on triple mode, same as wikidata official server
- `/wikidata-query-rdf-2` stored on quads mode, it will help in the condition with multiple graphs

It will take up to 128GB memories. So please ensure leave enough space for the server.

#### Wikifier Service (identifier)
This is the old version of wikifier. Basically it requires a Redis server, a data file(a large json) and a Flask server for POST interface. ~~Currenly it is running on minds03 machine,~~ the data has been copied to `dsbox02` server.
The following config is used to start the redis service in docker:
`$ docker run --detach --name wikifier-redis --publish 6379:6379 --volume=$HOME/data:/data --entrypoint redis-server redis --appendonly yes`
The data file of redis is stored at `/data00/dsbox/datamart/data`

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


 Currently, the detail config used is `gunicorn webapp-openapi:app -b 0.0.0.0:9000 -w 20 --preload --timeout 1800`
 - `-b`: where the service should be running. Currenly it is running on local port 9000
 - `-w`: How many processes(cores) that can be maximum used. Currenly it is 20 cores
 - `--timeout`: it will automatically kill the connection session after 1800 seconds. Which means any join attempt tooks larger than 30 minutes will be killed.

#### Memcache Service
This is the cache system used for datamart. For details, please refer to [here](https://github.com/usc-isi-i2/datamart-userend/tree/d3m/datamart_isi/cache "here")
To run the cache system, it is required to install mecache service. Currently  memcached version is 1.5.16, with dependency package libevent as 2.1.10.
The config file for memcache is stored at `/data00/dsbox/datamart/redis/src/memcached.conf` Currently it is running on `dsbox02.isi.edu:11211`.The maximum allowed cached value size is 100MB.
To start the memcache, run `./memcached.conf start`
There is also a memcache updater program that used to update the wikidata queries to ensure the cached results of the wikidata quries are up-to-date. The detail codes are over [here](https://github.com/usc-isi-i2/datamart-upload/tree/rest_api_test/datamart_web "here")
Currently, the system is scheduled to run the query updater on 2:00 AM each day.
