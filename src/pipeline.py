"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   VRF HVAC-LLM COMPLETE PIPELINE                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  HIGH-LEVEL FLOW (left → right = steps in order):                            ║
║                                                                              ║
║  Base IDF ──► [0] Load & Compliance Check                                    ║
║                       │                                                      ║
║                       ▼                                                      ║
║              [1] LLM Generation (Agent 1 — HVACGenerator)                    ║
║                       │  generates HVACTemplate:System:VRF                   ║
║                       │          + HVACTemplate:Zone:VRF  (per zone)         ║
║                       │          + HVACTemplate:Thermostat (per zone)        ║
║                       ▼                                                      ║
║              [1.5] LLM Quick Validation (Agent 1.5 — QuickValidator)         ║
║                       │  catches obvious errors before simulation            ║
║                       │  → [1.5b] auto-fix + [1.5c] re-validate if needed    ║
║                       ▼                                                      ║
║              [1.6] LLM Output Sanitization (in-memory, no agent)             ║
║                       │  • strip objects already in base IDF (avoid dupes)   ║
║                       │  • remove VRF blocks for non-HVAC zones (plenums…)   ║
║                       │  • clamp VRF outdoor-temp limits to spec             ║
║                       │  • rebuild malformed Zone:VRF blocks                 ║
║                       │  • delete orphaned comment-only lines                ║
║                       ▼                                                      ║
║              base_content + sanitized HVAC  →  _hvac.idf                     ║
║                       ▼                                                      ║
║              [2] Structural Validation (Eppy / IDFValidator)                 ║
║                       │  → [2.5] auto-fix validation errors if needed        ║
║                       ▼                                                      ║
║              [3] EnergyPlus Simulation                                       ║
║                       │  first run on _hvac.idf                              ║
║                       ▼                                                      ║
║              [4/5] Error-Correction Loop (Agent 3 — ErrorCorrector)          ║
║                       │  reads EnergyPlus error file, patches IDF,           ║
║                       │  re-simulates  (up to Config.MAX_ITERATIONS)         ║
║                       ▼                                                      ║
║              [Eval] Quality Evaluation (syntax + parameter + BLEU/ROUGE-L)   ║
║                       │                                                      ║
║                       ▼                                                      ║
║              _FINAL.idf  +  results JSON                                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ─── Standard library ──────────────────────────────────────────────────────
import os
import json
import time
from datetime import datetime

# ─── Project modules ───────────────────────────────────────────────────────
from config import Config                              # Global settings (paths, flags, limits)
from src.core.idf_handler import IDFHandler            # Loads / parses / upgrades IDF files
from src.core.simulator import EnergyPlusSimulator     # Runs EnergyPlus in a subprocess
from src.core.validator import IDFValidator            # Validates IDF schema via Eppy
from src.agents.agent1_generator import HVACGenerator  # Agent 1: LLM-based VRF generation
from src.agents.agent1_5_validator import QuickValidator  # Agent 1.5: LLM pre-simulation check
from src.agents.agent3_corrector import ErrorCorrector # Agent 3: LLM-based error correction
from src.core.evaluator import evaluate as evaluate_idf  # Syntax/parameter/BLEU scoring


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE CLASS
# ══════════════════════════════════════════════════════════════════════════════

