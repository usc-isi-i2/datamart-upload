# Data Download Schema and Examples

This describes the data format returned by the ISI Datamart.

# Data Format
Data returned by the ISI datamart is in CSV text format.

## Column Naming Convention

| Convention   | Description                                                |
|--------------|------------------------------------------------------------|
| Suffix `_id`   | Columns containing identifiers. |
|Suffiix `_unit` | Columns containing units of measurment. The units of measurement are in human-readable format. Internation System (SI) prefix notation is used.|
|Suffix `_precision` | Columns containing the precision of the quantity measured.|
| Prefix `qualifer_` | Columns generate from dataset qualifiers. |

## Data Columns

The following columns are common to all datasets. Some columns are optional, which are indicated by star (`*`). Some columns can made optional to reduce verbosity. Cell values for columns, like `dataset_id` and `subject_id`, are typically constant for the entire CSV files. Some datasets do not contain geographical information. For these datasets all the geographical columns, like `admin1` and `admin2`, will be missing. Other datasets may contain geographical information at higher levels of aggregation. For example, if the dataset contains geographical information at the Ethiopian region level, columns for `country` and `admin1` will be present, but `admin2` and lower level columns will be missing.

| Column Name   | Description and Example |
|---------------|-------------------------|
| `dataset_id`* | __*Description*__ Dataset identifier  <br/>__*Example value*__ Q_Food_Dataset|
| `variable`  | __*Description*__ Name of the variable <br/>__*Example value*__ Production in quintal|
| `variable_id` | __*Description*__ Variable identifier  <br/>__*Example value*__ [P1092](https://www.wikidata.org/wiki/Property:P1092)|   
| `subject_category`* | __*Description*__ Type or class of the subject column  <br/>__*Example value*__ Crops|
| `subject` | __*Description*__ Main subject  <br/>__*Example value*__ maize <br/>__*Example value*__ teff|
| `subject_id`  | __*Description*__ The main subject identifier <br/>__*Example value*__ [Q25618328](https://www.wikidata.org/wiki/Q25618328) <br/>__*Example value*__ [Q843942](https://www.wikidata.org/wiki/Q843942) |
| `value` | __*Description*__ Variable value  <br/>__*Example value*__ 1.182 |
| `value_unit` | __*Description*__ Unit of the variable value  <br/>__*Example value*__ M quintal|
| `time` | __*Description*__ The time in ISO format <br/>__*Example value*__ 2016-01-01T00:00:00 |
| `time_precision` | __*Description*__ Precision of the value  <br/>__*Example value*__ year|
| `country`* | __*Description*__ Country location  <br/>__*Example value*__ Ethiopia |
| `admin1*` | __*Description*__ First-level adminstrative country subdivision, such states in USA, provences in Canada, and regions in Ethiopia  <br/>__*Example value*__ Oromia|
| `admin1_id*` | __*Description*__ Identifier for the first-level adminstrative country subdivision  <br/>__*Example value*__ [Q202107](https://www.wikidata.org/wiki/Q202107)|
| `admin2*` | __*Description*__ Second-level adminstrative country subdivision, such as counties in USA and zones in Ethipoia <br/>__*Example value*__ Bale|
| `admin2_id*` | __*Description*__ Identifier for the second-level adminstrative country subdivision, such   <br/>__*Example value*__ [Q804883](https://www.wikidata.org/wiki/Q804883) |
| `admin3*` | __*Description*__  Third-level adminstrative country subdivision, such as municipalities in USA and woredas in Ethipoia <br/>__*Example value*__ Gura damole |
| `admin3_id*` | __*Description*__ Identifier for the third-level adminstrative country subdivision, such as municipalities in USA and woredas in Ethipoia  <br/>__*Example value*__ Q1000002|
| `place*` | __*Description*__ Geographic place, such as cities and neighborhoods  <br/>__*Example value*__ Addis Ababa|
| `place_id*` | __*Description*__  geographic place Identifier <br/>__*Example value*__ [Q3624](https://www.wikidata.org/wiki/Q3624) |
| `coordinate*` | __*Description*__ Latitude and longitude coordinates in WKT format.  <br/>__*Example value*__ POINT(9.001 38.757)|
| `shape*` | __*Description*__ Geometric shape in WKT format  <br/>__*Example value*__ POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10)) |


Some columns are specific to datasets. For the food production dataset, the source qualifer turns into columns.

| Column Name   | Description and Example |
|---------------|-------------------------|
| `qualifier_source` | __*Description*__ Column for the source qualifer  <br/>__*Example value*__ CSA |
| `qualifier_source_id` | __*Description*__ Identifier for source qualifer  <br/>__*Example value*__ [Q190360](https://www.wikidata.org/wiki/Q190360) |

## Example CSV files

Sample CSV file with one variable.

| variable   | variable_id | subject | subject_id | value | value_unit | time | time_precision | country | admin1 | admin1_id | source | source_id |
|------------|-------------|---------|------------|-------|------------|------|----------------|---------|--------|-----------|--------|-----------|
| Production | P1092       | maize   | Q25618328  | 1.182 | M Qunital  | 2016-01-01T00:00:00 | year | Ethiopia | Oromia | Q202107 | CSA | Q190360 |
| Production | P1092       | teff    | Q843942    | 2.345 | M Qunital  | 2016-01-01T00:00:00 | year | Ethiopia | Oromia | Q202107 | CSA | Q190360 |

Sample CSV file with multiple variables. This able contains two variables: total crop production and land area used for the production.

| variable   | variable_id | subject | subject_id | value | value_unit | time | time_precision | country | admin1 | admin1_id | source | source_id |
|------------|-------------|---------|------------|-------|------------|------|----------------|---------|--------|-----------|--------|-----------|
| Production | P1092       | maize   | Q25618328  | 1.182 | M Qunital  | 2016-01-01T00:00:00 | year | Ethiopia | Oromia | Q202107 | CSA | Q190360 |
| Production | P1092       | teff    | Q843942    | 2.345 | M Qunital  | 2016-01-01T00:00:00 | year | Ethiopia | Oromia | Q202107 | CSA | Q190360 |
| Area | P2046 | maize   | Q25618328  | 1000 | Hectore  | 2016-01-01T00:00:00 | year | Ethiopia | Oromia | Q202107 | CSA | Q190360 |
| Area | P2046 | teff    | Q843942    | 2000 | Hectore  | 2016-01-01T00:00:00 | year | Ethiopia | Oromia | Q202107 | CSA | Q190360 |