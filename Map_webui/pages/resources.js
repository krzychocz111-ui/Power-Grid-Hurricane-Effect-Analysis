function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    const units = ["KB", "MB", "GB"];
    let value = bytes / 1024;
    let index = 0;
    while (value >= 1024 && index < units.length - 1) { value /= 1024; index++; }
    return `${value.toFixed(1)} ${units[index]}`;
}

function buildTree(entries) {
    const root = { folders: new Map(), files: [], count: 0 };
    for (const entry of entries) {
        let node = root;
        node.count++;
        for (const folder of entry.folders) {
            if (!node.folders.has(folder)) node.folders.set(folder, { folders: new Map(), files: [], count: 0 });
            node = node.folders.get(folder);
            node.count++;
        }
        node.files.push(entry);
    }
    return root;
}

function renderTree(node, prefix = "") {
    const list = document.createElement("ol");
    list.className = "resourceTreeList";
    let index = 0;
    for (const [name, child] of node.folders) {
        const number = `${prefix}${++index}`;
        const item = document.createElement("li");
        const details = document.createElement("details");
        const summary = document.createElement("summary");
        summary.textContent = `${number}. ${name}`;
        const count = document.createElement("span");
        count.className = "resourceMeta";
        count.textContent = ` (${child.count} ${child.count === 1 ? "file" : "files"})`;
        summary.append(count);
        details.append(summary, renderTree(child, `${number}.`));
        item.append(details);
        list.append(item);
    }
    for (const file of node.files) {
        const item = document.createElement("li");
        item.className = "resourceFile";
        const number = document.createElement("span");
        number.textContent = `${prefix}${++index}. `;
        const link = document.createElement("a");
        link.href = file.url;
        link.download = file.name;
        link.textContent = file.name;
        const size = document.createElement("span");
        size.className = "resourceMeta";
        size.textContent = ` (${formatSize(file.size)})`;
        item.append(number, link, size);
        list.append(item);
    }
    return list;
}

async function loadResources() {
    const status = document.getElementById("resourceStatus");
    const container = document.getElementById("resourceTree");
    try {
        const response = await fetch("/resources-list", { cache: "no-store" });
        if (!response.ok) throw new Error("Unable to load resource list");
        const entries = await response.json();
        container.replaceChildren(renderTree(buildTree(entries)));
        status.textContent = entries.length ? `${entries.length} files available. Expand a category to browse.` : "No resources are available yet.";
        for (const [id, open] of [["expandAll", true], ["collapseAll", false]]) {
            const button = document.getElementById(id);
            button.disabled = !entries.length;
            button.onclick = () => container.querySelectorAll("details").forEach(details => { details.open = open; });
        }
    } catch (error) {
        status.textContent = "Could not load resources. Open this page through the dashboard server, then refresh to try again.";
    }
}
loadResources();
