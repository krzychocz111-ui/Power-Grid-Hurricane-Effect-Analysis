from pathlib import Path
import csv
import json
import os
from collections import defaultdict

os.environ.setdefault(
    "GDAL_PAM_PROXY_DIR",
    str(Path(__file__).resolve().parents[1] / "work_gdal_proxy"),
)

from osgeo import ogr, osr  # type: ignore


BASE_DIR = Path(__file__).resolve().parents[1]
GDB = BASE_DIR / "files" / "ArcGis" / "Substations3" / "Substations3.gdb"
INDUSTRIAL_GDB = Path(r"C:\Users\Krzysztof\Documents\ArcGIS\Projects\industrial\industrial.gdb")
INDUSTRIAL_LOADS = BASE_DIR / "files" / "IndustrialLoads.csv"
OUT_DIR = BASE_DIR / "data"
OUT_FILE = OUT_DIR / "dashboard_blocks.geojson"
BUILDINGS_OUT_FILE = OUT_DIR / "dashboard_buildings.geojson"

RAW_LAYER_NAME = "Census_2020_Block__Intersect"
PRIMARY_LAYER_NAME = "Census_2020_Block__Intersect_Overlaps"
BUILDING_JOIN_LAYER_NAME = "Census_2020_Block__Intersect_building_join"
INDUSTRIAL_LAYER_NAME = "EPA_POINTS_IN_EBRP"
RAW_TITLE_FIELD = "Substation_con_F__Statistics1_CONCATENATE_title"
RAW_N_TOTAL_FIELD = "Substation_con_F__Statistics1_FREQUENCY"
RESIDENTIAL_KWH_PER_HOUSEHOLD_DAY = 40.07
PRORATE_FIELDS = [
    "HH_UNITS",
    "SUM_POPL_TOTAL",
    "POPL_TOTAL",
    "Residential_kWh_day",
]
FIELDS = [
    "FID_Census_2020_Block_Nad83Albers",
    "GEOCODE",
    "TRACT",
    "BLOCK",
    "HH_UNITS",
    "SUM_POPL_TOTAL",
    "POPL_TOTAL",
    "CONCATENATE_title",
    "N_total",
    "OverlapFrac",
    "Residential_kWh_day",
    "LD_CLINIC",
    "LD_HOSP",
    "LD_SCHOOL",
    "LD_FIRE",
    "LD_OPO",
    "LD_SOCIAL",
    "LD_COURT",
    "LD_GOV",
    "LD_RETAIL",
    "LD_FOOD",
    "LD_ENT",
    "LD_EV",
    "LD_CHURCH",
    "LD_POLICE",
    "LD_POST",
    "LD_INDUSTRIAL",
]

LOAD_FIELDS = [field for field in FIELDS if field.startswith("LD_")]


