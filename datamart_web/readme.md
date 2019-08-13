[TOC]
### Datamart webservice
The main source code for open-api backend service is stored in webapp-openapi.py
The webservice mainly consist of 4 parts of codes. First 3 parts (search, download, augment) follow d3m's datamart api requirement.
####Search
There are 2 types of search: search with data and search without data. Base on this supplied data or json format query, datamart will automatically find some candidates search results that may help to improve the supplied data.
##### search with data
This type of search require must send a supplied data (csv format or a link) to the function. Currently the query for search with data is not used. 
##### search without data
This type of search do not require send a supplied data but the query is required. Detail query schema can be referred [here](https://gitlab.com/datadrivendiscovery/datamart-api/blob/devel/query_input_schema.json "here")

####Download
This function is used to download the detail searched results with `d3m dataset` format or `csv` format from the search results generated from `search` api. `d3m dataset` format will have extra metadata while `csv` format will only have data itself. The downloaded results will have an extra column `joining pairs`, this column is used to indicate which row may be used for augment on supplied data.
####Augment
Similar as download function, this function will do one more extra step that join the `joining pairs` for the user.

####Upload
This function is used to upload the customized datasets. There are 2 types of upload.
#### One-step Upload
This type of upload just do upload automatically, including materializing, generating metadata, prfiling, cleaning. Then after upload success, the corresponding dataset it will be returned to user.
#### Two-steps Upload
This type of upload will first materialize the given dataset and return the metadata of the given data. The user can then change the details metadata as they want.
In sencond step, then user can upload the modified version of metadata. 
This function is recommened for advanced users with specific purposes.


### Cahce query updater
This updater is used to update the wikidata query cache for datamart. The default update frequency is once per day. Update immediately when the function started.

####Current two parameter can be passed to the function

##### update time
A int value which indicate when to update the query, current only hour can be specified in 24 hour format. For example, value 3 means to update at 3AM.

##### update frequency
A float value which indicate how often to update the query in the unit of hour, default value is 24. For example, value 48 means to run updater each 48 hours.
For example:
`python cache_query_updater.py 1 48`
Means to update cache in 1AM. Run update each 48 hours.

#### Some other functions in query updater

##### save_all_values_from_key_file
This function is used to save all key-value(including both wikidata cache part and general search cache part) pairs from memcache for backup purpose. This function is now also scheduled in query updater.
##### load_all_saved_key_value_pairs
This function is used to load all keys back to memcache from the file generated from `save_all_values_from_key_file` in the case that the server was restarted.