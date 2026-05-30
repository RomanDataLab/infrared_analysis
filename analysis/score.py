"""
RenovationMap -- Step 3: Priority score + grade card
=====================================================
Usage:
    python score.py --site almaty
    python score.py --site riyadh
    python score.py --site almaty --json
    python score.py --compare          # side-by-side both sites

Reads baseline_stats.json + scenarios_summary.json -> courtyard_score.json
"""

import argparse
import json
import sys
from pathlib import Path
from sites import SITES

GRADES = [
    (80, "F  Critical  — fix immediately"),
    (65, "E  Severe    — high renovation priority"),
    (50, "D  Poor      — include in next cycle"),
    (35, "C  Moderate  — improvements recommended"),
    (20, "B  Fair      — minor enhancements worthwhile"),
    ( 0, "A  Good      — no urgent intervention needed"),
]


def results_dir(site_key, size=500):
    d = Path(__file__).parent / "results" / site_key
    return d / "1km" if size == 1000 else d


def normalise(value, worst, best):
    if worst == best:
        return 0.0
    return max(0.0, min(1.0, (value - best) / (worst - best)))


def grade(score):
    for threshold, label in GRADES:
        if score >= threshold:
            return label
    return GRADES[-1][1]


def best_scenario(scenarios, climate):
    """Best = highest combined improvement (wind + utci), weighted by climate."""
    if not scenarios:
        return None, None
    w_weight = 0.3 if climate == "hot" else 0.5
    u_weight = 1 - w_weight
    def combined(s):
        return w_weight * s["wind_improvement"] + u_weight * s["utci_improvement"]
    return max(scenarios.items(), key=lambda kv: combined(kv[1]))