def number(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def field_value(feature, field, default=None):
    try:
        return feature.GetField(field)
    except Exception:
        return default


def service_titles(feature):
    return field_value(feature, "CONCATENATE_title") or field_value(
        feature, RAW_TITLE_FIELD, ""
    )


def service_count(feature):
    value = field_value(feature, "N_total")
    if value not in (None, ""):
        return value
    value = field_value(feature, RAW_N_TOTAL_FIELD)
    if value not in (None, ""):
        return value
    names = [name for name in str(service_titles(feature)).split("|") if name.strip()]
    return len(names)


def residential_kwh_day(feature):
    value = field_value(feature, "Residential_kWh_day")
    if value not in (None, ""):
        return value
    return round(
        number(field_value(feature, "HH_UNITS")) * RESIDENTIAL_KWH_PER_HOUSEHOLD_DAY
    )


def census_block_key(feature):
    return field_value(feature, "FID_Census_2020_Block_Nad83Albers")


def feature_key(feature):
    return (
        census_block_key(feature),
        service_titles(feature),
    )


def feature_population(feature):
    return number(field_value(feature, "POPL_TOTAL")) + number(
        field_value(feature, "HH_UNITS")
    )


def select_dashboard_features(ds):
    primary_layer = ds.GetLayerByName(PRIMARY_LAYER_NAME)
    raw_layer = ds.GetLayerByName(RAW_LAYER_NAME)
    if primary_layer is None:
        raise RuntimeError(f"Could not find layer {PRIMARY_LAYER_NAME}")
    if raw_layer is None:
        raise RuntimeError(f"Could not find layer {RAW_LAYER_NAME}")

    selected = []
    raw_grouped_features = {}
    raw_populated_blocks = set()
    raw_layer.ResetReading()
    for feature in raw_layer:
        if feature_population(feature) <= 0:
            continue
        key = feature_key(feature)
        raw_populated_blocks.add(census_block_key(feature))
        overlap = number(field_value(feature, "OverlapFrac"))
        geom = feature.GetGeometryRef()
        if key not in raw_grouped_features:
            cloned = feature.Clone()
            raw_grouped_features[key] = {
                "id": f"raw-{feature.GetFID()}",
                "feature": cloned,
                "overlap": overlap,
                "geometry": geom.Clone() if geom is not None else None,
            }
        else:
            current = raw_grouped_features[key]
            current["overlap"] += overlap
            if geom is not None:
                if current["geometry"] is None:
                    current["geometry"] = geom.Clone()
                else:
                    unioned = current["geometry"].Union(geom)
                    if unioned is not None:
                        current["geometry"] = unioned

    for item in raw_grouped_features.values():
        feature = item["feature"]
        feature.SetField("OverlapFrac", min(1.0, item["overlap"]))
        if item["geometry"] is not None:
            feature.SetGeometry(item["geometry"])
        selected.append((item["id"], feature, "raw_intersect_prorated"))

    primary_layer.ResetReading()
    for feature in primary_layer:
        key = feature_key(feature)
        block_key = census_block_key(feature)
        if key in raw_grouped_features:
            continue
        source = "primary_zero_population" if block_key in raw_populated_blocks else "primary"
        selected.append((feature.GetFID(), feature.Clone(), source))

    return selected, primary_layer.GetSpatialRef(), len(raw_grouped_features)


def load_building_loads(ds):
    layer = ds.GetLayerByName(BUILDING_JOIN_LAYER_NAME)
    loads = defaultdict(lambda: defaultdict(float))
    if layer is None:
        return loads

    for feature in layer:
        key = feature_key(feature)
        for field in LOAD_FIELDS:
            if field != "LD_INDUSTRIAL":
                loads[key][field] += number(feature.GetField(field))
    return loads


def feature_centroid_lonlat(feature, transform):
    geom = feature.GetGeometryRef()
    if geom is None:
        return None, None
    centroid = geom.Centroid()
    if centroid is None:
        return None, None
    centroid = centroid.Clone()
    centroid.Transform(transform)
    return centroid.GetX(), centroid.GetY()


def load_building_points(ds, transform, key_to_feature_id):
    layer = ds.GetLayerByName(BUILDING_JOIN_LAYER_NAME)
    points = []
    if layer is None:
        return points

    layer.ResetReading()
    for feature in layer:
        service_feature_id = key_to_feature_id.get(feature_key(feature))
        if service_feature_id is None:
            continue
        label = (
            feature.GetField("BUSINESS_N")
            or feature.GetField("NAME")
            or feature.GetField("NAME_STD")
            or feature.GetField("FULL_ADDRE")
            or feature.GetField("BLDG_CAT")
            or "Building load"
        )
        address = feature.GetField("FULL_ADDRE") or feature.GetField("StreetAddr") or ""

        lon = number(feature.GetField("LONGITUDE"))
        lat = number(feature.GetField("LATITUDE"))
        if not lon or not lat:
            lon, lat = feature_centroid_lonlat(feature, transform)
        if lon is None or lat is None:
            continue

        for field in LOAD_FIELDS:
            if field == "LD_INDUSTRIAL":
                continue
            load_kw = number(feature.GetField(field))
            if load_kw <= 0:
                continue
            points.append(
                {
                    "type": "Feature",
                    "id": f"building-{feature.GetFID()}-{field}",
                    "properties": {
                        "category": field,
                        "source_category": feature.GetField("BLDG_CAT") or "",
                        "label": str(label),
                        "address": str(address),
                        "load_kw": load_kw,
                        "serviceFeatureId": service_feature_id,
                    },
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                }
            )
    layer.ResetReading()
    return points


def load_industrial_csv():
    if not INDUSTRIAL_LOADS.exists():
        return {}
    rows = {}
    with INDUSTRIAL_LOADS.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            try:
                object_id = int(row.get("OBJECTID") or 0)
            except ValueError:
                continue
            try:
                keep = int(float(row.get("Keep") or 0))
            except ValueError:
                keep = 0
            if keep != 1:
                continue
            rows[object_id] = number(row.get("Avg_Pwr_KW"))
    return rows


def load_industrial_outputs(selected_features, source_ref, target_ref):
    loads = defaultdict(float)
    points = []
    selected = load_industrial_csv()
    if not selected or not INDUSTRIAL_GDB.exists():
        return loads, points

    industrial_ds = ogr.Open(str(INDUSTRIAL_GDB))
    if industrial_ds is None:
        return loads, points
    point_layer = industrial_ds.GetLayerByName(INDUSTRIAL_LAYER_NAME)
    if point_layer is None:
        return loads, points

    point_ref = point_layer.GetSpatialRef()
    source_transform = None
    target_transform = None
    if point_ref is not None and source_ref is not None and not point_ref.IsSame(source_ref):
        source_transform = osr.CoordinateTransformation(point_ref, source_ref)
    if point_ref is not None and not point_ref.IsSame(target_ref):
        target_transform = osr.CoordinateTransformation(point_ref, target_ref)

    base_features = []
    for feature_id, feature, _source in selected_features:
        geom = feature.GetGeometryRef()
        if geom is None:
            continue
        base_features.append((feature_id, feature_key(feature), geom.Clone()))

    point_layer.ResetReading()
    for point_feature in point_layer:
        object_id = point_feature.GetFID()
        load_kw = selected.get(object_id)
        if not load_kw:
            continue
        geom = point_feature.GetGeometryRef()
        if geom is None:
            continue

        source_point = geom.Clone()
        if source_transform is not None:
            source_point.Transform(source_transform)

        service_feature_id = None
        service_key = None
        for feature_id, key, polygon in base_features:
            if polygon.Contains(source_point) or polygon.Intersects(source_point):
                service_feature_id = feature_id
                service_key = key
                break
        if service_feature_id is None or service_key is None:
            continue

        loads[service_key] += load_kw

        display_point = geom.Clone()
        if target_transform is not None:
            display_point.Transform(target_transform)
        points.append(
            {
                "type": "Feature",
                "id": f"industrial-{object_id}",
                "properties": {
                    "category": "LD_INDUSTRIAL",
                    "source_category": "INDUSTRIAL",
                    "label": point_feature.GetField("Name") or "Industrial load",
                    "address": point_feature.GetField("Name") or "",
                    "load_kw": load_kw,
                    "serviceFeatureId": service_feature_id,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [display_point.GetX(), display_point.GetY()],
                },
            }
        )

    return loads, points


def convert_ring(ring):
    return [[ring.GetX(i), ring.GetY(i)] for i in range(ring.GetPointCount())]


def convert_polygon(poly):
    return [convert_ring(poly.GetGeometryRef(i)) for i in range(poly.GetGeometryCount())]


def convert_geometry(geom):
    name = geom.GetGeometryName().upper()
    if name == "POLYGON":
        return {"type": "Polygon", "coordinates": convert_polygon(geom)}
    if name == "MULTIPOLYGON":
        return {
            "type": "MultiPolygon",
            "coordinates": [
                convert_polygon(geom.GetGeometryRef(i))
                for i in range(geom.GetGeometryCount())
            ],
        }
    return None


def main():
    OUT_DIR.mkdir(exist_ok=True)
    Path(os.environ["GDAL_PAM_PROXY_DIR"]).mkdir(exist_ok=True)

    ds = ogr.Open(str(GDB))
    if ds is None:
        raise RuntimeError(f"Could not open {GDB}")

    selected_features, source_ref, raw_intersect_count = select_dashboard_features(ds)
    target_ref = osr.SpatialReference()
    target_ref.ImportFromEPSG(4326)
    transform = osr.CoordinateTransformation(source_ref, target_ref)
    key_to_feature_id = {
        feature_key(feature): feature_id for feature_id, feature, _source in selected_features
    }
    building_loads = load_building_loads(ds)
    building_points = load_building_points(ds, transform, key_to_feature_id)
    industrial_loads, industrial_points = load_industrial_outputs(
        selected_features, source_ref, target_ref
    )

    features = []
    for feature_id, feature, source in selected_features:
        geom = feature.GetGeometryRef()
        if geom is None:
            continue
        geom = geom.Clone()
        geom.Transform(transform)
        geom = geom.SimplifyPreserveTopology(0.00002)
        geojson_geom = convert_geometry(geom)
        if not geojson_geom:
            continue

        props = {}
        for field in FIELDS:
            props[field] = field_value(feature, field)
        props["CONCATENATE_title"] = service_titles(feature)
        props["N_total"] = service_count(feature)
        props["Residential_kWh_day"] = residential_kwh_day(feature)
        props["dashboard_source_layer"] = source
        if source == "raw_intersect_prorated":
            overlap_fraction = number(props.get("OverlapFrac"))
            for field in PRORATE_FIELDS:
                if props.get(field) is not None:
                    props[field] = number(props[field]) * overlap_fraction
        key = feature_key(feature)
        for field in LOAD_FIELDS:
            props[field] = building_loads[key][field]
        props["LD_INDUSTRIAL"] = industrial_loads[key]

        features.append(
            {
                "type": "Feature",
                "id": feature_id,
                "properties": props,
                "geometry": geojson_geom,
            }
        )

    payload = {"type": "FeatureCollection", "features": features}
    OUT_FILE.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(
        f"Wrote {OUT_FILE} with {len(features)} features "
        f"({raw_intersect_count} populated raw-intersect features)"
    )

    building_payload = {
        "type": "FeatureCollection",
        "features": building_points + industrial_points,
    }
    BUILDINGS_OUT_FILE.write_text(
        json.dumps(building_payload, separators=(",", ":")), encoding="utf-8"
    )
    print(
        f"Wrote {BUILDINGS_OUT_FILE} with {len(building_payload['features'])} features"
    )


if __name__ == "__main__":
    main()
