# Data Schema and Examples

This page describes the data format returned by ISI Datamart.

* **Schema Version**: 0.0.2
* **Release date**: April 14th, 2020
* **Authors**: Pedro Szekely, Ke-Thia Yao and Daniel Garijo

# Canonical Data Format
The __canonical data__ format specifies the preferred schema for downloading or uploading data for individual variables from or to Datamart. Additional formats will be supported for different use cases, and these are documented in the next sections.

Data can be downloaded or uploaded to Datamart as text delimited files (CSV or TSV) and as JSON where the names of the attributes in the JSON format corresponds to the names of columns in the text delimited files.

<!-- ## Column Naming Convention (We don't need this section) -->
<!-- | Convention   | Description                                                | -->
<!-- |--------------|------------------------------------------------------------| -->
<!-- | `prefix_id`   | Columns containing identifiers for *prefix*. | -->
<!-- |`prefix_unit` | Columns containing units of measurement for *prefix*. The units of measurement are in human-readable format. International System (SI) prefix notation is used.| -->
<!-- |`prefix_precision` | Columns containing the precision of the quantity measured for variable *prefix*.| -->
<!-- | `qualifier_suffix` | Columns that qualify *suffix*. | -->

## Columns 

The canonical data format supports a large number of columns, which provide significant flexibility and convenience for both upload (data registration) and download. The table below lists all the columns that may appear in a canonical data file:

- `Column Name`: the name of the column in the data file
- `Type`: the type of value; the type `identifier` designates strings to used as identifiers and should contain only alphanumeric, underscore or minus.
- `Up`: whether this column is required (`r`), optional (`o`) or not allowed (blank) for data upload.
- `Down`: whether this column is required (`r`), optional (`o`) or not allowed (blank) for data download. When a column is optional, capital `O` specifies that the column will be included by default.
- `Description`: the meaning of the column.
- `Examples`: examples of values that may be present in a cell, different examples appear one per line.

<!-- following columns are common to all datasets. Some columns are optional, which are indicated by star (`*`). Some columns can made optional to reduce verbosity. For example, cell values for columns, like `dataset_id` and `main_subject_id`, are typically constant for the entire column. Some datasets do not contain geographical information. For these datasets all the geographical columns, like `admin1` and `admin2`, will be missing. Other datasets may contain geographical information at higher levels of aggregation. For example, if the dataset contains geographical information at the Ethiopian region level, columns for `country` and `admin1` will be present, but `admin2` and lower level columns will be missing. -->

