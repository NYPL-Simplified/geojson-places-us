FROM python:3.9.2-alpine

WORKDIR /tmp/places

RUN apk add --no-cache gdal-tools \
 && pip install geojson

COPY ./docker/extract_and_convert_zipfiles.sh /extract_and_convert_zipfiles.sh
COPY ./docker/consolidate_generated_geojson.py /consolidate_generated_geojson.py
COPY ./docker/docker-entrypoint.sh /docker-entrypoint.sh

ENTRYPOINT ["/bin/sh", "/docker-entrypoint.sh"]
