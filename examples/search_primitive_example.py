# initialization
from common_primitives.datamart_augment import Hyperparams as hyper_augment, DataMartAugmentPrimitive
from common_primitives.datamart_download import Hyperparams as hyper_download, DataMartDownloadPrimitive

from d3m.container.dataset import Dataset, D3MDatasetLoader
from common_primitives.denormalize import Hyperparams as hyper_denormalize, DenormalizePrimitive
import os
from dsbox.datapreprocessing.cleaner.wikifier import WikifierHyperparams, Wikifier

'''
# 3 example search results after pickled, those are generated from following codes:

from datamart_isi.entries import Datamart
from d3m.container.dataset import Dataset, D3MDatasetLoader
from common_primitives.denormalize import Hyperparams as hyper_denormalize, DenormalizePrimitive
from common_primitives.datamart_augment import Hyperparams as hyper_augment, DataMartAugmentPrimitive
import os
import pickle
a = Datamart(connection_url="http://dsbox02.isi.edu:9999/blazegraph/namespace/datamart3/sparql")

loader = D3MDatasetLoader()
path = "/Users/minazuki/Desktop/studies/master/2018Summer/data/datasets/seed_datasets_data_augmentation/DA_poverty_estimation/TRAIN/dataset_TRAIN/datasetDoc.json"
# path = "/Users/minazuki/Desktop/studies/master/2018Summer/data/datasets/seed_datasets_current/LL1_336_MS_Geolife_transport_mode_prediction/TRAIN/dataset_TRAIN/datasetDoc.json"
json_file = os.path.abspath(path)
all_dataset_uri = 'file://{}'.format(json_file)
all_dataset = loader.load(dataset_uri=all_dataset_uri)

denormalize_hyperparams = hyper_denormalize.defaults()
denormalize_primitive = DenormalizePrimitive(hyperparams = denormalize_hyperparams)
all_dataset = denormalize_primitive.produce(inputs = all_dataset).value

search_res = a.search_with_data(query=None, supplied_data=all_dataset)
# this should have only 2 wikidata search results
s1 = search_res.get_next_page()
# this should be none
s2 = search_res.get_next_page()
# augment with first search result
aug1 = s1[0].augment(supplied_data=search_res.supplied_data)
# augment second time
aug2 = s1[1].augment(supplied_data=aug1)

# search second time and skip searching with wikidata part
search_res2 = a.search_with_data(query=None, supplied_data=aug2, skip_wikidata=True)

s3 = search_res2.get_next_page()

example_search_wikidata1 = pickle.dumps(s1[0])
example_search_wikidata2 = pickle.dumps(s1[1])
example_search_wikidata3 = pickle.dumps(s3[0])
'''
example_search_wikidata1 = b'\x80\x03cdatamart_isi.entries\nDatamartSearchResult\nq\x00)\x81q\x01}q\x02(X\r\x00\x00\x00search_resultq\x03}q\x04(X\x0e\x00\x00\x00p_nodes_neededq\x05]q\x06(X\x05\x00\x00\x00P1082q\x07X\x05\x00\x00\x00P2046q\x08X\x04\x00\x00\x00P571q\teX\x19\x00\x00\x00target_q_node_column_nameq\nX\r\x00\x00\x00FIPS_wikidataq\x0buX\n\x00\x00\x00query_jsonq\x0cNX\x0b\x00\x00\x00search_typeq\rX\x08\x00\x00\x00wikidataq\x0eub.'
example_search_wikidata2 = b'\x80\x03cdatamart_isi.entries\nDatamartSearchResult\nq\x00)\x81q\x01}q\x02(X\r\x00\x00\x00search_resultq\x03}q\x04(X\x0e\x00\x00\x00p_nodes_neededq\x05]q\x06(X\x05\x00\x00\x00P1082q\x07X\x05\x00\x00\x00P1449q\x08X\x05\x00\x00\x00P1451q\tX\x05\x00\x00\x00P1549q\nX\x05\x00\x00\x00P1705q\x0bX\x05\x00\x00\x00P1813q\x0cX\x05\x00\x00\x00P2044q\rX\x05\x00\x00\x00P2046q\x0eX\x05\x00\x00\x00P2927q\x0fX\x04\x00\x00\x00P571q\x10X\x05\x00\x00\x00P6591q\x11eX\x19\x00\x00\x00target_q_node_column_nameq\x12X\x0e\x00\x00\x00State_wikidataq\x13uX\n\x00\x00\x00query_jsonq\x14NX\x0b\x00\x00\x00search_typeq\x15X\x08\x00\x00\x00wikidataq\x16ub.'
example_search_datamart1 = b'\x80\x03cdatamart_isi.entries\nDatamartSearchResult\nq\x00)\x81q\x01}q\x02(X\r\x00\x00\x00search_resultq\x03}q\x04(X\x05\x00\x00\x00scoreq\x05}q\x06(X\x08\x00\x00\x00datatypeq\x07X\'\x00\x00\x00http://www.w3.org/2001/XMLSchema#doubleq\x08X\x04\x00\x00\x00typeq\tX\x07\x00\x00\x00literalq\nX\x05\x00\x00\x00valueq\x0bX\x13\x00\x00\x000.22097086912079575q\x0cuX\x04\x00\x00\x00rankq\r}q\x0e(h\x07X$\x00\x00\x00http://www.w3.org/2001/XMLSchema#intq\x0fh\tX\x07\x00\x00\x00literalq\x10h\x0bX\x01\x00\x00\x004q\x11uX\x08\x00\x00\x00variableq\x12}q\x13(h\tX\x03\x00\x00\x00uriq\x14h\x0bXV\x00\x00\x00http://www.wikidata.org/entity/statement/D1000003-67558f8f-30af-48ca-8c29-b49eebe08900q\x15uX\x07\x00\x00\x00datasetq\x16}q\x17(h\tX\x03\x00\x00\x00uriq\x18h\x0bX\'\x00\x00\x00http://www.wikidata.org/entity/D1000003q\x19uX\x03\x00\x00\x00urlq\x1a}q\x1b(h\tX\x03\x00\x00\x00uriq\x1ch\x0bXf\x00\x00\x00https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/Unemployment.csvq\x1duX\x05\x00\x00\x00titleq\x1e}q\x1f(X\x08\x00\x00\x00xml:langq X\x02\x00\x00\x00enq!h\tX\x07\x00\x00\x00literalq"h\x0bX\x10\x00\x00\x00Unemployment.csvq#uX\x08\x00\x00\x00keywordsq$}q%(h\x07X\'\x00\x00\x00http://www.w3.org/2001/XMLSchema#stringq&h\tX\x07\x00\x00\x00literalq\'h\x0bX^\x04\x00\x00FIPStxt State Area_name Rural_urban_continuum_code_2013 Urban_influence_code_2013 Metro_2013  Civilian_labor_force_2007   Employed_2007   Unemployed_2007  Unemployment_rate_2007  Civilian_labor_force_2008   Employed_2008   Unemployed_2008  Unemployment_rate_2008 Civilian_labor_force_2009 Employed_2009 Unemployed_2009 Unemployment_rate_2009  Civilian_labor_force_2010   Employed_2010   Unemployed_2010  Unemployment_rate_2010  Civilian_labor_force_2011   Employed_2011   Unemployed_2011  Unemployment_rate_2011  Civilian_labor_force_2012   Employed_2012   Unemployed_2012  Unemployment_rate_2012  Civilian_labor_force_2013   Employed_2013   Unemployed_2013  Unemployment_rate_2013  Civilian_labor_force_2014   Employed_2014   Unemployed_2014  Unemployment_rate_2014  Civilian_labor_force_2015   Employed_2015   Unemployed_2015  Unemployment_rate_2015  Civilian_labor_force_2016   Employed_2016   Unemployed_2016  Unemployment_rate_2016 Civilian_labor_force_2017 Employed_2017 Unemployed_2017 Unemployment_rate_2017 Median_Household_Income_2017 Med_HH_Income_Percent_of_State_Total_2017 FIPStxt_wikidata State_wikidataq(uX\x11\x00\x00\x00extra_informationq)}q*(h\x07X\'\x00\x00\x00http://www.w3.org/2001/XMLSchema#stringq+h\tX\x07\x00\x00\x00literalq,h\x0bX\x02\x00\x00\x00{}q-uX\x0c\x00\x00\x00datasetLabelq.}q/(h X\x02\x00\x00\x00enq0h\tX\x07\x00\x00\x00literalq1h\x0bX\x08\x00\x00\x00D1000003q2uX\x0c\x00\x00\x00variableNameq3}q4(h\x07X\'\x00\x00\x00http://www.w3.org/2001/XMLSchema#stringq5h\tX\x07\x00\x00\x00literalq6h\x0bX\x10\x00\x00\x00FIPStxt_wikidataq7uuX\n\x00\x00\x00query_jsonq8}q9(X\x08\x00\x00\x00keywordsq:]q;X\t\x00\x00\x00variablesq<}q=X\r\x00\x00\x00FIPS_wikidataq>X0\x06\x00\x00Q483937 Q74704 Q507981 Q506181 Q17174784 Q312475 Q491556 Q267164 Q113906 Q1130480 Q490190 Q489642 Q502549 Q109160 Q488499 Q108418 Q495257 Q485539 Q115480 Q111575 Q119372 Q489855 Q486064 Q110262 Q488917 Q485229 Q502377 Q484551 Q502380 Q504410 Q505287 Q336190 Q494919 Q283657 Q489312 Q485532 Q485710 Q485370 Q484513 Q485577 Q506191 Q496176 Q496139 Q495013 Q485549 Q484378 Q507459 Q487704 Q511498 Q109651 Q113815 Q490937 Q490414 Q54236 Q502069 Q494926 Q156377 Q58698 Q502210 Q28283 Q494216 Q54064 Q111886 Q156353 Q375608 Q156163 Q484612 Q491941 Q341708 Q484263 Q496771 Q489919 Q111409 Q504838 Q503468 Q28285 Q26880 Q490727 Q490134 Q502945 Q500312 Q376053 Q492040 Q484354 Q484268 Q109308 Q515150 Q506538 Q156623 Q501096 Q111254 Q337270 Q493083 Q594313 Q508288 Q488659 Q495682 Q487578 Q492057 Q110655 Q494818 Q48874 Q488672 Q509757 Q486139 Q500871 Q110739 Q28311 Q497424 Q486394 Q48905 Q312497 Q486191 Q496406 Q511470 Q513933 Q486218 Q491190 Q108856 Q280826 Q24648 Q490378 Q484527 Q156628 Q111593 Q502483 Q495677 Q497737 Q109303 Q501130 Q389573 Q502592 Q509786 Q503554 Q495191 Q113096 Q111759 Q510947 Q489897 Q192650 Q271915 Q494822 Q109641 Q111549 Q211360 Q112061 Q111851 Q502273 Q506235 Q502373 Q488865 Q491035 Q61289 Q486207 Q486994 Q489079 Q461562 Q82510 Q490494 Q490734 Q346925 Q169952 Q156295 Q511935 Q113756 Q385931 Q110760 Q167580 Q336322 Q376059 Q485752 Q260871 Q506337 Q193167 Q484431 Q489864 Q497628 Q494180 Q507028 Q54065 Q491547 Q506315 Q484748 Q372648 Q488796 Q54089 Q483888 Q374527 Q26610 Q179954 Q491982 Q506068 Q494815 Q505854 Q489901 Q112271 Q495564 Q71136 Q28321 Q490949q?suX\x0b\x00\x00\x00search_typeq@X\x07\x00\x00\x00generalqAub.'


