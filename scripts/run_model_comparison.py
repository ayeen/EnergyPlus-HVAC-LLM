#!/usr/bin/env python3
"""
Model Comparison Runner — DOE Building Prototypes × 3 Prompt Complexities
==========================================================================

Runs all four model variants (Base, Base+RAG, Fine-tuned, Fine-tuned+RAG) on
16 DOE/ASHRAE prototype buildings from data/base_idfs/FinaIDF/ using three
prompt complexity levels (Simple / Medium / Detailed).

Buildings:
  10 from docs/Prompts_DOE.docx  (HealthCare, LargeHotel, MediumOffice,
    MidRiseApartment, PrimarySchool, Restaurant, RetailStandalone, SmallHotel,
    SmallOffice, Stripmall)
  5 additional ASHRAE prototypes  (Hospital, OfficeLarge, RestaurantFastFood,
    SchoolSecondary, Warehouse)
  1 new building  (ApartmentHighRise)

Test matrix:
  16 buildings  ×  3 complexities  =  48 test cases per model variant
  4 model variants  →  192 pipeline runs total (per --runs value)

Usage:
    python scripts/run_model_comparison.py                    # full run (all 48 cases)
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

# ── Project root & paths (absolute, so the script works from any cwd) ─────────
_SCRIPT_DIR   = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Stdout/stderr tee — writes to both a log file AND the real terminal.
# Silently swallows BrokenPipeError so a piped terminal can't kill a run.
# ---------------------------------------------------------------------------
class _Tee:
    """Write to a log file and the original stream; ignore broken pipes."""
    def __init__(self, stream, log_file):
        self._stream   = stream
        self._log_file = log_file

    def write(self, data):
        # Always write to the log file (never broken)
        try:
            self._log_file.write(data)
            self._log_file.flush()
        except Exception:
            pass
        # Try terminal — silently skip on BrokenPipeError
        try:
            self._stream.write(data)
            self._stream.flush()
        except (BrokenPipeError, OSError):
            pass

    def flush(self):
        try: self._log_file.flush()
        except Exception: pass
        try: self._stream.flush()
        except (BrokenPipeError, OSError): pass

    def fileno(self):
        return self._stream.fileno()

    def __getattr__(self, attr):
        return getattr(self._stream, attr)

from src.pipeline import HVACLLMPipeline
from src.agents.llm_interface import UniversalLLM
from config import Config


# ---------------------------------------------------------------------------
# IDF directory (FinaIDF = cleaned ASHRAE prototype IDFs)
# Absolute path so the script works regardless of the current working directory.
# ---------------------------------------------------------------------------

_BASE = str(_PROJECT_ROOT / "data" / "base_idfs" / "FinaIDF")

# ── Building registry ──────────────────────────────────────────────────────
# key → (idf_filename, num_zones, display_label)
# num_zones = actual auto-detected zone count from the IDF (informational;
# the pipeline re-detects zones at runtime, so this is only for the CSV).
_BUILDINGS = {
    # ── key → (idf_filename, num_zones, display_label) ────────────────────
    # num_zones = conditioned zone count after IDFHandler._NON_HVAC_ZONE_KEYWORDS
    # filtering (excludes plenums, attics, stairwells, mechanical rooms,
    # elevator cores/pump rooms, retail back-spaces, and undeveloped shells).
    # Medium/detailed prompts embed this count via {n} → all three CSV columns
    # (num_zones, prompt zone count, detected_zones) are always consistent.
    #
    # Excluded zone counts per building (audit: 2026-06):
    #   RetailStandalone : -1  Back_Space
    #   SmallOffice      : -1  Attic
    #   SmallHotel       : -13 Stairs(8) + MechanicalRoom(1) + ElevatorCore(4)
    #   LargeHotel       : -1  Mech_Flr_1
    #   PrimarySchool    : -1  Mech_ZN_1_FLR_1
    #   HealthCare       : -8  Stairs(3) + ElevatorPumpRoom(1) + Mechanical(2) + Undeveloped(2)
    #   Restaurant       : -1  attic
    #   RestaurantFastFood: -1 attic
    #   SchoolSecondary  : -2  Mech_ZN_1_FLR_1/2
    #   MediumOffice     : -3  plenums (already reflected in count)
    #   OfficeLarge      : -3  plenums (already reflected in count)
    "RetailStandalone":   ("RetailStandalone.idf",    4,  "Retail Standalone"),
    "Stripmall":          ("Stripmall.idf",           10,  "Strip Mall"),
    "SmallOffice":        ("SmallOffice.idf",          5,  "Small Office"),
    "MediumOffice":       ("MediumOffice.idf",        15,  "Medium Office"),
    "SmallHotel":         ("SmallHotel.idf",          54,  "Small Hotel"),
    "LargeHotel":         ("LargeHotel.idf",          21,  "Large Hotel"),
    "MidRiseApartment":   ("MidRiseApartment.idf",    27,  "Midrise Apt."),
    "PrimarySchool":      ("PrimarySchool.idf",       24,  "Primary School"),
    "HealthCare":         ("HealthCare.idf",         110,  "Healthcare"),
    "Restaurant":         ("Restaurant.idf",           2,  "Restaurant"),
    "Hospital":           ("Hospital.idf",            55,  "Hospital"),
    "OfficeLarge":        ("OfficeLarge.idf",         20,  "Large Office"),
    "RestaurantFastFood": ("RestaurantFastFood.idf",   2,  "Fast-Food Restaurant"),
    "SchoolSecondary":    ("SchoolSecondary.idf",     44,  "Secondary School"),
    "Warehouse":          ("Warehouse.idf",            3,  "Warehouse"),
    "ApartmentHighRise":  ("ApartmentHighRise.idf",   27,  "Highrise Apt."),
}


# ---------------------------------------------------------------------------
# Prompt templates  (3 complexity levels × 16 buildings)
# Source: docs/Prompts_DOE_new.docx — phrasing matches docx exactly.
#
# Medium and detailed prompts use {n} as a placeholder for the zone count.
# _build_prompts() fills {n} with the actual num_zones from _BUILDINGS so that
# the zone count in every sent prompt exactly matches the IDF-detected zone count
# (num_zones column) — eliminating the three-column confusion in the CSV.
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATES = {

    # ── Simple (Table 0 of docs/Prompts_DOE.docx)
    # {n} is replaced with the actual conditioned zone count at build time.
    "simple": {
        "RetailStandalone": (
            "Generate a simulation-ready EnergyPlus IDF for a standalone retail "
            "building containing {n} thermal zones with a variable refrigerant flow "
            "HVAC system and no heat recovery. Assign VRF terminal units only to "
            "occupied and conditioned zones. Do not assign VRF terminal units to "
            "any unoccupied or unconditioned zones."
        ),
        "Stripmall": (
            "Generate a simulation-ready EnergyPlus IDF for a strip mall containing "
            "{n} thermal zones with a variable refrigerant flow HVAC system and no "
            "heat recovery. Assign VRF terminal units only to occupied and "
            "conditioned zones. Do not assign VRF terminal units to any unoccupied "
            "or unconditioned zones."
        ),
        "SmallOffice": (
            "Generate a simulation-ready EnergyPlus IDF for a small office "
            "containing {n} thermal zones with a variable refrigerant flow HVAC "
            "system and no heat recovery. Assign VRF terminal units only to occupied "
            "and conditioned zones. Do not assign VRF terminal units to any "
            "unoccupied or unconditioned zones."
        ),
        "MediumOffice": (
            "Generate a simulation-ready EnergyPlus IDF for a medium office "
            "containing {n} thermal zones with a variable refrigerant flow HVAC "
            "system and no heat recovery. Assign VRF terminal units only to occupied "
            "and conditioned zones. Do not assign VRF terminal units to any "
            "unoccupied or unconditioned zones."
        ),
        "SmallHotel": (
            "Generate a simulation-ready EnergyPlus IDF for a small hotel "
            "containing {n} thermal zones with a variable refrigerant flow HVAC "
            "system and no heat recovery. Assign VRF terminal units only to occupied "
            "and conditioned zones. Do not assign VRF terminal units to any "
            "unoccupied or unconditioned zones."
        ),
        "LargeHotel": (
            "Generate a simulation-ready EnergyPlus IDF for a large hotel "
            "containing {n} thermal zones with a variable refrigerant flow HVAC "
            "system and no heat recovery. Assign VRF terminal units only to occupied "
            "and conditioned zones. Do not assign VRF terminal units to any "
            "unoccupied or unconditioned zones."
        ),
        "MidRiseApartment": (
            "Generate a simulation-ready EnergyPlus IDF for a midrise apartment "
            "containing {n} thermal zones with a variable refrigerant flow HVAC "
            "system and no heat recovery. Assign VRF terminal units only to occupied "
            "and conditioned zones. Do not assign VRF terminal units to any "
            "unoccupied or unconditioned zones."
        ),
        "PrimarySchool": (
            "Generate a simulation-ready EnergyPlus IDF for a primary school "
            "containing {n} thermal zones with a variable refrigerant flow HVAC "
            "system and no heat recovery. Assign VRF terminal units only to occupied "
            "and conditioned zones. Do not assign VRF terminal units to any "
            "unoccupied or unconditioned zones."
        ),
        "HealthCare": (
            "Generate a simulation-ready EnergyPlus IDF for an outpatient "
            "healthcare facility containing {n} thermal zones with a variable "
            "refrigerant flow HVAC system and no heat recovery. Assign VRF terminal "
            "units only to occupied and conditioned zones. Do not assign VRF "
            "terminal units to any unoccupied or unconditioned zones."
        ),
        "Restaurant": (
            "Generate a simulation-ready EnergyPlus IDF for a restaurant containing "
            "{n} thermal zones with a variable refrigerant flow HVAC system and no "
            "heat recovery. Assign VRF terminal units only to occupied and "
            "conditioned zones. Do not assign VRF terminal units to any unoccupied "
            "or unconditioned zones."
        ),
        "Warehouse": (
            "Generate a simulation-ready EnergyPlus IDF for a warehouse containing "
            "{n} thermal zones with a variable refrigerant flow HVAC system and no "
            "heat recovery. Assign VRF terminal units only to occupied and "
            "conditioned zones. Do not assign VRF terminal units to any unoccupied "
            "or unconditioned zones."
        ),
        "SchoolSecondary": (
            "Generate a simulation-ready EnergyPlus IDF for a secondary school "
            "containing {n} thermal zones with a variable refrigerant flow HVAC "
            "system and no heat recovery. Assign VRF terminal units only to occupied "
            "and conditioned zones. Do not assign VRF terminal units to any "
            "unoccupied or unconditioned zones."
        ),
        "ApartmentHighRise": (
            "Generate a simulation-ready EnergyPlus IDF for a highrise apartment "
            "containing {n} thermal zones with a variable refrigerant flow HVAC "
            "system and no heat recovery. Assign VRF terminal units only to occupied "
            "and conditioned zones. Do not assign VRF terminal units to any "
            "unoccupied or unconditioned zones."
        ),
        "RestaurantFastFood": (
            "Generate a simulation-ready EnergyPlus IDF for a fast food restaurant "
            "containing {n} thermal zones with a variable refrigerant flow HVAC "
            "system and no heat recovery. Assign VRF terminal units only to occupied "
            "and conditioned zones. Do not assign VRF terminal units to any "
            "unoccupied or unconditioned zones."
        ),
        "Hospital": (
            "Generate a simulation-ready EnergyPlus IDF for a hospital containing "
            "{n} thermal zones with a variable refrigerant flow HVAC system and no "
            "heat recovery. Assign VRF terminal units only to occupied and "
            "conditioned zones. Do not assign VRF terminal units to any unoccupied "
            "or unconditioned zones."
        ),
        "OfficeLarge": (
            "Generate a simulation-ready EnergyPlus IDF for a large office "
            "containing {n} thermal zones with a variable refrigerant flow HVAC "
            "system and no heat recovery. Assign VRF terminal units only to occupied "
            "and conditioned zones. Do not assign VRF terminal units to any "
            "unoccupied or unconditioned zones."
            "terminal units only to occupied and conditioned zones. Do not assign "
            "VRF terminal units to any unoccupied or unconditioned zones."
        ),
    },

    # ── Medium (Table 1 of docs/Prompts_DOE.docx)
    # {n} is replaced with the actual conditioned zone count at build time.
    "medium": {
        "RetailStandalone": (
            "Create a complete VRF HVAC configuration for a standalone retail "
            "building containing {n} thermal zones, with no heat recovery, where "
            "each thermal zone is served by one indoor terminal unit connected to a "
            "single shared outdoor condensing unit through a zone terminal unit list. "
            "Only assign VRF terminal units to zones that are occupied and "
            "conditioned. Skip any zone that is unoccupied or unconditioned."
        ),
        "Stripmall": (
            "Create a complete VRF HVAC configuration for a strip mall containing "
            "{n} thermal zones, with no heat recovery, where each thermal zone is "
            "served by one indoor terminal unit connected to a single shared outdoor "
            "condensing unit through a zone terminal unit list. Only assign VRF "
            "terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
        "SmallOffice": (
            "Create a complete VRF HVAC configuration for a small office containing "
            "{n} thermal zones, with no heat recovery, where each thermal zone is "
            "served by one indoor terminal unit connected to a single shared outdoor "
            "condensing unit through a zone terminal unit list. Only assign VRF "
            "terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
        "MediumOffice": (
            "Create a complete VRF HVAC configuration for a medium office containing "
            "{n} thermal zones, with no heat recovery, where each thermal zone is "
            "served by one indoor terminal unit connected to a single shared outdoor "
            "condensing unit through a zone terminal unit list. Only assign VRF "
            "terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
        "SmallHotel": (
            "Create a complete VRF HVAC configuration for a small hotel containing "
            "{n} thermal zones, with no heat recovery, where each thermal zone is "
            "served by one indoor terminal unit connected to a single shared outdoor "
            "condensing unit through a zone terminal unit list. Only assign VRF "
            "terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
        "LargeHotel": (
            "Create a complete VRF HVAC configuration for a large hotel containing "
            "{n} thermal zones, with no heat recovery, where each thermal zone is "
            "served by one indoor terminal unit connected to a single shared outdoor "
            "condensing unit through a zone terminal unit list. Only assign VRF "
            "terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
        "MidRiseApartment": (
            "Create a complete VRF HVAC configuration for a midrise apartment "
            "containing {n} thermal zones, with no heat recovery, where each thermal "
            "zone is served by one indoor terminal unit connected to a single shared "
            "outdoor condensing unit through a zone terminal unit list. Only assign "
            "VRF terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
        "PrimarySchool": (
            "Create a complete VRF HVAC configuration for a primary school "
            "containing {n} thermal zones, with no heat recovery, where each thermal "
            "zone is served by one indoor terminal unit connected to a single shared "
            "outdoor condensing unit through a zone terminal unit list. Only assign "
            "VRF terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
        "HealthCare": (
            "Create a complete VRF HVAC configuration for an outpatient healthcare "
            "facility containing {n} thermal zones, with no heat recovery, where "
            "each thermal zone is served by one indoor terminal unit connected to a "
            "single shared outdoor condensing unit through a zone terminal unit list. "
            "Only assign VRF terminal units to zones that are occupied and "
            "conditioned. Skip any zone that is unoccupied or unconditioned."
        ),
        "Restaurant": (
            "Create a complete VRF HVAC configuration for a restaurant containing "
            "{n} thermal zones, with no heat recovery, where each thermal zone is "
            "served by one indoor terminal unit connected to a single shared outdoor "
            "condensing unit through a zone terminal unit list. Only assign VRF "
            "terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
        "Warehouse": (
            "Create a complete VRF HVAC configuration for a warehouse containing "
            "{n} thermal zones, with no heat recovery, where each thermal zone is "
            "served by one indoor terminal unit connected to a single shared outdoor "
            "condensing unit through a zone terminal unit list. Only assign VRF "
            "terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
        "SchoolSecondary": (
            "Create a complete VRF HVAC configuration for a secondary school "
            "containing {n} thermal zones, with no heat recovery, where each thermal "
            "zone is served by one indoor terminal unit connected to a single shared "
            "outdoor condensing unit through a zone terminal unit list. Only assign "
            "VRF terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
        "ApartmentHighRise": (
            "Create a complete VRF HVAC configuration for a highrise apartment "
            "containing {n} thermal zones, with no heat recovery, where each thermal "
            "zone is served by one indoor terminal unit connected to a single shared "
            "outdoor condensing unit through a zone terminal unit list. Only assign "
            "VRF terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
        "RestaurantFastFood": (
            "Create a complete VRF HVAC configuration for a fast food restaurant "
            "containing {n} thermal zones, with no heat recovery, where each thermal "
            "zone is served by one indoor terminal unit connected to a single shared "
            "outdoor condensing unit through a zone terminal unit list. Only assign "
            "VRF terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
        "Hospital": (
            "Create a complete VRF HVAC configuration for a hospital containing "
            "{n} thermal zones, with no heat recovery, where each thermal zone is "
            "served by one indoor terminal unit connected to a single shared outdoor "
            "condensing unit through a zone terminal unit list. Only assign VRF "
            "terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
        "OfficeLarge": (
            "Create a complete VRF HVAC configuration for a large office containing "
            "{n} thermal zones, with no heat recovery, where each thermal zone is "
            "served by one indoor terminal unit connected to a single shared outdoor "
            "condensing unit through a zone terminal unit list. Only assign VRF "
            "terminal units to zones that are occupied and conditioned. Skip any "
            "zone that is unoccupied or unconditioned."
        ),
    },

    # ── Detailed (Table 2 of docs/Prompts_DOE.docx)
    # {n} is replaced with the actual conditioned zone count at build time.
    # Trailing two sentences enforce zone-exclusion (matches docx exactly).
    "detailed": {
        "RetailStandalone": (
            "Design a complete HVAC system for a standalone retail building with "
            "{n} thermal zones using variable refrigerant flow and no heat recovery. "
            "One indoor terminal unit per thermal zone connected to a single shared "
            "outdoor condensing unit via a zone terminal unit list. Complete and "
            "valid object relationships, references, and node connections for all "
            "zones. Zone equipment lists, equipment connections, and air node "
            "definitions for every zone. Dual setpoint thermostat control in all "
            "zones with cooling setpoint = 24°C and heating setpoint = 21°C. "
            "Availability schedules for system operation, fan operation, and "
            "thermostat control. Use autosize for all airflow rates, capacities, "
            "fan parameters, and other sizing-related inputs wherever permitted. "
            "Use realistic default values for all required inputs not explicitly "
            "specified. Generate all required schedules, curves, and supporting "
            "objects necessary for a complete, simulation-ready EnergyPlus IDF. "
            "Assign VRF terminal units to zones that are occupied and conditioned. "
            "Exclude any zone that is unconditioned, unoccupied, or does not serve "
            "as a habitable space."
        ),
        "Stripmall": (
            "Design a complete HVAC system for a strip mall with {n} thermal zones "
            "using variable refrigerant flow and no heat recovery. One indoor "
            "terminal unit per thermal zone connected to a single shared outdoor "
            "condensing unit via a zone terminal unit list. Complete and valid object "
            "relationships, references, and node connections for all zones. Zone "
            "equipment lists, equipment connections, and air node definitions for "
            "every zone. Dual setpoint thermostat control in all zones with cooling "
            "setpoint = 24°C and heating setpoint = 21°C. Availability schedules "
            "for system operation, fan operation, and thermostat control. Use "
            "autosize for all airflow rates, capacities, fan parameters, and other "
            "sizing-related inputs wherever permitted. Use realistic default values "
            "for all required inputs not explicitly specified. Generate all required "
            "schedules, curves, and supporting objects necessary for a complete, "
            "simulation-ready EnergyPlus IDF. Assign VRF terminal units to zones "
            "that are occupied and conditioned. Exclude any zone that is "
            "unconditioned, unoccupied, or does not serve as a habitable space."
        ),
        "SmallOffice": (
            "Design a complete HVAC system for a small office with {n} thermal "
            "zones using variable refrigerant flow and no heat recovery. One indoor "
            "terminal unit per thermal zone connected to a single shared outdoor "
            "condensing unit via a zone terminal unit list. Complete and valid object "
            "relationships, references, and node connections for all zones. Zone "
            "equipment lists, equipment connections, and air node definitions for "
            "every zone. Dual setpoint thermostat control in all zones with cooling "
            "setpoint = 24°C and heating setpoint = 21°C. Availability schedules "
            "for system operation, fan operation, and thermostat control. Use "
            "autosize for all airflow rates, capacities, fan parameters, and other "
            "sizing-related inputs wherever permitted. Use realistic default values "
            "for all required inputs not explicitly specified. Generate all required "
            "schedules, curves, and supporting objects necessary for a complete, "
            "simulation-ready EnergyPlus IDF. Assign VRF terminal units to zones "
            "that are occupied and conditioned. Exclude any zone that is "
            "unconditioned, unoccupied, or does not serve as a habitable space."
        ),
        "MediumOffice": (
            "Design a complete HVAC system for a medium office with {n} thermal "
            "zones using variable refrigerant flow and no heat recovery. One indoor "
            "terminal unit per thermal zone connected to a single shared outdoor "
            "condensing unit via a zone terminal unit list. Complete and valid object "
            "relationships, references, and node connections for all zones. Zone "
            "equipment lists, equipment connections, and air node definitions for "
            "every zone. Dual setpoint thermostat control in all zones with cooling "
            "setpoint = 24°C and heating setpoint = 21°C. Availability schedules "
            "for system operation, fan operation, and thermostat control. Use "
            "autosize for all airflow rates, capacities, fan parameters, and other "
            "sizing-related inputs wherever permitted. Use realistic default values "
            "for all required inputs not explicitly specified. Generate all required "
            "schedules, curves, and supporting objects necessary for a complete, "
            "simulation-ready EnergyPlus IDF. Assign VRF terminal units to zones "
            "that are occupied and conditioned. Exclude any zone that is "
            "unconditioned, unoccupied, or does not serve as a habitable space."
        ),
        "SmallHotel": (
            "Design a complete HVAC system for a small hotel with {n} thermal zones "
            "using variable refrigerant flow and no heat recovery. One indoor "
            "terminal unit per thermal zone connected to a single shared outdoor "
            "condensing unit via a zone terminal unit list. Complete and valid object "
            "relationships, references, and node connections for all zones. Zone "
            "equipment lists, equipment connections, and air node definitions for "
            "every zone. Dual setpoint thermostat control in all zones with cooling "
            "setpoint = 24°C and heating setpoint = 21°C. Availability schedules "
            "for system operation, fan operation, and thermostat control. Use "
            "autosize for all airflow rates, capacities, fan parameters, and other "
            "sizing-related inputs wherever permitted. Use realistic default values "
            "for all required inputs not explicitly specified. Generate all required "
            "schedules, curves, and supporting objects necessary for a complete, "
            "simulation-ready EnergyPlus IDF. Assign VRF terminal units to zones "
            "that are occupied and conditioned. Exclude any zone that is "
            "unconditioned, unoccupied, or does not serve as a habitable space."
        ),
        "LargeHotel": (
            "Design a complete HVAC system for a large hotel with {n} thermal zones "
            "using variable refrigerant flow and no heat recovery. One indoor "
            "terminal unit per thermal zone connected to a single shared outdoor "
            "condensing unit via a zone terminal unit list. Complete and valid object "
            "relationships, references, and node connections for all zones. Zone "
            "equipment lists, equipment connections, and air node definitions for "
            "every zone. Dual setpoint thermostat control in all zones with cooling "
            "setpoint = 24°C and heating setpoint = 21°C. Availability schedules "
            "for system operation, fan operation, and thermostat control. Use "
            "autosize for all airflow rates, capacities, fan parameters, and other "
            "sizing-related inputs wherever permitted. Use realistic default values "
            "for all required inputs not explicitly specified. Generate all required "
            "schedules, curves, and supporting objects necessary for a complete, "
            "simulation-ready EnergyPlus IDF. Assign VRF terminal units to zones "
            "that are occupied and conditioned. Exclude any zone that is "
            "unconditioned, unoccupied, or does not serve as a habitable space."
        ),
        "MidRiseApartment": (
            "Design a complete HVAC system for a midrise apartment with {n} thermal "
            "zones using variable refrigerant flow and no heat recovery. One indoor "
            "terminal unit per thermal zone connected to a single shared outdoor "
            "condensing unit via a zone terminal unit list. Complete and valid object "
            "relationships, references, and node connections for all zones. Zone "
            "equipment lists, equipment connections, and air node definitions for "
            "every zone. Dual setpoint thermostat control in all zones with cooling "
            "setpoint = 24°C and heating setpoint = 21°C. Availability schedules "
            "for system operation, fan operation, and thermostat control. Use "
            "autosize for all airflow rates, capacities, fan parameters, and other "
            "sizing-related inputs wherever permitted. Use realistic default values "
            "for all required inputs not explicitly specified. Generate all required "
            "schedules, curves, and supporting objects necessary for a complete, "
            "simulation-ready EnergyPlus IDF. Assign VRF terminal units to zones "
            "that are occupied and conditioned. Exclude any zone that is "
            "unconditioned, unoccupied, or does not serve as a habitable space."
        ),
        "PrimarySchool": (
            "Design a complete HVAC system for a primary school with {n} thermal "
            "zones using variable refrigerant flow and no heat recovery. One indoor "
            "terminal unit per thermal zone connected to a single shared outdoor "
            "condensing unit via a zone terminal unit list. Complete and valid object "
            "relationships, references, and node connections for all zones. Zone "
            "equipment lists, equipment connections, and air node definitions for "
            "every zone. Dual setpoint thermostat control in all zones with cooling "
            "setpoint = 24°C and heating setpoint = 21°C. Availability schedules "
            "for system operation, fan operation, and thermostat control. Use "
            "autosize for all airflow rates, capacities, fan parameters, and other "
            "sizing-related inputs wherever permitted. Use realistic default values "
            "for all required inputs not explicitly specified. Generate all required "
            "schedules, curves, and supporting objects necessary for a complete, "
            "simulation-ready EnergyPlus IDF. Assign VRF terminal units to zones "
            "that are occupied and conditioned. Exclude any zone that is "
            "unconditioned, unoccupied, or does not serve as a habitable space."
        ),
        "HealthCare": (
            "Design a complete HVAC system for an outpatient healthcare facility "
            "with {n} thermal zones using variable refrigerant flow and no heat "
            "recovery. One indoor terminal unit per thermal zone connected to a "
            "single shared outdoor condensing unit via a zone terminal unit list. "
            "Complete and valid object relationships, references, and node "
            "connections for all zones. Zone equipment lists, equipment connections, "
            "and air node definitions for every zone. Dual setpoint thermostat "
            "control in all zones with cooling setpoint = 24°C and heating "
            "setpoint = 21°C. Availability schedules for system operation, fan "
            "operation, and thermostat control. Use autosize for all airflow rates, "
            "capacities, fan parameters, and other sizing-related inputs wherever "
            "permitted. Use realistic default values for all required inputs not "
            "explicitly specified. Generate all required schedules, curves, and "
            "supporting objects necessary for a complete, simulation-ready "
            "EnergyPlus IDF. Assign VRF terminal units to zones that are occupied "
            "and conditioned. Exclude any zone that is unconditioned, unoccupied, "
            "or does not serve as a habitable space."
        ),
        "Restaurant": (
            "Design a complete HVAC system for a restaurant with {n} thermal zones "
            "using variable refrigerant flow and no heat recovery. One indoor "
            "terminal unit per thermal zone connected to a single shared outdoor "
            "condensing unit via a zone terminal unit list. Complete and valid object "
            "relationships, references, and node connections for all zones. Zone "
            "equipment lists, equipment connections, and air node definitions for "
            "every zone. Dual setpoint thermostat control in all zones with cooling "
            "setpoint = 24°C and heating setpoint = 21°C. Availability schedules "
            "for system operation, fan operation, and thermostat control. Use "
            "autosize for all airflow rates, capacities, fan parameters, and other "
            "sizing-related inputs wherever permitted. Use realistic default values "
            "for all required inputs not explicitly specified. Generate all required "
            "schedules, curves, and supporting objects necessary for a complete, "
            "simulation-ready EnergyPlus IDF. Assign VRF terminal units to zones "
            "that are occupied and conditioned. Exclude any zone that is "
            "unconditioned, unoccupied, or does not serve as a habitable space."
        ),
        "Warehouse": (
            "Design a complete HVAC system for a warehouse with {n} thermal zones "
            "using variable refrigerant flow and no heat recovery. One indoor "
            "terminal unit per thermal zone connected to a single shared outdoor "
            "condensing unit via a zone terminal unit list. Complete and valid object "
            "relationships, references, and node connections for all zones. Zone "
            "equipment lists, equipment connections, and air node definitions for "
            "every zone. Dual setpoint thermostat control in all zones with cooling "
            "setpoint = 24°C and heating setpoint = 21°C. Availability schedules "
            "for system operation, fan operation, and thermostat control. Use "
            "autosize for all airflow rates, capacities, fan parameters, and other "
            "sizing-related inputs wherever permitted. Use realistic default values "
            "for all required inputs not explicitly specified. Generate all required "
            "schedules, curves, and supporting objects necessary for a complete, "
            "simulation-ready EnergyPlus IDF. Assign VRF terminal units to zones "
            "that are occupied and conditioned. Exclude any zone that is "
            "unconditioned, unoccupied, or does not serve as a habitable space."
        ),
        "SchoolSecondary": (
            "Design a complete HVAC system for a secondary school with {n} thermal "
            "zones using variable refrigerant flow and no heat recovery. One indoor "
            "terminal unit per thermal zone connected to a single shared outdoor "
            "condensing unit via a zone terminal unit list. Complete and valid object "
            "relationships, references, and node connections for all zones. Zone "
            "equipment lists, equipment connections, and air node definitions for "
            "every zone. Dual setpoint thermostat control in all zones with cooling "
            "setpoint = 24°C and heating setpoint = 21°C. Availability schedules "
            "for system operation, fan operation, and thermostat control. Use "
            "autosize for all airflow rates, capacities, fan parameters, and other "
            "sizing-related inputs wherever permitted. Use realistic default values "
            "for all required inputs not explicitly specified. Generate all required "
            "schedules, curves, and supporting objects necessary for a complete, "
            "simulation-ready EnergyPlus IDF. Assign VRF terminal units to zones "
            "that are occupied and conditioned. Exclude any zone that is "
            "unconditioned, unoccupied, or does not serve as a habitable space."
        ),
        "ApartmentHighRise": (
            "Design a complete HVAC system for a highrise apartment with {n} "
            "thermal zones using variable refrigerant flow and no heat recovery. "
            "One indoor terminal unit per thermal zone connected to a single shared "
            "outdoor condensing unit via a zone terminal unit list. Complete and "
            "valid object relationships, references, and node connections for all "
            "zones. Zone equipment lists, equipment connections, and air node "
            "definitions for every zone. Dual setpoint thermostat control in all "
            "zones with cooling setpoint = 24°C and heating setpoint = 21°C. "
            "Availability schedules for system operation, fan operation, and "
            "thermostat control. Use autosize for all airflow rates, capacities, "
            "fan parameters, and other sizing-related inputs wherever permitted. "
            "Use realistic default values for all required inputs not explicitly "
            "specified. Generate all required schedules, curves, and supporting "
            "objects necessary for a complete, simulation-ready EnergyPlus IDF. "
            "Assign VRF terminal units to zones that are occupied and conditioned. "
            "Exclude any zone that is unconditioned, unoccupied, or does not serve "
            "as a habitable space."
        ),
        "RestaurantFastFood": (
            "Design a complete HVAC system for a fast food restaurant with "
            "{n} thermal zones using variable refrigerant flow and no heat recovery. "
            "One indoor terminal unit per thermal zone connected to a single shared "
            "outdoor condensing unit via a zone terminal unit list. Complete and "
            "valid object relationships, references, and node connections for all "
            "zones. Zone equipment lists, equipment connections, and air node "
            "definitions for every zone. Dual setpoint thermostat control in all "
            "zones with cooling setpoint = 24°C and heating setpoint = 21°C. "
            "Availability schedules for system operation, fan operation, and "
            "thermostat control. Use autosize for all airflow rates, capacities, "
            "fan parameters, and other sizing-related inputs wherever permitted. "
            "Use realistic default values for all required inputs not explicitly "
            "specified. Generate all required schedules, curves, and supporting "
            "objects necessary for a complete, simulation-ready EnergyPlus IDF. "
            "Assign VRF terminal units to zones that are occupied and conditioned. "
            "Exclude any zone that is unconditioned, unoccupied, or does not serve "
            "as a habitable space."
        ),
        "Hospital": (
            "Design a complete HVAC system for a hospital with {n} thermal zones "
            "using variable refrigerant flow and no heat recovery. One indoor "
            "terminal unit per thermal zone connected to a single shared outdoor "
            "condensing unit via a zone terminal unit list. Complete and valid object "
            "relationships, references, and node connections for all zones. Zone "
            "equipment lists, equipment connections, and air node definitions for "
            "every zone. Dual setpoint thermostat control in all zones with cooling "
            "setpoint = 24°C and heating setpoint = 21°C. Availability schedules "
            "for system operation, fan operation, and thermostat control. Use "
            "autosize for all airflow rates, capacities, fan parameters, and other "
            "sizing-related inputs wherever permitted. Use realistic default values "
            "for all required inputs not explicitly specified. Generate all required "
            "schedules, curves, and supporting objects necessary for a complete, "
            "simulation-ready EnergyPlus IDF. Assign VRF terminal units to zones "
            "that are occupied and conditioned. Exclude any zone that is "
            "unconditioned, unoccupied, or does not serve as a habitable space."
        ),
        "OfficeLarge": (
            "Design a complete HVAC system for a large office with {n} thermal "
            "zones using variable refrigerant flow and no heat recovery. One indoor "
            "terminal unit per thermal zone connected to a single shared outdoor "
            "condensing unit via a zone terminal unit list. Complete and valid object "
            "relationships, references, and node connections for all zones. Zone "
            "equipment lists, equipment connections, and air node definitions for "
            "every zone. Dual setpoint thermostat control in all zones with cooling "
            "setpoint = 24°C and heating setpoint = 21°C. Availability schedules "
            "for system operation, fan operation, and thermostat control. Use "
            "autosize for all airflow rates, capacities, fan parameters, and other "
            "sizing-related inputs wherever permitted. Use realistic default values "
            "for all required inputs not explicitly specified. Generate all required "
            "schedules, curves, and supporting objects necessary for a complete, "
            "simulation-ready EnergyPlus IDF. Assign VRF terminal units to zones "
            "that are occupied and conditioned. Exclude any zone that is "
            "unconditioned, unoccupied, or does not serve as a habitable space."
        ),
    },
}


def _count_total_idf_zones(base_idf_path: str) -> int:
    """Count every Zone object in a base IDF file (raw, no filtering)."""
    try:
        with open(base_idf_path, "r", errors="ignore") as fh:
            lines = fh.readlines()
        return sum(1 for line in lines if line.strip().upper() == "ZONE,")
    except Exception:
        return 0


def _build_prompts() -> dict:
    """
    Resolve {n} using total_idf_zones — the raw Zone object count read
    directly from each building's IDF file (all zones, including non-HVAC
    zones such as plenums, attics, and stairwells).

    Falls back to _BUILDINGS[bkey][1] if the IDF file cannot be read
    (e.g. when the FinaIDF directory is unavailable at import time).
    """
    prompts: dict = {}
    for level, templates in _PROMPT_TEMPLATES.items():
        prompts[level] = {}
        for bkey, tmpl in templates.items():
            fname, fallback_n, _ = _BUILDINGS[bkey]
            total = _count_total_idf_zones(os.path.join(_BASE, fname))
            n = total if total > 0 else fallback_n
            prompts[level][bkey] = tmpl.format(n=n)
    return prompts


PROMPTS = _build_prompts()

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
# Zone-coverage helpers
# ---------------------------------------------------------------------------

import re as _re_csv

# Non-HVAC keywords — kept in sync with IDFHandler._NON_HVAC_ZONE_KEYWORDS
_NON_HVAC_ZONE_KEYWORDS_CSV = (
    'plenum', 'attic', 'stair', 'mech',
    'elevatorcore', 'elevator pump', 'back_space', 'undeveloped',
)


def _get_base_idf_zone_info(base_idf_path: str) -> tuple[int, list[str], list[str]]:
    """
    Parse the base IDF and return:
      total_count  — every Zone object in the file (raw, unfiltered)
      conditioned  — zones that should receive VRF (non-HVAC keywords excluded)
      excluded     — non-HVAC zones (plenums, attics, stairs, mech rooms …)

    Uses a lightweight regex scan so it never requires eppy or the IDD file.
    """
    try:
        with open(base_idf_path, "r", errors="ignore") as fh:
            lines = fh.readlines()
        all_zones: list[str] = []
        i = 0
        while i < len(lines):
            if lines[i].strip().upper() == "ZONE,":
                j = i + 1
                while j < len(lines):
                    nl = lines[j].strip()
                    if nl and not nl.startswith("!"):
                        name = nl.split(",")[0].split(";")[0].strip()
                        all_zones.append(name)
                        break
                    j += 1
            i += 1
        excluded   = [z for z in all_zones
                      if any(kw in z.lower() for kw in _NON_HVAC_ZONE_KEYWORDS_CSV)]
        conditioned = [z for z in all_zones if z not in excluded]
        return len(all_zones), conditioned, excluded
    except Exception:
        return 0, [], []


def _extract_hvac_zone_names(idf_path: Optional[str]) -> list[str]:
    """
    Parse the final IDF and return the zone names that actually received an
    HVACTemplate:Zone:VRF object.

    The first field of every HVACTemplate:Zone:VRF block is the zone name
    (field A1 per EnergyPlus IDD).  Returns an empty list on any error.
    """
    if not idf_path:
        return []
    try:
        with open(idf_path, "r", errors="ignore") as fh:
            content = fh.read()
        zones: list[str] = []
        for m in _re_csv.finditer(
            r'HVACTemplate:Zone:VRF\s*,\s*\n\s*([^,;\n]+)',
            content, _re_csv.IGNORECASE,
        ):
            name = m.group(1).strip()
            # Strip trailing inline comments ( "ZoneName,  !- Zone Name" )
            name = _re_csv.sub(r'\s*!.*', '', name).rstrip(',').strip()
            if name:
                zones.append(name)
        return zones
    except Exception:
        return []


def _zone_coverage_stats(
    actual: list[str], generated: list[str]
) -> tuple[float, str, str]:
    """
    Compute zone coverage statistics.

    Returns
    -------
    coverage_pct : float
        Percentage of actual zones that received a VRF object (0–100).
    missing : str
        Semicolon-separated zones expected but not generated.
    extra : str
        Semicolon-separated zones generated that were not in the actual list
        (hallucinated zone names).
    """
    if not actual:
        return 0.0, "", ";".join(generated)
    actual_set    = {z.strip().lower() for z in actual}
    generated_set = {z.strip().lower() for z in generated}
    # Preserve original casing for readability
    actual_lower_map    = {z.strip().lower(): z for z in actual}
    generated_lower_map = {z.strip().lower(): z for z in generated}
    missing   = [actual_lower_map[z]    for z in sorted(actual_set    - generated_set)]
    extra     = [generated_lower_map[z] for z in sorted(generated_set - actual_set)]
    covered   = len(actual_set & generated_set)
    coverage  = round(covered / len(actual_set) * 100, 1)
    return coverage, ";".join(missing), ";".join(extra)


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
    num_zones:           int          # expected conditioned zone count (_BUILDINGS registry)
    prompt:              str
    simulation_success:  bool
    first_try_success:   bool
    total_time_seconds:  float
    correction_iterations: int
    hvac_objects_generated: int
    detected_zones:      Optional[int]   = None   # conditioned zone count (non-HVAC excluded)
    # ── Zone breakdown columns ────────────────────────────────────────────
    total_idf_zones:     Optional[int]   = None   # ALL zones in the raw base IDF (no filter)
    excluded_zone_names: Optional[str]   = None   # semicolon-sep non-HVAC zones filtered out
    actual_zone_names:   Optional[str]   = None   # semicolon-sep conditioned zones (fed to LLM)
    hvac_zone_names:     Optional[str]   = None   # semicolon-sep zones that got VRF objects
    hvac_zone_count:     Optional[int]   = None   # number of zones with VRF objects
    zone_coverage_pct:   Optional[float] = None   # (hvac_zone_count / detected_zones) × 100
    missing_zones:       Optional[str]   = None   # conditioned zones NOT covered by VRF
    extra_zones:         Optional[str]   = None   # VRF zones NOT in conditioned list (hallucinated)
    # ── Scoring / reference columns ───────────────────────────────────────
    bleu:                Optional[float] = None
    rouge_l:             Optional[float] = None
    hvac_tokens_generated: Optional[int] = None
    hvac_tokens_reference: Optional[int] = None
    syntax_score:        Optional[float] = None
    parameter_score:     Optional[float] = None
    error_message:       Optional[str]   = None
    output_idf_path:     Optional[str]   = None
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

        output_name = (
            f"{model_key}_{tc['building_key'].lower()}_"
            f"{tc['prompt_complexity']}_r{run_idx}"
        )

        # ── Per-run log file: tee pipeline output so a broken terminal pipe
        #   can never kill a run in progress. ────────────────────────────────
        log_path = self.output_dir / "logs" / f"{output_name}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            ref = tc.get("reference_idf") if self.use_reference else None

            with open(log_path, "w") as _log_fh:
                _orig_out, _orig_err = sys.stdout, sys.stderr
                sys.stdout = _Tee(_orig_out, _log_fh)
                sys.stderr = _Tee(_orig_err, _log_fh)
                try:
                    result = pipeline.run(
                        base_idf=tc["base_idf"],
                        zones=tc["zones"],
                        user_request=tc["prompt"],
                        output_name=output_name,
                        reference_idf=ref,
                        enable_quick_validation=False,
                    )
                finally:
                    sys.stdout = _orig_out
                    sys.stderr = _orig_err

            elapsed  = round(time.time() - start, 1)
            success  = result.get("final_status") == "SUCCESS"
            iters    = result.get("total_iterations", 0)
            ev       = result.get("evaluation") or {}
            bleu     = ev.get("bleu")

            # ── Total raw IDF zones (all, before any filter) ───────────────
            total_idf_count, _, excluded_list = _get_base_idf_zone_info(tc["base_idf"])
            excluded_zone_names = ";".join(excluded_list)

            # ── Conditioned zones fed to the LLM (non-HVAC already removed) ─
            actual_zones_list = result.get("zones") or []
            detected_zones    = len(actual_zones_list)
            actual_zone_names = ";".join(actual_zones_list)

            # ── VRF zones actually written into the output IDF ─────────────
            output_idf = result.get("final_idf")
            hvac_zones_list   = _extract_hvac_zone_names(output_idf)
            hvac_zone_count   = len(hvac_zones_list)
            hvac_zone_names   = ";".join(hvac_zones_list)

            # ── Coverage / gap analysis ────────────────────────────────────
            coverage_pct, missing_zones, extra_zones = _zone_coverage_stats(
                actual_zones_list, hvac_zones_list
            )

            hvac_count = 0
            for step in result.get("steps", []):
                if step.get("step") == 1 and "objects_added" in step:
                    hvac_count = step["objects_added"]
                    break

            icon = "✓" if success else "✗"
            print(f"  {icon} success={success}  "
                  f"total_idf={total_idf_count}  "
                  f"conditioned={detected_zones}  "
                  f"excluded={len(excluded_list)}  "
                  f"hvac_generated={hvac_zone_count}  "
                  f"coverage={coverage_pct}%  "
                  f"iters={iters}  time={elapsed}s"
                  + (f"  bleu={bleu:.3f}" if bleu is not None else ""))
            if excluded_list:
                print(f"  ↳ Excluded (non-HVAC): {', '.join(excluded_list)}")
            if missing_zones:
                print(f"  ⚠️  Missing VRF for: {missing_zones.replace(';', ', ')}")
            if extra_zones:
                print(f"  ⚠️  Extra/hallucinated zones: {extra_zones.replace(';', ', ')}")
            print(f"  📄 log → {log_path}")

            return RunResult(
                model=model_key,         model_label=label,
                test_case=tc["name"],    building_type=tc["building_type"],
                prompt_complexity=tc["prompt_complexity"],
                num_zones=tc["num_zones"], prompt=tc["prompt"],
                simulation_success=success,
                first_try_success=(success and iters == 0),
                total_time_seconds=elapsed, correction_iterations=iters,
                hvac_objects_generated=hvac_count,
                detected_zones=detected_zones,
                total_idf_zones=total_idf_count,
                excluded_zone_names=excluded_zone_names,
                actual_zone_names=actual_zone_names,
                hvac_zone_names=hvac_zone_names,
                hvac_zone_count=hvac_zone_count,
                zone_coverage_pct=coverage_pct,
                missing_zones=missing_zones,
                extra_zones=extra_zones,
                bleu=bleu,           rouge_l=ev.get("rouge_l"),
                hvac_tokens_generated=ev.get("hvac_tokens_generated"),
                hvac_tokens_reference=ev.get("hvac_tokens_reference"),
                syntax_score=ev.get("syntax_score"),
                parameter_score=ev.get("parameter_score"),
                output_idf_path=output_idf,
            )

        except Exception as exc:
            elapsed = round(time.time() - start, 1)
            print(f"  ✗ EXCEPTION: {exc}")
            print(f"  📄 log → {log_path}")
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
        "--output", default=str(_PROJECT_ROOT / "outputs" / "model_comparison"),
        help="Output directory (default: <project_root>/outputs/model_comparison)",
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
