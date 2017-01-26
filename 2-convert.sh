destdir="2-cb-geojson"
rm -rf $destdir
mkdir $destdir
src="1-cb-shapefiles"
for i in $src/*.shp; do
    dest=`echo $i | sed s/shp$/json/ | sed s/$src/$destdir/`
    echo $dest $i
    ogr2ogr -f "GeoJSON" $dest $i
done
