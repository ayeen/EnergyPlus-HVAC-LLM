"""
IDF File Handler
"""

from eppy.modeleditor import IDF
from config import Config

class IDFHandler:
    """Handle IDF file operations"""
    
    def __init__(self):
        IDF.setiddname(Config.IDD_FILE)
    
    def load(self, idf_path):
        """Load IDF file"""
        return IDF(idf_path)
    
    def create_new(self):
        """Create new empty IDF"""
        return IDF()
    
    def get_zones(self, idf):
        """Get all zones from IDF"""
        return [z.Name for z in idf.idfobjects.get('ZONE', [])]
    
    def get_hvac_systems(self, idf):
        """Get all HVAC systems"""
        systems = {}
        vrf_systems = idf.idfobjects.get('HVACTEMPLATE:SYSTEM:VRF', [])
        systems['vrf'] = [s.Name for s in vrf_systems]
        return systems
    
    def get_summary(self, idf):
        """Get IDF summary"""
        return {
            'zones': self.get_zones(idf),
            'vrf_systems': [s.Name for s in idf.idfobjects.get('HVACTEMPLATE:SYSTEM:VRF', [])],
            'thermostats': [t.Name for t in idf.idfobjects.get('HVACTEMPLATE:THERMOSTAT', [])],
            'hvac_assignments': self._get_hvac_assignments(idf)
        }
    
    def _get_hvac_assignments(self, idf):
        """Get HVAC zone assignments"""
        assignments = []
        vrf_zones = idf.idfobjects.get('HVACTEMPLATE:ZONE:VRF', [])
        for vz in vrf_zones:
            assignments.append({
                'zone': vz.Zone_Name,
                'system': vz.Template_VRF_System_Name,
                'thermostat': vz.Template_Thermostat_Name
            })
        return assignments
