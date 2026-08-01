from __future__ import annotations

import csv
import cgi
import io
import json
import mimetypes
import os
import re
import socket
import shutil
import subprocess
import sys
import threading
import time
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LIBREOFFICE_PROGRAM = r"C:\Program Files\LibreOffice\program"
if LIBREOFFICE_PROGRAM not in sys.path:
    sys.path.insert(0, LIBREOFFICE_PROGRAM)

import uno  # type: ignore

BASE_DIR = Path(__file__).resolve().parent
FILES_DIR = BASE_DIR / "files"
DATA_DIR = BASE_DIR / "data"
INDEX_HTML = BASE_DIR / "index.html"

DEFAULT_ODS = FILES_DIR / "Substations_default.ods"
CALCULATED_ODS = FILES_DIR / "Substations_calculated.ods"
BLOCKS_GEOJSON = DATA_DIR / "dashboard_blocks.geojson"
LIBREOFFICE_EXE = Path(r"C:\Program Files\LibreOffice\program\soffice.exe")
LO_PROFILE_DIR = BASE_DIR / "lo_profile"
UNO_PORT = 2002

_lo_process = None
_spreadsheet_lock = threading.Lock()

LOAD_FIELDS = [
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

LOAD_LABELS = {
    "LD_CLINIC": "Clinics",
    "LD_HOSP": "Hospitals",
    "LD_SCHOOL": "Schools",
    "LD_FIRE": "Fire stations",
    "LD_OPO": "Other public offices",
    "LD_SOCIAL": "Social services",
    "LD_COURT": "Courts",
    "LD_GOV": "Government",
    "LD_RETAIL": "Retail",
    "LD_FOOD": "Food retail",
    "LD_ENT": "Entertainment",
    "LD_EV": "EV charging",
    "LD_CHURCH": "Churches",
    "LD_POLICE": "Police",
    "LD_POST": "Post offices",
    "LD_INDUSTRIAL": "Industrial",
}


def column_index(name: str) -> int:
    value = 0
    for char in name.upper():
        value = value * 26 + ord(char) - 64
    return value - 1


COL_OUTPUT_SURVIVAL = column_index("AC")
COL_OUTPUT_COMPLETE = column_index("AD")
COL_OUTPUT_REDUCED = column_index("AE")
COL_OUTPUT_REPAIR_COST = column_index("AF")
COL_OUTPUT_LEAD_TIME = column_index("AG")
COL_OUTPUT_DAMAGED_LONG_LEAD = column_index("AH")
COL_OUTPUT_DIRECT_OUT = column_index("AI")
COL_OUTPUT_REDUCED_OTHER = column_index("AJ")
COL_OUTPUT_OUT_OTHER = column_index("AK")
COL_CUSTOM_INUNDATION = column_index("W")
COL_ELEVATION_FT = column_index("ZI")


def system_path_to_file_url(path: Path) -> str:
    return uno.systemPathToFileUrl(str(path.resolve()))


def wait_for_port(port: int, timeout: float = 15.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def start_libreoffice_listener():
    global _lo_process
    if wait_for_port(UNO_PORT, timeout=0.5):
        return

    LO_PROFILE_DIR.mkdir(exist_ok=True)
    cmd = [
        str(LIBREOFFICE_EXE),
        "--headless",
        f"--accept=socket,host=127.0.0.1,port={UNO_PORT};urp;",
        "--nologo",
        "--nodefault",
        "--norestore",
        f"-env:UserInstallation={LO_PROFILE_DIR.as_uri()}",
    ]
    _lo_process = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not wait_for_port(UNO_PORT, timeout=20):
        raise RuntimeError("LibreOffice listener did not start.")


def connect_to_libreoffice():
    last_error = None
    for attempt in range(2):
        try:
            start_libreoffice_listener()
            local_ctx = uno.getComponentContext()
            resolver = local_ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.bridge.UnoUrlResolver", local_ctx
            )
            ctx = resolver.resolve(
                f"uno:socket,host=127.0.0.1,port={UNO_PORT};urp;StarOffice.ComponentContext"
            )
            return ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", ctx
            )
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1)
    raise last_error