class HVACLLMPipeline:
    """
    Orchestrates the end-to-end VRF HVAC generation workflow.

    This class owns all three LLM agents and the simulation/validation tools.
    Call  pipeline.run(base_idf, ...)  to kick off the full pipeline.
    Every major decision — which LLM to use, whether to enable RAG, how many
    correction iterations to allow — is controlled by Config or the arguments
    passed to __init__ / run().
    """

    def __init__(self, use_rag: bool = None, llm_provider: str = None):
        """
        Initialize the HVAC-LLM pipeline.

        Args:
            use_rag: Whether to enable RAG (Retrieval-Augmented Generation).
                    - None (default): Use config setting (Config.USE_RAG)
                    - True: Scenario 2 - LLM + RAG (enhanced with knowledge base)
                    - False: Scenario 1 - LLM only (no RAG enhancement)
            llm_provider: LLM provider to use. Options:
                    - None (default): Use config setting (Config.LLM_PROVIDER)
                    - "gemini": Use Google Gemini API
                    - "mistral": Use fine-tuned Mistral model
                    - "openai": Use OpenAI API
                    - "anthropic": Use Anthropic Claude API
        """
        # ── Determine runtime configuration ────────────────────────────────
        # Fall back to global Config values when the caller doesn't override.
        self.use_rag = use_rag if use_rag is not None else Config.USE_RAG
        self.llm_provider = llm_provider

        # ── Core tools (stateless helpers shared across all steps) ──────────
        self.handler   = IDFHandler()            # IDF parsing, zone detection, upgrades
        self.simulator = EnergyPlusSimulator()   # EnergyPlus subprocess runner
        self.validator = IDFValidator()          # Eppy-based schema checker

        # ── LLM Agents (each wraps an LLM call with domain-specific prompts) ─
        # Agent 1 – generates the full VRF HVAC section from scratch
        self.generator      = HVACGenerator(use_rag=self.use_rag, llm_provider=llm_provider)
        # Agent 1.5 – quickly checks the generated text for obvious mistakes
        self.quick_validator = QuickValidator()
        # Agent 3 – reads EnergyPlus error output and proposes targeted IDF patches
        self.corrector      = ErrorCorrector(use_rag=self.use_rag, llm_provider=llm_provider)


    # ════════════════════════════════════════════════════════════════════════
    #  MAIN ENTRY POINT
    # ════════════════════════════════════════════════════════════════════════

    def run(self, base_idf, zones=None, output_name="pipeline_output", system_name="VRF_System_1", user_request=None, enable_quick_validation=None, check_idd_compliance=True, auto_fix_compliance=True, reference_idf=None):
        """
        Run complete pipeline with automatic building context extraction.

        Args:
            base_idf: Path to base IDF file
            zones: Optional list of zone names. If None, auto-detects all zones from IDF.
                   If provided, validates zones exist and uses only those zones.
            output_name: Name for output files
            system_name: HVAC system name
            user_request: Optional natural language design request
                         (e.g., "Design a VRF system with heat recovery")
            enable_quick_validation: Enable LLM pre-validation before simulation (default: True)
            check_idd_compliance: Check base IDF for IDD compliance issues (default: True)
            auto_fix_compliance: Automatically fix detected compliance issues (default: True)
        """

        # Record wall-clock start so we can report total execution time at the end.
        start_time = time.time()

        # ── Resolve the base IDF path ───────────────────────────────────────
        # Convert relative path to absolute so later os.path operations are
        # independent of which directory the caller launched Python from.
        if not os.path.isabs(base_idf):
            # Resolve relative to current working directory
            base_idf = os.path.abspath(base_idf)

        # Hard-stop early if the file doesn't exist — nothing else can proceed.
        if not os.path.exists(base_idf):
            raise FileNotFoundError(f"Base IDF file not found: {base_idf}")

        print("=" * 70)
        print("HVAC-LLM PIPELINE")
        print("=" * 70)


        # ══════════════════════════════════════════════════════════════════
        #  STEP 0  —  LOAD BASE IDF & BUILDING CONTEXT
        # ══════════════════════════════════════════════════════════════════
        # We parse the IDF into memory first so that every downstream step
        # (compliance check, zone detection, context extraction) can work
        # with the same in-memory object instead of re-reading the file.
        print("\n[0] Analyzing base IDF...")
        base_idf_obj = self.handler.load(base_idf)


        # ── STEP 0.1 — IDD Compliance Check (optional but on by default) ──
        # Some base IDFs were created for older EnergyPlus versions and may
        # be missing required fields, design days, or the Site:Location.
        # The compliance check detects and (optionally) auto-fixes these so
        # the simulation doesn't crash on a missing-object fatal error.
        compliance_result = {'fixes_applied': [], 'compliant': True}  # Default for when check is disabled
        if check_idd_compliance:
            print("\n[0.1] Checking IDD compliance...")
            compliance_result = self.handler.check_idd_compliance(base_idf_obj, auto_fix=auto_fix_compliance)

            if not compliance_result['compliant'] and not auto_fix_compliance:
                # Non-compliant and the caller explicitly said NOT to auto-fix.
                # Print the full report and bail out — the user must fix manually.
                self.handler.print_compliance_report(compliance_result)
                results = {
                    "timestamp": datetime.now().isoformat(),
                    "base_idf": base_idf,
                    "final_status": "IDD_COMPLIANCE_FAILED",
                    "final_idf": None,
                    "total_iterations": 0,
                    "compliance_report": compliance_result,
                    "error": "Base IDF has IDD compliance issues. Set auto_fix_compliance=True to auto-fix."
                }
                return results
            elif compliance_result['fixes_applied']:
                # Auto-fix was allowed and some patches were applied — report them.
                print(f"✓ IDD compliance check complete")
                print(f"  🔧 Auto-fixed {len(compliance_result['fixes_applied'])} issue(s)")
                for fix in compliance_result['fixes_applied']:
                    print(f"     - {fix}")
            elif compliance_result['compliant']:
                print("✓ Base IDF is IDD-compliant")

            # Surface non-fatal warnings even when the IDF is technically valid.
            if compliance_result['warnings']:
                for w in compliance_result['warnings']:
                    print(f"  ⚠ {w}")
        # ── End IDD compliance check ───────────────────────────────────────


        # ── Enable sizing runs so EnergyPlus can autosize HVAC equipment ──
        # Without this, autosized fields (e.g. "Autosize" capacity) may not
        # be resolved and the simulation will produce sizing-related errors.
        if self.handler.enable_sizing(base_idf_obj):
            print("✓ Enabled zone/system sizing for HVAC autosizing")

        # ── Basic structural validation of the base IDF ────────────────────
        # Checks for missing required objects (e.g. SimulationControl,
        # Building) that must exist before we add any HVAC on top.
        validation_issues = self.handler.validate_base_idf(base_idf_obj)
        if validation_issues:
            print("\n⚠ Base IDF validation warnings:")
            for issue in validation_issues:
                print(f"  {issue}")
            print()


        # ── Auto-detect conditioned zones (or use caller-supplied list) ────
        # get_zones() internally filters out unconditioned zones (plenums,
        # attics, stairwells …) so the LLM never sees — or generates — VRF
        # objects for spaces that shouldn't be conditioned.
        zones_auto_detected = False
        if zones is None:
            zones = self.handler.get_zones(base_idf_obj)
            zones_auto_detected = True
            print(f"✓ Auto-detected {len(zones)} zones from IDF")
            for i, zone in enumerate(zones, 1):
                print(f"  {i}. {zone}")
        else:
            # Caller supplied explicit zone names — validate they actually
            # exist in the IDF before proceeding.
            print(f"✓ Using provided zones: {', '.join(zones)}")
            try:
                self.handler.validate_zones(base_idf_obj, zones)
                print(f"✓ All {len(zones)} zones validated")
            except ValueError as e:
                print(f"\n{e}")
                raise


        # ── Extract rich building metadata for context-aware generation ────
        # Area, volume, orientation, internal-load schedules, weather file…
        # This dict is forwarded to the LLM generator so the prompt can
        # reference the actual building characteristics rather than generic defaults.
        building_context = self.handler.extract_building_context(base_idf_obj)

        print(f"\n📊 Building Context:")
        print(f"  • Zones: {building_context['num_zones']}")
        if building_context['total_area'] > 0:
            print(f"  • Total Floor Area: {building_context['total_area']:.1f} m²")
        if building_context['total_volume'] > 0:
            print(f"  • Total Volume: {building_context['total_volume']:.1f} m³")
        print(f"  • Orientation: {building_context['orientation']}°")
        print(f"  • Internal Loads: {'✓ Yes' if building_context['has_internal_loads'] else '✗ None'}")
        if building_context['has_internal_loads']:
            
            loads = []
            if building_context['has_people']: loads.append("People")
            if building_context['has_lights']: loads.append("Lights")
            if building_context['has_equipment']: loads.append("Equipment")
            print(f"    ({', '.join(loads)})")
        print(f"  • Location: {building_context['weather_file']}")
        # ── End Step 0 ─────────────────────────────────────────────────────


        # ── Initialise the results dict that accumulates every step's outcome ─
        # This gets serialised to JSON at the end so researchers can inspect
        # exactly what happened at each stage without re-reading log files.
        results = {
            "timestamp": datetime.now().isoformat(),
            "base_idf": base_idf,
            "zones": zones,
            "zones_auto_detected": zones_auto_detected,
            "building_context": building_context,
            "user_request": user_request,
            "quick_validation_enabled": enable_quick_validation,
            "idd_compliance_checked": check_idd_compliance,
            "idd_fixes_applied": compliance_result.get('fixes_applied', []) if check_idd_compliance else [],
            "steps": []
        }


        # ══════════════════════════════════════════════════════════════════
        #  STEP 1  —  LLM HVAC GENERATION  (Agent 1)
        # ══════════════════════════════════════════════════════════════════
        # Agent 1 (HVACGenerator) sends the zone list + building context to
        # the LLM (Gemini / Mistral / fine-tuned model) with a carefully
        # crafted system prompt.  The LLM returns raw IDF text containing:
        #   • One  HVACTemplate:System:VRF  (the outdoor unit)
        #   • One  HVACTemplate:Zone:VRF    per conditioned zone (indoor units)
        #   • One  HVACTemplate:Thermostat  per conditioned zone (setpoints)
        print("\n[1] Generating HVAC...")
        if user_request:
            print(f"User Request: {user_request}")

        # Pass building context to generator for context-aware generation
        hvac_response = self.generator.generate_vrf_system(
            zones,
            system_name=system_name,
            user_request=user_request,
            building_context=building_context
        )

        # Guard: if the LLM returned nothing (network error, empty response,
        # safety filter, etc.) there is nothing to sanitize or simulate.
        if not hvac_response or hvac_response.strip() == "":
            print("❌ Error: Empty HVAC configuration generated")
            results["final_status"] = "GENERATION_FAILED"
            results["final_idf"] = None
            results["total_iterations"] = 0
            results["error"] = "Empty HVAC response"
            return results

        # Count the HVACTemplate objects as a quick sanity-check.
        # A healthy response should have at least 1 + 2×len(zones) objects.
        hvac_count = hvac_response.count('HVACTemplate:') + hvac_response.count('HVACTEMPLATE:')
        print(f"✓ Generated {hvac_count} HVAC objects")

        results["steps"].append({
            "step": 1,
            "name": "HVAC Generation",
            "objects_generated": hvac_count,
            "hvac_content_length": len(hvac_response)
        })


        # ══════════════════════════════════════════════════════════════════
        #  STEP 1.5  —  LLM QUICK VALIDATION  (Agent 1.5)
        # ══════════════════════════════════════════════════════════════════
        # Before we spend time running EnergyPlus (can take minutes),
        # Agent 1.5 does a fast LLM-based sanity-check on the generated text:
        #   • Does every zone in the prompt have a Zone:VRF block?
        #   • Does every Zone:VRF reference an existing Thermostat name?
        #   • Are required fields present and non-empty?
        # If errors are found → [1.5b] auto-fix → [1.5c] re-validate.
        if enable_quick_validation:
            print("\n[1.5] LLM validation (pre-simulation)...")

            validation_result = self.quick_validator.validate(
                idf_content=hvac_response,
                zones=zones,
                user_request=user_request
            )

            results["steps"].append({
                "step": 1.5,
                "name": "Quick Validation (LLM)",
                "valid": validation_result['valid'],
                "errors": validation_result['errors'],
                "warnings": validation_result['warnings'],
                "passed_checks": validation_result['passed_checks']
            })

            # ── Step 1.5b — Quick fix if validation found errors ───────────
            # We pass the errors back to Agent 3 (re-used here for lightweight
            # fixes) which analyzes them and returns targeted text patches.
            if not validation_result['valid']:
                print("\n[1.5b] Attempting quick fix before simulation...")

                try:
                    # Flatten validation errors into a single string for the LLM.
                    error_text = "\n".join(validation_result['errors'])

                    # Read base IDF to pass to corrector
                    with open(base_idf, 'r') as f:
                        base_content = f.read()

                    # The corrector needs a *complete* IDF (base + HVAC) to
                    # understand the full context of the errors.
                    temp_complete = base_content.rstrip() + "\n\n! === HVAC SYSTEM ===\n\n" + hvac_response.strip() + "\n"
                    temp_idf_path = os.path.join(Config.OUTPUT_DIR, "generated_idfs", f"{output_name}_temp.idf")
                    os.makedirs(os.path.dirname(temp_idf_path), exist_ok=True)
                    with open(temp_idf_path, 'w') as f:
                        f.write(temp_complete)

                    # Ask Agent 3 for patch suggestions based on the validation errors.
                    fixes = self.corrector.analyze_and_fix(temp_idf_path, [error_text])

                    if fixes:
                        # Apply the suggested patches to a new file.
                        temp_fixed_path = os.path.join(Config.OUTPUT_DIR, "generated_idfs", f"{output_name}_temp_fixed.idf")
                        applied = self.corrector.apply_fixes(temp_idf_path, fixes, temp_fixed_path)

                        if applied > 0:
                            # Extract just the HVAC section from fixed file
                            with open(temp_fixed_path, 'r') as f:
                                fixed_complete = f.read()

                            # Slice out only the HVAC portion (after our sentinel header)
                            # so the rest of the pipeline continues to work on HVAC-only text.
                            if "! === HVAC SYSTEM ===" in fixed_complete:
                                hvac_response = fixed_complete.split("! === HVAC SYSTEM ===")[1].strip()

                            print(f"✓ Quick fix applied ({applied} fixes)")

                            results["steps"].append({
                                "step": "1.5b",
                                "name": "Quick Fix Applied",
                                "fixes_applied": applied,
                                "status": "success"
                            })

                            # ── Step 1.5c — Re-validate after fix ─────────────
                            # Confirm the quick fix actually resolved the errors
                            # before we move on to the sanitization stage.
                            print("\n[1.5c] Re-validating after quick fix...")
                            revalidation = self.quick_validator.validate(
                                idf_content=hvac_response,
                                zones=zones,
                                user_request=user_request
                            )

                            results["steps"].append({
                                "step": "1.5c",
                                "name": "Re-validation After Quick Fix",
                                "valid": revalidation['valid'],
                                "errors": revalidation['errors']
                            })
                        else:
                            print("⚠ Quick fix returned no fixes")
                            results["steps"].append({
                                "step": "1.5b",
                                "name": "Quick Fix Failed",
                                "status": "no_fixes"
                            })
                    else:
                        print("⚠ Corrector returned no fixes")
                        results["steps"].append({
                            "step": "1.5b",
                            "name": "Quick Fix Failed",
                            "status": "no_fixes"
                        })

                except Exception as e:
                    print(f"⚠ Quick fix failed: {e}")
                    results["steps"].append({
                        "step": "1.5b",
                        "name": "Quick Fix Error",
                        "error": str(e)
                    })
        else:
            # Quick validation is disabled (e.g., in batch/benchmark runs to save time).
            print("\n[1.5] LLM validation SKIPPED (disabled)")
            results["steps"].append({
                "step": 1.5,
                "name": "LLM Validation",
                "status": "skipped"
            })
        # ── End Step 1.5 ───────────────────────────────────────────────────


        # ══════════════════════════════════════════════════════════════════
        #  STEP 1.6  —  LLM OUTPUT SANITIZATION
        # ══════════════════════════════════════════════════════════════════
        # The LLM's raw output is not always a clean HVAC-only snippet.
        # This stage applies several text-based guards IN ORDER to produce
        # a safe, EnergyPlus-ready HVAC section before merging with the base IDF.
        # No LLM calls happen here — purely regex / string operations.

        # ── Output file path for the merged IDF ───────────────────────────
        # The _hvac.idf is the intermediate file: base IDF + generated HVAC.
        # If all checks pass it goes to simulation; if not, corrections are
        # applied and the result is saved as _fixed_N.idf / _FINAL.idf.
        hvac_idf = os.path.join(Config.OUTPUT_DIR, "generated_idfs", f"{output_name}_hvac.idf")
        os.makedirs(os.path.dirname(hvac_idf), exist_ok=True)

        # ── Read base IDF as raw text (NOT via eppy) ───────────────────────
        # IMPORTANT: We deliberately read the original text file rather than
        # using eppy's idf.save() because eppy maps fields using the current
        # IDD (EnergyPlus 25.2) which added new optional fields not present
        # in older DOE prototype IDFs.  Saving through eppy shifts subsequent
        # field values by one position, corrupting geometry and boundary
        # conditions.  Instead we apply targeted text-based upgrades below.
        with open(base_idf, 'r') as f:
            base_content = f.read()

        # ── Upgrade base IDF text to EnergyPlus 25.2 field format ─────────
        # Inserts the blank optional fields added in v25.2 at the correct
        # positions (e.g. Space Name in BuildingSurface:Detailed, Sensible
        # Heat Fraction in People) without touching any existing values.
        base_content = self.handler.upgrade_idf_for_v25(base_content)

        # ── Patch People objects missing Activity Level Schedule Name ──────
        # After upgrade_idf_for_v25 inserts the blank SensibleHeatFraction
        # field at position 9, the Activity Level Schedule ends up at
        # position 10.  Many prototype IDFs omit this field entirely.
        # EnergyPlus requires it for internal-gain calculations, so we
        # default to the 120 W/person constant schedule added by compliance.
        import re as _re
        def _add_activity_schedule(m):
            obj = m.group(0)
            tokens = _re.split(r'([,;])', obj)
            values = [tokens[i] for i in range(0, len(tokens), 2) if i < len(tokens)]
            seps   = [tokens[i] for i in range(1, len(tokens), 2)]
            # After upgrade, old format now has 11 fields (type + 10 data).
            # If ActivitySchedule (index 10) is blank or missing, set it.
            if len(values) >= 11:
                activity_val = values[10].strip()
                if not activity_val:
                    values[10] = ' Activity_Schedule_120W'
            result = ''
            for v, s in zip(values, seps):
                result += v + s
            if len(values) > len(seps):
                result += values[-1]
            return result

        base_content = _re.sub(r'\bPeople,[\s\S]*?;', _add_activity_schedule, base_content, flags=_re.IGNORECASE)

        # ── Force SimulationControl to run sizing periods ──────────────────
        # The base IDF's SimulationControl may have sizing calculations
        # turned off.  We always override it via text replacement so that
        # autosized HVAC capacity fields get resolved during simulation.
        sim_ctrl_new = (
            "SimulationControl,\n"
            "  Yes,                     !- Do Zone Sizing Calculation\n"
            "  Yes,                     !- Do System Sizing Calculation\n"
            "  Yes,                     !- Do Plant Sizing Calculation\n"
            "  Yes,                     !- Run Simulation for Sizing Periods\n"
            "  Yes;                     !- Run Simulation for Weather File Run Periods"
        )
        base_content = _re.sub(
            r'SimulationControl,[\s\S]*?;',
            sim_ctrl_new,
            base_content,
            count=1,
        )

        # ── Append compliance-generated objects as raw IDF text ────────────
        # The compliance check may have added new objects (Site:Location,
        # DesignDays, Activity schedule) to base_idf_obj in memory, but we
        # never call eppy's saveas().  Instead _build_compliance_addon_text()
        # generates the equivalent IDF text so it can be safely appended.
        addon_objects = self._build_compliance_addon_text(compliance_result, base_idf_obj)
        if addon_objects:
            base_content = base_content.rstrip() + "\n\n" + addon_objects + "\n"

        # ── Section header written between base IDF and HVAC block ─────────
        # Makes it easy to visually identify the LLM-generated portion when
        # reviewing the merged IDF in a text editor.
        hvac_section_header = """
!-======================================================================
!- VRF HVAC SYSTEM SECTION - GENERATED BY VRF HVAC-LLM
!-======================================================================
!- Generated from user request (if provided)
!- This section contains all VRF HVAC Template objects
!- Generation timestamp: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """
!-======================================================================

