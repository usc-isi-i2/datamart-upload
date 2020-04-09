This page describes the current schema used by ISI the Datamart to represent datasets.

* **Schema Version**: 0.0.1
* **Release date**: April 8th, 2020
* **Authors**: Pedro Szekely, Ke-Thia Yao and Daniel Garijo

## Dataset Definition
We define a **Dataset** as a collection of files which contain information (typically observations) about one or multiple **variables** that describe **entities** of interest. For example, consider the sample table below:


|Country  |Number of homicides|Year  |
| ---     | ---               | ---  |
| Burundi | 1000              | 2000 |
| USA     | 2000              | 2000 |

The table contains information about the variable **number of homicides**, which describe **Countries** (Burundi, USA) in some **year**. Here **year** is a special type of variable which describes the information in the row (i.e., the number of homicides on a particular year). We refer to these special variables as **qualifiers**.


!!! warning
    If a dataset containes several files, it is not required to declare all of its parts as datasets.  

## Describing dataset metadata
Datasets have the following required, recommended and optional properties. **Required properties** MUST be submitted as part of the metadata in order to be inserted in Datamart. **Recommended properties** are not, but highly recommended in order to exploit the full features of the system. **Optional properties** provide additional insight into the dataset, helping it understand its context to others.


| Required Property    | Description and Examples           |
| -------------------    |:-------------                     | 
| Name [[P1476](https://www.wikidata.org/wiki/Property:P1476)]|  __*Expected value*__: **String**<br/>__*Description*__: Full name of the dataset <br/>__*Example*__: "Criminal records in the US for the year 2000"                     | 
| Description [[schema:description](http://schema.org/description)]            | __*Expected value*__: **String**<br/>__*Description*__: Text with a brief explanation of the dataset and its context <br/>__*Example*__: "This dataset contains criminal records in the US (himicides, robbery, assault) organized by State and County as reported by their local administrations."                          | 
| URL  [[P2699](https://www.wikidata.org/wiki/Property:P2699)]                  | __*Expected value*__: **URL**<br/>__*Description*__: URL where to download the Dataset. It the dataset includes several files, this would be the URL where to download all of them. <br/>__*Example*__: [http://s3-us-gov-west-1.amazonaws.com/cg-d4b776d0-d898-4153-90c8-8336f86bdfec/2018/AL-2018.zip](http://s3-us-gov-west-1.amazonaws.com/cg-d4b776d0-d898-4153-90c8-8336f86bdfec/2018/AL-2018.zip)  <br/>__*Qualifiers [OPTIONAL]*__: Of [[P642](https://www.wikidata.org/wiki/Property:P642)] digital data download [[Q165194](https://www.wikidata.org/wiki/Property:Q165194)]; file format [[P2701](https://www.wikidata.org/wiki/Property:P2701)] (e.g., ZIP [[Q136218](https://www.wikidata.org/wiki/Property:Q136218)], N-Triples [[Q44044](https://www.wikidata.org/wiki/Property:Q44044)])          | 


| Recommended Property      | Description and Examples          |
| ------------- |:-------------| 
| Short Name [[P1813](https://www.wikidata.org/wiki/Property:P1813)]|  __*Expected value*__: **String**<br/>__*Description*__: Short name of the dataset <br/>__*Example*__: "Criminal records in the US" |
| Keywords [[schema:keywords](https://schema.org/keywords)]|  __*Expected value*__: **String**<br/>__*Description*__: Keywords describing the dataset. Multiple entries are delimited by commas <br/>__*Example*__: "crime, homicide" |
| Creator [[P170](https://www.wikidata.org/wiki/Property:P170)]|  __*Expected value*__: **String** (will be matched to QNode of Person or Organization)<br/>__*Description*__: Person or Organization responsible for the creation of the Dataset <br/>__*Example*__: "Federal Bureau of Investigation"<br/>__*Example*__: "John Doe" |
| Contributor [[P767](https://www.wikidata.org/wiki/Property:P767)]|  __*Expected value*__: **String** (will be matched to QNode of Person or Organization)<br/>__*Description*__: Person or Organization who helped in the development of the Dataset. <br/>__*Example*__: "John Doe" |
| Cites Work [[P2860](https://www.wikidata.org/wiki/Property:P2860)]|  __*Expected value*__: **String or URL**<br/>__*Description*__: Bibliographic citation for the dataset <br/>__*Example*__: "Doe J (2014) Influence of X ... https://doi.org/10.1111/111"<br/>__*Example*__: [https://doi.org/10.1111/111](https://doi.org/10.1111/111) |
| CopyRight License [[P275](https://www.wikidata.org/wiki/Property:P275)]|  __*Expected value*__: **String** (will be matched to a QNode)<br/>__*Description*__: license under which this copyrighted work is released  <br/>__*Example*__: "Creative Commons Attribution-ShareAlike 4.0 International" ([Q18199165](https://www.wikidata.org/wiki/Q18199165)) |
| Version [[schema:version](https://schema.org/version)]|  __*Expected value*__: **String**<br/>__*Description*__: Version number of the Dataset. Semantic versioning (X.Y.Z) is preferred.<br/>__*Example*__: "1.0.0" |
| DOI [[P356](https://www.wikidata.org/wiki/Property:P356)]|  __*Expected value*__: **String**<br/>__*Description*__: Digital Objet Identifier (DOI) of the dataset. Note that this identifier is different from the DOI used in "Cites Work".<br/>__*Example*__: "https://doi.org/10.1000/182" |
| Main Subject [[P921](https://www.wikidata.org/wiki/Property:P921)]|  __*Expected value*__: **String** (will be mapped to QNode)<br/>__*Description*__: Primary topic(s) of a Dataset. This property may be used to identify all the entities described in a dataset <br/>__*Example*__: "USA" ([Q30](https://www.wikidata.org/wiki/Q30)) <br/>__*Example*__: "Burundi"([Q967](https://www.wikidata.org/wiki/Q967)) |
| Coordinate Location [[P921](https://www.wikidata.org/wiki/Property:P921)]|  __*Expected value*__: **String** <br/>__*Description*__: Geocoordinates of the subject in WGS84 format.<br/>__*Example*__: "14°S, 53°W"  
| Geoshape [[P3896](https://www.wikidata.org/wiki/Property:P3896)]|  __*Expected value*__: **String** <br/>__*Description*__: Geographic data in Well Known Text (WKT) format. <br/>__*Example*__: "POINT (30 10)"<br/> __*Example*__: "POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))"|
| Country [[P17](https://www.wikidata.org/wiki/Property:P17)]|  __*Expected value*__: **String** (will be mapped to QNode)<br/>__*Description*__: Country where the dataset observations were collected <br/>__*Example*__: "USA" ([Q30](https://www.wikidata.org/wiki/Q30)) <br/>__*Example*__: "Burundi"([Q967](https://www.wikidata.org/wiki/Q967)) |
| Location [[P276](https://www.wikidata.org/wiki/Property:P276)]|  __*Expected value*__: **String** (will be mapped to QNode)<br/>__*Description*__: Location of the Dataset <br/>__*Example*__: "Los Angeles" ([Q65](https://www.wikidata.org/wiki/Q65)) <br/>__*Example*__: "Burundi"([Q967](https://www.wikidata.org/wiki/Q967)) |
| Start Time [[P580](https://www.wikidata.org/wiki/Property:P580)]|  __*Expected value*__: **String** <br/>__*Description*__: Time at which the Dataset starts collecting observationsThe value should follow the ISO 8601 format (YYYY-MM-DD). Precision may vary from seconds to years. <br/>__*Example*__: "2020-04-06" <br/>__*Example*__: "2020"<br/>__*Qualifiers [OPTIONAL]*__: Precision [[P2803](https://www.wikidata.org/wiki/P2803)] (e.g., Year [[Q577](https://www.wikidata.org/wiki/Q577)]), Calendar [[P2803]()] (e.g., Gregorian [Q12138](https://www.wikidata.org/wiki/Q12138)) |
| End Time [[P582](https://www.wikidata.org/wiki/Property:P582)]|  __*Expected value*__: **String** <br/>__*Description*__: Time at which the Dataset stops collecting observations. The value should follow the ISO 8601 format (YYYY-MM-DD). Precision may vary from seconds to years. <br/>__*Example*__: "2020-04-06" <br/>__*Example*__: "2020"<br/>__*Qualifiers [OPTIONAL]*__: Precision [[P2803](https://www.wikidata.org/wiki/P2803)] (e.g., Year [[Q577](https://www.wikidata.org/wiki/Q577)]), Calendar [[P2803]()] (e.g., Gregorian [Q12138](https://www.wikidata.org/wiki/Q12138)) |
| Data interval [[P921](https://www.wikidata.org/wiki/Property:P921)]|  __*Expected value*__: **[Hourly ([Q59657010](https://www.wikidata.org/wiki/Q59657010)) OR Daily ([Q59657036](https://www.wikidata.org/wiki/Q59657036)) OR Monthly ([Q59657037](https://www.wikidata.org/wiki/Q59657037))]** <br/>__*Description*__: Primary topic(s) of a Dataset. This property may be used to identify all the entities described in a dataset <br/>__*Qualifiers [OPTIONAL]*__: Start Time [[P580](https://www.wikidata.org/wiki/Property:P580)], End Time [[P582](https://www.wikidata.org/wiki/Property:P582)] |
| Variable Measured [[schema:variableMeasured](https:schema.orf/variableMeasured)]|  __*Expected value*__: **String** (will be mapped to QNode)<br/>__*Description*__: Variables that are measured in a Dataset <br/>__*Example*__: "Price" ([P2284](https://www.wikidata.org/wiki/Property:P2284)) <br/>|
| Mapping file [[to be determined]()]|  __*Expected value*__: **URL** <br/>__*Description*__: File used to create map the dataset statements to WikiData tiples <br/>__*Example*__: http://example.com/T2WMLProject-FBI <br/>__*Qualifiers [OPTIONAL]*__: File format ([P2701](https://www.wikidata.org/wiki/Property:P2701)) (e.g., T2WML [TBD], D-REPR [TBD]) |


| Optional Property      | Description and Examples          |
| ------------- |:-------------| 
| Official website [[P856](https://www.wikidata.org/wiki/Property:P856)]|  __*Expected value*__: **URL**<br/>__*Description*__: URL of the official homepage of a Dataset <br/>__*Example*__: [https://crime-data-explorer.fr.cloud.gov](https://crime-data-explorer.fr.cloud.gov/) |
| Date created [[schema:dateCreated](https://schema.org/dateCreated)]|  __*Expected value*__: **Date**<br/>__*Description*__: Creation date of the Dataset in ISO 8601 format (YYYY-MM-DD) <br/>__*Example*__: 2020-04-06 |
| API endpoint [[P6269](https://www.wikidata.org/wiki/Property:P6269)]|  __*Expected value*__: **URL**<br/>__*Description*__: Base URL of a web service <br/>__*Example*__: [https://www.wikidata.org/w/api.php](https://www.wikidata.org/w/api.php) |
| Included in Data Catalog [[schema:includedInDataCatalog](https://schema.org/includedInDataCatalog)]|  __*Expected value*__: **String** (will be mapped to QNode)<br/>__*Description*__: Catalog where the Dataset is included <br/>__*Example*__: "FigShare"([Q17013516](https://www.wikidata.org/wiki/Q17013516)) |
| Has Part [[P527](https://www.wikidata.org/wiki/Property:P527)]|  __*Expected value*__: **URL**<br/>__*Description*__: Link to the files that are included on a Dataset (in case the dataset contains multiple files) <br/>__*Example*__: http://example.com/example.csv1 <br/>__*Qualifiers [OPTIONAL]*__: File format ([P2701](https://www.wikidata.org/wiki/Property:P2701)) (e.g., CSV [[Q935809](https://www.wikidata.org/wiki/Q935809)]) |



When a property is marked as (will be marked to QNode) it means that Datamart will automatically transform the target string into an entity with a QNode in Wikidata. If no match is found, a new QNode will be created.

## Dataset Variable Metadata (Work In Progress)

| Recommended Property      | Description and Examples          |
| ------------- |:-------------| 
| Name [[P1476](https://www.wikidata.org/wiki/Property:P1476)]|  __*Expected value*__: **String**<br/>__*Description*__: Full name of the variable <br/>__*Example*__: "Number of homicides"                     | 
| Description [[schema:description](http://schema.org/description)]            | __*Expected value*__: **String**<br/>__*Description*__: Text with a brief explanation of the Variable and its context <br/>__*Example*__: "The number of homicides in a region."                          | 
| Short Name [[P1813](https://www.wikidata.org/wiki/Property:P1813)]|  __*Expected value*__: **String**<br/>__*Description*__: Short name of the Variable. Typically, this corresponds to the name of the variable in the corresponding column of the table <br/>__*Example*__: "Homicides" <br/>__*Example*__: "H" |

---------
## Contribution Guidelines
If you have suggestions or concerns with any of the aspects covered in this schema, please open an issue [in our Github repository](https://github.com/usc-isi-i2/datamart-upload) with the headline [DatasetSchema].


