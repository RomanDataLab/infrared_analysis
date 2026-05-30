"""
refine.py — Re-run the full simulation pipeline when enriched input data is ready
==================================================================================
Detects stale baselines and re-executes:

    baseline.py → scenarios.py → canopy_scenario.py (hot) → score.py → export_web.py

Staleness triggers
------------------
  1. ndvi_trees.json is NEWER than baseline_utci.npy
       → NDVI-derived canopy generated after the last baseline run
  2. fetched_data.json has NO "ov_*" keys AND overturemaps library is installed
       → Overture buildings haven't been incorporated into the cache yet
  3. --force flag → re-run every site unconditionally

Usage
-----
    python refine.py                  # check all sites, re-run stale ones
    python refine.py --site almaty    # one site only
    python refine.py --force          # re-run everything unconditionally
    python refine.py --check          # dry-run — print plan only, no simulation

Typical workflow after getting new data
----------------------------------------
  1.  Run GEE script (gee_ndvi_canopy.js) → download 4 GeoJSON files
  2.  For each site:
        python postprocess_ndvi.py --site <s> --geojson <City>_canopy_polygons.geojson
  3.  Then:
        python refine.py
      The script detects which sites have new ndvi_trees.json files, re-runs them
      and prints a before/after comparison table.
"""

import argparse
import io
import json
import sys
import time
import subprocess
from pathlib import Path

# Force UTF-8 output on Windows (cp1252 can't render box-drawing chars)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

sys.path.insert(0, str(Path(__file__).parent))
from sites import SITES

ANALYSIS_DIR = Path(__file__).parent
HOT_SITES    = {k for k, v in SITES.items() if v["climate"] == "hot"}


# ── Staleness detection ───────────────────────────────────────────────────────

def _overture_installed() -> bool:
    try:
        import overturemaps   # noqa: F401
        return True
    except ImportError:
        return False


def _overture_applied(fetched_json: Path) -> bool:
    """
    Return True if Overture enrichment has already been attempted for this site.

    Two signals:
      1. fetched_data.json contains any "ov_*" building keys  (enrichment added buildings)
      2. fetched_data.json has "overture_checked": true        (enrichment ran but found 0)

    The second condition prevents an infinite re-run loop for sites where Overture
    simply has no extra coverage (e.g. sparse Mecca bbox).
    """
    if not fetched_json.exists():
        return False
    try:
        with open(fetched_json) as f:
            data = json.load(f)
        if data.get("overture_checked"):
            return True
        return any(k.startswith("ov_") for k in data.get("buildings", {}))
    except Exception:
        return False


def _ndvi_stale(out_dir: Path) -> bool:
    """Return True if ndvi_trees.json exists and is newer than the last baseline run."""
    ndvi = out_dir / "ndvi_trees.json"
    utci = out_dir / "baseline_utci.npy"
    if not ndvi.exists():
        return False
    if not utci.exists():
        return True   # baseline has never run
    return ndvi.stat().st_mtime > utci.stat().st_mtime


def check_site(site_key: str, force: bool) -> dict:
    """
    Return {needs_run: bool, reasons: list[str], data_status: dict}
    describing why (or why not) the site should be re-run.
    """
    out     = ANALYSIS_DIR / "results" / site_key
    fetched = out / "fetched_data.json"
    ndvi    = out / "ndvi_trees.json"
    utci    = out / "baseline_utci.npy"

    reasons = []
    data    = {}

    # Count enrichment sources in current cache
    if fetched.exists():
        with open(fetched) as f:
            fd = json.load(f)
        bldgs         = fd.get("buildings", {})
        data["n_osm"] = sum(1 for k in bldgs if not k.startswith("ov_"))
        data["n_ov"]  = sum(1 for k in bldgs if k.startswith("ov_"))
    else:
        data["n_osm"] = 0
        data["n_ov"]  = 0

    if ndvi.exists():
        with open(ndvi) as f:
            data["n_ndvi"] = len(json.load(f))
    else:
        data["n_ndvi"] = 0

    data["has_baseline"] = utci.exists()

    if force:
        reasons.append("--force")
    else:
        if not utci.exists():
            reasons.append("no baseline yet")
        if _ndvi_stale(out):
            reasons.append(
                f"ndvi_trees.json ({data['n_ndvi']} trees) is newer than baseline"
            )
        if _overture_installed() and not _overture_applied(fetched):
            reasons.append(
                "overturemaps installed but Overture buildings not in cache"
            )

    return {"needs_run": bool(reasons), "reasons": reasons, "data": data}


# ── Result snapshot ───────────────────────────────────────────────────────────

