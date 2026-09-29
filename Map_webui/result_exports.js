/* Export the last successful result, never the currently edited input controls. */
const ResultExports = (() => {
    function snapshot(data) {
        return JSON.parse(JSON.stringify({
            schema_version: 1,
            captured_at: new Date().toISOString(),
            scenario: data.scenario || { source: "unknown" },
            units: { load: "MW", repair_cost: "USD", households: "households", building_counts: "affected service polygons with this load type" },
            summary: data.summary,
            affected_households: data.summary.residential_full_customers + data.summary.residential_partial_customers,
            building_loads: Object.entries(data.load_labels).map(([field, label]) => ({
                field, label,
                full_outage_mw: data.summary.building_full_mw[field] || 0,
                partial_outage_mw: data.summary.building_partial_mw[field] || 0,
                total_outage_mw: (data.summary.building_full_mw[field] || 0) + (data.summary.building_partial_mw[field] || 0),
                full_affected: data.summary.building_full_customers[field] || 0,
                partial_affected: data.summary.building_partial_customers[field] || 0,
                total_affected: (data.summary.building_full_customers[field] || 0) + (data.summary.building_partial_customers[field] || 0)
            })),
            substation_results: data.substations || [],
            service_area_statuses: data.statuses || [],
            custom_csv: data.custom_csv
        }));
    }
    function toCsv(result) {
        const rows = [["section", "category", "metric", "value", "unit"]];
        rows.push(["metadata", "", "captured_at", result.captured_at, "UTC"]);
        for (const [key,value] of Object.entries(result.scenario)) rows.push(["scenario", "", key, value ?? "", ""]);
        for (const [key,value] of Object.entries(result.summary)) {
            if (typeof value !== "number") continue;
            const unit = key.endsWith("_mw") ? "MW" : key.includes("repair_cost") ? "USD" : key.startsWith("residential_") ? "households" : "count";
            rows.push(["summary", "", key, value, unit]);
        }
        rows.push(["summary", "", "affected_households", result.affected_households, "households"]);
        for (const item of result.building_loads) {
            for (const key of ["full_outage_mw", "partial_outage_mw", "total_outage_mw", "full_affected", "partial_affected", "total_affected"]) {
                rows.push(["building_load", item.label, key, item[key], key.endsWith("_mw") ? "MW" : "affected service polygons"]);
            }
        }
        const escape = value => {
            let text = String(value);
            // Prevent spreadsheet formula execution in filenames and other text fields.
            if (typeof value === "string" && /^[=+\-@\t\r]/.test(text)) text = "'" + text;
            return '"' + text.replace(/"/g, '""') + '"';
        };
        return rows.map(row => row.map(escape).join(",")).join("\r\n") + "\r\n";
    }
    return { snapshot, toCsv };
})();
if (typeof module !== "undefined") module.exports = ResultExports;
