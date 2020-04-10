# Data Download Schema and Examples

This page describes the data format returned by ISI Datamart.

* **Schema Version**: 0.0.1
* **Release date**: April 9th, 2020
* **Authors**: Pedro Szekely, Ke-Thia Yao and Daniel Garijo

# Data Format
Data returned by ISI datamart is in CSV text format.

## Column Naming Convention

| Convention   | Description                                                |
|--------------|------------------------------------------------------------|
| `prefix_id`   | Columns containing identifiers for *prefix*. |
|`prefix_unit` | Columns containing units of measurement for *prefix*. The units of measurement are in human-readable format. International System (SI) prefix notation is used.|
|`prefix_precision` | Columns containing the precision of the quantity measured for variable *prefix*.|
| `qualifier_suffix` | Columns that qualify *suffix*. |

## Data Columns

The following columns are common to all datasets. Some columns are optional, which are indicated by star (`*`). Some columns can made optional to reduce verbosity. For example, cell values for columns, like `dataset_id` and `main_subject_id`, are typically constant for the entire column. Some datasets do not contain geographical information. For these datasets all the geographical columns, like `admin1` and `admin2`, will be missing. Other datasets may contain geographical information at higher levels of aggregation. For example, if the dataset contains geographical information at the Ethiopian region level, columns for `country` and `admin1` will be present, but `admin2` and lower level columns will be missing.

| Column Name   | Description and Example |
|---------------|-------------------------|
| `dataset_id`* | __*Description*__: Dataset identifier in Datamart  <br/>__*Example value*__: Q_Food_Dataset|
| `variable_measured`  | __*Description*__: Name of the variable <br/>__*Example value*__: Production <br/>__*Example value*__: Price|
| `variable_measured_id` | __*Description*__: Variable identifier (in Wikidata)  <br/>__*Example value*__: [P1092](https://www.wikidata.org/wiki/Property:P1092)|   
| `main_subject_category`* | __*Description*__: Type of the main subject column  <br/>__*Example value*__: Crops|
| `main_subject` | __*Description*__: Main subject  <br/>__*Example value*__: Maize <br/>__*Example value*__ Teff|
| `main_subject_id`  | __*Description*__ :Wikidata identifier corresponding to entity described with the `main_subject` property<br/>__*Example value*__: [Q25618328](https://www.wikidata.org/wiki/Q25618328) (for Maize) <br/>__*Example value*__: [Q843942](https://www.wikidata.org/wiki/Q843942) (for Teff) |
| `value` | __*Description*__: Variable value  <br/>__*Example value*__: 1.182 |
| `value_unit` | __*Description*__: Unit of the variable value  <br/>__*Example value*__: M quintal|
| `time` | __*Description*__: The time is in ISO format <br/>__*Example value*__: 2016-01-01T00:00:00 |
| `time_precision` | __*Description*__: Precision of the time value  <br/>__*Example value*__: year|
| `country`* | __*Description*__: Country location  <br/>__*Example value*__: Ethiopia |
| `admin1`* | __*Description*__: First-level administrative country subdivision, such states in USA, provinces in Canada, and regions in Ethiopia  <br/>__*Example value*__: Oromia|
| `admin1_id`* | __*Description*__: Identifier for the first-level administrative country subdivision  <br/>__*Example value*__: [Q202107](https://www.wikidata.org/wiki/Q202107)|
| `admin2`* | __*Description*__: Second-level administrative country subdivision, such as counties in USA and zones in Ethiopia <br/>__*Example value*__: Bale|
| `admin2_id`* | __*Description*__: Identifier for the second-level administrative country subdivision   <br/>__*Example value*__: [Q804883](https://www.wikidata.org/wiki/Q804883) |
| `admin3`* | __*Description*__:  Third-level administrative country subdivision, such as municipalities in USA and woredas in Ethiopia <br/>__*Example value*__ Goba |
| `admin3_id`* | __*Description*__: Identifier for the third-level administrative country subdivision, such as municipalities in USA and woredas in Ethiopia  <br/>__*Example value*__: [Q3109573](https://www.wikidata.org/wiki/Q3109573)|
| `place`* | __*Description*__: Geographic place, such as cities and neighborhoods  <br/>__*Example value*__: Addis Ababa|
| `place_id`* | __*Description*__:  Geographic place Identifier <br/>__*Example value*__: [Q3624](https://www.wikidata.org/wiki/Q3624) |
| `coordinate`* | __*Description*__: Latitude and longitude coordinates in [WKT format](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry).  <br/>__*Example value*__: POINT(9.001 38.757)|
| `shape`* | __*Description*__: Geometric shape in [WKT format](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry)  <br/>__*Example value*__: POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10)) |


Some columns are specific to datasets. For the food production dataset, the source qualifier turns into columns.

| Column Name   | Description and Example |
|---------------|-------------------------|
| `qualifier_source` | __*Description*__: Column for the source qualifier  <br/>__*Example value*__: CSA |
| `qualifier_source_id` | __*Description*__: Identifier for source qualifier  <br/>__*Example value*__: [Q190360](https://www.wikidata.org/wiki/Q190360) |

## Example CSV files

Sample CSV file with one variable (production) and one qualifier (source).

| variable   | variable_id | main_subject | main_subject_id | value | value_unit | time | time_precision | country | admin1 | admin1_id | qualifier_source | qualifier_source_id |
|------------|-------------|---------|------------|-------|------------|------|----------------|---------|--------|-----------|--------|-----------|
| Production | P1092       | maize   | Q25618328  | 1.182 | M quintal  | 2016-01-01T00:00:00 | year | Ethiopia | Oromia | Q202107 | CSA | Q190360 |
| Production | P1092       | teff    | Q843942    | 2.345 | M quintal  | 2016-01-01T00:00:00 | year | Ethiopia | Oromia | Q202107 | CSA | Q190360 |

Sample CSV file with multiple variables (production and area) and one qualifier (source).

| variable   | variable_id | main_subject | main_subject_id | value | value_unit | time | time_precision | country | admin1 | admin1_id | qualifier_source | qualifier_source_id |
|------------|-------------|---------|------------|-------|------------|------|----------------|---------|--------|-----------|--------|-----------|
| Production | P1092       | maize   | Q25618328  | 1.182 | M quintal  | 2016-01-01T00:00:00 | year | Ethiopia | Oromia | Q202107 | CSA | Q190360 |
| Production | P1092       | teff    | Q843942    | 2.345 | M quintal  | 2016-01-01T00:00:00 | year | Ethiopia | Oromia | Q202107 | CSA | Q190360 |
| Area | P2046 | maize   | Q25618328  | 1000 | Hectare  | 2016-01-01T00:00:00 | year | Ethiopia | Oromia | Q202107 | CSA | Q190360 |
| Area | P2046 | teff    | Q843942    | 2000 | Hectare  | 2016-01-01T00:00:00 | year | Ethiopia | Oromia | Q202107 | CSA | Q190360 |