"""

        # ══════════════════════════════════════════════════════════════════
        #  GUARD 1 — Duplicate-object stripping
        # ══════════════════════════════════════════════════════════════════
        # The LLM sometimes echoes back global singleton objects (Version,
        # Building, SimulationControl, etc.) that already exist in the base
        # IDF.  EnergyPlus treats duplicate object names as a fatal error.
        # We strip any matching object type from the LLM output before merge.
        import re as _re2
        _DUPE_TYPES = (
            # Simulation-level singletons — base IDF owns these
            r'Version\s*,[^;]*;',
            r'SimulationControl\s*,[^;]*;',
            r'Building\s*,[^;]*;',
            r'GlobalGeometryRules\s*,[^;]*;',
            r'HeatBalanceAlgorithm\s*,[^;]*;',
            r'Timestep\s*,[^;]*;',
            r'SurfaceConvectionAlgorithm:Inside\s*,[^;]*;',
            r'SurfaceConvectionAlgorithm:Outside\s*,[^;]*;',
            r'ShadowCalculation\s*,[^;]*;',
            r'ConvergenceLimits\s*,[^;]*;',
            r'RunPeriod\s*,[^;]*;',
            r'RunPeriodControl:[A-Za-z:]+\s*,[^;]*;',
            r'SummerDesignDay\s*,[^;]*;',
            r'WinterDesignDay\s*,[^;]*;',
            r'SizingPeriod:DesignDay\s*,[^;]*;',
            r'Site:Location\s*,[^;]*;',
            r'Site:WaterMainsTemperature\s*,[^;]*;',
            r'Sizing:Parameters\s*,[^;]*;',
            r'OutputControl:[A-Za-z:]+\s*,[^;]*;',
            r'Output:[A-Za-z:]+\s*,[^;]*;',
            r'ScheduleTypeLimits\s*,[^;]*;',
        )
        sanitized_hvac = hvac_response.strip()
        for _pat in _DUPE_TYPES:
            sanitized_hvac = _re2.sub(
                r'(?im)^\s*' + _pat,
                '',
                sanitized_hvac,
                flags=_re2.DOTALL
            )
        # Collapse runs of blank lines left behind after removals.
        sanitized_hvac = _re2.sub(r'\n{3,}', '\n\n', sanitized_hvac).strip()


        # ══════════════════════════════════════════════════════════════════
        #  GUARD 2 — Non-HVAC zone filter
        # ══════════════════════════════════════════════════════════════════
        # get_zones() already filters unconditioned zones before the LLM sees
        # them, but the LLM may hallucinate VRF blocks for zones it was told to
        # ignore (e.g. it sometimes still emits a plenum block).  Strip any
        # HVACTemplate:Zone:VRF whose zone name matches a non-HVAC keyword.
        # Keywords kept in sync with IDFHandler._NON_HVAC_ZONE_KEYWORDS.
        _NON_HVAC_KW = (
            'plenum',
            'attic',
            'stair',
            'mech',
            'elevatorcore',
            'elevator pump',
            'back_space',
            'undeveloped',
        )

        def _remove_non_hvac_vrf_zones(hvac_text):
            """Remove HVACTemplate:Zone:VRF AND their Thermostat blocks for non-HVAC zones."""

            # ── Pass 1: scan every Zone:VRF block and drop non-HVAC ones ──
            # We also collect the names of removed zones so Pass 2 can find
            # the matching orphaned Thermostat objects.
            removed_zones: set[str] = set()
            block_re = _re2.compile(
                r'HVACTemplate:Zone:VRF\s*,[^;]+;',
                _re2.IGNORECASE | _re2.DOTALL
            )
            def _keep_or_drop(m):
                block = m.group(0)
                # The first data field (after the object-type comma) is the zone name.
                after_comma = block[block.index(',') + 1:]
                first_field = after_comma.split(',')[0]
                first_field = _re2.sub(r'!.*', '', first_field).strip()  # strip inline comment
                zone_lower = first_field.lower()
                if any(kw in zone_lower for kw in _NON_HVAC_KW):
                    print(f"  ⚠️  Removing Zone:VRF block for non-HVAC zone: '{first_field}'")
                    removed_zones.add(first_field.lower())
                    return ''   # delete this block
                return block    # keep this block
            hvac_text = block_re.sub(_keep_or_drop, hvac_text)

            # If nothing was removed in Pass 1, skip the Thermostat sweep.
            if not removed_zones:
                return hvac_text

            # ── Pass 2: strip orphaned HVACTemplate:Thermostat blocks ─────
            # Convention: Thermostat name = "Thermostat_{zone_name}".
            # We match the thermostat's first field (its name) and check
            # whether it embeds any of the removed zone names or keywords.
            thermo_re = _re2.compile(
                r'HVACTemplate:Thermostat\s*,[^;]+;',
                _re2.IGNORECASE | _re2.DOTALL
            )
            def _drop_orphan_thermostat(m):
                block = m.group(0)
                after_comma = block[block.index(',') + 1:]
                name_field = after_comma.split(',')[0]
                name_field = _re2.sub(r'!.*', '', name_field).strip()
                name_lower = name_field.lower()
                # Drop if the thermostat name contains any removed-zone keyword,
                # OR if the full lowercase name matches a removed zone directly.
                if (any(kw in name_lower for kw in _NON_HVAC_KW) or
                        any(z in name_lower for z in removed_zones)):
                    print(f"  ⚠️  Removing orphaned Thermostat block: '{name_field}'")
                    return ''
                return block
            return thermo_re.sub(_drop_orphan_thermostat, hvac_text)

        sanitized_hvac = _remove_non_hvac_vrf_zones(sanitized_hvac)
        sanitized_hvac = _re2.sub(r'\n{3,}', '\n\n', sanitized_hvac).strip()
        # ── End Guard 2 ────────────────────────────────────────────────────


        # ══════════════════════════════════════════════════════════════════
        #  GUARD 3 — VRF outdoor-temperature range clamping
        # ══════════════════════════════════════════════════════════════════
        # LLMs sometimes hallucinate temperature values outside the physical
        # operating envelope of real VRF equipment.  We clamp the minimum
        # cooling outdoor temperature to the realistic range: −15 °C to −5 °C.
    
        def _fix_vrf_min_cooling_temp(hvac_text: str) -> str:
            """Clamp HVACTemplate:System:VRF min cooling temp to -6.0 °C if out of range."""
            def _clamp(m):
                try:
                    val = float(m.group(1))
                except ValueError:
                    return m.group(0)
                # Valid range: -15 °C (extended) to -5 °C (standard).
                # Anything outside → replace with EnergyPlus default -6.0 °C.
                if val < -15 or val > -5:
                    replacement = '-6.0'
                    print(f"  ⚠️  VRF min-cooling-temp: {val}°C → -6.0°C "
                          f"(EnergyPlus default / real equipment spec)")
                    return replacement + m.group(2)
                return m.group(0)
            # Match the numeric value that immediately precedes the specific
            # inline comment "!- Minimum Outdoor Temperature in Cooling".
            return _re2.sub(
                r'(-?\d+(?:\.\d+)?)(,\s*!-\s*Minimum\s+Outdoor\s+Temperature\s+in\s+Cooling)',
                _clamp,
                hvac_text,
                flags=_re2.IGNORECASE,
            )

        sanitized_hvac = _fix_vrf_min_cooling_temp(sanitized_hvac)
        sanitized_hvac = _re2.sub(r'\n{3,}', '\n\n', sanitized_hvac).strip()
        # ── End Guard 3 ────────────────────────────────────────────────────


        # ══════════════════════════════════════════════════════════════════
        #  GUARD 4 — Malformed Zone:VRF reconstruction
        # ══════════════════════════════════════════════════════════════════
        # The LLM occasionally collapses the zone name and the object type
        # name onto one comma-separated line, e.g.:
        #
        #   HVACTemplate:Zone:VRF,
        #     ZoneName,HVACTemplate:System:VRF,   ← type in field-2 slot
        #     VRF_System_1,                        ← system name in field-3 slot
        #
        # EnergyPlus validators then report:
        #   "Zone references non-existent system: HVACTemplate:System:VRF"
        #   "Zone references non-existent thermostat: VRF_System_1"

        def _fix_malformed_zone_vrf(hvac_text: str) -> str:
            # Find the actual VRF system name from the System:VRF block so
            # the rebuilt Zone:VRF references the correct outdoor unit.
            sys_m = _re2.search(
                r'HVACTemplate:System:VRF,\s*\n\s*([^,;\n]+)',
                hvac_text, _re2.IGNORECASE
            )
            system_name = sys_m.group(1).strip() if sys_m else 'VRF_System_1'

            def _zone_block(zone_name: str) -> str:
                """
                Return a correctly-formatted Zone:VRF block for zone_name.
                Uses exactly 44 fields per the EnergyPlus 25.2 IDD for
                HVACTemplate:Zone:VRF (confirmed from Energy+.idd).
                Fields 41-44 are the additional fields beyond the original 40:
                  F41 Zone Heating Design Supply Air Temperature Difference
                  F42 Baseboard Heating Type
                  F43 Baseboard Heating Availability Schedule Name
                  F44 Baseboard Heating Capacity
                """
                return (
                    f"HVACTemplate:Zone:VRF,\n"
                    f"  {zone_name},                          !- Zone Name (F1)\n"
                    f"  {system_name},                        !- Template VRF System Name (F2)\n"
                    f"  Thermostat_{zone_name},               !- Template Thermostat Name (F3)\n"
                    f"  ,                                     !- Zone Heating Sizing Factor (F4)\n"
                    f"  ,                                     !- Zone Cooling Sizing Factor (F5)\n"
                    f"  ,                                     !- Rated Total Heating Capacity Sizing Ratio (F6)\n"
                    f"  Autosize,                             !- Cooling Supply Air Flow Rate (F7)\n"
                    f"  Autosize,                             !- No Cooling Supply Air Flow Rate (F8)\n"
                    f"  Autosize,                             !- Heating Supply Air Flow Rate (F9)\n"
                    f"  Autosize,                             !- No Heating Supply Air Flow Rate (F10)\n"
                    f"  Autosize,                             !- Cooling Outdoor Air Flow Rate (F11)\n"
                    f"  Autosize,                             !- Heating Outdoor Air Flow Rate (F12)\n"
                    f"  Autosize,                             !- No Load Outdoor Air Flow Rate (F13)\n"
                    f"  ,                                     !- Outdoor Air Method (F14)\n"
                    f"  ,                                     !- Outdoor Air Flow Rate per Person (F15)\n"
                    f"  ,                                     !- Outdoor Air Flow Rate per Zone Floor Area (F16)\n"
                    f"  ,                                     !- Outdoor Air Flow Rate per Zone (F17)\n"
                    f"  ,                                     !- Design Specification Outdoor Air Object Name (F18)\n"
                    f"  ,                                     !- Design Specification Zone Air Distribution Object Name (F19)\n"
                    f"  ,                                     !- System Availability Schedule Name (F20)\n"
                    f"  ,                                     !- Supply Fan Operating Mode Schedule Name (F21)\n"
                    f"  DrawThrough,                          !- Supply Air Fan Placement (F22)\n"
                    f"  ,                                     !- Supply Fan Total Efficiency (F23)\n"
                    f"  ,                                     !- Supply Fan Delta Pressure (F24)\n"
                    f"  ,                                     !- Supply Fan Motor Efficiency (F25)\n"
                    f"  VariableRefrigerantFlowDX,            !- Cooling Coil Type (F26)\n"
                    f"  ,                                     !- Cooling Coil Availability Schedule Name (F27)\n"
                    f"  Autosize,                             !- Cooling Coil Gross Rated Total Capacity (F28)\n"
                    f"  Autosize,                             !- Cooling Coil Gross Rated Sensible Heat Ratio (F29)\n"
                    f"  VariableRefrigerantFlowDX,            !- Heat Pump Heating Coil Type (F30)\n"
                    f"  ,                                     !- Heat Pump Heating Coil Availability Schedule Name (F31)\n"
                    f"  Autosize,                             !- Heat Pump Heating Coil Gross Rated Capacity (F32)\n"
                    f"  30,                                   !- Zone Terminal Unit On Parasitic Electric Energy Use (F33)\n"
                    f"  20,                                   !- Zone Terminal Unit Off Parasitic Electric Energy Use (F34)\n"
                    f"  ,                                     !- Dedicated Outdoor Air System Name (F35)\n"
                    f"  SupplyAirTemperature,                 !- Zone Cooling Design Supply Air Temperature Input Method (F36)\n"
                    f"  12.8,                                 !- Zone Cooling Design Supply Air Temperature (F37)\n"
                    f"  ,                                     !- Zone Cooling Design Supply Air Temperature Difference (F38)\n"
                    f"  SupplyAirTemperature,                 !- Zone Heating Design Supply Air Temperature Input Method (F39)\n"
                    f"  50,                                   !- Zone Heating Design Supply Air Temperature (F40)\n"
                    f"  ,                                     !- Zone Heating Design Supply Air Temperature Difference (F41)\n"
                    f"  ,                                     !- Baseboard Heating Type (F42)\n"
                    f"  ,                                     !- Baseboard Heating Availability Schedule Name (F43)\n"
                    f"  ;                                     !- Baseboard Heating Capacity (F44)\n"
                )

            # Split on Zone:VRF header tokens so we can inspect each block.
            parts = _re2.split(r'(?=\nHVACTemplate:Zone:VRF,)', hvac_text)
            result_parts = []
            fixed_count = 0

            for part in parts:
                # Detect the malformed pattern: the first data line contains
                # "ZoneName,HVACTemplate:..." (zone name and object type merged).
                mal_m = _re2.match(
                    r'(\nHVACTemplate:Zone:VRF,\n)'
                    r'\s*([^,\n]+),HVACTemplate:[A-Za-z:]+,',
                    part
                )
                if mal_m:
                    zone_name = mal_m.group(2).strip()
                    # Find the end of this malformed block (start of next block or EOF).
                    block_end_m = _re2.search(
                        r'\n(?=HVACTemplate:|HVACTemplate:Thermostat)',
                        part[mal_m.end():]
                    )
                    tail = part[mal_m.end() + (block_end_m.start() if block_end_m else len(part)):]
                    result_parts.append('\n' + _zone_block(zone_name) + tail)
                    fixed_count += 1
                    print(f"  ⚠️  Zone:VRF rebuilt for '{zone_name}' "
                          f"(collapsed type+name on one line → fixed)")
                else:
                    result_parts.append(part)

            return ''.join(result_parts)

        sanitized_hvac = _fix_malformed_zone_vrf(sanitized_hvac)
        sanitized_hvac = _re2.sub(r'\n{3,}', '\n\n', sanitized_hvac).strip()
        # ── End Guard 4 ────────────────────────────────────────────────────


        # ══════════════════════════════════════════════════════════════════
        #  GUARD 5 — Orphaned comment-only line removal
        # ══════════════════════════════════════════════════════════════════
        # The LLM occasionally emits a bare "   !- Field Name" line AFTER the
        # semicolon that already closes an EnergyPlus object, e.g.:
        
        before = sanitized_hvac.count('\n')
        sanitized_hvac = _re2.sub(r'\n[ \t]+!-[^\n]*', '', sanitized_hvac)
        removed = before - sanitized_hvac.count('\n')
        if removed:
            print(f"  ⚠️  Removed {removed} orphaned comment-only line(s) from HVAC section")
        sanitized_hvac = _re2.sub(r'\n{3,}', '\n\n', sanitized_hvac).strip()
        # ── End Guard 5 (all sanitization complete) ────────────────────────


        # ══════════════════════════════════════════════════════════════════
        #  MERGE  —  base IDF text  +  sanitized HVAC section
        # ══════════════════════════════════════════════════════════════════
        # Concatenate the (possibly upgraded + patched) base IDF text with
        # the fully sanitized HVAC block to produce the _hvac.idf file that
        # goes into simulation.
        complete_idf = base_content.rstrip() + "\n" + hvac_section_header + sanitized_hvac + "\n"

        # ── DEBUG: check for a known bad sentinel value before writing ─────
        # "Baseboard Heating Type;" should never appear in a VRF-only file;
      
        if 'Baseboard Heating Type;' in complete_idf:
            print("  ❌ DEBUG: Problem STILL in complete_idf before write!")
            # More detailed debug
            if 'Baseboard Heating Type;' in hvac_response:
                print("    ↳ Problem is in hvac_response")
            if 'Baseboard Heating Type;' in base_content:
                print("    ↳ Problem is in base_content")
            if 'Baseboard Heating Type;' in hvac_section_header:
                print("    ↳ Problem is in hvac_section_header")
        else:
            print("  ✓ DEBUG: complete_idf is clean before write")

        # Write the merged IDF to disk.
        with open(hvac_idf, 'w') as f:
            f.write(complete_idf)

        # Re-count HVAC objects in the final merged text for the log.
        hvac_count = hvac_response.count('HVACTemplate:') + hvac_response.count('HVACTEMPLATE:')
        print(f"✓ Added {hvac_count} HVAC objects")
        results["steps"].append({
            "step": 1,
            "name": "HVAC Generation",
            "output": hvac_idf,
            "objects_added": hvac_count
        })


        # ══════════════════════════════════════════════════════════════════
        #  STEP 2  —  STRUCTURAL VALIDATION  (Eppy / IDFValidator)
        # ══════════════════════════════════════════════════════════════════
        # IDFValidator loads the merged _hvac.idf through Eppy and checks
        # that every object has the correct number of fields and that all
        # cross-references (e.g. thermostat names, system names) resolve.
        # This catches schema-level errors before EnergyPlus even runs.
        print("\n[2] Validating IDF...")
        is_valid = self.validator.validate(hvac_idf)
        report = self.validator.get_report()
        print(f"Valid: {is_valid}, Errors: {len(report['errors'])}")

        results["steps"].append({
            "step": 2,
            "name": "Validation",
            "valid": is_valid,
            "errors": report['errors']
        })


        # ══════════════════════════════════════════════════════════════════
        #  STEP 2.5  —  PRE-SIMULATION AUTO-FIX  (if validation failed)
        # ══════════════════════════════════════════════════════════════════
        # If Eppy found schema errors we try one round of LLM-based fixes
        # (Agent 3) before proceeding to EnergyPlus.  Fixing schema errors
        # now is cheaper than letting EnergyPlus abort with a fatal error
        # on the very first line it can't parse.
        if not is_valid and len(report['errors']) > 0:
            print("\n[2.5] Validation failed. Attempting pre-simulation fix...")
            print(f"      Found {len(report['errors'])} validation errors")

            try:
                # Summarise the first 10 errors (Agent 3 prompt has a token budget).
                error_text = "VALIDATION ERRORS:\n" + "\n".join(report['errors'][:10])  # Limit to first 10 errors

                # Ask Agent 3 to suggest patches for the Eppy-detected errors.
                fixes = self.corrector.analyze_and_fix(hvac_idf, [error_text])

                if fixes and len(fixes) > 0:
                    # Write the patched IDF to a new file to preserve the original.
                    pre_fixed_idf = os.path.join(
                        Config.OUTPUT_DIR,
                        "generated_idfs",
                        f"{output_name}_pre_fixed.idf"
                    )
                    applied = self.corrector.apply_fixes(hvac_idf, fixes, pre_fixed_idf)

                    if applied > 0:
                        print(f"✓ Applied {applied} pre-simulation fixes")

                        # ── Step 2.6 — Re-validate the patched file ────────
                        # Confirm the fix actually resolved the Eppy errors.
                        print("[2.6] Re-validating after fix...")
                        is_valid_after_fix = self.validator.validate(pre_fixed_idf)
                        re_report = self.validator.get_report()

                        results["steps"].append({
                            "step": 2.5,
                            "name": "Pre-Simulation Fix",
                            "fixes_applied": applied,
                            "revalidation_valid": is_valid_after_fix,
                            "errors_before": len(report['errors']),
                            "errors_after": len(re_report['errors'])
                        })

                        if is_valid_after_fix:
                            print("✓ Validation passed after fix!")
                            hvac_idf = pre_fixed_idf  # Use fixed version for simulation
                            is_valid = True  # Update validation status
                        else:
                            print(f"⚠ Still {len(re_report['errors'])} validation errors after fix")

                            # Even a partial improvement (fewer errors) is
                            # worth trying in EnergyPlus — some errors are
                            # non-fatal warnings that EnergyPlus tolerates.
                            if len(re_report['errors']) < len(report['errors']):
                                print(f"✓ Reduced errors from {len(report['errors'])} to {len(re_report['errors'])}")
                                print("  Proceeding to simulation with remaining errors...")
                                hvac_idf = pre_fixed_idf  # Use partially fixed version
                            else:
                                # Fix made things no better (or worse) — bail out.
                                print("❌ Fixes didn't reduce errors. Stopping pipeline.")
                                results["final_status"] = "VALIDATION_FAILED_AFTER_FIX"
                                results["final_idf"] = hvac_idf
                                results["total_iterations"] = 0
                                results["error_reason"] = f"Validation failed with {len(report['errors'])} errors, fix attempt didn't help"

                                # Save results
                                result_file = os.path.join(Config.OUTPUT_DIR, "logs", f"{output_name}_results.json")
                                os.makedirs(os.path.dirname(result_file), exist_ok=True)
                                with open(result_file, 'w') as f:
                                    json.dump(results, f, indent=2)

                                print(f"\nResults saved: {result_file}")
                                print("\n💡 Suggestion: Review validation errors or check generated HVAC objects")
                                return results
                    else:
                        # analyze_and_fix returned fix objects but apply_fixes
                        # wrote zero patches — something internal went wrong.
                        print("❌ No fixes could be applied")
                        results["final_status"] = "VALIDATION_FAILED_NO_FIX_APPLIED"
                        results["final_idf"] = hvac_idf
                        results["total_iterations"] = 0

                        # Save results
                        result_file = os.path.join(Config.OUTPUT_DIR, "logs", f"{output_name}_results.json")
                        os.makedirs(os.path.dirname(result_file), exist_ok=True)
                        with open(result_file, 'w') as f:
                            json.dump(results, f, indent=2)

                        print(f"\nResults saved: {result_file}")
                        return results
                else:
                    # Agent 3 found nothing to fix — the errors may be too
                    # structural for LLM-based correction (e.g. bad geometry).
                    print("❌ Corrector found no fixes for validation errors")
                    results["final_status"] = "VALIDATION_FAILED_NO_FIX"
                    results["final_idf"] = hvac_idf
                    results["total_iterations"] = 0

                    # Save results
                    result_file = os.path.join(Config.OUTPUT_DIR, "logs", f"{output_name}_results.json")
                    os.makedirs(os.path.dirname(result_file), exist_ok=True)
                    with open(result_file, 'w') as f:
                        json.dump(results, f, indent=2)

                    print(f"\nResults saved: {result_file}")
                    print("\n💡 Suggestion: Review validation errors manually")
                    return results

            except Exception as e:
                print(f"❌ Pre-simulation fix failed with error: {e}")
                results["steps"].append({
                    "step": 2.5,
                    "name": "Pre-Simulation Fix Error",
                    "error": str(e)
                })
                results["final_status"] = "VALIDATION_FIX_ERROR"
                results["error"] = str(e)

                # Save results
                result_file = os.path.join(Config.OUTPUT_DIR, "logs", f"{output_name}_results.json")
                os.makedirs(os.path.dirname(result_file), exist_ok=True)
                with open(result_file, 'w') as f:
                    json.dump(results, f, indent=2)

                print(f"\nResults saved: {result_file}")
                return results
        else:
            if is_valid:
                print("✓ Validation passed - proceeding to simulation")
        # ── End Step 2 / 2.5 ──────────────────────────────────────────────


        # ══════════════════════════════════════════════════════════════════
        #  STEP 3  —  ENERGYPLUS SIMULATION  (first run)
        # ══════════════════════════════════════════════════════════════════
        # EnergyPlusSimulator launches EnergyPlus as a subprocess, waits for
        # it to finish, then parses the .err file to extract error blocks.
        # sim_result['success'] is True only when EnergyPlus exits with 0
        # severe/fatal errors.
        print("\n[3] Simulating...")
        sim_dir = os.path.join(Config.OUTPUT_DIR, "simulations", f"{output_name}_sim1")
        sim_result = self.simulator.run(hvac_idf, sim_dir)
        print(f"Success: {sim_result['success']}, Errors: {sim_result['error_count']}")

        results["steps"].append({
            "step": 3,
            "name": "Simulation",
            "success": sim_result['success'],
            "error_count": sim_result['error_count']
        })


        # ══════════════════════════════════════════════════════════════════
        #  STEPS 4 / 5  —  ERROR-CORRECTION LOOP  (Agent 3)
        # ══════════════════════════════════════════════════════════════════
        # If EnergyPlus reported errors, Agent 3 reads the error blocks,
        # understands the domain context (VRF HVAC, zone layout), and
        # proposes targeted IDF patches.  We re-simulate after each round.
        # The loop runs at most Config.MAX_ERROR_CORRECTION_ITERATIONS times
        # to avoid infinite correction cycles on unfixable files.
        iteration = 1
        current_idf = hvac_idf

        while not sim_result['success'] and iteration <= Config.MAX_ERROR_CORRECTION_ITERATIONS:
            print(f"\n[4.{iteration}] Fixing errors...")

            # Collect all severe + fatal error blocks from the EnergyPlus output.
            all_errors = sim_result.get('error_blocks', sim_result['severe_errors'] + sim_result['fatal_errors'])
            # Ask Agent 3 to analyse the error blocks and generate fix suggestions.
            fixes = self.corrector.analyze_and_fix(current_idf, all_errors)

            # Write each correction round to its own file so we preserve the
            # full correction history for debugging / research logging.
            fixed_idf = os.path.join(
                Config.OUTPUT_DIR,
                "generated_idfs",
                f"{output_name}_fixed_{iteration}.idf"
            )

            applied = self.corrector.apply_fixes(current_idf, fixes, fixed_idf)
            print(f"✓ Applied {applied} fixes")

            results["steps"].append({
                "step": f"4.{iteration}",
                "name": f"Error Correction {iteration}",
                "fixes_applied": applied
            })

            # ── Step 5.N — Re-simulate with the corrected IDF ─────────────
            print(f"\n[5.{iteration}] Re-simulating...")
            sim_dir = os.path.join(
                Config.OUTPUT_DIR,
                "simulations",
                f"{output_name}_sim{iteration+1}"
            )
            sim_result = self.simulator.run(fixed_idf, sim_dir)
            print(f"Success: {sim_result['success']}")

            results["steps"].append({
                "step": f"5.{iteration}",
                "name": f"Re-simulation {iteration}",
                "success": sim_result['success'],
                "error_count": sim_result['error_count']
            })

            # Advance the "current" IDF pointer so the next iteration patches
            # the most recently corrected file, not the original.
            current_idf = fixed_idf
            iteration += 1
        # ── End error-correction loop ──────────────────────────────────────


        # ══════════════════════════════════════════════════════════════════
        #  FINAL OUTPUTS
        # ══════════════════════════════════════════════════════════════════

        # Determine overall pipeline outcome.
        results["final_status"] = "SUCCESS" if sim_result['success'] else "FAILED"
        results["final_idf"] = current_idf
        results["total_iterations"] = iteration - 1

        if sim_result['success']:
            # ── Copy corrected IDF to a stable, human-friendly filename ────
            # The _FINAL.idf is the clean deliverable: ready to open in
            # EP-Launch, share with colleagues, or use as a reference IDF
            # for future VRF generation tasks.
            final_output = os.path.join(
                Config.OUTPUT_DIR,
                "generated_idfs",
                f"{output_name}_FINAL.idf"
            )
            import shutil
            shutil.copy(current_idf, final_output)
            print(f"\n✓ Final corrected IDF copied to: {final_output}")
            print(f"  Use this file in EP-Launch for simulation!")

            # ── Quality Evaluation ─────────────────────────────────────────
            # Computes four complementary scores:
            #   • syntax_score   — rule-based: does the IDF have the right
            #                      objects, field counts, and required names?
            #   • parameter_score — value-range checks: are temperatures,
            #                      setpoints, flow rates within realistic bands?
            #   • bleu / rouge_l — token-overlap vs. a reference IDF (if one
            #                      was supplied); skipped when reference=None.
            print(f"\n[Eval] Running quality evaluation...")
            try:
                eval_scores = evaluate_idf(
                    generated_idf_path=final_output,
                    reference_idf_path=reference_idf if reference_idf and os.path.exists(reference_idf) else None,
                    zones=zones,
                    simulation_success=sim_result["success"],
                )
                results["evaluation"] = eval_scores
                print(f"  Syntax correctness:   {eval_scores['syntax_score']:.2f}")
                print(f"  Parameter accuracy:   {eval_scores['parameter_score']:.2f}")
                print(f"  Simulation success:   {eval_scores['simulation_success']}")
                if eval_scores.get("bleu") is not None:
                    print(f"  BLEU:                 {eval_scores['bleu']:.4f}")
                    print(f"  ROUGE-L:              {eval_scores['rouge_l']:.4f}")
            except Exception as e:
                print(f"  ⚠ Evaluation failed: {e}")
                results["evaluation"] = {"error": str(e)}

        # ── Persist the full results dict to a JSON log file ───────────────
        # The JSON log is the primary artefact used by the comparison scripts
        # (run_model_comparison.py / run_model_comparison_with_noisy_prompt.py)
        # to populate their CSV result tables.
        result_file = os.path.join(Config.OUTPUT_DIR, "logs", f"{output_name}_results.json")
        os.makedirs(os.path.dirname(result_file), exist_ok=True)

        results["total_execution_time_seconds"] = round(time.time() - start_time, 1)
        results["llm_provider"] = self.llm_provider or Config.LLM_PROVIDER
        results["correction_iterations"] = results.get("total_iterations", 0)

        with open(result_file, 'w') as f:
            json.dump(results, f, indent=2)

        # ── Final summary banner ───────────────────────────────────────────
        print("\n" + "=" * 70)
        print(f"PIPELINE COMPLETE: {results['final_status']}")
        print(f"Results saved: {result_file}")
        if sim_result['success']:
            print(f"\n🎉 SUCCESS! Use this file:")
            print(f"   {final_output}")
        print("=" * 70)
        return results


    # ════════════════════════════════════════════════════════════════════════
    #  HELPER METHODS
    # ════════════════════════════════════════════════════════════════════════

    def _build_compliance_addon_text(self, compliance_result: dict, base_idf_obj) -> str:
        """
        Generate plain IDF text for objects that the compliance check ADDED to the
        in-memory IDF (via eppy) but that we can never persist through eppy's saveas
        (because saveas would corrupt geometry field offsets).

        The three possible addon categories are:
          1. Schedule:Constant  —  Activity_Schedule_120W for People objects
          2. Site:Location      —  Chicago default when base IDF had none
          3. SizingPeriod:DesignDay  —  Chicago winter + summer days for autosizing

        The returned string is appended verbatim to the raw base IDF text just before
        the HVAC section header so EnergyPlus sees all objects in one file.
        """
        fixes = compliance_result.get('fixes_applied', [])
        addon = []

        # ── 1. Activity Level Schedule (for People internal-gain calculation) ─
        # Required field for People objects in EnergyPlus 25.2.
        # Defaults to 120 W/person (seated office activity, ASHRAE 55).
        needs_activity = any('Activity_Level_Schedule_Name' in f for f in fixes)
        if needs_activity:
            addon.append(
                "Schedule:Constant,\n"
                "  Activity_Schedule_120W,  !- Name\n"
                "  ,                        !- Schedule Type Limits Name\n"
                "  120;                     !- Hourly Value\n"
            )
            # Patch People objects in the base text to reference this schedule.
            # (Handled below by the caller injecting into base_content.)

        # ── 2. Site:Location  ─────────────────────────────────────────────
        # Some prototype IDFs omit this object.  EnergyPlus requires it to
        # determine sun angles and set the time zone for schedules.
        # Defaulting to Chicago (ASHRAE 90.1 prototype standard location).
        needs_site = any('Site:Location' in f for f in fixes)
        if needs_site:
            addon.append(
                "Site:Location,\n"
                "  Chicago_IL_USA,          !- Name\n"
                "  41.88,                   !- Latitude {deg}\n"
                "  -87.63,                  !- Longitude {deg}\n"
                "  -6.0,                    !- Time Zone {hr}\n"
                "  190;                     !- Elevation {m}\n"
            )

        # ── 3. Design Days (for HVAC autosizing) ──────────────────────────
        # EnergyPlus needs at least one SizingPeriod:DesignDay to run sizing
        # calculations.  We add the standard ASHRAE 90.1 Chicago design days
        # (same city as Site:Location above) when the base IDF had none.
        needs_dd = any('design days' in f.lower() for f in fixes)
        if needs_dd:
            addon.append(
                "SizingPeriod:DesignDay,\n"
                "  Chicago_Winter_Design_Day, !- Name\n"
                "  1,                       !- Month\n"
                "  21,                      !- Day of Month\n"
                "  WinterDesignDay,         !- Day Type\n"
                "  -17.3,                   !- Maximum Dry-Bulb Temperature {C}\n"
                "  0,                       !- Daily Dry-Bulb Temperature Range {deltaC}\n"
                "  ,                        !- Dry-Bulb Temperature Range Modifier Type\n"
                "  ,                        !- Dry-Bulb Temperature Range Modifier Schedule Name\n"
                "  Wetbulb,                 !- Humidity Condition Type\n"
                "  -17.3,                   !- Wetbulb or DewPoint at Maximum Dry-Bulb {C}\n"
                "  ,                        !- Humidity Condition Day Schedule Name\n"
                "  ,                        !- Humidity Ratio at Maximum Dry-Bulb {kgWater/kgDryAir}\n"
                "  ,                        !- Enthalpy at Maximum Dry-Bulb {J/kg}\n"
                "  ,                        !- Daily Wet-Bulb Temperature Range {deltaC}\n"
                "  99063,                   !- Barometric Pressure {Pa}\n"
                "  4.9,                     !- Wind Speed {m/s}\n"
                "  270,                     !- Wind Direction {deg}\n"
                "  No,                      !- Rain Indicator\n"
                "  No,                      !- Snow Indicator\n"
                "  No;                      !- Daylight Saving Time Indicator\n"
            )
            addon.append(
                "SizingPeriod:DesignDay,\n"
                "  Chicago_Summer_Design_Day, !- Name\n"
                "  7,                       !- Month\n"
                "  21,                      !- Day of Month\n"
                "  SummerDesignDay,         !- Day Type\n"
                "  33.3,                    !- Maximum Dry-Bulb Temperature {C}\n"
                "  10.7,                    !- Daily Dry-Bulb Temperature Range {deltaC}\n"
                "  ,                        !- Dry-Bulb Temperature Range Modifier Type\n"
                "  ,                        !- Dry-Bulb Temperature Range Modifier Schedule Name\n"
                "  Wetbulb,                 !- Humidity Condition Type\n"
                "  23.8,                    !- Wetbulb or DewPoint at Maximum Dry-Bulb {C}\n"
                "  ,                        !- Humidity Condition Day Schedule Name\n"
                "  ,                        !- Humidity Ratio at Maximum Dry-Bulb {kgWater/kgDryAir}\n"
                "  ,                        !- Enthalpy at Maximum Dry-Bulb {J/kg}\n"
                "  ,                        !- Daily Wet-Bulb Temperature Range {deltaC}\n"
                "  99063,                   !- Barometric Pressure {Pa}\n"
                "  5.3,                     !- Wind Speed {m/s}\n"
                "  230,                     !- Wind Direction {deg}\n"
                "  No,                      !- Rain Indicator\n"
                "  No,                      !- Snow Indicator\n"
                "  No;                      !- Daylight Saving Time Indicator\n"
            )

        return "\n".join(addon)


# ══════════════════════════════════════════════════════════════════════════════
#  SCRIPT ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """
    Minimal example: run the pipeline on a single building IDF.
    Replace base_idf and zones with real paths/names for your building.
    For batch/benchmarking runs use scripts/run_model_comparison.py instead.
    """

    # Example usage
    pipeline = HVACLLMPipeline()

    # You need to provide a base IDF with zones
    base_idf = "data/base_idfs/building_with_zones.idf"
    zones = ["Zone_1"]

    results = pipeline.run(base_idf, zones, output_name="example_run")

    return results

if __name__ == "__main__":
    main()
