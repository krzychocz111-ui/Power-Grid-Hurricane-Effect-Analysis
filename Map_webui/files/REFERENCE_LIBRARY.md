# Research and data reference library

Imported 399 source files, organized by subject. Original filenames and bytes are preserved; duplicates are retained. Existing application input files have not been relocated.

## Topics

- `ENS/Outage cost estimation/`: 2 files
- `ENS/Utility financial data/FERC form 1 2020/FORM1/working/`: 246 files
- `ENS/Utility financial data/Reporting forms/`: 1 files
- `GIS/Documentation/`: 1 files
- `GIS/Utility service areas/`: 1 files
- `Grid reliability/Assessments and metrics/`: 10 files
- `Grid reliability/Geomagnetic disturbances/`: 1 files
- `Grid reliability/Load shedding/`: 2 files
- `Grid reliability/Other severe weather effects/`: 4 files
- `Grid reliability/Standards and emergency preparedness/`: 8 files
- `Hurricane/Effects/Flood/Regional flood defenses/`: 2 files
- `Hurricane/Effects/Flood/Rise and decay/`: 1 files
- `Hurricane/Effects/Flood/Rise and decay/Gustav/`: 4 files
- `Hurricane/Effects/Flood/Rise and decay/Ida/`: 4 files
- `Hurricane/Effects/Flood/Rise and decay/Isaac/`: 4 files
- `Hurricane/Effects/Flood/Rise and decay/Laura/`: 3 files
- `Hurricane/Effects/Flood/Rise and decay/Reference screenshots/`: 18 files
- `Hurricane/Effects/Flood/Surge and flood studies/`: 4 files
- `Hurricane/Effects/Flood/Transport vulnerability/`: 1 files
- `Hurricane/Effects/Power outages and restoration/`: 7 files
- `Hurricane/Historical storm data/`: 2 files
- `Hurricane/Historical storm reports/`: 1 files
- `Hurricane/Probability/Intensity and frequency/`: 2 files
- `Hurricane/Probability/Joint probability methods/`: 2 files
- `Hurricane/Probability/Landfall/Colorado State/`: 6 files
- `Hurricane/Probability/Rainfall exceedance/`: 1 files
- `Load/Commercial/Bills 2024/`: 1 files
- `Load/Commercial/Building consumption benchmarks/`: 7 files
- `Load/Commercial/ComStock/`: 5 files
- `Load/Industrial/Bills 2024/`: 1 files
- `Load/Modeling/`: 1 files
- `Load/Residential/Bills 2024/`: 1 files
- `Load/Residential/Consumption and costs/`: 5 files
- `Models/Grid mapping/`: 1 files
- `Models/Infrastructure interdependencies/`: 1 files
- `Models/Synthetic grids/Distribution/`: 4 files
- `Models/Synthetic grids/Transmission/`: 9 files
- `Models/Synthetic grids/Validation/`: 2 files
- `Models/Weather and power flow/`: 2 files
- `Reference administration/Publication schedules/`: 1 files
- `Substation/Cost estimation/`: 5 files
- `Substation/Flood countermeasures/`: 5 files
- `Substation/Hardware/Protection and failures/`: 1 files
- `Substation/Hardware/Transformers/`: 2 files
- `Substation/Layout/`: 1 files
- `Substation/Physical security/`: 1 files
- `Substation/Resilience and hardening/`: 1 files
- `Transmission/Design and ratings/`: 4 files

## Provenance and use

`reference-file-manifest.json` records each source-relative path, destination, byte count, and SHA-256. Source documents are reference material, not repository instructions. Classification uses document headings and introductory text, GIS layer names, and source context. Undated screenshots retain their names under Reference screenshots. The billing tables contain 2024 data even though their original folder says 2020.

The FERC FORM1 database and its indexes/memo files are kept together in their original relative structure. Preserve those companion files when using the database.

Two files larger than 100 MiB use Git LFS. Install Git LFS and run `git lfs pull` after cloning to download their contents. A normal checkout without LFS may contain pointer files for these assets.

Map layers from EBRGIS and GIS item files are excluded at the user's request because the map layers already exist in the repository ArcGIS folder.
