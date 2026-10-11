"""
Render every spec in specs/ to a PNG in ../../Design/previews/.

The browser gets its styling from specs/config.json, which js/embed.js passes to
vegaEmbed. The CLI does not do that, so previews rendered straight from a spec
come out unstyled and do not match the live page. This merges the config in
first, writes a temp spec, and renders that.

    python render-previews.py            all specs
    python render-previews.py 05 11      only specs starting 05 or 11
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).parent
SPECS = HERE / "specs"
OUT = HERE.parent.parent / "Design" / "previews"
OUT.mkdir(parents=True, exist_ok=True)

CMD = ["npx", "-y", "-p", "vega-cli@6", "-p", "vega-lite@6", "vl2png"]

config = json.loads((SPECS / "config.json").read_text(encoding="utf-8"))
wanted = sys.argv[1:]

specs = sorted(SPECS.glob("*.vl.json"))
if wanted:
    specs = [s for s in specs if any(s.name.startswith(w) for w in wanted)]

failed = []
for spec_path in specs:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["config"] = {**config, **spec.get("config", {})}
    # config.json sets background null so the live page shows through; a PNG
    # needs something opaque or it composites black in any viewer.
    spec["config"]["background"] = "#F7F8F4"
    # specs set background null so the live card shows through; a top-level
    # value beats config, so clear it or every preview comes out transparent
    spec.pop("background", None)

    with tempfile.NamedTemporaryFile(
        "w", suffix=".vl.json", dir=HERE, delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(spec, tmp)
        tmp_path = pathlib.Path(tmp.name)

    png = OUT / (spec_path.name.replace(".vl.json", ".png"))
    try:
        r = subprocess.run(
            CMD + ["-b", str(HERE), str(tmp_path), str(png)],
            capture_output=True, text=True, shell=True,
        )
        err = "\n".join(
            l for l in r.stderr.splitlines()
            if "ERROR" in l.upper() or "WARN" in l.upper()
        )
        if r.returncode != 0 or not png.exists():
            failed.append(spec_path.name)
            print(f"FAIL {spec_path.name}\n{r.stderr[:500]}")
        else:
            size = png.stat().st_size
            flag = "  <-- check" if size < 6000 else ""
            print(f"ok   {spec_path.name:42s} {size:>7,} B{flag}")
            if err:
                print(f"     {err[:300]}")
    finally:
        tmp_path.unlink(missing_ok=True)

print(f"\n{len(specs) - len(failed)}/{len(specs)} rendered into {OUT}")
if failed:
    print("failed:", ", ".join(failed))
    sys.exit(1)
