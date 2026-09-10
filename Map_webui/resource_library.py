"""Folder-backed resource catalog, independent of the spreadsheet runtime."""

import json
import shutil
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, quote, urlsplit


MAP_PREFIX = ("ArcGis", "Substations3", "EBRGIS data layers")


def display_parts(relative):
    parts = relative.parts
    if len(parts) < 2 or parts[0].casefold() == "old":
        return None
    if any(part.startswith(".") or part == "__pycache__" for part in parts):
        return None
    if parts[:2] == ("ArcGis", "Substations3"):
        return ("EBRGIS map layers",) + parts[3:] if parts[:3] == MAP_PREFIX and len(parts) > 3 else None
    return parts


def resource_path(root, relative):
    """Apply the same eligibility and containment rules to listings and downloads."""
    relative = PurePosixPath(relative)
    if relative.is_absolute() or ".." in relative.parts or "\\" in str(relative):
        return None
    if display_parts(relative) is None:
        return None
    root = root.resolve()
    candidate = root.joinpath(*relative.parts)
    if any(part.is_symlink() for part in (candidate, *candidate.parents)):
        return None
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        return None
    return resolved


def resource_catalog(root):
    entries = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        display = display_parts(relative)
        if display is None or resource_path(root, relative.as_posix()) is None:
            continue
        entries.append({
            "folders": list(display[:-1]),
            "name": display[-1],
            "size": path.stat().st_size,
            "url": "/resource-download?path=" + quote(relative.as_posix(), safe=""),
        })
    return sorted(entries, key=lambda item: tuple(p.casefold() for p in (*item["folders"], item["name"])))


class ResourceLibraryMixin:
    def handle_resource_request(self, files_dir):
        request = urlsplit(self.path)
        if request.path == "/resources-list":
            body = json.dumps(resource_catalog(files_dir)).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return True
        if request.path != "/resource-download":
            return False
        relative = parse_qs(request.query).get("path", [""])[0]
        path = resource_path(files_dir, relative)
        if path is None:
            self.send_error(404, "Resource not found")
            return True
        # Stream large database files instead of loading them into memory.
        with path.open("rb") as source:
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(path.stat().st_size))
            self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(path.name, safe=""))
            self.end_headers()
            shutil.copyfileobj(source, self.wfile, length=1024 * 1024)
        return True
