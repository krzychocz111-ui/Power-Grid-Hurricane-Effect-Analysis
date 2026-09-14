"""Export regional reference layers from the services saved in the ArcGIS project.
Requires GDAL/OGR only when regenerating; dashboard runtime uses bundled GeoJSON.
"""
from pathlib import Path
import json, urllib.request, urllib.parse
from datetime import datetime, timezone
from osgeo import ogr
ogr.UseExceptions()
base=Path(__file__).resolve().parents[1]
blocks=json.loads((base/'data/dashboard_blocks.geojson').read_text())
bounds=[]
for f in blocks['features']:
 e=ogr.CreateGeometryFromJson(json.dumps(f['geometry'])).GetEnvelope()
 bounds.append((e[0],e[2],e[1],e[3]))
extent=[min(b[0] for b in bounds)-.15,min(b[1] for b in bounds)-.15,max(b[2] for b in bounds)+.15,max(b[3] for b in bounds)+.15]
x1,y1,x2,y2=extent
clip=ogr.CreateGeometryFromWkt(f'POLYGON (({x1} {y1},{x2} {y1},{x2} {y2},{x1} {y2},{x1} {y1}))')
services={'transmission':'US_Electric_Power_Transmission_Lines','plants':'Power_Plants_in_the_US'}
for kind,service in services.items():
 url=f'https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/{service}/FeatureServer/0'
 def request(params):
  data=json.load(urllib.request.urlopen(url+'/query?'+urllib.parse.urlencode(params),timeout=90))
  if 'error' in data:raise RuntimeError(data['error'])
  return data
 query={'f':'json','where':'1=1','geometry':','.join(map(str,extent)),'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects','returnIdsOnly':'true'}
 ids=request(query).get('objectIds') or []
 features=[]
 for start in range(0,len(ids),100):
  data=request({'f':'geojson','objectIds':','.join(map(str,ids[start:start+100])),'outFields':'*','outSR':4326,'returnGeometry':'true'})
  for f in data['features']:
   geom=ogr.CreateGeometryFromJson(json.dumps(f['geometry'])).Intersection(clip)
   if geom.IsEmpty():continue
   f['geometry']=json.loads(geom.ExportToJson());features.append(f)
 output={'type':'FeatureCollection','features':features,'source':url,'exported_at':datetime.now(timezone.utc).isoformat(),'extent':extent}
 (base/f'data/dashboard_{kind}.geojson').write_text(json.dumps(output),encoding='utf-8')
 print(kind,len(features))
