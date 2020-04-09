This page describes the current schema used by ISI the Datamart to represent datasets.

## Dataset Definition
We define a **Dataset** as a collection of files which contain information (typically observations) about one or multiple **variables** that describe **entities** of interest. For example, consider the sample table below:


|Country  |Number of homicides|Year  |
| ---     | ---               | ---  |
| Burundi | 1000              | 2000 |
| USA     | 2000              | 2000 |

The table contains information about the variable **number of homicides**, which describe **Country** at in some **year**. Here **year** is a special type of variable which describes the information in the row (i.e., the number of homicides on a particular year). We refer to these special variables as **qualifiers**.


!!! warning
    If a dataset containes several files, it is not required to declare all of its parts as datasets.  

## Describing dataset metadata
Datasets have the following required and recommended properties. **Required properties** MUST be submitted as part of the metadata in order to be inserted in Datamart. **Recommended properties** are optional, but recommended in order to exploit the full features of the system.

| Required Property    | Description and Examples           |
| -------------------    |:-------------                     | 
| Name [[P1476](https://www.wikidata.org/wiki/Property:P1476)]|  __*Expected value*__: **String**.<br/>__*Description*__: Full name of the dataset <br/>__**Example**__: "Criminal records in the US"                     | 
| Description [[schema:description](http://schema.org/description)]            | __*Expected value*__: **String**.<br/>__*Description*__: Text with a brief explanation of the dataset and its context <br/>__*Example*__: "This dataset contains criminal records in the US (himicides, robbery, assault) organized by State and County as reported by their local administrations."                          | 
| URL  [[P2699](https://www.wikidata.org/wiki/Property:P2699)]                  | __*Expected value*__: **URL**.<br/>__*Description*__: URL where to download the dataset. It the dataset includes several files, this would be the URL where to download all of them. <br/>__*Example*__:http://s3-us-gov-west-1.amazonaws.com/cg-d4b776d0-d898-4153-90c8-8336f86bdfec/2018/AL-2018.zip  <br/>__*Qualifiers*__: Of digital data download []; format (e.g., ZIP)[]                          | 



| Recommended Properties      | Description and Examples          |
| ------------- |:-------------:| 
| col 3 is      | right-aligned  | 
| col 2 is      | centered      | 
| zebra stripes | are neat      | 

## Dataset Variable Metadata

---------
## Contribution Guidelines
If you have suggestions or concerns with any of the aspects covered in this schema, please open an issue [in our Github repository](https://github.com/usc-isi-i2/datamart-upload) with the headline [DatasetSchema].


