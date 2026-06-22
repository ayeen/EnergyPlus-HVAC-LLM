"""
IDF Evaluation Module
=====================
Computes four quality dimensions for a generated IDF file:

  1. IDF Syntax Correctness  – structural / parse-level checks
  2. VRF Parameter Accuracy  – domain-range checks on key VRF fields
  3. EnergyPlus Simulation Success – passed in from pipeline results
  4. Text Similarity          – BLEU and ROUGE-L vs a reference IDF
"""

import re
from typing import Optional

from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer


# ─────────────────────────────────────────────────────────────────────────────
# 1. HVACTemplate section extraction / tokenisation
# ─────────────────────────────────────────────────────────────────────────────

def extract_hvac_section(idf_content: str) -> str:
    """Return only the HVACTemplate:* objects from an IDF string, normalised."""
    lines = []
    inside = False
    for line in idf_content.splitlines():
        stripped = line.strip()
        if re.match(r"HVACTemplate:", stripped, re.IGNORECASE):
            inside = True
        if inside:
            if not stripped or stripped.startswith("!"):
                continue
            clean = re.sub(r"!.*$", "", stripped).strip()
            if clean:
                lines.append(clean)
        if inside and stripped.endswith(";"):
            inside = False
    return "\n".join(lines)


def _tokenize(text: str) -> list:
    return re.findall(r"[A-Za-z0-9_.\-]+", text.lower())


# ─────────────────────────────────────────────────────────────────────────────
# 2. Text-similarity metrics (BLEU & ROUGE-L)
# ─────────────────────────────────────────────────────────────────────────────

def compute_bleu(hypothesis: str, reference: str) -> float:
    hyp = _tokenize(hypothesis)
    ref = _tokenize(reference)
    if not hyp or not ref:
        return 0.0
    return round(
        sentence_bleu([ref], hyp,
                      weights=(0.25, 0.25, 0.25, 0.25),
                      smoothing_function=SmoothingFunction().method1),
        4,
    )


def compute_rouge_l(hypothesis: str, reference: str) -> float:
    if not hypothesis.strip() or not reference.strip():
        return 0.0
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)
    return round(scorer.score(reference, hypothesis)["rougeL"].fmeasure, 4)


# ─────────────────────────────────────────────────────────────────────────────
# 3. IDF syntax-correctness checks
# ─────────────────────────────────────────────────────────────────────────────

