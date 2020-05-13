# Datamart Dataset APIs

* **API Version**: 0.0.1
* **Release date**: [Discussion DRAFT]
* **Uses Dataset Metadata version schema**: 0.0.1
* **Uses Dataset version schema**: 0.0.3
* **Authors**: Pedro Szekely, Ke-Thia Yao and Daniel Garijo

Datamart exposes two main APIs: a **Dataset metadata API**, where developers may retrieve metadata about datasets and variables; and a **Dataset content API**, where developers may download datasets and their variable time series.

!!! info
    The metadata API follows the Dataset schema in [https://datamart-upload.readthedocs.io/en/latest/](https://datamart-upload.readthedocs.io/en/latest/). The content API follows the schema in  [https://datamart-upload.readthedocs.io/en/latest/download/](https://datamart-upload.readthedocs.io/en/latest/download/)

## Metadata API. Tentative URL:  metadata.datamart.isi.edu
The metadata API supports the following operations:

**`GET /datasets`**: Returns all datasets.

**_-Parameters_**: We support filtering datasets according to the following parameters:

  * `name`: name of the dataset. **Example**: `&name=fbiData2009`
  * `geo`: Spatial location: **Example**: `&geo=33.946799,-118.4307395,15z`
  * `intersects`: Intersection if the dataset location with a bounding box in format [lonmin,lonmax,latmin,latmax]. **Example**: `&intersects=84.7142,-76.7142,14.9457,22.945`
  * `keyword`: A relevant keyword (or keyword list separated by ",") that points to relevant variables, subjects or location of the dataset **Example**: `&keyword=maize,ethiopia`

**_-Returns_**: list of [`Dataset`](https://datamart-upload.readthedocs.io/en/latest/#describing-dataset-metadata)

**`GET /datasets/id`**: Returns the metadata of the dataset identified by `id`.

**_-Returns_**: [`Dataset`](https://datamart-upload.readthedocs.io/en/latest/#describing-dataset-metadata)

**`GET /datasets/id/variables`**: Returns all variable metadata in a dataset identified by `id`.

**_-Returns_**: list [`Variable`](https://datamart-upload.readthedocs.io/en/latest/#dataset-variable-metadata)

**`GET /datasets/id/variables/id2`**: Returns the variable `id2` in the dataset identified by `id`

**_-Returns_**: [`Variable`](https://datamart-upload.readthedocs.io/en/latest/#dataset-variable-metadata)

**`POST /dataset`**: Creates a new dataset record (See the [Dataset metadata schema](https://datamart-upload.readthedocs.io/en/latest/#describing-dataset-metadata) for more information about required and optional fields). If the dataset contains variables, they should be part of the POST request (there is no additional POST path for variables).

**_-Returns_**: Status code. 201 (created) if successful, along with the dataset id.

**`PUT /dataset/id`**: **REPLACES** the entry of the dataset identified by `id` with the JSON received in the request. Contents **are not** added incrementally. For example, if a dataset had an author and the PUT request contains another author, the latter will replace the former.

**_-Returns_**: Status code. 200 if successful.

**`GET /variables`**: Returns all existing variable metadata.

**_-Parameters_**: We support filtering variables according to the following parameters:

  * `name`: name of the variable. **Example**: `&name=population`
  * `geo`: Spatial location: **Example**: `&geo=33.946799,-118.4307395,15z`
  * `intersects`: Intersection if the variable location with a bounding box in format [lonmin,lonmax,latmin,latmax]. **Example**: `&intersects=84.7142,-76.7142,14.9457,22.945`
  * `keyword`: A relevant keyword (or keyword list separated by ",") that points to relevant aspects of the variable **Example**: `&keyword=production,ethiopia`

**`GET /variables/id`**: Returns the metadata of the variable identified by `id`.

**_-Returns_**: [`Variable`](https://datamart-upload.readthedocs.io/en/latest/#dataset-variable-metadata)

## Data Content API. Tentative URL: data.datamart.isi.edu

The data content API supports the following operations:

**`GET /datasets`**: Not supported

**_-Returns_**: 403 (forbidden) (PATH under discussion)

**`GET /datasets/id`**: Returns the raw dataset in its original format. Raw data could be in any format, such as CSV, TSV, PDF, images, zip, etc.

**_-Returns_**: raw dataset identified by `id`

**`GET /datasets/id/variables`**: Returns a CSV with the variables included in the dataset identified by `id`. The results follow the [canonical data format](https://datamart-upload.readthedocs.io/en/latest/download/#canonical-data-format), and do not include qualifiers.

**_-Returns_**: list of the variables included in the dataset, in the [canonical data format](https://datamart-upload.readthedocs.io/en/latest/download/#canonical-data-format)

**`GET /datasets/id/variables/id`**: Returns a CSV in [canonical data format](https://datamart-upload.readthedocs.io/en/latest/download/#canonical-data-format) for the specified dataset and variable.

**_-Parameters_**:

  * `include`: Additional columns to download.
    - Example: `&include=country_id,admin1_id`
  * `exclude`: Exclude columns from download.
    - Example: `&exclude=coordinate`
  * `country`: Download rows where the main subject is one of the specified countries.
    - Example: `&country=Ethiopia,Sudan`
  * `country_id`: Download rows where the main subject is one of the specified country identifiers.
    - Example: `&country=Q115,Q1049`
  * `admin1`: Download rows where the main subject is one of the specified first-level administrative regions.
      - Example: `&admin1=Oromia+Region`
  * `admin1_id`: Download rows where the main subject is one of the specified first-level administrative region identifiers.
	  - Example: `&admin1_id=Q202107`
  * `admin2`: Download rows where the main subject is one of the specified second-level administrative regions.
      - Example: `&admin2=Arsi+Zone`
  * `admin2_id`: Download rows where the main subject is one of the specified second-level administrative region identifiers.
      - Example: `&admin2_id=Q646859`
  * `admin3`: Download rows where the main subject is one of the specified third-level administrative regions.
      - Example: `&admin3=Amigna,Digeluna+Tijo`
  * `admin3_id`: Download rows where the main subject is one of the specified third-level administrative region identifiers.
      - Example: `&admin3_id=Q2843318,Q5275598`
  * `in_country`: Download rows where the main subject is a first-level administrative regions of the specified countries.
    - Example: `&in_country=Ethiopia'
  * `in_country_id`: Download rows where the main subject is a first-level administrative regions of the specified country identifiers.
    - Example: `&in_country_id=Q115
  * `in_admin1`: Download rows where the main subject is a second-level administrative regions of the specified first-level administrative regions.
    - Example: `&in_admin1=Oromia+Region`
  * `in_admin1_id`: Download rows where the main subject is a second-level administrative regions of the specified first-level administrative region identifiers.
    - Example: `&in_admin1_id=Q202107`
  * `in_admin2`: Download rows where the main subject is a third-level administrative regions of the specified second-level administrative regions.
    - Example: `&in_admin2=Arsi+Zone'
  * `in_admin2_id`: Download rows where the main subject is a third-level administrative regions of the specified second-level administrative regions.
    - Example: `&in_admin2_id=Q646859'

All the region parameters (i.e. `country`, `country_id`, `admin1`,
etc) can be used at the same. The Datamart interprets multiple region
parameters as *or* constraints.

The Datamart uses place names based on Wikidata place name labels in
English. Also, a place can be identified using its Wikidata qnode
id. The mapping between place name and its identifier, as well as its
administrative hierarchy, can be found in this
[file](https://github.com/usc-isi-i2/wikidata-fuzzy-search/raw/master/backend/metadata/region.csv).

**_-Returns_**: dataset CSV in [canonical data format](https://datamart-upload.readthedocs.io/en/latest/download/#canonical-data-format)

**_-Example_**:

  * `GET data.datamart.isi.edu/food_dataset/variable/production`: Get a CSV table of crop productions
  * `GET data.datamart.isi.edu/food_dataset/variable/area&include=admin1_id`: Get a CSV table of land area used for crop productions, and include the `admin1_id` column in the table.

## Aggregation of Data Content API

**`GET /datasets/id/variable/id?group-by=column&operator=function`**: Return aggregated dataset in [canonical data format](https://datamart-upload.readthedocs.io/en/latest/download/#canonical-data-format).

**_-Parameters_**:

  * `group-by`: specifies the column to use for aggregation
  * `operator`: specifies the function to use for aggregation

**_-Returns_**: dataset CSV in [canonical data format](https://datamart-upload.readthedocs.io/en/latest/download/#canonical-data-format)

**_-Example_**:
  - `GET data.datamart.isi.edu/food_dataset/variable/production?group-by=admin1_id&operator=sum`: Get food production aggregated at the` admin1` region level.
