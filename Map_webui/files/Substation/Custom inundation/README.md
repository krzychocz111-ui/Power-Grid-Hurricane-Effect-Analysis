# Custom inundation CSV example

Download `custom_inundation_example.csv` and edit the `inundation_ft` column. It contains all 183 modeled substations, including those outside EBRP. Linde LLC is excluded because it is not a substation. Every value starts at zero.

1. Keep the `substation,inundation_ft` header and the supplied substation names.
2. Enter water depths in feet, using a decimal point (for example, 2.5).
3. Save as a comma-separated UTF-8 CSV.
4. In the dashboard select **Custom CSV, depth from ground**, upload the file, and click **Recalculate**.
5. Confirm that the status reports **183/183 CSV rows matched**.

Zero means no inundation when using depth from ground. To supply water-surface elevations instead, enter elevations in feet and select **Custom CSV, elevation from sea level**. The CSV does not record that choice; it comes from the dropdown. In sea-level mode the importer subtracts each substation's ground elevation and clamps negative depths to zero. A zero water-surface elevation is not the same as zero depth above ground.

Omitted, unrecognized, or invalid rows are skipped; they do not reset previous values. Keep all rows for a complete scenario.
