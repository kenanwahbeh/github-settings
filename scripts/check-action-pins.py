"""Check direct Action references in active workflows and distributed templates."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import apply  # noqa: E402

root = Path(__file__).resolve().parent.parent
failures = []
for folder in (root / ".github/workflows", root / "workflows"):
    for path in sorted(folder.glob("*.y*ml")):
        try:
            refs = apply.unpinned_action_refs(apply.yaml.safe_load(path.read_text()))
        except apply.yaml.YAMLError as error:
            failures.append(f"{path.relative_to(root)}: invalid YAML: {error}")
            continue
        failures.extend(f"{path.relative_to(root)}: {ref}" for ref in refs)
if failures:
    print("Mutable Action references found:\n" + "\n".join(failures))
    sys.exit(1)
print("All direct external Action references are pinned to full SHAs")