def hidden_property():
    hidden = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    hidden.Name = "Hidden"
    hidden.Value = True
    return hidden


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def cell_string(sheet, col: int, row: int) -> str:
    return str(sheet.getCellByPosition(col, row).String or "").strip()


def cell_value(sheet, col: int, row: int) -> float:
    try:
        return float(sheet.getCellByPosition(col, row).Value or 0)
    except Exception:
        return 0.0


def truthy_cell(sheet, col: int, row: int) -> bool:
    text = cell_string(sheet, col, row).lower()
    return text in {"y", "yes", "true", "1"} or cell_value(sheet, col, row) >= 1


def apply_scenario(sheet, source: str, category: str):
    source = source.upper()
    sheet.getCellRangeByName("D1").String = source
    sheet.getCellRangeByName("I1").String = source
    if source == "H":
        sheet.getCellRangeByName("I2").Value = float(category)
    elif source == "N":
        sheet.getCellRangeByName("I2").Value = 0


def apply_custom_csv(sheet, upload, source: str):
    if upload is None or not upload.filename:
        return {"matched": 0, "rows": 0}

    text = upload.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return {"matched": 0, "rows": 0}

    names = {}
    for row_idx in range(3, 191):
        name = normalize_name(cell_string(sheet, 1, row_idx))
        if name:
            names[name] = row_idx

    matched = 0
    for row in rows:
        name = normalize_name(
            row.get("substation")
            or row.get("name")
            or row.get("Substation")
            or row.get("Name")
            or ""
        )
        if not name or name not in names:
            continue
        raw_depth = (
            row.get("inundation_ft")
            or row.get("depth_ft")
            or row.get("flood_depth_ft")
            or row.get("depth")
            or ""
        )
        try:
            depth = float(raw_depth)
        except ValueError:
            continue
        row_idx = names[name]
        if source.upper() == "S":
            elevation_ft = cell_value(sheet, COL_ELEVATION_FT, row_idx)
            depth = max(0.0, depth - elevation_ft)
        sheet.getCellByPosition(COL_CUSTOM_INUNDATION, row_idx).Value = depth
        matched += 1

    return {"matched": matched, "rows": len(rows)}


def read_substation_results(sheet):
    results = {}
    for row_idx in range(3, 191):
        name = cell_string(sheet, 1, row_idx)
        if not name:
            continue
        complete_probability = cell_value(sheet, COL_OUTPUT_COMPLETE, row_idx)
        reduced_probability = cell_value(sheet, COL_OUTPUT_REDUCED, row_idx)
        direct_out = truthy_cell(sheet, COL_OUTPUT_DIRECT_OUT, row_idx)
        reduced_other = truthy_cell(sheet, COL_OUTPUT_REDUCED_OTHER, row_idx)
        out_other = truthy_cell(sheet, COL_OUTPUT_OUT_OTHER, row_idx)
        full = direct_out or out_other or complete_probability >= 0.5
        partial = (not full) and (reduced_other or reduced_probability >= 0.5)
        results[normalize_name(name)] = {
            "name": name,
            "full": full,
            "partial": partial,
            "complete_probability": complete_probability,
            "reduced_probability": reduced_probability,
            "survival_probability": cell_value(sheet, COL_OUTPUT_SURVIVAL, row_idx),
            "repair_cost": cell_value(sheet, COL_OUTPUT_REPAIR_COST, row_idx),
            "lead_time_days": cell_value(sheet, COL_OUTPUT_LEAD_TIME, row_idx),
            "damaged_long_lead_count": cell_value(
                sheet, COL_OUTPUT_DAMAGED_LONG_LEAD, row_idx
            ),
        }
    return results


def recalculate_spreadsheet(source: str, category: str, upload=None, include_geojson=False):
    with _spreadsheet_lock:
        desktop = connect_to_libreoffice()
        doc = desktop.loadComponentFromURL(
            system_path_to_file_url(CALCULATED_ODS), "_blank", 0, (hidden_property(),)
        )
        custom_info = {"matched": 0, "rows": 0}
        try:
            sheet = doc.Sheets.getByName("Substations")
            apply_scenario(sheet, source, category)
            if source.upper() in {"G", "S"}:
                custom_info = apply_custom_csv(sheet, upload, source)
            doc.calculateAll()
            doc.store()
            substations = read_substation_results(sheet)
        finally:
            try:
                doc.close(True)
            except Exception:
                pass
    return build_dashboard_state(substations, custom_info, include_geojson=include_geojson)


