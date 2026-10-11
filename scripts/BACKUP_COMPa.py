#!/usr/bin/env python3
"""
Model Comparison Runner — DOE Building Prototypes × 3 Prompt Complexities
==========================================================================

Runs all four model variants (Base, Base+RAG, Fine-tuned, Fine-tuned+RAG) on
15 DOE/ASHRAE prototype buildings from data/base_idfs/FinaIDF/ using three
prompt complexity levels (Simple / Medium / Detailed).

Buildings:
  10 from docs/New Prompts.docx  (HealthCare, LargeHotel, MediumOffice,
    MidRiseApartment, PrimarySchool, Restaurant, RetailStandalone, SmallHotel,
    SmallOffice, Stripmall)
  5 additional ASHRAE prototypes  (Hospital, OfficeLarge, RestaurantFastFood,
    SchoolSecondary, Warehouse)

Test matrix:
  15 buildings  ×  3 complexities  =  45 test cases per model variant
  4 model variants  →  180 pipeline runs total (per --runs value)

Usage:
    python scripts/run_model_comparison.py                    # full run (all 30 cases)
    python scripts/run_model_comparison.py --complexity simple    # simple prompts only
    python scripts/run_model_comparison.py --complexity medium    # medium prompts only
    python scripts/run_model_comparison.py --complexity detailed  # detailed prompts only
    python scripts/run_model_comparison.py --quick                # 3 cases only (1 per level)
    python scripts/run_model_comparison.py --no-ref               # skip BLEU/ROUGE-L
    python scripts/run_model_comparison.py --runs 3               # repeat each case 3×
"""

import os
import sys
import json
import time
import csv
import argparse
from collections import defaultdict
from datetime import datetime
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import HVACLLMPipeline
from src.agents.llm_interface import UniversalLLM
from config import Config


# ---------------------------------------------------------------------------
# IDF directory (FinaIDF = cleaned ASHRAE prototype IDFs)
# ---------------------------------------------------------------------------

_BASE = "data/base_idfs/FinaIDF"

# ── Building registry ──────────────────────────────────────────────────────
# key → (idf_filename, num_zones, display_label)
# num_zones = zone count referenced in Medium/Detailed prompts (informational;
# the pipeline auto-detects all conditioned zones from the IDF at runtime).
_BUILDINGS = {
    # ── Original 10 (from docs/New Prompts.docx) ──────────────────────────
    "RetailStandalone":   ("RetailStandalone.idf",   2,  "Retail Standalone"),
    "Stripmall":          ("Stripmall.idf",           4,  "Strip Mall"),
    "SmallOffice":        ("SmallOffice.idf",          5,  "Small Office"),
    "MediumOffice":       ("MediumOffice.idf",         5,  "Medium Office"),
    "SmallHotel":         ("SmallHotel.idf",           6,  "Small Hotel"),
    "LargeHotel":         ("LargeHotel.idf",           6,  "Large Hotel"),
    "MidRiseApartment":   ("MidRiseApartment.idf",     5,  "Midrise Apt."),
    "PrimarySchool":      ("PrimarySchool.idf",        5,  "Primary School"),
    "HealthCare":         ("HealthCare.idf",           5,  "Healthcare"),
    "Restaurant":         ("Restaurant.idf",           3,  "Restaurant"),
    # ── Additional 5 ASHRAE prototypes ────────────────────────────────────
    "Hospital":           ("Hospital.idf",            10,  "Hospital"),
    "OfficeLarge":        ("OfficeLarge.idf",         20,  "Large Office"),
    "RestaurantFastFood": ("RestaurantFastFood.idf",   3,  "Fast-Food Restaurant"),
    "SchoolSecondary":    ("SchoolSecondary.idf",     10,  "Secondary School"),
    "Warehouse":          ("Warehouse.idf",            3,  "Warehouse"),
}


# ---------------------------------------------------------------------------
# Prompt library  (3 complexity levels × 15 buildings)
# Source: docs/New Prompts.docx — "New Prompts – Building DOE" (original 10)
#         + 5 additional ASHRAE prototypes following the same pattern
# ---------------------------------------------------------------------------

