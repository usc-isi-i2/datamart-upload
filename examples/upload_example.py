from datamart.upload.store import Datamart_dataset
# this sample will save the following online csv datasets into datamart in blaze graph
a = Datamart_dataset()
all_dir = ["https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/List_of_United_States_counties_by_per_capita_income.csv", 
    "https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/Most-Recent-Cohorts-Scorecard-Elements.csv", 
    "https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/Unemployment.csv", 
    "https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/educate.csv", 
    "https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/population.csv", 
    "https://raw.githubusercontent.com/usc-isi-i2/datamart-userend/master/example_datasets/poverty.csv"
    ]
for input_dir in all_dir:
    df,meta=a.load_and_preprocess(input_dir=input_dir,file_type="online_csv")
    # there should only have one table extracted from one online csv address
    a.model_data(df, meta, 0)
    a.upload()

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

