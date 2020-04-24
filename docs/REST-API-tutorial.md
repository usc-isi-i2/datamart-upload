﻿﻿﻿﻿﻿﻿﻿﻿﻿
# Datamart REST API Tutorial

This page demonstrates how to access the Datamart using REST. This is
an initial demonstration. Only the end point for getting dataset CSV
tables is demonstrated. Error checking for faulty URL queries is
minimal.

There are three tables, i.e. variables, available for access:

* Gross domestic product (GDP) at country level (P4010)
* Precipitation at the third administrative (woreda) level in Oromia (P3036)
* Flood duration in a month at the third administrative (woreda) level in Oromia (P1200149)

On the current Datamart these three variables are organized as one
dataset with three variables. The dataset is called `Qwikidata`, and
the variables are `P4010`, `P3036` and `P1200149`.

In the future, they will be organized as three datasets, each with one variable.

## Place Names and Place Name Identifiers

The Datamart uses place names based on Wikidata place name labels in
English. Also, a place can be identified using its Wikidata qnode
id. The mapping between place name and its identifier, as well as its
administrative hierarchy, can be found in this
[file](https://github.com/usc-isi-i2/wikidata-fuzzy-search/raw/master/backend/metadata/region.csv).

## Example REST Get Commands

**Get the GDP for the country of Ethiopia**:  [GET](https://worldmodeler:tb9H7w69FX7eTFr@dsbox02.isi.edu:10020/open-backend/datasets/Qwikidata/variables/P4010?country=Ethiopia)

```
curl -s "https://worldmodeler:tb9H7w69FX7eTFr@dsbox02.isi.edu:10020/open-backend/datasets/Qwikidata/variables/P4010?country=Ethiopia"
```

Sample rows from of the CSV table:

| variable | main\_subject | main\_subject\_id | value | value\_unit | time | time\_precision | country | place | coordinate |
|----------|---------------|-------------------|-------|-------------|------|-----------------|---------|-------|------------|
| GDP (PPP) | Ethiopia | Q115 | 20257819022 | international United States dollar | 1990-01-01T00:00:00Z | 9 | Ethiopia |  |  |
| GDP (PPP) | Ethiopia | Q115 | 19438078562 | international United States dollar | 1991-01-01T00:00:00Z | 9 | Ethiopia |  |  |
| GDP (PPP) | Ethiopia | Q115 | 18156988059 | international United States dollar | 1992-01-01T00:00:00Z | 9 | Ethiopia |  |  |
| GDP (PPP) | Ethiopia | Q115 | 21032110413 | international United States dollar | 1993-01-01T00:00:00Z | 9 | Ethiopia |  |  |
| GDP (PPP) | Ethiopia | Q115 | 22164896544 | international United States dollar | 1994-01-01T00:00:00Z | 9 | Ethiopia |  |  |

If no countries are specified, the Get command returns a sample of the dataset.

**Get the GDP for the countries of Ethiopia and Sudan, but without the place and coordinate columns**: [GET](https://worldmodeler:tb9H7w69FX7eTFr@dsbox02.isi.edu:10020/open-backend/datasets/Qwikidata/variables/P4010?country=Ethiopia,Sudan&exclude=place,coordinate)

```
curl -s "https://worldmodeler:tb9H7w69FX7eTFr@dsbox02.isi.edu:10020/open-backend/datasets/Qwikidata/variables/P4010?country=Ethiopia,Sudan&exclude=place,coordinate"
```

Sample row from of the CSV table:

| variable | main\_subject | main\_subject\_id | value | value\_unit | time | time\_precision | country |
|----------|---------------|-------------------|-------|-------------|------|-----------------|---------|
| GDP (PPP) | Sudan | Q1049 | 29196493611 | international United States dollar | 1990-01-01T00:00:00Z | 9 | Sudan |
| GDP (PPP) | Sudan | Q1049 | 32434216974 | international United States dollar | 1991-01-01T00:00:00Z | 9 | Sudan |
| GDP (PPP) | Sudan | Q1049 | 35355682896 | international United States dollar | 1992-01-01T00:00:00Z | 9 | Sudan |
| GDP (PPP) | Sudan | Q1049 | 37850632024 | international United States dollar | 1993-01-01T00:00:00Z | 9 | Sudan |
| GDP (PPP) | Sudan | Q1049 | 39045112803 | international United States dollar | 1994-01-01T00:00:00Z | 9 | Sudan |


**Get the precipitation for all the woredas with the second administrative level of Arsi Zone**: [GET](https://worldmodeler:tb9H7w69FX7eTFr@dsbox02.isi.edu:10020/open-backend/datasets/Qwikidata/variables/P3036?in_admin2=Arsi+Zone)

```
curl -s "https://worldmodeler:tb9H7w69FX7eTFr@dsbox02.isi.edu:10020/open-backend/datasets/Qwikidata/variables/P3036?in_admin2=Arsi+Zone"
```

Sample row from of the CSV table:

| variable | main\_subject | main\_subject\_id | value | value\_unit | time | time\_precision | country | admin1 | admin2 | admin3 | place | coordinate |
|----------|---------------|-------------------|-------|-------------|------|-----------------|---------|--------|--------|--------|-------|------------|
| precipitation height | Amigna | Q2843318 | 8.379636317 | mm | 2008-01-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna |  |  |
| precipitation height | Amigna | Q2843318 | 6.269173235 | mm | 2008-02-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna |  |  |
| precipitation height | Amigna | Q2843318 | 36.78374541 | mm | 2008-03-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna |  |  |
| precipitation height | Amigna | Q2843318 | 107.6538849 | mm | 2008-04-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna |  |  |
| precipitation height | Amigna | Q2843318 | 137.1296549 | mm | 2008-05-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna |  |  |
| precipitation height | Amigna | Q2843318 | 98.78545761 | mm | 2008-06-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna |  |  |
| precipitation height | Amigna | Q2843318 | 159.2030706 | mm | 2008-07-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna |  |  |

**Get the precipitation for all the woredas with the second
administrative level of Arsi Zone and include the identifier columns
for country_id, admin1_id, admin2_id and amin3_id, but exclude the place and
coordinate columns**:
[GET](https://worldmodeler:tb9H7w69FX7eTFr@dsbox02.isi.edu:10020/open-backend/datasets/Qwikidata/variables/P3036?in_admin2=Arsi+Zone&include=country_id,admin1_id,admin2_id,admin3_id&exclude=place,coordinate)

```
curl -s "https://worldmodeler:tb9H7w69FX7eTFr@dsbox02.isi.edu:10020/open-backend/datasets/Qwikidata/variables/P3036?in_admin2=Arsi+Zone&include=country_id,admin1_id,admin2_id,admin3_id&exclude=place,coordinate"
```

| variable | main\_subject | main\_subject\_id | value | value\_unit | time | time\_precision | country | country\_id | admin1 | admin1\_id | admin2 | admin2\_id | admin3 | admin3\_id |
|----------|---------------|-------------------|-------|-------------|------|-----------------|---------|-------------|--------|------------|--------|------------|--------|------------|
| precipitation height | Amigna | Q2843318 | 8.379636317 | mm | 2008-01-01T00:00:00Z | 9 | Ethiopia | Q115 | Oromia Region | Q202107 | Arsi Zone | Q646859 | Amigna | Q2843318 |
| precipitation height | Amigna | Q2843318 | 6.269173235 | mm | 2008-02-01T00:00:00Z | 9 | Ethiopia | Q115 | Oromia Region | Q202107 | Arsi Zone | Q646859 | Amigna | Q2843318 |
| precipitation height | Amigna | Q2843318 | 36.78374541 | mm | 2008-03-01T00:00:00Z | 9 | Ethiopia | Q115 | Oromia Region | Q202107 | Arsi Zone | Q646859 | Amigna | Q2843318 |
| precipitation height | Amigna | Q2843318 | 107.6538849 | mm | 2008-04-01T00:00:00Z | 9 | Ethiopia | Q115 | Oromia Region | Q202107 | Arsi Zone | Q646859 | Amigna | Q2843318 |
| precipitation height | Amigna | Q2843318 | 137.1296549 | mm | 2008-05-01T00:00:00Z | 9 | Ethiopia | Q115 | Oromia Region | Q202107 | Arsi Zone | Q646859 | Amigna | Q2843318 |


**Get the flood data for all the woredas with the second administrative
level of Arsi Zone using its identifier Q646859, and without the place
and coordinate columns**: [GET](https://worldmodeler:tb9H7w69FX7eTFr@dsbox02.isi.edu:10020/open-backend/datasets/Qwikidata/variables/P1200149?in_admin2_id=Q646859&exclude=place,coordinate)

```
curl -s "https://worldmodeler:tb9H7w69FX7eTFr@dsbox02.isi.edu:10020/open-backend/datasets/Qwikidata/variables/P1200149?in_admin2_id=Q646859&exclude=place,coordinate"
```

Sample row from of the CSV table:

| variable | main\_subject | main\_subject\_id | value | value\_unit | time | time\_precision | country | admin1 | admin2 | admin3 | significant\_event |
|----------|---------------|-------------------|-------|-------------|------|-----------------|---------|--------|--------|--------|--------------------|
| flood duration in a month | Amigna | Q2843318 | 0 | day | 2008-01-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna | 2-year flood |
| flood duration in a month | Amigna | Q2843318 | 0 | day | 2008-01-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna | 5-year flood |
| flood duration in a month | Amigna | Q2843318 | 0 | day | 2008-01-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna | 20-year flood |
| flood duration in a month | Amigna | Q2843318 | 0 | day | 2008-02-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna | 20-year flood |
| flood duration in a month | Amigna | Q2843318 | 0 | day | 2008-02-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna | 2-year flood |

**Get the flood data for the two woredas, Amigna and Digeluna Tijo, and without the place
and coordinate columns**: [GET](https://worldmodeler:tb9H7w69FX7eTFr@dsbox02.isi.edu:10020/open-backend/datasets/Qwikidata/variables/P1200149?admin3=Amigna,Digeluna+Tijo&exclude=place,coordinate)

```
curl -s "https://worldmodeler:tb9H7w69FX7eTFr@dsbox02.isi.edu:10020/open-backend/datasets/Qwikidata/variables/P1200149?admin3=Amigna,Digeluna+Tijo&exclude=place,coordinate"
```

Sample row from of the CSV table:

| variable | main\_subject | main\_subject\_id | value | value\_unit | time | time\_precision | country | admin1 | admin2 | admin3 | significant\_event |
|----------|---------------|-------------------|-------|-------------|------|-----------------|---------|--------|--------|--------|--------------------|
| flood duration in a month | Amigna | Q2843318 | 0 | day | 2008-01-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna | 2-year flood |
| flood duration in a month | Amigna | Q2843318 | 0 | day | 2008-01-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna | 5-year flood |
| flood duration in a month | Amigna | Q2843318 | 0 | day | 2008-01-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna | 20-year flood |
| flood duration in a month | Amigna | Q2843318 | 0 | day | 2008-02-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna | 20-year flood |
| flood duration in a month | Amigna | Q2843318 | 0 | day | 2008-02-01T00:00:00Z | 9 | Ethiopia | Oromia Region | Arsi Zone | Amigna | 2-year flood |