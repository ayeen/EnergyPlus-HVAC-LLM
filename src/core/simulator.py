"""
EnergyPlus Simulator
"""

import subprocess
import os
import shutil
from config import Config

class EnergyPlusSimulator:
    """Run EnergyPlus simulations"""
    
    def __init__(self):
        self.energyplus_exe = Config.ENERGYPLUS_EXE
        self.weather_file = Config.WEATHER_FILE
        self.idd_file = Config.IDD_FILE
        # ExpandObjects executable is in the same directory as EnergyPlus
        # On Windows it's ExpandObjects.exe, on Linux/Mac it's ExpandObjects
        expand_name = "ExpandObjects.exe" if os.name == 'nt' else "ExpandObjects"
        self.expand_objects_exe = os.path.join(
            os.path.dirname(self.energyplus_exe),
            expand_name
        )
    
    def run(self, idf_path, output_dir):
        """Run simulation with HVACTemplate expansion if needed"""
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Copy files
        idf_filename = os.path.basename(idf_path)
        target_idf = os.path.join(output_dir, idf_filename)
        shutil.copy(idf_path, target_idf)
        shutil.copy(self.idd_file, os.path.join(output_dir, "Energy+.idd"))
        
        # Check if IDF contains HVACTemplate objects
        has_hvac_template = self._check_hvac_template(target_idf)
        
        # Run EnergyPlus
        original_dir = os.getcwd()
        os.chdir(output_dir)
        
        try:
            # If HVACTemplate objects exist, run ExpandObjects first
            if has_hvac_template:
                expand_result = self._expand_objects(idf_filename)
                if not expand_result["success"]:
                    return expand_result
                # Use the expanded IDF
                idf_filename = "expanded.idf"
            
            cmd = [
                self.energyplus_exe,
                "-w", self.weather_file,
                "-d", ".",
                idf_filename
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=Config.SIMULATION_TIMEOUT
            )
            
            return self._parse_results(output_dir)
            
        except subprocess.TimeoutExpired:
            return {
                "success": False, 
                "error": "Timeout",
                "error_count": 0,
                "severe_errors": [],
                "fatal_errors": [],
                "warnings": []
            }
        except Exception as e:
            return {
                "success": False, 
                "error": str(e),
                "error_count": 0,
                "severe_errors": [],
                "fatal_errors": [],
                "warnings": []
            }
        finally:
            os.chdir(original_dir)
    
    def _check_hvac_template(self, idf_path):
        """Check if IDF contains HVACTemplate objects"""
        try:
            with open(idf_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return 'HVACTemplate:' in content
        except:
            return False
    
    def _expand_objects(self, idf_filename):
        """Run ExpandObjects preprocessor"""
        try:
            # ExpandObjects expects in.idf as input
            if idf_filename != "in.idf":
                shutil.copy(idf_filename, "in.idf")
            
            # Run ExpandObjects
            result = subprocess.run(
                [self.expand_objects_exe],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # ExpandObjects creates expanded.idf
            if not os.path.exists("expanded.idf"):
                return {
                    "success": False,
                    "error": f"ExpandObjects failed to create expanded.idf: {result.stderr}",
                    "error_count": 1,
                    "severe_errors": [f"ExpandObjects failed: {result.stderr}"],
                    "fatal_errors": [],
                    "warnings": []
                }
            
            return {"success": True}
            
        except Exception as e:
            return {
                "success": False, 
                "error": f"ExpandObjects error: {str(e)}",
                "error_count": 1,
                "severe_errors": [f"ExpandObjects error: {str(e)}"],
                "fatal_errors": [],
                "warnings": []
            }
    
    def _parse_results(self, output_dir):
        """Parse simulation results"""
        
        err_file = os.path.join(output_dir, "eplusout.err")
        
        if not os.path.exists(err_file):
            return {"success": False, "error": "No error file generated"}
        
        with open(err_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Collect error lines and their continuation lines (marked with ~~~)
        error_blocks = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if '** Severe  **' in line or '**  Fatal  **' in line:
                # Start new error block
                block = [line.strip()]
                i += 1
                # Collect continuation lines
                while i < len(lines) and '**   ~~~   **' in lines[i]:
                    block.append(lines[i].strip())
                    i += 1
                error_blocks.append('\n'.join(block))
            else:
                i += 1
        
        # Keep original severe/fatal lists for compatibility
        severe = [l.strip() for l in lines if '** Severe  **' in l]
        fatal = [l.strip() for l in lines if '**  Fatal  **' in l]
        warnings = [l.strip() for l in lines if '** Warning **' in l]
        
        success = "EnergyPlus Completed Successfully" in content
        
        return {
            "success": success,
            "severe_errors": severe,
            "fatal_errors": fatal,
            "warnings": warnings,
            "error_blocks": error_blocks,  # New: full error blocks with details
            "error_count": len(severe) + len(fatal),
            "err_file": err_file
        }