def load_blocks():
    if not BLOCKS_GEOJSON.exists():
        raise FileNotFoundError(
            "Dashboard GeoJSON is missing. Run tools/export_dashboard_geojson.py first."
        )
    return json.loads(BLOCKS_GEOJSON.read_text(encoding="utf-8"))


def feature_load_mw(props):
    residential_mw = float(props.get("Residential_kWh_day") or 0) / 24 / 1000
    building_mw = sum(float(props.get(field) or 0) for field in LOAD_FIELDS) / 1000
    return residential_mw + building_mw


def classify_feature(props, substations):
    names = [
        normalize_name(name)
        for name in str(props.get("CONCATENATE_title") or "").split("|")
        if normalize_name(name)
    ]
    if not names:
        return "served", 0, 0, 0
    full = sum(1 for name in names if substations.get(name, {}).get("full"))
    partial = sum(1 for name in names if substations.get(name, {}).get("partial"))
    total = len(names)
    if full >= total:
        return "full", full, partial, total
    if full or partial:
        return "partial", full, partial, total
    return "served", full, partial, total


def build_dashboard_state(substations, custom_info=None, include_geojson=True):
    blocks = load_blocks()
    statuses = []
    summary = {
        "full_outage_mw": 0.0,
        "partial_outage_mw": 0.0,
        "residential_full_customers": 0,
        "residential_partial_customers": 0,
        "building_full_customers": {field: 0 for field in LOAD_FIELDS},
        "building_partial_customers": {field: 0 for field in LOAD_FIELDS},
        "building_full_mw": {field: 0.0 for field in LOAD_FIELDS},
        "building_partial_mw": {field: 0.0 for field in LOAD_FIELDS},
        "served_blocks": 0,
        "partial_blocks": 0,
        "full_blocks": 0,
    }

    for feature in blocks["features"]:
        props = feature["properties"]
        status, full_count, partial_count, total = classify_feature(props, substations)
        props["dashboard_status"] = status
        props["dashboard_full_substations"] = full_count
        props["dashboard_partial_substations"] = partial_count
        props["dashboard_total_substations"] = total
        statuses.append(
            {
                "id": feature.get("id"),
                "status": status,
                "full": full_count,
                "partial": partial_count,
                "total": total,
            }
        )

        load_mw = feature_load_mw(props)
        hh_units = int(float(props.get("HH_UNITS") or 0))
        if status == "full":
            summary["full_blocks"] += 1
            summary["full_outage_mw"] += load_mw
            summary["residential_full_customers"] += hh_units
            factor = 1.0
            bucket = "full"
        elif status == "partial":
            summary["partial_blocks"] += 1
            outage_fraction = min(1.0, (full_count + 0.5 * partial_count) / max(total, 1))
            summary["partial_outage_mw"] += load_mw * outage_fraction
            summary["residential_partial_customers"] += round(hh_units * outage_fraction)
            factor = outage_fraction
            bucket = "partial"
        else:
            summary["served_blocks"] += 1
            factor = 0.0
            bucket = "served"

        if bucket in {"full", "partial"}:
            for field in LOAD_FIELDS:
                load_kw = float(props.get(field) or 0)
                if load_kw > 0:
                    summary[f"building_{bucket}_customers"][field] += 1
                    summary[f"building_{bucket}_mw"][field] += load_kw * factor / 1000

    summary["total_full_and_partial_mw"] = (
        summary["full_outage_mw"] + summary["partial_outage_mw"]
    )
    response = {
        "success": True,
        "summary": summary,
        "load_labels": LOAD_LABELS,
        "statuses": statuses,
        "custom_csv": custom_info or {"matched": 0, "rows": 0},
    }
    if include_geojson:
        response["geojson"] = blocks
    return response


