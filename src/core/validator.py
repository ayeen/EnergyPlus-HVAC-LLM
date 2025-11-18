"""
IDF Validator
"""

from src.core.idf_handler import IDFHandler

class IDFValidator:
    """Validate IDF files"""
    
    def __init__(self):
        self.handler = IDFHandler()
        self.errors = []
        self.warnings = []
    
    def validate(self, idf_path):
        """Validate IDF file"""
        
        self.errors = []
        self.warnings = []
        
        try:
            idf = self.handler.load(idf_path)
        except Exception as e:
            self.errors.append(f"Cannot load IDF: {str(e)}")
            return False
        
        # Check required objects
        self._check_required_objects(idf)
        
        # Check zones
        self._check_zones(idf)
        
        # Check HVAC
        self._check_hvac(idf)
        
        return len(self.errors) == 0
    
    def _check_required_objects(self, idf):
        """Check for required objects"""
        required = ['VERSION', 'BUILDING']
        
        for obj_type in required:
            if len(idf.idfobjects.get(obj_type, [])) == 0:
                self.errors.append(f"Missing required object: {obj_type}")
    
    def _check_zones(self, idf):
        """Check zone objects"""
        zones = idf.idfobjects.get('ZONE', [])
        
        if len(zones) == 0:
            self.errors.append("No zones defined")
    
    def _check_hvac(self, idf):
        """Check HVAC assignments"""
        zones = [z.Name for z in idf.idfobjects.get('ZONE', [])]
        
        # Check VRF assignments
        vrf_zones = idf.idfobjects.get('HVACTEMPLATE:ZONE:VRF', [])
        vrf_systems = [s.Name for s in idf.idfobjects.get('HVACTEMPLATE:SYSTEM:VRF', [])]
        thermostats = [t.Name for t in idf.idfobjects.get('HVACTEMPLATE:THERMOSTAT', [])]
        
        for vz in vrf_zones:
            # Check zone exists
            if vz.Zone_Name not in zones:
                self.errors.append(f"HVAC assigned to non-existent zone: {vz.Zone_Name}")
            
            # Check system exists
            if vz.Template_VRF_System_Name not in vrf_systems:
                self.errors.append(f"Zone references non-existent system: {vz.Template_VRF_System_Name}")
            
            # Check thermostat exists
            if vz.Template_Thermostat_Name and vz.Template_Thermostat_Name not in thermostats:
                self.errors.append(f"Zone references non-existent thermostat: {vz.Template_Thermostat_Name}")
    
    def get_report(self):
        """Get validation report"""
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings
        }