PROMPTS = {

    # ── Simple ─────────────────────────────────────────────────────────────
    "simple": {
        "RetailStandalone": (
            "Design an energy-efficient VRF HVAC system for a retail standalone "
            "building for effective heating and cooling."
        ),
        "Stripmall": (
            "Design an energy-efficient VRF HVAC system for a strip mall for "
            "effective heating and cooling."
        ),
        "SmallOffice": (
            "Design an energy-efficient VRF HVAC system for a small office for "
            "effective heating and cooling."
        ),
        "MediumOffice": (
            "Design an energy-efficient VRF HVAC system for a medium office for "
            "effective heating and cooling."
        ),
        "SmallHotel": (
            "Design an energy-efficient VRF HVAC system for a small hotel for "
            "effective heating and cooling."
        ),
        "LargeHotel": (
            "Design an energy-efficient VRF HVAC system for a large hotel for "
            "effective heating and cooling."
        ),
        "MidRiseApartment": (
            "Design an energy-efficient VRF HVAC system for a midrise apartment "
            "for effective heating and cooling."
        ),
        "PrimarySchool": (
            "Design an energy-efficient VRF HVAC system for a primary school for "
            "effective heating and cooling."
        ),
        "HealthCare": (
            "Design an energy-efficient VRF HVAC system for a healthcare facility "
            "for effective heating and cooling."
        ),
        "Restaurant": (
            "Design an energy-efficient VRF HVAC system for a restaurant for "
            "effective heating and cooling."
        ),
        # ── Additional 5 ASHRAE prototypes ────────────────────────────────
        "Hospital": (
            "Design an energy-efficient VRF HVAC system for a hospital for "
            "effective heating and cooling."
        ),
        "OfficeLarge": (
            "Design an energy-efficient VRF HVAC system for a large office "
            "building for effective heating and cooling."
        ),
        "RestaurantFastFood": (
            "Design an energy-efficient VRF HVAC system for a fast-food "
            "restaurant for effective heating and cooling."
        ),
        "SchoolSecondary": (
            "Design an energy-efficient VRF HVAC system for a secondary school "
            "for effective heating and cooling."
        ),
        "Warehouse": (
            "Design an energy-efficient VRF HVAC system for a warehouse "
            "facility for effective heating and cooling."
        ),
    },

    # ── Medium ─────────────────────────────────────────────────────────────
    "medium": {
        "RetailStandalone": (
            "Design a VRF HVAC system for a retail standalone building with "
            "5 thermal zones and energy recovery. Connect all components properly "
            "to their respective thermal zones."
        ),
        "Stripmall": (
            "Design a VRF HVAC system for a strip mall with 10 thermal zones and "
            "independent zone control. Connect all components properly to their "
            "respective thermal zones."
        ),
        "SmallOffice": (
            "Design an energy-efficient VRF HVAC system for a small office "
            "building with 6 thermal zones and individual setpoint control. "
            "Connect all components properly to their respective thermal zones."
        ),
        "MediumOffice": (
            "Design a VRF HVAC system for a medium office building with 18 thermal "
            "zones with simultaneous heating and cooling capability. Connect all "
            "components properly to their respective thermal zones."
        ),
        "SmallHotel": (
            "Design a VRF HVAC system for a small hotel with 6 thermal zones and "
            "room-level heat recovery. Connect all components properly to their "
            "respective thermal zones."
        ),
        "LargeHotel": (
            "Design a VRF HVAC system for a large hotel with 22 thermal zones and "
            "independent zone-level thermal control. Connect all components "
            "properly to their respective thermal zones."
        ),
        "MidRiseApartment": (
            "Design a VRF HVAC system for a midrise apartment with 27 thermal "
            "zones and independent climate control per zone. Connect all components "
            "properly to their respective thermal zones."
        ),
        "PrimarySchool": (
            "Design a VRF HVAC system for a primary school with 25 thermal zones "
            "and individual zone setpoint control. Connect all components properly "
            "to their respective thermal zones."
        ),
        "HealthCare": (
            "Design a VRF HVAC system for a healthcare facility with 112 thermal "
            "zones and precise zone-level temperature control. Connect all "
            "components properly to their respective thermal zones."
        ),
        "Restaurant": (
            "Design a VRF HVAC system for a restaurant with 3 thermal zones and "
            "independent zone control. Connect all components properly to their "
            "respective thermal zones."
        ),
        # ── Additional 5 ASHRAE prototypes ────────────────────────────────
        "Hospital": (
            "Design a VRF HVAC system for a hospital with 55 clinical zones and "
            "precise zone-level temperature control. Connect all components "
            "properly to their respective thermal zones."
        ),
        "OfficeLarge": (
            "Design a VRF HVAC system for a large office building with 23 thermal "
            "zones and heat recovery between perimeter and core zones. Connect all "
            "components properly to their respective thermal zones."
        ),
        "RestaurantFastFood": (
            "Design a VRF HVAC system for a fast-food restaurant with 3 thermal "
            "zones and independent zone control. Connect all components properly "
            "to their respective thermal zones."
        ),
        "SchoolSecondary": (
            "Design a VRF HVAC system for a secondary school with 10 thermal "
            "zones and individual zone setpoint control. Connect all components "
            "properly to their respective thermal zones."
        ),
        "Warehouse": (
            "Design a VRF HVAC system for a warehouse facility with 46 thermal "
            "zones and appropriate zone-level temperature control. Connect all "
            "components properly to their respective thermal zones."
        ),
    },

    # ── Detailed ───────────────────────────────────────────────────────────
    "detailed": {
        "RetailStandalone": (
            "Design a VRF HVAC system for a retail standalone building with "
            "5 thermal zones. Include one indoor terminal unit per zone, a shared "
            "outdoor condensing unit, supply and return fans, heating and cooling "
            "coils, zone-level thermostats, and operating schedules. Include a zone "
            "terminal unit list connecting all indoor units to the outdoor condensing "
            "unit, zone HVAC equipment lists, zone HVAC equipment connections "
            "defining inlet and outlet air nodes, and performance curves for outdoor "
            "unit capacity and COP. Use automatic sizing for all airflow and capacity "
            "parameters. Set cooling setpoints to 24 °C and heating setpoints to "
            "21 °C. Connect all components properly to their respective thermal zones."
        ),
        "Stripmall": (
            "Design a VRF HVAC system for a strip mall with 10 thermal zones. "
            "Include one indoor terminal unit per zone, a shared outdoor condensing "
            "unit, supply and return fans, heating and cooling coils, zone-level "
            "thermostats, and operating schedules. Include a zone terminal unit list "
            "connecting all indoor units to the outdoor condensing unit, zone HVAC "
            "equipment lists, zone HVAC equipment connections defining inlet and "
            "outlet air nodes, and performance curves for outdoor unit capacity and "
            "COP. Use automatic sizing for all airflow and capacity parameters. Set "
            "cooling setpoints to 24 °C and heating setpoints to 21 °C. Connect all "
            "components properly to their respective thermal zones."
        ),
        "SmallOffice": (
            "Design a VRF HVAC system for a small office with 6 thermal zones. "
            "Include one indoor terminal unit per zone, a shared outdoor condensing "
            "unit, supply and return fans, heating and cooling coils, zone-level "
            "thermostats, and operating schedules. Include a zone terminal unit list "
            "connecting all indoor units to the outdoor condensing unit, zone HVAC "
            "equipment lists, zone HVAC equipment connections defining inlet and "
            "outlet air nodes, and performance curves for outdoor unit capacity and "
            "COP. Use automatic sizing for all airflow and capacity parameters. Set "
            "cooling setpoints to 24 °C and heating setpoints to 21 °C. Connect all "
            "components properly to their respective thermal zones."
        ),
        "MediumOffice": (
            "Design a VRF HVAC system for a medium office with 18 thermal zones. "
            "Include one indoor terminal unit per zone, a shared outdoor condensing "
            "unit, supply and return fans, heating and cooling coils, zone-level "
            "thermostats, and operating schedules. Include a zone terminal unit list "
            "connecting all indoor units to the outdoor condensing unit, zone HVAC "
            "equipment lists, zone HVAC equipment connections defining inlet and "
            "outlet air nodes, and performance curves for outdoor unit capacity and "
            "COP. Use automatic sizing for all airflow and capacity parameters. Set "
            "cooling setpoints to 24 °C and heating setpoints to 21 °C. Connect all "
            "components properly to their respective thermal zones."
        ),
        "SmallHotel": (
            "Design a VRF HVAC system for a small hotel with 6 thermal zones. "
            "Include one indoor terminal unit per zone, a shared outdoor condensing "
            "unit, supply and return fans, heating and cooling coils, zone-level "
            "thermostats, and operating schedules. Include a zone terminal unit list "
            "connecting all indoor units to the outdoor condensing unit, zone HVAC "
            "equipment lists, zone HVAC equipment connections defining inlet and "
            "outlet air nodes, and performance curves for outdoor unit capacity and "
            "COP. Use automatic sizing for all airflow and capacity parameters. Set "
            "cooling setpoints to 24 °C and heating setpoints to 21 °C. Connect all "
            "components properly to their respective thermal zones."
        ),
        "LargeHotel": (
            "Design a VRF HVAC system for a large hotel with 22 thermal zones. "
            "Include one indoor terminal unit per zone, a shared outdoor condensing "
            "unit, supply and return fans, heating and cooling coils, zone-level "
            "thermostats, and operating schedules. Include a zone terminal unit list "
            "connecting all indoor units to the outdoor condensing unit, zone HVAC "
            "equipment lists, zone HVAC equipment connections defining inlet and "
            "outlet air nodes, and performance curves for outdoor unit capacity and "
            "COP. Use automatic sizing for all airflow and capacity parameters. Set "
            "cooling setpoints to 24 °C and heating setpoints to 21 °C. Connect all "
            "components properly to their respective thermal zones."
        ),
        "MidRiseApartment": (
            "Design a VRF HVAC system for a midrise apartment with 27 thermal "
            "zones. Include one indoor terminal unit per zone, a shared outdoor "
            "condensing unit, supply and return fans, heating and cooling coils, "
            "zone-level thermostats, and operating schedules. Include a zone "
            "terminal unit list connecting all indoor units to the outdoor "
            "condensing unit, zone HVAC equipment lists, zone HVAC equipment "
            "connections defining inlet and outlet air nodes, and performance curves "
            "for outdoor unit capacity and COP. Use automatic sizing for all "
            "airflow and capacity parameters. Set cooling setpoints to 24 °C and "
            "heating setpoints to 21 °C. Connect all components properly to their "
            "respective thermal zones."
        ),
        "PrimarySchool": (
            "Design a VRF HVAC system for a primary school with 25 thermal zones. "
            "Include one indoor terminal unit per zone, a shared outdoor condensing "
            "unit, supply and return fans, heating and cooling coils, zone-level "
            "thermostats, and operating schedules. Include a zone terminal unit list "
            "connecting all indoor units to the outdoor condensing unit, zone HVAC "
            "equipment lists, zone HVAC equipment connections defining inlet and "
            "outlet air nodes, and performance curves for outdoor unit capacity and "
            "COP. Use automatic sizing for all airflow and capacity parameters. Set "
            "cooling setpoints to 24 °C and heating setpoints to 21 °C. Connect all "
            "components properly to their respective thermal zones."
        ),
        "HealthCare": (
            "Design a VRF HVAC system for a healthcare facility with 112 thermal "
            "zones. Include one indoor terminal unit per zone, a shared outdoor "
            "condensing unit, supply and return fans, heating and cooling coils, "
            "zone-level thermostats, and operating schedules. Include a zone "
            "terminal unit list connecting all indoor units to the outdoor "
            "condensing unit, zone HVAC equipment lists, zone HVAC equipment "
            "connections defining inlet and outlet air nodes, and performance curves "
            "for outdoor unit capacity and COP. Use automatic sizing for all "
            "airflow and capacity parameters. Set cooling setpoints to 24 °C and "
            "heating setpoints to 21 °C. Connect all components properly to their "
            "respective thermal zones."
        ),
        "Restaurant": (
            "Design a VRF HVAC system for a restaurant with 3 thermal zones. "
            "Include one indoor terminal unit per zone, a shared outdoor condensing "
            "unit, supply and return fans, heating and cooling coils, zone-level "
            "thermostats, and operating schedules. Include a zone terminal unit list "
            "connecting all indoor units to the outdoor condensing unit, zone HVAC "
            "equipment lists, zone HVAC equipment connections defining inlet and "
            "outlet air nodes, and performance curves for outdoor unit capacity and "
            "COP. Use automatic sizing for all airflow and capacity parameters. Set "
            "cooling setpoints to 24 °C and heating setpoints to 21 °C. Connect all "
            "components properly to their respective thermal zones."
        ),
        # ── Additional 5 ASHRAE prototypes ────────────────────────────────
        "Hospital": (
            "Design a VRF HVAC system for a hospital with 55 clinical zones. "
            "Include one indoor terminal unit per zone, a shared outdoor condensing "
            "unit, supply and return fans, heating and cooling coils, zone-level "
            "thermostats, and operating schedules. Include a zone terminal unit list "
            "connecting all indoor units to the outdoor condensing unit, zone HVAC "
            "equipment lists, zone HVAC equipment connections defining inlet and "
            "outlet air nodes, and performance curves for outdoor unit capacity and "
            "COP. Use automatic sizing for all airflow and capacity parameters. Set "
            "cooling setpoints to 24 °C and heating setpoints to 21 °C. Connect all "
            "components properly to their respective thermal zones."
        ),
        "OfficeLarge": (
            "Design a VRF HVAC system for a large office building with 23 thermal "
            "zones. Include one indoor terminal unit per zone, a shared outdoor "
            "condensing unit, supply and return fans, heating and cooling coils, "
            "zone-level thermostats, and operating schedules. Include a zone "
            "terminal unit list connecting all indoor units to the outdoor condensing "
            "unit, zone HVAC equipment lists, zone HVAC equipment connections "
            "defining inlet and outlet air nodes, and performance curves for outdoor "
            "unit capacity and COP. Use automatic sizing for all airflow and capacity "
            "parameters. Set cooling setpoints to 24 °C and heating setpoints to "
            "21 °C. Connect all components properly to their respective thermal zones."
        ),
        "RestaurantFastFood": (
            "Design a VRF HVAC system for a fast-food restaurant with 3 thermal "
            "zones. Include one indoor terminal unit per zone, a shared outdoor "
            "condensing unit, supply and return fans, heating and cooling coils, "
            "zone-level thermostats, and operating schedules. Include a zone "
            "terminal unit list connecting all indoor units to the outdoor condensing "
            "unit, zone HVAC equipment lists, zone HVAC equipment connections "
            "defining inlet and outlet air nodes, and performance curves for outdoor "
            "unit capacity and COP. Use automatic sizing for all airflow and capacity "
            "parameters. Set cooling setpoints to 24 °C and heating setpoints to "
            "21 °C. Connect all components properly to their respective thermal zones."
        ),
        "SchoolSecondary": (
            "Design a VRF HVAC system for a secondary school with 25 thermal "
            "zones. Include one indoor terminal unit per zone, a shared outdoor "
            "condensing unit, supply and return fans, heating and cooling coils, "
            "zone-level thermostats, and operating schedules. Include a zone "
            "terminal unit list connecting all indoor units to the outdoor condensing "
            "unit, zone HVAC equipment lists, zone HVAC equipment connections "
            "defining inlet and outlet air nodes, and performance curves for outdoor "
            "unit capacity and COP. Use automatic sizing for all airflow and capacity "
            "parameters. Set cooling setpoints to 24 °C and heating setpoints to "
            "21 °C. Connect all components properly to their respective thermal zones."
        ),
        "Warehouse": (
            "Design a VRF HVAC system for a warehouse facility with 46 thermal "
            "zones. Include one indoor terminal unit per zone, a shared outdoor "
            "condensing unit, supply and return fans, heating and cooling coils, "
            "zone-level thermostats, and operating schedules. Include a zone "
            "terminal unit list connecting all indoor units to the outdoor condensing "
            "unit, zone HVAC equipment lists, zone HVAC equipment connections "
            "defining inlet and outlet air nodes, and performance curves for outdoor "
            "unit capacity and COP. Use automatic sizing for all airflow and capacity "
            "parameters. Set cooling setpoints to 24 °C and heating setpoints to "
            "21 °C. Connect all components properly to their respective thermal zones."
        ),
    },
}