def snapshot(site_key: str) -> dict:
    """Read current baseline_stats + courtyard_score + cache counts."""
    out  = ANALYSIS_DIR / "results" / site_key
    snap = {}

    stats = out / "baseline_stats.json"
    if stats.exists():
        with open(stats) as f:
            bs = json.load(f)
        snap["utci_mean"]     = bs["utci"]["mean_c"]
        snap["wind_mean"]     = bs["wind"]["mean_ms"]
        snap["sun_mean"]      = bs["sun"]["mean_hrs_day"]
        snap["utci_bad_frac"] = bs["utci"]["frac_utci_bad"]

    score = out / "courtyard_score.json"
    if score.exists():
        with open(score) as f:
            sc = json.load(f)
        snap["composite"]   = sc["composite_score"]
        snap["grade"]       = sc.get("grade", "")[:3].strip()
        bi = sc.get("best_intervention") or {}
        snap["best_key"]    = bi.get("key")
        snap["best_utci"]   = bi.get("utci_improv_c")
        snap["best_label"]  = bi.get("label")

    fetched = out / "fetched_data.json"
    if fetched.exists():
        with open(fetched) as f:
            fd = json.load(f)
        bldgs        = fd.get("buildings", {})
        snap["n_bld_total"] = len(bldgs)
        snap["n_bld_ov"]    = sum(1 for k in bldgs if k.startswith("ov_"))
        snap["n_bld_osm"]   = snap["n_bld_total"] - snap["n_bld_ov"]

    ndvi = out / "ndvi_trees.json"
    snap["n_ndvi"] = 0
    if ndvi.exists():
        with open(ndvi) as f:
            snap["n_ndvi"] = len(json.load(f))

    return snap


# ── Delta printer ─────────────────────────────────────────────────────────────

def print_delta(site_key: str, before: dict, after: dict):
    name = SITES[site_key]["name"]
    W = 62

    def row(label, key, fmt=".2f", unit="", flip_sign=False):
        """Print one comparison row; flip_sign=True means negative delta is good."""
        b = before.get(key)
        a = after.get(key)
        if b is None and a is None:
            return
        b_s = f"{b:{fmt}}{unit}" if isinstance(b, (int, float)) else str(b or "—")
        a_s = f"{a:{fmt}}{unit}" if isinstance(a, (int, float)) else str(a or "—")
        delta_s = ""
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            d = a - b
            if flip_sign:
                arrow = "↓ better" if d < 0 else ("↑ worse" if d > 0 else "=")
            else:
                arrow = "↑ better" if d > 0 else ("↓ worse" if d < 0 else "=")
            delta_s = f"   {d:+.2f}  {arrow}"
        print(f"  │  {label:<24}  {b_s:>9}  →  {a_s:>9}{delta_s}")

    print(f"\n  ┌── {name} {'─'*(W - len(name) - 5)}")

    # Input data counts
    b_total = before.get("n_bld_total", "—")
    a_total = after.get("n_bld_total", "—")
    b_ov    = before.get("n_bld_ov", 0)
    a_ov    = after.get("n_bld_ov", 0)
    b_nd    = before.get("n_ndvi", 0)
    a_nd    = after.get("n_ndvi", 0)

    print(f"  │  Input data")
    print(f"  │    Buildings total     {str(b_total):>9}  →  {str(a_total):>9}"
          f"   ({a_total - b_total if isinstance(a_total,int) and isinstance(b_total,int) else '?':+d} Overture added)" \
          if isinstance(a_ov, int) and a_ov > 0 else
          f"  │    Buildings total     {str(b_total):>9}  →  {str(a_total):>9}")
    if a_ov > 0:
        print(f"  │    Of which Overture  {b_ov:>9}  →  {a_ov:>9}")
    print(f"  │    NDVI trees         {b_nd:>9}  →  {a_nd:>9}")
    print(f"  │  {'─'*(W-4)}")

    # Simulation results
    print(f"  │  Simulation results")
    row("UTCI mean",        "utci_mean",     ".2f", " °C",  flip_sign=True)
    row("UTCI bad fraction","utci_bad_frac", ".3f", "",     flip_sign=True)
    row("Wind mean",        "wind_mean",     ".2f", " m/s", flip_sign=False)
    row("Sun mean",         "sun_mean",      ".2f", " h/d", flip_sign=False)
    print(f"  │  {'─'*(W-4)}")

    row("Composite score",  "composite",     ".1f", "/100", flip_sign=False)

    g_b = str(before.get("grade", "—"))[:2]
    g_a = str(after.get("grade", "—"))[:2]
    changed = "  ← grade changed" if g_b != g_a else ""
    print(f"  │  {'Grade':<24}  {g_b:>9}  →  {g_a:>9}{changed}")

    b_lbl = (after.get("best_label") or "—")[:30]
    b_key = after.get("best_key") or "—"
    b_imp = after.get("best_utci")
    if b_imp is not None:
        print(f"  │  Best scenario [{b_key}]  {b_lbl}  UTCI +{b_imp:.2f}°C")

    print(f"  └{'─'*(W-1)}")


# ── Pipeline runner ───────────────────────────────────────────────────────────

