This repository contains the model of the East Baton Rouge Parish power grid for predicting the effects of hurricanes on it.
Currently it models only the effect of inundation on substations and not the effect of the wind on the transmission and distribution lines, 
because the damage resulting from floods is more costly and more difficult to remove quickly.
It also contains various documents and other resources that were used for or gathered in the process of creating this model. They are in Map_webui/files/
## Run on Windows

Extract the complete portable project ZIP to a writable local folder, then double-click **Start Dashboard.cmd**. Windows PowerShell unpacks the bundled LibreOffice on first use and launches the dashboard with LibreOffice's own Python. No separate Python, LibreOffice, or ArcGIS installation is needed. Keep the launcher window open; press Ctrl+C there to stop.

For a Git checkout, install Git LFS and run `git lfs pull` before launching. The runtime archive and two reference database files use LFS. GitHub's source ZIP may contain LFS pointers depending on repository settings; use the complete portable bundle for a no-Git installation.

The runtime is stored in `runtime/LibreOffice.zip` and extracted to the ignored `runtime/LibreOffice/` folder. The dashboard prefers this bundled runtime. Developers may alternatively set `LIBREOFFICE_PROGRAM` or use a standard installed LibreOffice. The bundled runtime is Windows x64; other operating systems are not included.


The Resources tab lists downloadable files from subfolders of `Map_webui/files`, with numbered, collapsible categories. It refreshes its catalog on page load; root-level files and `Old` are omitted. Only `ArcGis/Substations3/EBRGIS data layers` is shown from `Substations3`, under the label `EBRGIS map layers`. Restart the dashboard after updating its Python code.
`Show substations` adds diamond markers using the 74 parish locations exported from `Substations_v2_EBRP_Only`. Hover, click, or focus a marker for status and modeled repair cost (USD). The summary counts all modeled substations once and sums their repair costs, including partial outages. Ordinal spacing differences such as 72 nd and 72nd are normalized when matching spreadsheet and map names. Regenerate the location GeoJSON with `Map_webui/tools/export_substations.py` in a GDAL-enabled Python environment when the source point layer changes.

Transmission lines and Generation plants have independent toggles. Local snapshots from the ArcGIS project's US_Electric_Power_Transmission_Lines and Power_Plants_in_the_US services cover the dashboard extent plus 0.15 degrees on each side. Enabling either layer expands the map to that regional extent. Line colors represent voltage, not simulated outages. Plant details show fuel and total capacity. The snapshots work offline; regenerate with Map_webui/tools/export_grid_reference.py using GDAL/OGR and internet access. Source URLs and export timestamps are embedded in the GeoJSON.
