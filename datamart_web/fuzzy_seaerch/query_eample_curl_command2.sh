# this is just uploaded for testing purpose
curl -X POST "https://dsbox02.isi.edu:9000/fuzzy_search/search?max_return_docs=1" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"keywords\":[\"contest\"],\"geospatial_names\":[\"contest\"]}"