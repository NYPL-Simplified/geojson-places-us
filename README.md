This repository includes data from multiple sources, and a script which consolidates the data to create a flat list of annotated GeoJSON objects representing the boundaries of a large number of places in the United States and its territories:

* The United States itself
* Each state and territory
* Each county
* Each census-designated place (e.g. cities and towns)
* Each ZIP Code Tabulation area

Generating the list is as simple as 1-2-3:

```
sh 1-extract.sh
sh 2-convert.sh
python 3-consolidate.py
```

Running the script requires that `ogr2ogr` be installed (it's
available in the Debian package `gdal-bin`) and that the `geojson`
Python library be installed.

This repository includes CC-BY data from [[GeoNames|http://download.geonames.org/export/zip/]], and public domain data from [[the US Census Bureau|https://www.census.gov/geo/maps-data/data/tiger-cart-boundary.html]].