def check_idf_syntax_correctness(idf_content: str, zones: list) -> dict:
    """
    Rule-based structural checks on the HVACTemplate section.

    Returns:
        score          – 0.0–1.0  (fraction of checks passed)
        checks_passed  – list of passing check names
        checks_failed  – list of failing check names
        details        – human-readable notes
    """
    checks_passed, checks_failed, details = [], [], []
    hvac = extract_hvac_section(idf_content)

    # --- Object termination ---
    objects_raw = re.split(r"(?=HVACTemplate:)", hvac)
    objects_raw = [o.strip() for o in objects_raw if o.strip()]
    unterminated = [o.splitlines()[0] for o in objects_raw if not o.rstrip().endswith(";")]
    if unterminated:
        checks_failed.append("object_termination")
        details.append(f"Unterminated objects: {unterminated[:3]}")
    else:
        checks_passed.append("object_termination")

    # --- Required object types present ---
    has_system    = bool(re.search(r"HVACTemplate:System:VRF",     hvac, re.I))
    has_thermostat= bool(re.search(r"HVACTemplate:Thermostat",     hvac, re.I))
    has_zone_vrf  = bool(re.search(r"HVACTemplate:Zone:VRF",       hvac, re.I))

    for name, present in [
        ("has_System_VRF",    has_system),
        ("has_Thermostat",    has_thermostat),
        ("has_Zone_VRF",      has_zone_vrf),
    ]:
        (checks_passed if present else checks_failed).append(name)

    # --- Zone count matches expected ---
    if zones:
        zone_vrf_count = len(re.findall(r"HVACTemplate:Zone:VRF,", hvac, re.I))
        therm_count    = len(re.findall(r"HVACTemplate:Thermostat,", hvac, re.I))
        if zone_vrf_count == len(zones):
            checks_passed.append("zone_vrf_count_matches")
        else:
            checks_failed.append("zone_vrf_count_matches")
            details.append(f"Expected {len(zones)} Zone:VRF, found {zone_vrf_count}")
        if therm_count == len(zones):
            checks_passed.append("thermostat_count_matches")
        else:
            checks_failed.append("thermostat_count_matches")
            details.append(f"Expected {len(zones)} Thermostats, found {therm_count}")

    # --- No markdown fences leaked into output ---
    if "```" in idf_content:
        checks_failed.append("no_markdown_artifacts")
        details.append("Markdown code-fence detected in output")
    else:
        checks_passed.append("no_markdown_artifacts")

    total = len(checks_passed) + len(checks_failed)
    score = round(len(checks_passed) / total, 4) if total else 0.0

    return {
        "score":          score,
        "checks_passed":  checks_passed,
        "checks_failed":  checks_failed,
        "details":        details,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. VRF parameter-accuracy checks
# ─────────────────────────────────────────────────────────────────────────────

# Valid ranges: (min, max) or list of allowed strings
_VRF_FIELD_RULES = {
    # Cooling COP
    r"(?:gross[_ ]rated[_ ]cooling[_ ]cop|cooling[_ ]cop)[^\n]*?\n\s*([\d.]+)": (2.5, 6.0),
    # Heating COP
    r"(?:gross[_ ]rated[_ ]heating[_ ]cop|heating[_ ]cop)[^\n]*?\n\s*([\d.]+)": (2.5, 6.0),
    # Cooling setpoint
    r"constant[_ ]cooling[_ ]setpoint[^\n]*?\n\s*([\d.]+)": (18.0, 32.0),
    # Heating setpoint
    r"constant[_ ]heating[_ ]setpoint[^\n]*?\n\s*([\d.]+)": (10.0, 25.0),
}

# Field values extracted inline (comma-separated IDF format)
_COP_PATTERN = re.compile(
    r"HVACTemplate:System:VRF,.*?"   # start of VRF system block
    r"(?:[\s\S]*?,){3}\s*([\d.]+)",  # 4th field = cooling COP
    re.IGNORECASE,
)


def check_vrf_parameter_accuracy(idf_content: str) -> dict:
    """
    Check that key VRF numeric parameters are within physically valid ranges.

    Returns:
        score          – 0.0–1.0
        checks_passed  – passing field names
        checks_failed  – failing field names
        details        – out-of-range values found
    """
    checks_passed, checks_failed, details = [], [], []
    hvac = extract_hvac_section(idf_content)

    # ── COP values (scan all numeric tokens after known COP keywords) ──────
    cop_pattern = re.compile(
        r"(cooling[_\s]cop|heating[_\s]cop)[,\s]*([\d.]+)",
        re.IGNORECASE,
    )
    for m in cop_pattern.finditer(hvac):
        field_name = m.group(1).replace(" ", "_").lower()
        try:
            val = float(m.group(2))
        except ValueError:
            continue
        if 2.5 <= val <= 6.0:
            checks_passed.append(f"{field_name}={val}")
        else:
            checks_failed.append(f"{field_name}={val}")
            details.append(f"{field_name} value {val} outside [2.5, 6.0]")

    # ── Setpoint temperatures ─────────────────────────────────────────────
    heat_sp = re.findall(r"constant[_\s]heating[_\s]setpoint[,\s]*([\-\d.]+)", hvac, re.I)
    cool_sp = re.findall(r"constant[_\s]cooling[_\s]setpoint[,\s]*([\-\d.]+)", hvac, re.I)

    for val_str in heat_sp:
        try:
            val = float(val_str)
            if 10.0 <= val <= 25.0:
                checks_passed.append(f"heating_setpoint={val}")
            else:
                checks_failed.append(f"heating_setpoint={val}")
                details.append(f"Heating setpoint {val} outside [10, 25] °C")
        except ValueError:
            pass

    for val_str in cool_sp:
        try:
            val = float(val_str)
            if 18.0 <= val <= 32.0:
                checks_passed.append(f"cooling_setpoint={val}")
            else:
                checks_failed.append(f"cooling_setpoint={val}")
                details.append(f"Cooling setpoint {val} outside [18, 32] °C")
        except ValueError:
            pass

    # ── Master thermostat dependency ──────────────────────────────────────
    if re.search(r"MasterThermostatPriority", hvac, re.I):
        has_master_zone = bool(
            re.search(r"zone[_\s]name[_\s]for[_\s]master[_\s]thermostat", hvac, re.I)
        )
        if has_master_zone:
            checks_passed.append("master_thermostat_zone_set")
        else:
            checks_failed.append("master_thermostat_zone_set")
            details.append("MasterThermostatPriority used but zone not specified")

    # ── Autosize fields present ───────────────────────────────────────────
    autosize_count = len(re.findall(r"\bAutosize\b", hvac, re.I))
    if autosize_count >= 3:
        checks_passed.append("autosize_fields_present")
    else:
        checks_failed.append("autosize_fields_present")
        details.append(f"Only {autosize_count} Autosize fields found (expected ≥ 3)")

    total = len(checks_passed) + len(checks_failed)
    score = round(len(checks_passed) / total, 4) if total else 0.0

    return {
        "score":         score,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "details":       details,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Master evaluate() function
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(
    generated_idf_path: str,
    reference_idf_path: Optional[str] = None,
    zones: Optional[list] = None,
    simulation_success: bool = False,
) -> dict:
    """
    Full evaluation of a generated IDF file.

    Args:
        generated_idf_path:   Path to the pipeline-generated IDF.
        reference_idf_path:   Optional expert reference IDF for BLEU/ROUGE-L.
        zones:                List of expected zone names (for count checks).
        simulation_success:   Whether EnergyPlus simulation passed.

    Returns dict with keys:
        syntax_score          – IDF syntax correctness  (0–1)
        parameter_score       – VRF parameter accuracy  (0–1)
        simulation_success    – bool (passed in)
        bleu                  – BLEU vs reference       (0–1, or None)
        rouge_l               – ROUGE-L vs reference    (0–1, or None)
        hvac_tokens_generated – int
        hvac_tokens_reference – int or None
        reference_idf         – path used, or None
        syntax_detail         – full syntax result dict
        parameter_detail      – full parameter result dict
    """
    with open(generated_idf_path, "r", encoding="utf-8", errors="ignore") as f:
        gen_content = f.read()

    gen_hvac = extract_hvac_section(gen_content)
    syntax   = check_idf_syntax_correctness(gen_content, zones or [])
    params   = check_vrf_parameter_accuracy(gen_content)

    result = {
        "syntax_score":           syntax["score"],
        "parameter_score":        params["score"],
        "simulation_success":     simulation_success,
        "bleu":                   None,
        "rouge_l":                None,
        "hvac_tokens_generated":  len(_tokenize(gen_hvac)),
        "hvac_tokens_reference":  None,
        "reference_idf":          reference_idf_path,
        "syntax_detail":          syntax,
        "parameter_detail":       params,
    }

    if reference_idf_path:
        try:
            with open(reference_idf_path, "r", encoding="utf-8", errors="ignore") as f:
                ref_content = f.read()
            ref_hvac = extract_hvac_section(ref_content)
            result["bleu"]                  = compute_bleu(gen_hvac, ref_hvac)
            result["rouge_l"]               = compute_rouge_l(gen_hvac, ref_hvac)
            result["hvac_tokens_reference"] = len(_tokenize(ref_hvac))
        except Exception as e:
            result["reference_error"] = str(e)

    return result
