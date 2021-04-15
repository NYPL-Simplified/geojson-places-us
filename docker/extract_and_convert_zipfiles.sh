#!/bin/sh

set -e

WORKDIR=/tmp/places_workdir
DESTDIR=/places/docker-artifacts

mkdir -p ${WORKDIR}/shapefiles ${WORKDIR}/geonames ${WORKDIR}/geojson

echo "Unzipping shapefile archives:"
for fname in /places/cb_*.zip; do
    echo "  $(basename $fname)"
    unzip -o $fname -d ${WORKDIR}/shapefiles -q
done

echo "Unzipping geoname archives:"
for fname in /places/??.zip; do
    echo "  $(basename $fname)"
    unzip -o $fname -d ${WORKDIR}/geonames -q
done

shapefile_count=$(ls -1 ${WORKDIR}/shapefiles/*.shp | wc -l)
echo "Converting ${shapefile_count} shapefiles to GeoJSON..."

loop_counter=0
for shapefile in ${WORKDIR}/shapefiles/*.shp; do
    loop_counter=$((loop_counter+1))
    filename=$(basename $shapefile .shp)
    printf "(%2s/%2s) %30s --> %-35s\n" "$loop_counter" "$shapefile_count" "${filename}.shp" "${filename}.json"
    ogr2ogr -f "GeoJSON" "${WORKDIR}/geojson/${filename}.json" $shapefile
done
