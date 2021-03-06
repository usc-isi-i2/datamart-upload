from datamart_isi.upload.store import Datamart_isi_upload
# this sample will save the following online csv datasets into datamart in blaze graph
a = Datamart_isi_upload(update_server="http://dsbox02.isi.edu:9002/blazegraph/namespace/datamart3/sparql", query_server = "http://dsbox02.isi.edu:9002/blazegraph/namespace/datamart3/sparql")

all_dir = ["https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/List_of_United_States_counties_by_per_capita_income.csv", # 1
    "https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/Most-Recent-Cohorts-Scorecard-Elements.csv", # 2
    "https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/Unemployment.csv", # 3
    "https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/educate.csv", # 4
    "https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/population.csv", # 5
    "https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/poverty.csv", # 6
"https://gitlab.com/svattam/datamart-uploads/raw/master/2017-yellow-cab-lga.csv", # 7
"https://gitlab.com/svattam/datamart-uploads/raw/master/FIFA_2018_Statistics_N.csv", # 8
"https://gitlab.com/svattam/datamart-uploads/raw/master/NPDB1807.CSV", # 9
"https://gitlab.com/svattam/datamart-uploads/raw/master/ny_lga_weather_16_17_18.csv", # 10
"https://gitlab.com/svattam/datamart-uploads/raw/master/psam_h06.csv", # 11
"https://github.com/usc-isi-i2/datamart-userend/raw/d3m/example_datasets/NPDB1901-subset.csv.gz", # 12
"https://raw.githubusercontent.com/yuqiuhe/Dsbox/master/New-York-La-Guadia-Airport-Weather-Hourly.csv", # 13

]

for input_dir in all_dir:
    # input_dir = "https://github.com/usc-isi-i2/datamart-userend/raw/d3m/example_datasets/NPDB1901-subset.csv.gz"
    print("*"*100)
    print("Now processing " + input_dir)
    print("*"*100)
    df,meta=a.load_and_preprocess(input_dir=input_dir,file_type="online_csv")
    # there should only have one table extracted from one online csv address
    a.model_data(df, meta, 0)
    res = a.upload()
    print("uploaded dataset's id is " + res)

all_dir_wikipedia_test = ["https://en.wikipedia.org/wiki/1962_Washington_Senators_season", "https://en.wikipedia.org/wiki/2017%E2%80%9318_New_Orleans_Privateers_women%27s_basketball_team"]

for input_dir in all_dir_wikipedia_test:
    df,meta=a.load_and_preprocess(input_dir=input_dir,file_type="wikitable")
    for i in range(len(df)):
        a.model_data(df, meta, i)
        a.upload()

# input_dir = "/Users/minazuki/Downloads/usda/population_new.csv"
# df,meta=a.load_and_preprocess(input_dir)
# a.model_data(df, meta)
# a.output_to_ttl("2")

# input_dir = "/Users/minazuki/Downloads/usda/poverty_new.csv"
# df,meta=a.load_and_preprocess(input_dir)
# a.model_data(df, meta)
# a.output_to_ttl("3")

# input_dir = "/Users/minazuki/Downloads/usda/Unemployment_new.csv"
# df,meta=a.load_and_preprocess(input_dir)
# a.model_data(df, meta)
# a.output_to_ttl("4")

