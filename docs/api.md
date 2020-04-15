# Dataset APIs 

We will have 2 different APIs: a metadata-based API, where developers may retrieve metadata about datasets and variables; and a content-based API, where developers may download datasets and their variable time series. The metadata schema will follow the Dataset schema in https://datamart-upload.readthedocs.io/en/latest/. The content-based API will follow the schema in  https://datamart-upload.readthedocs.io/en/latest/download/ 

## Metadata API. Proposed URL:  metadata.datamart.isi.edu
GET /datasets -- Returns all datasets. 
Parameters: We allow filtering datasets according to the following parameters:
Name: name of the dataset. Example:&name=fbiData2009
Spatial location: coordinates.
Example: &geo=33.946799,-118.4307395,15z
Example: &intersects=POINT(33.946799+-118.4307395)
Example: &intersects=POLYGON((30+-115,30+-120,35+-120,35+-115,30+-115))
Temporal resolution: To be determined
Example: &time-from=2000
Included variables: Example: &variable=price
  Returns: list [Dataset] [See Dataset Definition]
  Example:
[
{“datasetId”:”Q21231”,“name”:”FBI”,”description”:”Blah”},
{“datasetId”:”Q21232”,“name”:”FBI2”,”description”:”Blah2”},
]
GET /datasets/id -- Returns the dataset metadata identified by id.
  Returns: Dataset [See Dataset Definition]
  Example: {“datasetId”:”Q21232”,“name”:”FBI2”,”description”:”Blah2”}

GET /datasets/id/variables: Returns all variable metadata in a dataset. No additional parameters are defined.
  Returns: list [Variable] [See Variable Definition]
  Example: TBD

GET /datasets/id/variables/id: 
  Examples: TBD

POST /dataset -- Creates a new dataset record. If variables are provided, they are expected to be included in the original POST request. 
Example: TBD, full dataset with variables.

PUT /dataset/id -- Modifies a given dataset with the content provided in the JSON request. This request will REPLACE the contents from id. The contents are not added incrementally. For example, if a dataset had an author and the PUT request contains another author, the latter will replace the former.