# load the poverty as example and prepare the input dataset for the augment
loader = D3MDatasetLoader()
path = "/Users/minazuki/Desktop/studies/master/2018Summer/data/datasets/seed_datasets_data_augmentation/DA_poverty_estimation/TRAIN/dataset_TRAIN/datasetDoc.json"
# path = "/Users/minazuki/Desktop/studies/master/2018Summer/data/datasets/seed_datasets_current/LL1_336_MS_Geolife_transport_mode_prediction/TRAIN/dataset_TRAIN/datasetDoc.json"
json_file = os.path.abspath(path)
all_dataset_uri = 'file://{}'.format(json_file)
all_dataset = loader.load(dataset_uri=all_dataset_uri)

# denormalize it
denormalize_hyperparams = hyper_denormalize.defaults()
denormalize_primitive = DenormalizePrimitive(hyperparams = denormalize_hyperparams)
all_dataset = denormalize_primitive.produce(inputs = all_dataset).value

# wikifier it
wikifier_hyperparams = WikifierHyperparams.defaults()
wikifier_primitive = Wikifier(hyperparams = wikifier_hyperparams)
all_dataset = wikifier_primitive.produce(inputs = all_dataset).value


# run augment and download with primitive from the search results
a = hyper_augment.defaults()
a = a.replace({"search_result":example_search_wikidata1})
c = DataMartAugmentPrimitive(hyperparams=a)
augment_result = c.produce(inputs=all_dataset).value
augment_result['augmentData'].head()


# run download
b = hyper_download.defaults()
b = b.replace({"search_result":example_search_wikidata1})
d = DataMartDownloadPrimitive(hyperparams=b)
download_result = d.produce(inputs=all_dataset).value
download_result['augmentData'].head()

# here we can find the difference bewtween download and augment: 
# augment run the join but download will only give joining pairs

# run augment second time
e = a.replace({"search_result":example_search_wikidata2})
f = DataMartAugmentPrimitive(hyperparams=e)
augment_result2 = f.produce(inputs=augment_result).value

# run augment third time
g = a.replace({"search_result":example_search_datamart1})
h = DataMartAugmentPrimitive(hyperparams=g)
augment_result3 = h.produce(inputs=augment_result2).value
# this one is the final output of Datamart: after 3 times of augment, augmented from 6 columns to 53 columns
augment_result3['augmentData'].head()

# now we have following column informations
augment_result3['augmentData'].columns