# ISI Datamart
This project provides an implementation of the [D3M's Datamart API](https://gitlab.com/datadrivendiscovery/datamart-api).

## Using ISI Datamart

[Here](https://github.com/usc-isi-i2/datamart-userend/blob/d3m/examples/search_primitive_example.ipynb) is a Jupyter notebook that shows how to search the datamart.

Below are the key steps to to query for datamart datasets using a supplied D3M dataset, and to augment this supplied dataset with datamart datasets.

First, load in the D3M dataset, and denormalized it:
```Python
dataset_uri = 'uri path to DA_poverty_estimation datasetDoc.json'
dataset = D3MDatasetLoader().load(dataset_uri=dataset_uri)
denormalize_primitive = DenormalizePrimitive(hyperparams=hyper_denormalize.defaults())
dataset = denormalize_primitive.produce(inputs=dataset)
```

Create an ISI datamart instance, and call its `search_with_data` method:
```Python
from datamart_isi.entries import Datamart

connection_url = "http://dsbox02.isi.edu:9001/blazegraph/namespace/datamart3/sparql"
datamart = Datamart(connection_url=connection_url)
search_cursor = search_result.search_with_data(query=None, supplied_data=dataset)
page = search_cursor.get_next_page()
```

In this case `page` should contain only two datasets. Now, augment the supplied dataset with these two datasets.
```python
augmented_dataset_1 = page[0].augment(supplied_data=search_cursor.supplied_data)
augmented_dataset_2 = page[1].augment(supplied_data=augmented_dataset_1)
```

## Using the Search Results in Pipelines

To use the search results in pipelines, the search results have to serialized and passed in as hyperparameters to the Datamart primitives in the common primitives repository.

```python
from common_primitives.datamart_augment import Hyperparams as hyper_augment

result0 = pickle.dumps(page[0])

hyper = hyper_augment.defaults()
hyper = hyper.replace({"search_result": result0})
augment_primitive = DataMartAugmentPrimitive(hyperparams=hyper)
augment_result = augment_primitive.produce(inputs=dataset).value
```

[Here](examples/sample-augment-pipeline.json) is a sample pipeline.

## Uploading Dataset

To upload datasets into the ISI Datamart, use the python class `datamart_isi.upload.Datamart_isi_upload`, [here](https://github.com/usc-isi-i2/datamart-upload).

[Here](https://github.com/usc-isi-i2/datamart-upload/blob/master/examples/upload_example.ipynb) is a sample Jupyter notebook that shows how to upload datasets into the ISI Datamart.

First, create an uploader instance, and call its `load_and_preprocess` method with a URL pointing to the CSV file. The `load_and_preprocess` method returns two lists: a list of dataframes and a list of metadata describing those dataframes. In this case, the length of each list is one since the input URL references a single CSV file. At this point the dataset has not yet been uploaded to the datamart.
```python
from datamart_isi.upload.store import Datamart_isi_upload

uploader = Datamart_isi_upload()
url_to_csv_file = 'https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/List_of_United_States_counties_by_per_capita_income.csv'
dataframes, metadata = uploader.load_and_preprocess(input_dir=url_to_csv_file, file_type='online_csv')
```

The metadata contains information deduced by the data profiler. To add additional metadata information to the dataset do:
```python
metadata[0]['title'] = "County Income"
metadata[0]['description'] = "Rank of counties by income"
metadata[0]['keywords'] = ["Per capita income", "Median household income", "Median family income"]
```

Finally, upload the dataset with the updated metadata into the datmart:
```python
uploader.model_data(dataframes, metadata, 0)
uploader.upload()
```