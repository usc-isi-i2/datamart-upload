# Datamart Dataset APIs

* **API Version**: 1.0.0
* **Release date**: Stable release
* **Uses Dataset Metadata version schema**: 1.0.0
* **Uses Dataset version schema**: 0.0.3
* **Authors**: Pedro Szekely, Ke-Thia Yao and Daniel Garijo

Datamart exposes two main APIs: a **Dataset metadata API**, where developers may retrieve metadata about datasets and variables; and a **Dataset content API**, where developers may download datasets and their variable time series.

!!! info
    The metadata API follows the Dataset schema in [https://datamart-upload.readthedocs.io/en/latest/](https://datamart-upload.readthedocs.io/en/latest/). The content API follows the schema in  [https://datamart-upload.readthedocs.io/en/latest/download/](https://datamart-upload.readthedocs.io/en/latest/download/)

An implementation of the API is available at: https://dsbox02.isi.edu:10020/open-backend/. We illustrate how to use it in a [Jupyter notebook](https://github.com/usc-isi-i2/datamart-api/blob/master/Datamart%20Data%20API%20Demo.ipynb). 

## Metadata API. 
The metadata API supports the following operations:

| Path     | Method       | Description | Parameters
| -------- |:-------------| ------------|----------|
|**/metadata/datasets**|GET| Returns all datasets (list of [Dataset](https://datamart-upload.readthedocs.io/en/latest/#describing-dataset-metadata))| We support **filtering** datasets according to the following parameters:<br/> **`name`**: name of the dataset. **Example**: `&name=fbiData2009` <br/> **`geo`**: Spatial location. **Example**: `&geo=33.946799,-118.4307395,15z`<br/>**`intersects`**: Intersection if the dataset location with a bounding box in format [lonmin,lonmax,latmin,latmax]. **Example**: `&intersects=84.7142,-76.7142,14.9457,22.945`<br/>**`keyword`**: A relevant keyword (or keyword list separated by ",") that points to relevant variables, subjects or location of the dataset **Example**: `&keyword=maize,ethiopia`|
|**/metadata/datasets**|POST| Creates a new [Dataset](https://datamart-upload.readthedocs.io/en/latest/#describing-dataset-metadata) record. <br>Returns: Status code 201 (created) if successful, along with the dataset id. | None |
|**/metadata/datasets/dataset_id**|PUT| **REPLACES** the entry of the dataset identified by `dataset_id` with the JSON received in the request. Returns: Status code 200 if successful.| None |
|**/metadata/datasets/dataset_id**|GET| Returns the metadata of the [Dataset](https://datamart-upload.readthedocs.io/en/latest/#describing-dataset-metadata) identified by `dataset_id`| None |
|**/metadata/datasets/dataset_id/variables**|GET| Returns all [Variables](https://datamart-upload.readthedocs.io/en/latest/#dataset-variable-metadata) in a dataset identified by `dataset_id` (list of variable)| None |
|**/metadata/datasets/dataset_id/variables**|POST| Creates a new [Variable](https://datamart-upload.readthedocs.io/en/latest/#dataset-variable-metadata) in the dataset identified by `dataset_id`. Returns 201 if successful| None |
|**/metadata/datasets/dataset_id/variables/variable_id**|GET| Returns the [`Variable`](https://datamart-upload.readthedocs.io/en/latest/#dataset-variable-metadata) `variable_id` in the dataset identified by `dataset_id`| None |
|**/metadata/variables**|GET| Returns all existing variable metadata|We support **filtering** datasets according to the following parameters:<br/>  **`ids`**: Variable ids to be returned (could be more than one). **Example**: `&ids=H123,H124` <br/>**`name`**: name of the variable. **Example**: `&name=population`<br/>**`geo`**: Spatial location: **Example**: `&geo=33.946799,-118.4307395,15z`<br/>**`intersects`**: Intersection if the variable location with a bounding box in format [lonmin,lonmax,latmin,latmax]. **Example**: `&intersects=84.7142,-76.7142,14.9457,22.945` <br/>**`keyword`**: A relevant keyword (or keyword list separated by ",") that points to relevant aspects of the variable **Example**: `&keyword=production,ethiopia` |



## Data Content API. Tentative URL: data.datamart.isi.edu

| Path     | Method       | Description | Parameters
| -------- |:-------------| ------------|----------|
|**/datasets/id**|GET| Returns the raw dataset identified by `id` in its original format. Raw data could be in any format, such as CSV, TSV, PDF, images, zip, etc.| None
|**/datasets/id/variables**|GET| Returns a CSV with the variables included in the dataset identified by `id`. The results follow the [canonical data format](https://datamart-upload.readthedocs.io/en/latest/download/#canonical-data-format), and do not include qualifiers.| None|
|**/datasets/dataset_id/variables/variable_id**|GET| Returns a CSV in [canonical data format](https://datamart-upload.readthedocs.io/en/latest/download/#canonical-data-format) for the specified dataset (`dataset_id`) and variable (`variable_id`).|**`include`**: Additional columns to download. Example: `&include=country_id,admin1_id` <br/>**`exclude`**: Exclude columns from download. Example: `&exclude=coordinate`<br/>**`country`**: Download rows where the main subject is one of the specified countries. Example: `&country=Ethiopia,Sudan`<br/>**`country_id`**: Download rows where the main subject is one of the specified country identifiers.Example: `&country=Q115,Q1049` <br/> **`admin1`**: Download rows where the main subject is one of the specified first-level administrative regions. Example: `&admin1=Oromia+Region`<br/>**`admin1_id`**: Download rows where the main subject is one of the specified first-level administrative region identifiers.Example: `&admin1_id=Q202107`<br/>**`admin2`**: Download rows where the main subject is one of the specified second-level administrative regions.- Example: `&admin2=Arsi+Zone`<br/>**`admin2_id`**: Download rows where the main subject is one of the specified second-level administrative region identifiers. Example: `&admin2_id=Q646859`<br/>**`admin3`**: Download rows where the main subject is one of the specified third-level administrative regions. Example: `&admin3=Amigna,Digeluna+Tijo` <br/> **`admin3_id`**: Download rows where the main subject is one of the specified third-level administrative region identifiers. Example: `&admin3_id=Q2843318,Q5275598` <br/>**`in_country`**: Download rows where the main subject is a first-level administrative regions of the specified countries. Example: `&in_country=Ethiopia`<br/> **`in_country_id`**: Download rows where the main subject is a first-level administrative regions of the specified country identifiers. Example: `&in_country_id=Q115` <br/> **`in_admin1`**: Download rows where the main subject is a second-level administrative regions of the specified first-level administrative regions. Example: `&in_admin1=Oromia+Region` <br/> **`in_admin1_id`**: Download rows where the main subject is a second-level administrative regions of the specified first-level administrative region identifiers. Example: `&in_admin1_id=Q202107` <br/>**`in_admin2`**: Download rows where the main subject is a third-level administrative regions of the specified second-level administrative regions.  Example: `&in_admin2=Arsi+Zone` <br/> **`in_admin2_id`**: Download rows where the main subject is a third-level administrative regions of the specified second-level administrative regions. Example: `&in_admin2_id=Q646859`

**Additional considerations:**

All the region parameters (i.e. `country`, `country_id`, `admin1`,
etc) can be used at the same time. Datamart interprets multiple region parameters as *or* constraints.

The Datamart uses place names based on Wikidata place name labels in English. Also, a place can be identified using its Wikidata qnode id. The mapping between place name and its identifier, as well as its administrative hierarchy, can be found in this
[file](https://github.com/usc-isi-i2/wikidata-fuzzy-search/raw/master/backend/metadata/region.csv).


**_-Example_**:

  * `GET [API_URL]/[dataset_id]/variable/[variable_id]`: Get a CSV table of crop productions
  * `GET [API_URL]/[dataset_id]/variable/[variable_id]/area&include=admin1_id`: Get a CSV table of land area used for crop productions, and include the `admin1_id` column in the table.

## Aggregation of Data Content API

| Path     | Method       | Description | Parameters
| -------- |:-------------| ------------|----------|
|**/datasets/dataset_id/variable/variable_id**|GET| Returns an aggregated dataset from dataset `dataset_id` and variable `variable_id` in [canonical data format](https://datamart-upload.readthedocs.io/en/latest/download/#canonical-data-format).| **`group-by`**: specifies the column to use for aggregation <br/> **`operator`**: specifies the function to use for aggregation


**_-Example_**:
  - `GET [API_URL]/datasets/[dataset_id]/variables/[variable_id]?group-by=admin1_id&operator=sum`: Get food production aggregated at the` admin1` region level.