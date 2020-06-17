
# Data Schema and Examples

This page describes the data format returned by ISI Datamart.

* **Schema Version**: 0.0.3
* **Release date**: April 15th, 2020
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
- `Up`: whether this column is required (`r`) or optional (`o`) for data upload.
- `Down`: whether this column is required (`r`) or optional (`o`) for data download. When a column is optional, capital `O` specifies that the column will be included by default.
- `Description`: the meaning of the column.
- `Examples`: examples of values that may be present in a cell, different examples appear one per line.

<!-- following columns are common to all datasets. Some columns are optional, which are indicated by star (`*`). Some columns can made optional to reduce verbosity. For example, cell values for columns, like `dataset_id` and `main_subject_id`, are typically constant for the entire column. Some datasets do not contain geographical information. For these datasets all the geographical columns, like `admin1` and `admin2`, will be missing. Other datasets may contain geographical information at higher levels of aggregation. For example, if the dataset contains geographical information at the Ethiopian region level, columns for `country` and `admin1` will be present, but `admin2` and lower level columns will be missing. -->

| Column Name       | Type       | Up | Down | Description                                                                                                                                                                                                                                                                                                                                                                                                        | Examples                                                                                                                          |
|-------------------|------------|:--:|:----:|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `dataset_id`      | identifier | o  | r    | Globally unique identifier of a dataset in Datamart                                                                                                                                                                                                                                                                                                                                                                | Wikidata                                                                                                                           |
| `dataset`         | string     | o  | r    | Name of a dataset                                                                                                                                                                                                                                                                                                                                                                                                  | Wikidata Knowledge Base                                                                                                            |
| `variable_id`     | identifier | o  | r    | Identifier of a variable; must be unique within the dataset, but variables with the same identifier may be present in multiple datasets, e.g., the population variable may be present in a dataset from the census and a dataset from the World Bank                                                                                                                                                                                                      | population <br/> price                                                    |
| `variable`        | string     | o  | O    | Name of a variable                                                                                                                                                                                                                                                                                                                                                                                                 | Total population both sexes <br/> Price based on local currency                                                                                         |
| `category`        | string     | o  | o    | The category of data present in a variable. For example, variable `production` could be tagged with category Crops, and may have multiple main subjects corresponding to individual corps such as maize, wheat, etc.                                                                                                                                                                                               | Crops                                                                                                                             |
| `main_subject`    | string     | r  | r    | The subject for which a variable is measured, for example population of `Ethiopia`, production of `Maize`, speed of `TGV`. Often, additional values are needed to fully specify a variable, for example the population may be measured for a specific age group, ethnicity or gender. The main subject is meant to be used as a primary key for joins as it is expected that joins on main subject are meaningful. | Ethiopia <br/> Maize <br/> TGV                                                                                                    |
| `main_subject_id` | identifier | o  | O    | Wikidata identifier for the entity present in the `main_subject` column. The value may be missing if Datamart is unable to entity link the main subject to Wikidata.                                                                                                                                                                                                                                               | [Q25618328](https://www.wikidata.org/wiki/Q25618328) (for Maize) <br/>[Q843942](https://www.wikidata.org/wiki/Q843942) (for Teff) |
| `value`           | number     | r  | r    | The value of the variable. The value is a number and will be left blank when the value of the variable is non numeric; in such cases the value will be present in the qualifier columns.                                                                                                                                                                                                                           | 1.182                                                                                                                             |
| `value_unit`      | string     | o  | O    | The unit of measure of the variable value. When possible the unit of measure will be specified in SI units in a machine and human readable language. It is possible to list the units as a string.                                                                                                                                                                                                                 | quintal <br/> M quintal (mega quintal)                                                                                            |
| `time`            | string     | r  | r    | The time when the value of a variable was measured. For download, the time will be formated in ISO format with seconds resolution. For upload the dates may be provided in a wide variety of formats. | 2016-01-01T00:00:00 <br/> (download)  <br/> Jan 1, 2016 <br/> (upload) |
| `time_precision`  | string     | o  | O    | Precision of the time (second, minute, hour, day, month, year). On download, times will are formatted in ISO format with second precision for easy parsing. The `time_precision` attribute specifies the intended precision, and is useful for determining how to format the axis of charts. For upload, the time precision is optional and if not provided is inferred automatically. | year |
| `country`         | string     | o  | O    | The country associated with the location information of the variable value. The country is optional for upload; if not provided, it will be automatically inferred from other geospatial attributes, or left empty. For download, the country will be present if it was provided on upload or inferred. The country will be formatted using the Wikipedia English label.   | Ethiopia                                                                                                                          |
| `country_id`      | string     | o  | o    | The Wikidata identifier for the country.  | [Q115](https://www.wikidata.org/wiki/Q115) (Ethiopia)|
| `admin1`          | string     | o  | o    | First-level administrative country subdivision, such as states in USA, provinces in Canada, and regions in Ethiopia. This attribute is optional for upload, and will be inferred automatically from lower level admin attributes or geospatial coordinates if provided. For download, the admin1 will be formatted using the Wikipedia English label.  | Oromia Region <br/> California |
| `admin1_id`       | string     | o  | o    | Wikidata identifier for the first-level administrative country subdivision.    | [Q202107](https://www.wikidata.org/wiki/Q202107) <br/> (Oromia Region)                                                                               |
| `admin2`          | string     | o  | o    | Second-level administrative country subdivision, such as counties in USA and zones in Ethiopia. This attribute is optional for upload, and will be inferred automatically from lower level admin attributes or geospatial coordinates if provided. For download, the admin2 will be formatted using the Wikipedia English label.      | Bale Zone         |
| `admin2_id`       | string     | o  | o    | Wikidata identifier for the second-level administrative country subdivision.      | [Q804883](https://www.wikidata.org/wiki/Q804883) <br/> (Bale Zone)  |
| `admin3`          | string     | o  | o    | Third-level administrative country subdivision, such as municipalities in USA or woredas in Ethiopia.  This attribute is optional for upload, and will be inferred automatically from geospatial coordinates if provided. For download, the admin3 will be formatted using the Wikipedia English label.  | Goba  |
| `admin3_id`       | string     | o  | o    | Wikidata identifier for the third-level administrative country subdivision  | [Q3109573](https://www.wikidata.org/wiki/Q3109573)  (Goba)) |
| `place`           | string     | o  | o    | Geographic place, such as cities, neighborhoods, mountains, lakes, etc. This attribute is used to specify places that do not fit into any of the other attributes for geopolitical entities. For upload any string can be entered and the system will attempt to link it to a place in Wikidata (geonames). If linking is possible and unambiguous the Wikidata identifier will be recorded in `place_id`.   | Addis Ababa    |
| `place_id`        | string     | o  | o    | Wikidata identifier for a place. This attribute is optional for upload, if not provided the system will attempt to infer it from the value of the `place` attribute if provided. | [Q3624](https://www.wikidata.org/wiki/Q3624) <br/> (Addis Ababa)  |
| `coordinate`      | string     | o  | O    | Latitude and longitude coordinates in [WKT format](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry). This attribute is optional for upload. If not provided, it will be inferred from the shape, if provided, otherwise from the lowest level admin level or place provided. | POINT(9.001 38.757)                                                                                                               |
| `shape`           | string     | o  | o    | Geometric shape in [WKT format](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry). This attribute is not inferred if not provided.  | POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))  |

### Qualifiers

The table above specifies the standard columns in the canonical data format. In many applications, it is useful or necessary to supply additional information to fully specify the context for the measurement of a variable. __Qualifiers__ are an extension mechanism to specify additional attributes for a variable. Each variable may have its own collection of qualifiers.
For example, a `population` variable may include qualifiers to specify that population values are for a specific ethnicity, age group or
gender; a `number of casualties` variable may include qualifiers to distinguish civilian or combatant casualties.

Qualifiers can appear as additional columns in canonical data files for variables. The following conventions are used:

- Any column whose name is different from the names used in the table above will be interpreted as a column containing qualifier information.
- Columns with suffix `_id` will be interpreted as containing identifiers for another column. For example, `gender_id` is interpreted as containing identifiers for a `gender` column.

For upload, Datamart will provide little or no understanding of qualifier columns; Datamart will automatically detect common data types such as numbers and dates, and store them appropriately to support range queries. The user in the loop curation tools will provide additional support for qualifier columns, normalizing values by linking them to Wikidata.

## Examples

### Country Population

Uploading tables to Datamart must be with respect to a particular variable (`variable_id`) within a dataset
(`dataset_id`). ISI Datamart follows the REST software architectural style. The `dataset_id` and `variable_id` are
specified as part of the REST endpoint URL.

The following table is an example of a simple canonical data file for a variable called `population`.

| variable_id | value      | time | country  |
|------------|-------------|------|----------|
| population | 100,000,000 | 2018 | Ethiopia |
| population | 109,000,000 | 2019 | Ethiopia |
| population | 320,000,000 | 2018 | USA      |
| population | 328,000,000 | 2019 | USA      |

When this table is uploaded to Datamart, say to the `dataset_id` `Wikidata`, it will automatically perform the following enhancements:

- Check that `dataset_id` `Wikidata` exists
- Check that `variable_id` `population` is variable of `Wikidata`
- Validates whether the cells of the `variable_id` column matches the identifier `population`.
- Validates whether the cells of the `value` column are numeric.
- Validates whether the cells of the `time` column are dates.
- Parse the values as numbers assuming American conventions for commas and decimal points.
- Convert the times to ISO format and automatically determine the precision as year.
- Link the countries to Wikidata so that country names are standardized (United States of America instead of USA), and
  support downloading the country identifiers to support accurate joins.
- Infer `country` as the main subject of the variable.

When a client downloads the variable, it will by default include columns as show below. Note: the API enables
clients to configure the set of optional columns present in the downloaded files; the API also supports downloading the
raw uploaded file.


| dataset\_id | variable_id | main_subject             | main_subject_id |     value | time                | time_precision | country                  |  coordinate            |
|-------------|-------------|--------------------------|-----------------|-----------|---------------------|----------------|--------------------------|------------------------|
| Wikidata    | population  | Ethiopia                 | Q115            | 100000000 | 2018-01-01T00:00:00 | year           | Ethiopia                 |  POINT(9.145 40.490)   |
| Wikidata    | population  | Ethiopia                 | Q115            | 109000000 | 2019-01-01T00:00:00 | year           | Ethiopia                 |  POINT(9.145 40.490)   |
| Wikidata    | population  | United States of America | Q30             | 320000000 | 2018-01-01T00:00:00 | year           | United States of America |  POINT(37.090 -95.713) |
| Wikidata    | population  | United States of America | Q30             | 328000000 | 2019-01-01T00:00:00 | year           | United States of America |  POINT(37.090 -95.713) |


### Production Data

Upload admin1-level (region-level) food production data. In this example the units (M quintal) are written in line with the values. The units also could have been separated out in this own value_unit column, or included in the column header.

| variable_id | main_subject | value           | time                | admin1 |
|-------------|--------------|-----------------|---------------------|--------|
| production  | maize        | 1.182 M quintal | 2016-01-01T00:00:00 | Oromia |
| production  | teff         | 2.345 M quintal | 2016-01-01T00:00:00 | Oromia |
| production  | maize        | 2.234 M quintal | 2017-01-01T00:00:00 | Oromia |
| production  | teff         | 3.356 M quintal | 2017-01-01T00:00:00 | Oromia |

Download food production data with optional identifier columns.

| dataset\_id | variable_id | main_subject | main\_subject\_id | value | value_unit | time                | time_precision | country  | country_id | admin1 | admin1_id |
|-------------|-------------|--------------|-------------------|-------|------------|---------------------|----------------|----------|------------|--------|-----------|
| Wikidata    | production  | maize        | Q25618328         | 1.182 | M quintal  | 2016-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   |
| Wikidata    | production  | teff         | Q843942           | 2.345 | M quintal  | 2016-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   |
| Wikidata    | production  | maize        | Q25618328         | 2.234 | M quintal  | 2017-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   |
| Wikidata    | production  | teff         | Q843942           | 3.356 | M quintal  | 2017-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   |

### Grid Data

Upload grid data of precipitation for the month of June 2016. In this example, the precipitation unit is included in the column header.

| variable | value in mm |    time | time_precision | coordinate        |
|----------|-------------|---------|----------------|-------------------|
| rain     |         543 | 2016-06 | month          | POINT(9.15 40.70) |
| rain     |         490 | 2016-06 | month          | POINT(9.25 40.70) |
| rain     |         550 | 2016-06 | month          | POINT(9.15 40.80) |
| rain     |         528 | 2016-06 | month          | POINT(9.25 40.80) |







<!-- Download data with multiple variables. -->

<!-- | variable   | variable_id | main_subject | main_subject_id | value | value_unit | time                | time_precision | country  | country_id | admin1 | admin1_id | qualifier_source | qualifier_source_id | -->
<!-- |------------|-------------|--------------|-----------------|-------|------------|---------------------|----------------|----------|------------|--------|-----------|------------------|---------------------| -->
<!-- | production | P1092       | maize        | Q25618328       | 1.182 | M quintal  | 2016-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   | CSA              | Q190360             | -->
<!-- | production | P1092       | teff         | Q843942         | 2.345 | M quintal  | 2016-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   | CSA              | Q190360             | -->
<!-- | area       | P2046       | maize        | Q25618328       |  1000 | hectare    | 2016-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   | CSA              | Q190360             | -->
<!-- | area       | P2046       | teff         | Q843942         |  2000 | hectare    | 2016-01-01T00:00:00 | year           | Ethiopia | Q115       | Oromia | Q202107   | CSA              | Q190360             | -->