| Column Name       | Type       | Up | Down | Description                                                                                                                                                                                                                                                                                                                                                                                                        | Examples                                                                                                                          |
|-------------------|------------|:--:|:----:|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `dataset_id`      | identifier | o  | o    | Globally unique identifier of a dataset in Datamart                                                                                                                                                                                                                                                                                                                                                                | Q123456                                                                                                                           |
| `variable`        | string     | r  | r    | Name of a variable                                                                                                                                                                                                                                                                                                                                                                                                 | population <br/> production <br/> price                                                                                           |
| `variable_id`     | identifier |    | o    | Identifier of a variable; variables with the same identifier may be present in multiple datasets, e.g., the population variable may be present in a dataset from the census and a dataset from the World Bank                                                                                                                                                                                                      | [P1092](https://www.wikidata.org/wiki/Property:P1092) <br/>(id of production)                                                     |
| `category`        | string     | o  | o    | The category of data present in a variable. For example, variable `production` could be tagged with category Crops, and may have multiple main subjects corresponding to individual corps such as maize, wheat, etc.                                                                                                                                                                                               | Crops                                                                                                                             |
| `main_subject`    | string     | o  | r    | The subject for which a variable is measured, for example population of `Ethiopia`, production of `Maize`, speed of `TGV`. Often, additional values are needed to fully specify a variable, for example the population may be measured for a specific age group, ethnicity or gender. The main subject is meant to be used as a primary key for joins as it is expected that joins on main subject are meaningful. | Ethiopia <br/> Maize <br/> TGV                                                                                                    |
| `main_subject_id` | identifier | o  | O    | Wikidata identifier for the entity present in the `main_subject` column. The value may be missing if Datamart is unable to entity link the main subject to Wikidata.                                                                                                                                                                                                                                               | [Q25618328](https://www.wikidata.org/wiki/Q25618328) (for Maize) <br/>[Q843942](https://www.wikidata.org/wiki/Q843942) (for Teff) |
| `value`           | number     | r  | r    | The value of the variable. The value is a number and will be left blank when the value of the variable is non numeric; in such cases the value will be present in the qualifier columns.                                                                                                                                                                                                                           | 1.182                                                                                                                             |
| `value_unit`      | string     | o  | O    | The unit of measure of the variable value. When possible the unit of measure will be specified in SI units in a machine and human readable language. It is possible to list the units as a string.                                                                                                                                                                                                                 | quintal <br/> M quintal (mega quintal)                                                                                            |
| `time`            | string     | r  | r    | The time is in ISO format                                                                                                                                                                                                                                                                                                                                                                                          | 2016-01-01T00:00:00                                                                                                               |
| `time_precision`  | string     | o  | r    | Precision of the time value                                                                                                                                                                                                                                                                                                                                                                                        | year                                                                                                                              |
| `country`         | string     | o  | O    | Country location                                                                                                                                                                                                                                                                                                                                                                                                   | Ethiopia                                                                                                                          |
| `country_id`      | string     | o  | o    | Country location identifier                                                                                                                                                                                                                                                                                                                                                                                        | Ethiopia                                                                                                                          |
| `admin1`          | string     | o  | O    | First-level administrative country subdivision, such states in USA, provinces in Canada, and regions in Ethiopia                                                                                                                                                                                                                                                                                                   | Oromia                                                                                                                            |
| `admin1_id`       | string     | o  | o    | Identifier for the first-level administrative country subdivision                                                                                                                                                                                                                                                                                                                                                  | [Q202107](https://www.wikidata.org/wiki/Q202107)                                                                                  |
| `admin2`          | string     | o  | O    | Second-level administrative country subdivision, such as counties in USA and zones in Ethiopia                                                                                                                                                                                                                                                                                                                     | Bale                                                                                                                              |
| `admin2_id`       | string     | o  | o    | Identifier for the second-level administrative country subdivision                                                                                                                                                                                                                                                                                                                                                 | [Q804883](https://www.wikidata.org/wiki/Q804883)                                                                                  |
| `admin3`          | string     | o  | O    | Third-level administrative country subdivision, such as municipalities in USA and woredas in Ethiopia                                                                                                                                                                                                                                                                                                              | Goba                                                                                                                              |
| `admin3_id`       | string     | o  | o    | Identifier for the third-level administrative country subdivision, such as municipalities in USA and woredas in Ethiopia                                                                                                                                                                                                                                                                                           | [Q3109573](https://www.wikidata.org/wiki/Q3109573)                                                                                |
| `place`           | string     | o  | O    | Geographic place, such as cities and neighborhoods                                                                                                                                                                                                                                                                                                                                                                 | Addis Ababa                                                                                                                       |
| `place_id`        | string     | o  | o    | Geographic place Identifier                                                                                                                                                                                                                                                                                                                                                                                        | [Q3624](https://www.wikidata.org/wiki/Q3624)                                                                                      |
| `coordinate`      | string     | o  | O    | Latitude and longitude coordinates in [WKT format](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry).                                                                                                                                                                                                                                                                                      | POINT(9.001 38.757)                                                                                                               |
| `shape`           | string     | o  | o    | Geometric shape in [WKT format](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry)                                                                                                                                                                                                                                                                                                          | POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))                                                                                     |


Qualifiers represent additional information to fully specify the context for the measurement of a variable. These qualifiers are
specific to individual datasets. For example, the value of the population value may be for a certain ethnicity, age group or
gender. The following example shows how to specify the context for gender and age.

| Column Name           | Type   | Up | Down | Description                     | Examples                                                                               |
|-----------------------|--------|:--:|:----:|---------------------------------|----------------------------------------------------------------------------------------|
| `qualifier_gender`    | string | o  | O    | Column for the gender qualifier | male <br/> female                                                                      |
| `qualifier_gender_id` | string | o  | o    | Identifier for gender qualifier | [Q48277](https://www.wikidata.org/wiki/Q48277)                                         |
| `qualifier_age`       | string | o  | O    | Column for the age qualifier    | Under 18 years old <br/> 18-30 years old <br/> 30-59 years old <br/> 60 years or older |
| `qualifier_age_id`    | string | o  | o    | Identifier for age qualifier    | [Q185836](https://www.wikidata.org/wiki/Q185836)                                       |

## Upload Examples

Upload country-level population data by year.

| variable   | value       | time | country  |
|------------|-------------|------|----------|
| population | 100,000,000 | 2018 | Ethiopia |
| population | 109,000,000 | 2019 | Ethiopia |
| population | 320,000,000 | 2018 | USA      |
| population | 328,000,000 | 2019 | USA      |

 
Upload admin1-level (region-level) food production data. In this example the units (M quintal) are written in line with the values. The units also could have been separated out in this own value_unit column, or included in the column header.

| variable   | main_subject | value           | time                | admin1 |
|------------|--------------|-----------------|---------------------|--------|
| production | maize        | 1.182 M quintal | 2016-01-01T00:00:00 | Oromia |
| production | teff         | 2.345 M quintal | 2016-01-01T00:00:00 | Oromia |
| production | maize        | 2.234 M quintal | 2017-01-01T00:00:00 | Oromia |
| production | teff         | 3.356 M quintal | 2017-01-01T00:00:00 | Oromia |

Upload grid data of precipitation for the month of June 2016. In this example, the precipitation unit is included in the column header.

| variable | value in mm |    time | time_precision | coordinate        |
|----------|-------------|---------|----------------|-------------------|
| rain     |         543 | 2016-06 | month          | POINT(9.15 40.70) |
| rain     |         490 | 2016-06 | month          | POINT(9.25 40.70) |
| rain     |         550 | 2016-06 | month          | POINT(9.15 40.80) |
| rain     |         528 | 2016-06 | month          | POINT(9.25 40.80) |

## Download Examples

Download original population data.

| variable   | value       | time                | country  |
|------------|-------------|---------------------|----------|
| population | 100,000,000 | 2018-01-01T00:00:00 | Ethiopia |
| population | 109,000,000 | 2019-01-01T00:00:00 | Ethiopia |
| population | 320,000,000 | 2018-01-01T00:00:00 | USA      |
| population | 328,000,000 | 2019-01-01T00:00:00 | USA      |

Download population data with optional identifier columns.


| variable   | variable_id | value       | time                | time_precision | country  | country_id |
|------------|-------------|-------------|---------------------|----------------|----------|------------|
| population | P1082       | 100,000,000 | 2018-01-01T00:00:00 | year           | Ethiopia | Q115       |
| population | P1082       | 109,000,000 | 2019-01-01T00:00:00 | year           | Ethiopia | Q115       |
| population | P1082       | 320,000,000 | 2018-01-01T00:00:00 | year           | USA      | Q30        |
| population | P1082       | 328,000,000 | 2019-01-01T00:00:00 | year           | USA      | Q30        |


Download food production data with optional identifier columns.

| variable   | variable_id | main_subject | main\_subject\_id | value | value_unit | time                | time_precision | country  | country_id | admin1 | admin1_id |
|------------|-------------|--------------|-----------------|-------|------------|---------------------|----------------|----------|------------|--------|-----------|
| production | P1092       | maize        | Q25618328       | 1.182 | M quintal  | 2016-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   |
| production | P1092       | teff         | Q843942         | 2.345 | M quintal  | 2016-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   |
| production | P1092       | maize        | Q25618328       | 2.234 | M quintal  | 2017-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   |
| production | P1092       | teff         | Q843942         | 3.356 | M quintal  | 2017-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   |


<!-- Download data with multiple variables. -->

<!-- | variable   | variable_id | main_subject | main_subject_id | value | value_unit | time                | time_precision | country  | country_id | admin1 | admin1_id | qualifier_source | qualifier_source_id | -->
<!-- |------------|-------------|--------------|-----------------|-------|------------|---------------------|----------------|----------|------------|--------|-----------|------------------|---------------------| -->
<!-- | production | P1092       | maize        | Q25618328       | 1.182 | M quintal  | 2016-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   | CSA              | Q190360             | -->
<!-- | production | P1092       | teff         | Q843942         | 2.345 | M quintal  | 2016-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   | CSA              | Q190360             | -->
<!-- | area       | P2046       | maize        | Q25618328       |  1000 | hectare    | 2016-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   | CSA              | Q190360             | -->
<!-- | area       | P2046       | teff         | Q843942         |  2000 | hectare    | 2016-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   | CSA              | Q190360             | -->
