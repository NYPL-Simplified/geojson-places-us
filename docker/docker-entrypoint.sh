#!/bin/sh

set -e

/bin/sh /extract_and_convert_zipfiles.sh

OUTPUT_FILE="/places/docker-output/us-places.ndjson"
echo "Writing the output to $(basename $OUTPUT_FILE) in the docker-output directory"
python3 /consolidate_generated_geojson.py > $OUTPUT_FILE
echo "Write complete! Exiting."