COMPLEXITY_LEVELS = ["simple", "medium", "detailed"]


# ---------------------------------------------------------------------------
# Build test-case list
# ---------------------------------------------------------------------------

def _build_test_cases(complexities: list[str]) -> list[dict]:
    """Return list of test-case dicts for the requested complexity levels."""
    cases = []
    for complexity in complexities:
        for bkey, (fname, n_zones, label) in _BUILDINGS.items():
            cases.append({
                "name":             f"{bkey.lower()}_{complexity}",
                "building_key":     bkey,
                "building_type":    label,
                "prompt_complexity": complexity,
                "prompt":           PROMPTS[complexity][bkey],
                "base_idf":         f"{_BASE}/{fname}",
                "reference_idf":    None,          # no reference VRF IDFs in FinaIDF
                "zones":            None,           # let pipeline detect zones from IDF
                "num_zones":        n_zones,
            })
    return cases


# Full 45-case suite (15 buildings × 3 complexity levels)
TEST_CASES = _build_test_cases(COMPLEXITY_LEVELS)

# Quick subset: 1 building per complexity level (3 cases total)
QUICK_TEST_CASES = [
    next(c for c in TEST_CASES if c["building_key"] == "SmallOffice"
         and c["prompt_complexity"] == lvl)
    for lvl in COMPLEXITY_LEVELS
]


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    model:               str          # "base" | "base_rag" | "finetuned" | "finetuned_rag"
    model_label:         str          # display name
    test_case:           str
    building_type:       str
    prompt_complexity:   str          # "simple" | "medium" | "detailed"
    num_zones:           int
    prompt:              str

    # Success flags
    simulation_success:  bool
    first_try_success:   bool

    # Performance
    total_time_seconds:  float
    correction_iterations: int
    hvac_objects_generated: int

    # Text quality
    bleu:                Optional[float] = None
    rouge_l:             Optional[float] = None
    hvac_tokens_generated: Optional[int] = None
    hvac_tokens_reference: Optional[int] = None

    # Structural quality
    syntax_score:        Optional[float] = None
    parameter_score:     Optional[float] = None

    # Misc
    error_message:       Optional[str] = None
    output_idf_path:     Optional[str] = None
    timestamp:           str = field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class ModelComparisonRunner:

    MODEL_CONFIGS = {
        "base":          {"label": "Base",             "provider": "mistral-api", "use_rag": False},
        "base_rag":      {"label": "Base + RAG",       "provider": "mistral-api", "use_rag": True},
        "finetuned":     {"label": "Fine-tuned",       "provider": "mistral",     "use_rag": False},
        "finetuned_rag": {"label": "Fine-tuned + RAG", "provider": "mistral",     "use_rag": True},
    }

    def __init__(self, output_dir: str = "outputs/model_comparison",
                 use_reference: bool = False):
        self.output_dir    = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_reference = use_reference

    # ------------------------------------------------------------------
    # Single-case runner
    # ------------------------------------------------------------------

    def _run_case(self, pipeline, model_key: str, label: str,
                  tc: dict, run_idx: int, n: int, total: int) -> RunResult:
        """Run one test case on an already-initialised pipeline."""
        print(f"\n{'='*70}")
        print(f"  [{n}/{total}]  {label}  |  "
              f"{tc['building_type']}  [{tc['prompt_complexity'].upper()}]")
        print(f"{'='*70}")

        start = time.time()
        try:
            output_name = (
                f"{model_key}_{tc['building_key'].lower()}_"
                f"{tc['prompt_complexity']}_r{run_idx}"
            )
            ref = tc.get("reference_idf") if self.use_reference else None

            result = pipeline.run(
                base_idf=tc["base_idf"],
                zones=tc["zones"],
                user_request=tc["prompt"],
                output_name=output_name,
                reference_idf=ref,
                enable_quick_validation=False,
            )

            elapsed  = round(time.time() - start, 1)
            success  = result.get("final_status") == "SUCCESS"
            iters    = result.get("total_iterations", 0)
            ev       = result.get("evaluation") or {}
            bleu     = ev.get("bleu")

            hvac_count = 0
            for step in result.get("steps", []):
                if step.get("step") == 1 and "objects_added" in step:
                    hvac_count = step["objects_added"]
                    break

            icon = "✓" if success else "✗"
            print(f"  {icon} success={success}  iters={iters}  time={elapsed}s"
                  + (f"  bleu={bleu:.3f}" if bleu is not None else ""))

            return RunResult(
                model=model_key,         model_label=label,
                test_case=tc["name"],    building_type=tc["building_type"],
                prompt_complexity=tc["prompt_complexity"],
                num_zones=tc["num_zones"], prompt=tc["prompt"],
                simulation_success=success,
                first_try_success=(success and iters == 0),
                total_time_seconds=elapsed, correction_iterations=iters,
                hvac_objects_generated=hvac_count,
                bleu=bleu,           rouge_l=ev.get("rouge_l"),
                hvac_tokens_generated=ev.get("hvac_tokens_generated"),
                hvac_tokens_reference=ev.get("hvac_tokens_reference"),
                syntax_score=ev.get("syntax_score"),
                parameter_score=ev.get("parameter_score"),
                output_idf_path=result.get("final_idf"),
            )

        except Exception as exc:
            elapsed = round(time.time() - start, 1)
            print(f"  ✗ EXCEPTION: {exc}")
            return RunResult(
                model=model_key,         model_label=label,
                test_case=tc["name"],    building_type=tc["building_type"],
                prompt_complexity=tc["prompt_complexity"],
                num_zones=tc["num_zones"], prompt=tc["prompt"],
                simulation_success=False, first_try_success=False,
                total_time_seconds=elapsed, correction_iterations=0,
                hvac_objects_generated=0,  error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self, test_cases: list, num_runs: int = 1) -> list[RunResult]:
        """
        Iterates MODEL-FIRST to load the fine-tuned model only once per group.
        Saves partial results after every model group for fault tolerance.
        """
        all_results: list[RunResult] = []
        total = len(self.MODEL_CONFIGS) * num_runs * len(test_cases)
        done  = 0

        # Cap iterations for faster comparison runs
        Config.MAX_ERROR_CORRECTION_ITERATIONS = 2

        for model_key, cfg in self.MODEL_CONFIGS.items():
            print(f"\n{'#'*70}")
            print(f"  MODEL : {cfg['label']}")
            print(f"  {len(test_cases)} case(s) × {num_runs} run(s)")
            print(f"{'#'*70}")

            UniversalLLM.reset()
            try:
                pipeline = HVACLLMPipeline(
                    use_rag=cfg["use_rag"],
                    llm_provider=cfg["provider"],
                )
            except Exception as init_exc:
                print(f"\n  ❌ Failed to initialise model '{cfg['label']}': {init_exc}")
                print(f"     Skipping all {len(test_cases) * num_runs} runs for this group.")
                for run_idx in range(1, num_runs + 1):
                    for tc in test_cases:
                        done += 1
                        all_results.append(RunResult(
                            model=model_key,
                            model_label=cfg["label"],
                            test_case=tc["name"],
                            building_type=tc["building_type"],
                            prompt_complexity=tc["prompt_complexity"],
                            num_zones=tc["num_zones"],
                            prompt=tc["prompt"],
                            simulation_success=False,
                            first_try_success=False,
                            total_time_seconds=0.0,
                            correction_iterations=0,
                            hvac_objects_generated=0,
                            error_message=f"Model init failed: {init_exc}",
                        ))
                print(f"\n  Saving partial results ({done}/{total} done)…")
                self._save(all_results)
                continue

            for run_idx in range(1, num_runs + 1):
                for tc in test_cases:
                    done += 1
                    r = self._run_case(pipeline, model_key, cfg["label"],
                                       tc, run_idx, done, total)
                    all_results.append(r)

            print(f"\n  Saving partial results ({done}/{total} done)…")
            self._save(all_results)

        self._print_summary(all_results)
        return all_results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self, results: list[RunResult]):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ── JSON ──────────────────────────────────────────────────────────
        payload = {
            "timestamp":  ts,
            "models":     list(self.MODEL_CONFIGS.keys()),
            "results":    [asdict(r) for r in results],
            "summary":              self._aggregate_by_model(results),
            "by_complexity":        self._aggregate_by_complexity(results),
            "by_building":          self._aggregate_by_building(results),
            "complexity_heatmap":   self._complexity_heatmap(results),
        }

        json_path = self.output_dir / f"model_comparison_{ts}.json"
        with open(json_path, "w") as f:
            json.dump(payload, f, indent=2)

        # ── CSV ───────────────────────────────────────────────────────────
        csv_path = self.output_dir / f"model_comparison_{ts}.csv"
        if results:
            fieldnames = list(asdict(results[0]).keys())
            with open(csv_path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(asdict(r) for r in results)

        # ── Stable "latest" copy ──────────────────────────────────────────
        latest_json = self.output_dir / "latest_comparison.json"
        with open(latest_json, "w") as f:
            json.dump(payload, f, indent=2)

        print(f"\n✓ Results → {json_path}")
        print(f"✓ CSV      → {csv_path}")
        print(f"✓ Latest   → {latest_json}")

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _metrics(subset: list[RunResult]) -> dict:
        """Compute metric dict for a subset of results."""
        if not subset:
            return {}
        n = len(subset)
        ok   = sum(r.simulation_success  for r in subset)
        fts  = sum(r.first_try_success   for r in subset)
        bleu_v   = [r.bleu          for r in subset if r.bleu          is not None]
        rouge_v  = [r.rouge_l       for r in subset if r.rouge_l       is not None]
        syn_v    = [r.syntax_score  for r in subset if r.syntax_score  is not None]
        par_v    = [r.parameter_score for r in subset if r.parameter_score is not None]
        return {
            "total_runs":             n,
            "success_rate":           round(ok  / n, 4),
            "first_try_success_rate": round(fts / n, 4),
            "avg_iterations":  round(sum(r.correction_iterations for r in subset) / n, 2),
            "avg_time_seconds":round(sum(r.total_time_seconds     for r in subset) / n, 1),
            "avg_bleu":         round(sum(bleu_v)  / len(bleu_v),  4) if bleu_v  else None,
            "avg_rouge_l":      round(sum(rouge_v) / len(rouge_v), 4) if rouge_v else None,
            "avg_syntax_score": round(sum(syn_v)   / len(syn_v),   4) if syn_v   else None,
            "avg_parameter_score": round(sum(par_v)/ len(par_v),   4) if par_v   else None,
        }

    def _aggregate_by_model(self, results: list[RunResult]) -> dict:
        """Overall metrics per model variant."""
        out = {}
        for key, cfg in self.MODEL_CONFIGS.items():
            subset = [r for r in results if r.model == key]
            out[key] = {"label": cfg["label"], **self._metrics(subset)}
        return out

    def _aggregate_by_complexity(self, results: list[RunResult]) -> dict:
        """Per complexity level × per model variant."""
        out = {}
        for level in COMPLEXITY_LEVELS:
            out[level] = {}
            for key, cfg in self.MODEL_CONFIGS.items():
                subset = [r for r in results
                          if r.model == key and r.prompt_complexity == level]
                out[level][key] = {"label": cfg["label"], **self._metrics(subset)}
        return out

    def _aggregate_by_building(self, results: list[RunResult]) -> dict:
        """Per building type × per model variant (all complexities combined)."""
        out = {}
        for bkey, (_, _, label) in _BUILDINGS.items():
            out[label] = {}
            for key, cfg in self.MODEL_CONFIGS.items():
                subset = [r for r in results
                          if r.model == key and r.building_type == label]
                out[label][key] = {"label": cfg["label"], **self._metrics(subset)}
        return out

    def _complexity_heatmap(self, results: list[RunResult]) -> list[dict]:
        """
        One row per (model, complexity, building_type) — useful for
        building a heatmap of success rates in the notebook.
        """
        rows = []
        for key, cfg in self.MODEL_CONFIGS.items():
            for level in COMPLEXITY_LEVELS:
                for bkey, (_, _, label) in _BUILDINGS.items():
                    subset = [r for r in results
                              if r.model == key
                              and r.prompt_complexity == level
                              and r.building_type == label]
                    if not subset:
                        continue
                    sr = round(sum(r.simulation_success for r in subset) / len(subset), 4)
                    rows.append({
                        "model":       key,
                        "model_label": cfg["label"],
                        "complexity":  level,
                        "building":    label,
                        "success_rate": sr,
                        "n_runs":      len(subset),
                    })
        return rows

    # ------------------------------------------------------------------
    # Console summary
    # ------------------------------------------------------------------

    def _print_summary(self, results: list[RunResult]):
        agg = self._aggregate_by_model(results)

        # ── Overall table ──────────────────────────────────────────────────
        W = 20
        print("\n" + "="*70)
        print("  OVERALL SUMMARY")
        print("="*70)
        header = f"{'Metric':<28}" + "".join(f"{v['label']:>{W}}" for v in agg.values())
        print(header)
        print("-"*70)
        _METRICS = [
            ("Success Rate",           "success_rate",           "{:.1%}"),
            ("First-Try Success",      "first_try_success_rate", "{:.1%}"),
            ("Avg Correction Iters",   "avg_iterations",         "{:.2f}"),
            ("Avg Time (s)",           "avg_time_seconds",       "{:.1f}"),
            ("Avg BLEU",               "avg_bleu",               "{:.4f}"),
            ("Avg ROUGE-L",            "avg_rouge_l",            "{:.4f}"),
            ("Avg Syntax Score",       "avg_syntax_score",       "{:.4f}"),
            ("Avg Parameter Score",    "avg_parameter_score",    "{:.4f}"),
        ]
        for lbl, key, fmt in _METRICS:
            row = f"{lbl:<28}"
            for v in agg.values():
                val = v.get(key)
                row += f"{(fmt.format(val) if val is not None else 'N/A'):>{W}}"
            print(row)

        # ── Per-complexity breakdown ───────────────────────────────────────
        by_cx = self._aggregate_by_complexity(results)
        print("\n" + "="*70)
        print("  SUCCESS RATE BY PROMPT COMPLEXITY")
        print("="*70)
        header = f"{'Complexity':<14}" + "".join(
            f"{cfg['label']:>{W}}" for cfg in self.MODEL_CONFIGS.values())
        print(header)
        print("-"*70)
        for level in COMPLEXITY_LEVELS:
            row = f"{level.capitalize():<14}"
            for key in self.MODEL_CONFIGS:
                val = by_cx[level].get(key, {}).get("success_rate")
                row += f"{('{:.1%}'.format(val) if val is not None else 'N/A'):>{W}}"
            print(row)

        # ── Per-building breakdown (finetuned_rag only for readability) ───
        by_bt = self._aggregate_by_building(results)
        print("\n" + "="*70)
        print("  SUCCESS RATE BY BUILDING TYPE  (Fine-tuned + RAG)")
        print("="*70)
        for bt, model_agg in by_bt.items():
            val = model_agg.get("finetuned_rag", {}).get("success_rate")
            bar = "█" * int((val or 0) * 20)
            print(f"  {bt:<22} {('{:.0%}'.format(val) if val is not None else 'N/A'):>5}  {bar}")

        print("="*70)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="DOE building prototype model comparison — 3 prompt complexities"
    )
    parser.add_argument(
        "--complexity",
        choices=COMPLEXITY_LEVELS + ["all"],
        default="all",
        help="Prompt complexity level to run (default: all)",
    )
    parser.add_argument(
        "--runs",   type=int, default=1,
        help="Number of repeat runs per test case (default: 1)",
    )
    parser.add_argument(
        "--quick",  action="store_true",
        help="Run only 3 test cases (SmallOffice at each complexity level)",
    )
    parser.add_argument(
        "--no-ref", action="store_true",
        help="Skip BLEU / ROUGE-L scoring (no reference IDFs)",
    )
    parser.add_argument(
        "--output", default="outputs/model_comparison",
        help="Output directory (default: outputs/model_comparison)",
    )
    args = parser.parse_args()

    if args.quick:
        cases = QUICK_TEST_CASES
    elif args.complexity == "all":
        cases = TEST_CASES
    else:
        cases = _build_test_cases([args.complexity])

    print(f"\nTest matrix:")
    print(f"  Complexities : {args.complexity}")
    print(f"  Buildings    : {len(_BUILDINGS)}")
    print(f"  Test cases   : {len(cases)}")
    print(f"  Model variants: {len(ModelComparisonRunner.MODEL_CONFIGS)}")
    print(f"  Runs/case    : {args.runs}")
    print(f"  Total runs   : {len(cases) * len(ModelComparisonRunner.MODEL_CONFIGS) * args.runs}")
    print(f"  Output dir   : {args.output}")

    runner = ModelComparisonRunner(
        output_dir=args.output,
        use_reference=not args.no_ref,
    )
    runner.run(cases, num_runs=args.runs)


if __name__ == "__main__":
    main()
