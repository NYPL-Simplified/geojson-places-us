rm -rf 1-shapefiles
rm -rf 1-geonames
for i in cb_*.zip; do
    unzip "$i" -d 1-cb-shapefiles
done

for i in ??.zip; do
    unzip -o $i -d 1-geonames
done
