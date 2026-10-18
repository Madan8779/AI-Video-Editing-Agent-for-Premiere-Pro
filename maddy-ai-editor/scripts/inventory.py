"""Generate dependency metadata and preserve installed license files for review."""
import importlib.metadata as metadata
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = root / "docs" / "third-party-licenses"
output.mkdir(parents=True, exist_ok=True)
packages = []
for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
    name = dist.metadata["Name"]
    packages.append({"name": name, "version": dist.version,
                     "license": dist.metadata.get("License-Expression") or dist.metadata.get("License", "UNREPORTED"),
                     "homepage": dist.metadata.get("Home-page", ""),
                     "project_urls": dist.metadata.get_all("Project-URL", [])})
    for file in dist.files or []:
        path = Path(str(file))
        if ".dist-info" in str(path) and any(term in path.name.lower() for term in ("license", "copying", "notice")):
            source = Path(dist.locate_file(file))
            if source.is_file():
                pieces = list(path.parts)
                dist_info_index = next(i for i, part in enumerate(pieces) if part.endswith(".dist-info"))
                destination = output / name / Path(*pieces[dist_info_index + 1:])
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
(root / "docs" / "dependency-inventory.json").write_text(json.dumps(packages, indent=2), encoding="utf-8")
print(f"Recorded {len(packages)} distributions; license texts in {output}")
