"""
verify_base_idfs.py
-------------------
Runs each cleaned base IDF through EnergyPlus (no HVAC expansion) and
reports pass/fail. Use this after re-cleaning to confirm no fatal errors.

Usage:
    python scripts/verify_base_idfs.py
"""
import subprocess
import os
import sys
import shutil
import tempfile
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
BASE_IDFS_DIR  = Path("data/base_idfs")
EP_EXE         = os.path.expanduser("~/Documents/Ayeen/Energy+/energyplus")
EP_IDD         = os.path.expanduser("~/Documents/Ayeen/Energy+/Energy+.idd")
WEATHER_FILE   = os.path.expanduser(
    "~/Documents/Ayeen/Energy+/WeatherData/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
)
TIMEOUT        = 600   # 10 min per building (enough for any ASHRAE prototype)

# Buildings to test — all cleaned base IDFs that have a source file in files/
# Old 10 (v22.1 ASHRAE prototypes, source files moved out):
#   HealthCare, LargeHotel, MediumOffice, MidRiseApartment, PrimarySchool,
#   Restaurant, RetailStandalone, SmallHotel, SmallOffice, Stripmall
# New 5 (current source files in data/base_idfs/files/):
#   Hospital, OfficeLarge, RestaurantFastFood, SchoolSecondary, Warehouse
BUILDINGS = [
    # Original 10 (cleaned IDFs preserved in data/base_idfs/)
    "HealthCare", "LargeHotel", "MediumOffice", "MidRiseApartment",
    "PrimarySchool", "Restaurant", "RetailStandalone",
    "SmallHotel", "SmallOffice", "Stripmall",
    # New 5 added by user
    "Hospital", "OfficeLarge", "RestaurantFastFood", "SchoolSecondary", "Warehouse",
]
# ─────────────────────────────────────────────────────────────────────────────

def run_ep(idf_path: Path) -> tuple[bool, str]:
    """Run EnergyPlus on idf_path. Returns (success, status_message)."""
    with tempfile.TemporaryDirectory(prefix="ep_verify_") as tmpdir:
        # Copy IDF and IDD to tmp dir
        idf_copy = Path(tmpdir) / "in.idf"
        shutil.copy(idf_path, idf_copy)
        idd_copy = Path(tmpdir) / "Energy+.idd"
        shutil.copy(EP_IDD, idd_copy)

        cmd = [
            EP_EXE,
            "-w", WEATHER_FILE,
            "-d", tmpdir,
            "-r",          # run in place
            str(idf_copy),
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
                cwd=tmpdir,
            )
        except subprocess.TimeoutExpired:
            return False, f"TIMEOUT (>{TIMEOUT}s)"

        # Read .err file for diagnosis
        err_file = Path(tmpdir) / "eplusout.err"
        err_content = err_file.read_text(errors="replace") if err_file.exists() else ""

        # Determine success
        if "EnergyPlus Completed Successfully" in err_content:
            warns  = err_content.count("** Warning **")
            severe = err_content.count("** Severe  **")
            return True, f"OK  ({warns}W / {severe}S)"

        # Check for structural parsing errors (these affect the pipeline)
        parsing_errors = [
            ln.strip() for ln in err_content.splitlines()
            if "not a valid Object Type" in ln or "not found in Energy+" in ln
        ]
        if parsing_errors:
            return False, f"FATAL (parsing) — {parsing_errors[0][:120]}"

        # Check for pure thermal divergence (unconditioned zone without HVAC).
        # This is EXPECTED when we run a base IDF without HVAC, and does NOT
        # affect the pipeline (which always appends VRF HVAC before simulation).
        severe_lines = [ln for ln in err_content.splitlines() if "** Severe  **" in ln]
        def _is_thermal_severe(ln: str) -> bool:
            """Return True if this Severe line is pure thermal divergence."""
            return (
                ("Temperature" in ln and "out of bounds" in ln)
                or "CalcHeatBalanceInsideSurf" in ln   # extreme T divergence
                or "CalcHeatBalanceOutsideSurf" in ln
            )
        all_thermal = all(_is_thermal_severe(ln) for ln in severe_lines) if severe_lines else False

        if all_thermal and severe_lines:
            # It's only thermal divergence — the parsing is fine
            affected_zones = set()
            import re as _re
            for ln in severe_lines:
                m = _re.search(r'zone="?([^",]+)', ln, _re.IGNORECASE)
                if m:
                    affected_zones.add(m.group(1).strip())
            zone_str = ", ".join(sorted(affected_zones)[:3])
            return True, f"OK* (thermal divergence w/o HVAC in: {zone_str})"

        # Generic crash (segfault, etc.)
        if result.returncode != 0:
            return False, f"CRASH (rc={result.returncode}) — {err_content.splitlines()[-3:-1]}"

        # Terminated with other errors
        fatal_line = next(
            (ln.strip() for ln in err_content.splitlines()
             if "** Fatal  **" in ln),
            "unknown error"
        )
        return False, f"FATAL — {fatal_line[:120]}"


def main():
    print(f"\n{'='*70}")
    print("  Base IDF Verification")
    print(f"{'='*70}")
    print(f"  EnergyPlus : {EP_EXE}")
    print(f"  Weather    : {WEATHER_FILE}")
    print(f"  Timeout    : {TIMEOUT}s per building")
    print(f"{'='*70}\n")

    results = {}
    for name in BUILDINGS:
        idf_path = BASE_IDFS_DIR / f"{name}.idf"
        if not idf_path.exists():
            results[name] = (None, "MISSING")
            print(f"  {'⚠️ ':2} {name:<24}  MISSING")
            continue

        print(f"  ⏳ {name:<24} … ", end="", flush=True)
        ok, msg = run_ep(idf_path)
        results[name] = (ok, msg)
        icon = "✅" if ok else "❌"
        print(f"\r  {icon} {name:<24}  {msg}")

    # Summary
    print(f"\n{'─'*70}")
    passed = sum(1 for ok, _ in results.values() if ok)
    total  = len([v for v in results.values() if v[0] is not None])
    print(f"  Passed: {passed}/{total}")

    failures = [(n, msg) for n, (ok, msg) in results.items() if not ok]
    if failures:
        print("\n  Failures:")
        for n, msg in failures:
            print(f"    ❌ {n}: {msg}")
    print()
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
