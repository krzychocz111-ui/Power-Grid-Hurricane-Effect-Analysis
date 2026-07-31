import json
import math
from typing import Any, Dict, List


# ---------- CONFIG ----------
LAYER_NAME = "Baton Rouge substation connected areas"  # layer title (or part of it)
INPUT_FILE = ".\data.json"                      # your web map data JSON
OUTPUT_FILE = "baton_rouge_substation_areas.geojson"   # output GeoJSON
# -----------------------------


# ---- Coordinate conversion (Web Mercator -> WGS84) ----
def mercator_to_wgs84(x: float, y: float):
    """Convert Web Mercator (EPSG:3857) to WGS84 (EPSG:4326).
       If coords already look like lon/lat, return as-is."""
    # If it already looks like lon/lat, don't transform
    if -180.0 <= x <= 180.0 and -90.0 <= y <= 90.0:
        return [x, y]

    R = 6378137.0
    lon = (x / R) * (180.0 / math.pi)
    lat = (2.0 * math.atan(math.exp(y / R)) - math.pi / 2.0) * (180.0 / math.pi)
    return [lon, lat]


# ---- Recursive geometry extraction for CIM-style structures ----
def extract_paths_or_rings(obj: Any) -> List[List[List[float]]]:
    """
    Recursively search for geometry arrays with 'paths' or 'rings'.
    Returns a flat list of path/ring arrays: [ [ [x,y], [x,y], ... ], ... ]
    """
    paths: List[List[List[float]]] = []

    if isinstance(obj, dict):
        if "paths" in obj and isinstance(obj["paths"], list):
            paths += obj["paths"]
        if "rings" in obj and isinstance(obj["rings"], list):
            paths += obj["rings"]

        for v in obj.values():
            if isinstance(v, (dict, list)):
                paths += extract_paths_or_rings(v)

    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, (dict, list)):
                paths += extract_paths_or_rings(v)

    return paths


def find_layer_features(js: Dict[str, Any], layer_name: str) -> List[Dict[str, Any]]:
    """
    Find the feature array for a given layer title inside a web map JSON.
    Looks under js['operationalLayers'] for a layer whose 'title' (or 'id')
    matches (contains) layer_name, then returns its featureCollection -> featureSet -> features.
    """
    op_layers = js.get("operationalLayers", [])
    if not isinstance(op_layers, list):
        raise ValueError("JSON has no 'operationalLayers' list; not a web map?")

    candidates = []
    for lyr in op_layers:
        if not isinstance(lyr, dict):
            continue
        title = lyr.get("title") or lyr.get("id") or ""
        if layer_name.lower() in str(title).lower():
            candidates.append(lyr)

    if not candidates:
        # Helpful debug: show all titles
        titles = [str(lyr.get("title") or lyr.get("id")) for lyr in op_layers if isinstance(lyr, dict)]
        raise ValueError(
            f"Could not find a layer matching '{layer_name}' in operationalLayers.\n"
            f"Available layer titles/ids:\n  - " + "\n  - ".join(titles)
        )

    # If more than one matches, just take the first
    lyr = candidates[0]

    fc = lyr.get("featureCollection")
    if not isinstance(fc, dict):
        raise ValueError(f"Layer '{layer_name}' does not have an embedded featureCollection (it may be a reference layer).")

    layers = fc.get("layers")
    if not (isinstance(layers, list) and layers):
        raise ValueError(f"Layer '{layer_name}' has featureCollection but no 'layers' array.")

    first_layer = layers[0]
    if not isinstance(first_layer, dict):
        raise ValueError(f"Layer '{layer_name}' featureCollection.layers[0] is not an object.")

    feature_set = first_layer.get("featureSet")
    if not isinstance(feature_set, dict):
        raise ValueError(f"Layer '{layer_name}' featureCollection.layers[0] has no 'featureSet'.")

    features = feature_set.get("features")
    if not isinstance(features, list):
        raise ValueError(f"Layer '{layer_name}' featureSet has no 'features' list.")

    return features


def arcgis_layer_to_geojson(infile: str, outfile: str, layer_name: str):
    with open(infile, "r", encoding="utf-8") as f:
        js = json.load(f)

    features = find_layer_features(js, layer_name)

    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    for ftr in features:
        if not isinstance(ftr, dict):
            continue

        geom = ftr.get("geometry", {}) or {}
        attrs = ftr.get("attributes", {}) or {}

        # --- Primary case for your areas: polygons with rings ---
        # Try the simple case first: geometry.rings exists
        if "rings" in geom and isinstance(geom["rings"], list):
            rings_wgs84 = []
            for ring in geom["rings"]:
                if not isinstance(ring, list):
                    continue
                rings_wgs84.append([mercator_to_wgs84(x, y) for x, y in ring])

            geojson["features"].append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": rings_wgs84
                },
                "properties": attrs
            })
            continue

        # --- If not simple rings, try to dig them out of CIM / nested geometry ---
        paths = extract_paths_or_rings(geom)
        if paths:
            # Decide polygon vs line by closedness
            def is_closed(path):
                return len(path) > 1 and path[0] == path[-1]

            non_trivial = [p for p in paths if len(p) > 1]
            if non_trivial and all(is_closed(p) for p in non_trivial):
                # treat as polygon
                rings_wgs84 = []
                for ring in paths:
                    rings_wgs84.append([mercator_to_wgs84(x, y) for x, y in ring])

                geojson["features"].append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": rings_wgs84
                    },
                    "properties": attrs
                })
            else:
                # treat as lines (just in case you have some)
                lines_wgs84 = []
                for seg in paths:
                    lines_wgs84.append([mercator_to_wgs84(x, y) for x, y in seg])

                geojson["features"].append({
                    "type": "Feature",
                    "geometry": {
                        "type": "MultiLineString",
                        "coordinates": lines_wgs84
                    },
                    "properties": attrs
                })
            continue

        # --- Fallback: points, if any ---
        if "x" in geom and "y" in geom:
            x = geom.get("x")
            y = geom.get("y")
            if x is not None and y is not None:
                lon, lat = mercator_to_wgs84(x, y)
                geojson["features"].append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "properties": attrs
                })

    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)

    print(f"✅ Layer '{layer_name}' → {len(geojson['features'])} features → {outfile}")


if __name__ == "__main__":
    arcgis_layer_to_geojson(INPUT_FILE, OUTPUT_FILE, LAYER_NAME)
