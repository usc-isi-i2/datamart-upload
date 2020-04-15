# Datamart Dataset APIs 

* **API Version**: 0.0.1
* **Release date**: [Discussion DRAFT]
* **Uses Dataset Metadata version schema**: 0.0.1
* **Uses Dataset version schema**: 0.0.2
* **Authors**: Pedro Szekely, Ke-Thia Yao and Daniel Garijo

Datamart exposes two main APIs: a Dataset metadata API, where developers may retrieve metadata about datasets and variables; and a dataset content API, where developers may download datasets and their variable time series.

!!! info
    The metadata API follows the Dataset schema in [https://datamart-upload.readthedocs.io/en/latest/](https://datamart-upload.readthedocs.io/en/latest/). The content API follows the schema in  [https://datamart-upload.readthedocs.io/en/latest/download/](https://datamart-upload.readthedocs.io/en/latest/download/) 

## Metadata API. Tentative URL:  metadata.datamart.isi.edu
The metadata API supports the following operations:

`GET /datasets`: Returns all datasets. 
* Parameters: We support filtering datasets according to the following parameters:
  * `name`: name of the dataset. 
    * Example: `&name=fbiData2009`
  * `geo`: Spatial location:
    * Example: `&geo=33.946799,-118.4307395,15z`
  * `intersects`: Intersection if the dataset location with a bounding box in format [lonmin,lonmax,latmin,latmax]
    * Example: `&intersects=84.7142,-76.7142,14.9457,22.945`
  * `keyword`: A relevant keyword (or keyword list separated by ",") that points to relevant variables, subjects or location of the dataset.
    * Example: `&keyword=maize,ethiopia`
* Returns: list of [`Dataset`](https://datamart-upload.readthedocs.io/en/latest/#describing-dataset-metadata) 

`GET /datasets/id`: Returns the dataset metadata identified by id.
* Returns: [`Dataset`](https://datamart-upload.readthedocs.io/en/latest/#describing-dataset-metadata) 

`GET /datasets/id/variables`: Returns all variable metadata in a dataset. No additional parameters are defined.
  Returns: list [Variable] [See Variable Definition]
  Example: TBD

`GET /datasets/id/variables/id`: 
  Examples: TBD

`POST /dataset` -- Creates a new dataset record. If variables are provided, they are expected to be included in the original POST request. 
Example: TBD, full dataset with variables.

`PUT /dataset/id` -- Modifies a given dataset with the content provided in the JSON request. This request will REPLACE the contents from id. The contents are not added incrementally. For example, if a dataset had an author and the PUT request contains another author, the latter will replace the former.