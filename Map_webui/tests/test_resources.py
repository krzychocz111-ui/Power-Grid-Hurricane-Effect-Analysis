import json
import tempfile
import threading
import unittest
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from resource_library import ResourceLibraryMixin, resource_catalog, resource_path


class ResourcesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.names = ["root.ods", "Old/archived.csv", "Load/Commercial/usage # é.csv",
                      "Hurricane/Probability/report.pdf", "ArcGis/Substations3/project.aprx",
                      "ArcGis/Substations3/Default.gdb/data.bin",
                      "ArcGis/Substations3/EBRGIS data layers/School.shp",
                      "ArcGis/Substations3/EBRGIS data layers/School.dbf"]
        for name in self.names:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"original\r\nbytes\x00")

    def test_catalog_filters_and_aliases(self):
        entries = resource_catalog(self.root)
        self.assertEqual(len(entries), 4)
        self.assertEqual(sum(e['folders'] == ['EBRGIS map layers'] for e in entries), 2)
        self.assertFalse(any('Substations3' in e['folders'] for e in entries))
        (self.root / 'Load/new.txt').write_text('new')
        self.assertEqual(len(resource_catalog(self.root)), 5)

    def test_path_validation(self):
        for name in ['../outside', '/etc/passwd', 'Old/archived.csv', 'root.ods',
                     'Load/../root.ods', 'ArcGis/Substations3/project.aprx', 'Load\\..\\root.ods']:
            self.assertIsNone(resource_path(self.root, name))

    def test_http_catalog_and_downloads(self):
        root = self.root
        class Handler(ResourceLibraryMixin, SimpleHTTPRequestHandler):
            def do_GET(self):
                if not self.handle_resource_request(root):
                    self.send_error(404)
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            with urlopen(base + '/resources-list') as response:
                entries = json.load(response)
            for entry in entries:
                with urlopen(base + entry['url']) as response:
                    self.assertEqual(response.read(), b'original\r\nbytes\x00')
                    self.assertIn('attachment;', response.headers['Content-Disposition'])
                    self.assertEqual(int(response.headers['Content-Length']), entry['size'])
            for name in ['../outside', 'root.ods', 'Old/archived.csv']:
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + '/resource-download?path=' + quote(name))
                self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

if __name__ == '__main__': unittest.main()