def truthy_request_value(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def current_state(include_geojson=True):
    with _spreadsheet_lock:
        desktop = connect_to_libreoffice()
        doc = desktop.loadComponentFromURL(
            system_path_to_file_url(CALCULATED_ODS), "_blank", 0, (hidden_property(),)
        )
        try:
            sheet = doc.Sheets.getByName("Substations")
            return build_dashboard_state(
                read_substation_results(sheet), include_geojson=include_geojson
            )
        finally:
            try:
                doc.close(True)
            except Exception:
                pass


class UploadedFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    def read(self):
        return self._content


class DashboardHandler(SimpleHTTPRequestHandler):
    server_version = "EBRPDashboard/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def log_message(self, format, *args):
        print(format % args, flush=True)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_download(self, path: Path, filename: str):
        if not path.exists():
            self.send_json({"success": False, "error": f"Missing file: {filename}"}, 404)
            return
        body = path.read_bytes()
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def read_multipart_body(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type"),
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            },
        )
        fields = {}
        files = {}
        for key in form:
            item = form[key]
            if isinstance(item, list):
                item = item[0]
            if item.filename:
                files[key] = UploadedFile(item.filename, item.file.read())
            else:
                fields[key] = item.value
        return fields, files

    def shutdown_server(self):
        def stop():
            time.sleep(0.2)
            self.server.shutdown()

        threading.Thread(target=stop, daemon=True).start()
        self.send_json({"success": True, "message": "Dashboard shutting down"})

    def do_GET(self):
        try:
            if self.path == "/":
                self.path = "/index.html"
                return super().do_GET()
            if self.path == "/state":
                return self.send_json(current_state())
            if self.path == "/app-info":
                return self.send_json(
                    {
                        "success": True,
                        "base_dir": str(BASE_DIR),
                        "index_mtime": INDEX_HTML.stat().st_mtime
                        if INDEX_HTML.exists()
                        else None,
                    }
                )
            if self.path == "/shutdown":
                return self.shutdown_server()
            if self.path == "/download":
                return self.send_download(CALCULATED_ODS, "Substations_calculated.ods")
            if self.path == "/download-map":
                return self.send_download(BLOCKS_GEOJSON, "dashboard_blocks.geojson")
            if self.path == "/test-open":
                desktop = connect_to_libreoffice()
                doc = desktop.loadComponentFromURL(
                    "private:factory/scalc", "_blank", 0, (hidden_property(),)
                )
                doc.close(True)
                return self.send_json(
                    {"success": True, "message": "Blank Calc opened successfully"}
                )
            return super().do_GET()
        except Exception as e:
            traceback.print_exc()
            self.send_json({"success": False, "error": str(e)}, 500)

    def do_POST(self):
        try:
            if self.path == "/shutdown":
                return self.shutdown_server()

            if self.path == "/reset":
                shutil.copyfile(DEFAULT_ODS, CALCULATED_ODS)
                return self.send_json(current_state(include_geojson=False))

            if self.path == "/calculate":
                content_type = self.headers.get("Content-Type", "")
                upload = None
                include_geojson = False
                if content_type.startswith("multipart/form-data"):
                    fields, files = self.read_multipart_body()
                    source = str(fields.get("source", "H")).strip().upper()
                    category = str(fields.get("category", "1")).strip()
                    include_geojson = truthy_request_value(fields.get("includeGeojson"))
                    upload = files.get("customCsv")
                else:
                    data = self.read_json_body()
                    source = str(data.get("source", "H")).strip().upper()
                    category = str(data.get("category", "1")).strip()
                    include_geojson = truthy_request_value(data.get("includeGeojson"))

                if source not in {"H", "N", "G", "S"}:
                    return self.send_json(
                        {"success": False, "error": "Unknown scenario source"}, 400
                    )
                return self.send_json(
                    recalculate_spreadsheet(
                        source, category, upload, include_geojson=include_geojson
                    )
                )

            self.send_json({"success": False, "error": "Unknown endpoint"}, 404)
        except Exception as e:
            traceback.print_exc()
            self.send_json({"success": False, "error": str(e)}, 500)


def main():
    os.chdir(BASE_DIR)
    port = int(os.environ.get("DASHBOARD_PORT", "5000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"Dashboard server running at http://127.0.0.1:{port}/", flush=True)
    print(f"Serving files from {BASE_DIR}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