def score_site(site_key, size=500):
    site = SITES[site_key]
    out  = results_dir(site_key, size)
    sc   = site["score_config"]
    climate = site["climate"]

    with open(out / "baseline_stats.json") as f:
        bs = json.load(f)

    scenarios = {}
    sp = out / "scenarios_summary.json"
    if sp.exists():
        with open(sp) as f:
            scenarios = json.load(f)

    w_val  = bs["wind"][sc["wind_metric"]]
    s_val  = bs["sun"][sc["solar_metric"]]
    u_val  = bs["utci"]["frac_utci_bad"]

    wind_score  = normalise(w_val, sc["wind_worst"],  sc["wind_best"])
    solar_score = normalise(s_val, sc["solar_worst"], sc["solar_best"])
    utci_score  = normalise(u_val, sc["utci_worst"],  sc["utci_best"])

    composite = (
        sc["wind_weight"]  * wind_score  +
        sc["solar_weight"] * solar_score +
        sc["utci_weight"]  * utci_score
    ) * 100

    grade_label        = grade(composite)
    best_key, best_s   = best_scenario(scenarios, climate)

    result = {
        "site_key":        site_key,
        "site_name":       site["name"],
        "climate":         climate,
        "composite_score": round(composite, 1),
        "grade":           grade_label,
        "components": {
            sc["wind_label"]:  round(wind_score  * 100, 1),
            sc["solar_label"]: round(solar_score * 100, 1),
            sc["utci_label"]:  round(utci_score  * 100, 1),
        },
        "key_stats": {
            "wind_mean_ms":   bs["wind"]["mean_ms"],
            "sun_mean_h_day": bs["sun"]["mean_hrs_day"],
            "utci_mean_c":    bs["utci"]["mean_c"],
        },
        "best_intervention": {
            "key":            best_key,
            "label":          best_s["label"]          if best_s else None,
            "wind_improv_ms": best_s["wind_improvement"] if best_s else None,
            "utci_improv_c":  best_s["utci_improvement"] if best_s else None,
        } if best_key else None,
        "all_scenarios": {
            k: {
                "label":          v["label"],
                "wind_improv_ms": v["wind_improvement"],
                "utci_improv_c":  v["utci_improvement"],
                "frac_wind_pct":  round(v["frac_wind_improved"] * 100, 1),
                "frac_utci_pct":  round(v["frac_utci_improved"] * 100, 1),
            }
            for k, v in scenarios.items()
        },
    }

    with open(out / "courtyard_score.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def print_card(r):
    sc   = SITES[r["site_key"]]["score_config"]
    climate_tag = "WINTER COLD" if r["climate"] == "cold" else "SUMMER HEAT"
    sep = "-" * 62
    print(f"\n{'='*62}")
    print(f"  RENOVATION PRIORITY SCORE  [{climate_tag}]")
    print(f"  {r['site_name']}")
    print(f"{'='*62}")
    print(f"  COMPOSITE   {r['composite_score']:5.1f} / 100   {r['grade']}")
    print(sep)
    for label, val in r["components"].items():
        print(f"  {label:<22}  {val:5.1f} / 100")
    print(sep)
    ks = r["key_stats"]
    print(f"  Wind mean {ks['wind_mean_ms']} m/s  |  "
          f"Sun {ks['sun_mean_h_day']} h/day  |  "
          f"UTCI {ks['utci_mean_c']} degC")
    if r["all_scenarios"]:
        print(sep)
        print("  Interventions:")
        for k, s in r["all_scenarios"].items():
            print(f"    [{k}] {s['label']}")
            print(f"         wind {s['wind_improv_ms']:+.3f} m/s  "
                  f"utci {s['utci_improv_c']:+.3f} degC  "
                  f"({s['frac_utci_pct']:.0f}% cells better)")
        bi = r["best_intervention"]
        if bi:
            print(sep)
            print(f"  Best: [{bi['key']}] {bi['label']}")
            print(f"        wind {bi['wind_improv_ms']:+.3f} m/s  "
                  f"utci {bi['utci_improv_c']:+.3f} degC")
    print(f"{'='*62}")
    print(f"  -> results/{r['site_key']}/courtyard_score.json")


def print_compare(alm, riy):
    print(f"\n{'='*70}")
    print(f"  RENOVATIONMAP — DUAL-SITE COMPARISON")
    print(f"{'='*70}")
    header = f"  {'Metric':<30}  {'ALMATY (winter)':>15}  {'RIYADH (summer)':>15}"
    print(header)
    print("-" * 70)
    rows = [
        ("Composite score / 100",
         f"{alm['composite_score']:.1f}", f"{riy['composite_score']:.1f}"),
        ("Grade",
         alm['grade'].split()[0], riy['grade'].split()[0]),
        ("Wind mean (m/s)",
         str(alm['key_stats']['wind_mean_ms']),
         str(riy['key_stats']['wind_mean_ms'])),
        ("Sun exposure (h/day)",
         str(alm['key_stats']['sun_mean_h_day']),
         str(riy['key_stats']['sun_mean_h_day'])),
        ("UTCI mean (degC)",
         str(alm['key_stats']['utci_mean_c']),
         str(riy['key_stats']['utci_mean_c'])),
    ]
    if alm.get("best_intervention") and riy.get("best_intervention"):
        rows += [
            ("Best intervention",
             alm['best_intervention']['label'][:20],
             riy['best_intervention']['label'][:20]),
            ("  -> UTCI gain (degC)",
             f"{alm['best_intervention']['utci_improv_c']:+.3f}",
             f"{riy['best_intervention']['utci_improv_c']:+.3f}"),
        ]
    for label, a, b in rows:
        print(f"  {label:<30}  {a:>15}  {b:>15}")
    print(f"{'='*70}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", choices=list(SITES.keys()))
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--json",    action="store_true")
    parser.add_argument("--size", type=int, choices=[500, 1000], default=500)
    args = parser.parse_args()

    if args.compare:
        results = {sk: score_site(sk, size=args.size) for sk in SITES}
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results.values():
                print_card(r)
            if "almaty" in results and "riyadh" in results:
                print_compare(results["almaty"], results["riyadh"])
    elif args.site:
        r = score_site(args.site, size=args.size)
        if args.json:
            print(json.dumps(r, indent=2))
        else:
            print_card(r)
    else:
        parser.print_help()
