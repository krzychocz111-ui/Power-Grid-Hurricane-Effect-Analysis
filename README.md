This repository contains the model of the East Baton Rouge Parish power grid for predicting the effects of hurricanes on it.
Currently it models only the effect of inundation on substations and not the effect of the wind on the transmission and distribution lines, 
because the damage resulting from floods is more costly and more difficult to remove quickly.
It also contains various documents and other resources that were used for or gathered in the process of creating this model. They are in Map_webui/files/
In order to run the web UI, a LibreOffice installation is needed and its install path must be given inside the app.py and start_all.py files if it differs on the user's computer. 
It uses LibreOffice's Python in order to enable calculation using the formulas in a spreadsheet.
To start the web UI, run the start_all.py after extracting the whole repository to a folder and changing the LibreOffice paths if necessary.

The Resources tab lists downloadable files from subfolders of `Map_webui/files`, with numbered, collapsible categories. It refreshes its catalog on page load; root-level files and `Old` are omitted. Only `ArcGis/Substations3/EBRGIS data layers` is shown from `Substations3`, under the label `EBRGIS map layers`. Restart the dashboard after updating its Python code.
`Show substations` adds diamond markers using the 74 parish locations exported from `Substations_v2_EBRP_Only`. Hover, click, or focus a marker for status and modeled repair cost (USD). The summary counts all modeled substations once and sums their repair costs, including partial outages. One location at 72nd Ave has no matching spreadsheet row and displays an unavailable status in gray. Regenerate the location GeoJSON with `Map_webui/tools/export_substations.py` in a GDAL-enabled Python environment when the source point layer changes.