def run_step(script: str, args: list = None, label: str = None) -> bool:
    """
    Run one pipeline script as a subprocess.
    Streams its output to the terminal in real time.
    Returns True on success (exit code 0).
    """
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"   # prevent cp1252 crash on Unicode print

    cmd = [sys.executable, str(ANALYSIS_DIR / script)] + (args or [])
    tag = label or script
    print(f"\n  -- {tag} " + "-" * max(0, 50 - len(tag)))
    t0  = time.time()
    result = subprocess.run(cmd, cwd=str(ANALYSIS_DIR), env=env)
    elapsed = time.time() - t0
    ok = result.returncode == 0
    status = "OK done" if ok else f"FAILED (exit {result.returncode})"
    print(f"  \\-- {status}  ({elapsed:.0f}s)")
    return ok


def run_pipeline(site_key: str, dry_run: bool = False) -> bool:
    """
    Execute all five pipeline stages for one site.
    Returns True if every stage succeeded.
    """
    name = SITES[site_key]["name"]
    print(f"\n{'═'*62}")
    print(f"  REFINING: {name}")
    print(f"{'═'*62}")

    before = snapshot(site_key)

    steps = [
        ("baseline.py",  ["--site", site_key], "1/5  baseline (OSM + Overture + NDVI)"),
        ("scenarios.py", ["--site", site_key], "2/5  scenarios A/B/C"),
    ]
    if site_key in HOT_SITES:
        steps.append(
            ("canopy_scenario.py", ["--site", site_key], "3/5  canopy scenario D")
        )
    else:
        print("\n       3/5  canopy scenario — skipped (cold site)")

    steps += [
        ("score.py",      ["--site", site_key], "4/5  score"),
        ("export_web.py", [],                   "5/5  export web assets"),
    ]

    if dry_run:
        print("\n  [dry-run] would execute:")
        for script, args, label in steps:
            print(f"    python {script} {' '.join(args)}")
        return True

    ok = True
    for script, args, label in steps:
        success = run_step(script, args, label)
        if not success:
            print(f"\n  Pipeline aborted at {script}")
            ok = False
            break

    if ok:
        after = snapshot(site_key)
        print_delta(site_key, before, after)

    return ok


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Re-run simulation pipeline when enriched building/tree data is ready",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python refine.py                  # detect and re-run stale sites
  python refine.py --site almaty    # one site only
  python refine.py --force          # re-run everything
  python refine.py --check          # dry-run, print plan only
  python refine.py --check --force  # show full plan for all sites
""",
    )
    parser.add_argument("--site",  choices=list(SITES.keys()),
                        help="Re-run only this site")
    parser.add_argument("--force", action="store_true",
                        help="Re-run even if no new enrichment data detected")
    parser.add_argument("--check", action="store_true",
                        help="Dry-run — print plan only, skip API calls")
    args = parser.parse_args()

    sites = [args.site] if args.site else list(SITES.keys())

    # ── Status report ─────────────────────────────────────────────────────
    print("\n  RenovationMap — enrichment detector")
    print("  " + "═" * 58)
    over_avail = _overture_installed()
    print(f"  overturemaps library : {'✓ installed' if over_avail else '✗ not installed  (pip install overturemaps)'}")
    print()

    to_run = []
    for sk in sites:
        info  = check_site(sk, args.force)
        ddata = info["data"]
        parts = []
        if ddata["n_ndvi"]:
            parts.append(f"NDVI trees: {ddata['n_ndvi']}")
        else:
            parts.append("no ndvi_trees.json")
        if ddata["n_ov"]:
            parts.append(f"Overture cached: {ddata['n_ov']}")
        elif over_avail:
            parts.append("Overture: not yet cached")

        stale_tag = "STALE — needs rerun" if info["needs_run"] else "up-to-date"
        print(f"  {SITES[sk]['name']}")
        print(f"    {stale_tag}")
        print(f"    {',  '.join(parts)}")
        if info["reasons"]:
            for r in info["reasons"]:
                print(f"    • {r}")
        print()
        if info["needs_run"]:
            to_run.append(sk)

    if not to_run:
        print("  Nothing to do — all sites are up-to-date.")
        print()
        print("  To trigger a re-run:")
        print("    1. Run GEE script (gee_ndvi_canopy.js) and download results")
        print("    2. python postprocess_ndvi.py --site <site> --geojson <file>.geojson")
        print("    3. python refine.py              ← detects new ndvi_trees.json")
        print()
        print("  Or force re-run: python refine.py --force")
        return

    if args.check:
        print(f"  Would re-run: {', '.join(to_run)}")
        for sk in to_run:
            run_pipeline(sk, dry_run=True)
        return

    # ── Run pipeline ──────────────────────────────────────────────────────
    ok_sites   = []
    fail_sites = []
    total_t0   = time.time()

    for sk in to_run:
        success = run_pipeline(sk, dry_run=False)
        (ok_sites if success else fail_sites).append(sk)

    elapsed = time.time() - total_t0
    print(f"\n{'═'*62}")
    print(f"  COMPLETE  ({elapsed/60:.1f} min)")
    if ok_sites:
        print(f"  Refined : {', '.join(ok_sites)}")
    if fail_sites:
        print(f"  Failed  : {', '.join(fail_sites)}")
    print(f"{'═'*62}")


if __name__ == "__main__":
    main()
