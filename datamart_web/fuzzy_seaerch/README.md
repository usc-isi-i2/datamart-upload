## query(search) API
This is the API that sent from fuzzy search main menu, With default, it will return maximum 20 search results. It can contains:
### POST
#### (required) Query
This is the main query in json format, it should be send via a content body
##### keywords
It should be a list of string, each string represent what related domain the user want to search
##### geospatial data
Corresponding geospatial data (in string format) which is the details of the area the user what to search. For example, we can give `los angeles`, `new york`, `orange county`
#### (optional) max_return_docs
The maxixum returned search results is allow adjustable, if not given, the default value will be 20. This parameter should be sent separately from query, please see `query_eample_curl_command.sh` for details.
### RETURN <200>
The API Will return a list of search results, each search results contains:
#### id
a unique datamart ID which used to identify the dataset
#### score
The search relavant score to indicate the relevance of this dataset to query
#### metadata
The extra information about the dataset, if it is a csv, it will have some information like the semantic types, structural types
#### type
Indicate what the original file format is when uploaded to Datamart
#### sample data
A small sample for user to preview
### RETURN <400>
If the system search failed, the system will return a string with detail errors

## Download API
This is the download API that user want to download the original uploaded file from Datamart
### GET
#### id
The unique datamart ID returned from query API
### Return <200>
Depending on the original file format, this could vary from different format. The file would be attached in a body
### Return <400>
If the given id does not exist in datamart system, or the file is unavailable, the system will return a string with detail errors