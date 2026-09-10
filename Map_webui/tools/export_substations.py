"""Export actual parish substation points; run with GDAL/OGR available."""
from pathlib import Path
import json
from osgeo import ogr, osr
base = Path(__file__).resolve().parents[1]
dataset = ogr.Open(str(base / 'files/ArcGis/Substations3/Substations3.gdb'))
layer = dataset.GetLayerByName('Substations_v2_EBRP_Only')
source = layer.GetSpatialRef()
source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
target = osr.SpatialReference()
target.ImportFromEPSG(4326)
target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
transform = osr.CoordinateTransformation(source, target)
features = []
for feature in layer:
    geometry = feature.GetGeometryRef().Clone()
    geometry.Transform(transform)
    features.append({'type': 'Feature', 'properties': {'name': feature.GetField('title')},
                     'geometry': json.loads(geometry.ExportToJson())})
output = base / 'data/dashboard_substations.geojson'
output.write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, indent=2), encoding='utf-8')
print(f'Exported {len(features)} substation locations')
