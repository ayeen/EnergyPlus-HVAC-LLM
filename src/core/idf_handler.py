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
    
    def extract_building_context(self, idf):
        """
        Extract comprehensive building context for LLM-based generation.
        
        Args:
            idf: Loaded IDF object
            
        Returns:
            dict: Building metadata including zones, area, orientation, loads, etc.
            {
                'num_zones': int,
                'zone_names': List[str],
                'total_area': float,  # m²
                'total_volume': float,  # m³
                'orientation': float,  # degrees
                'has_internal_loads': bool,
                'has_people': bool,
                'has_lights': bool,
                'has_equipment': bool,
                'construction_type': str,
                'weather_file': str,
            }
        """
        zones = self.get_zones(idf)
        
        # Calculate total floor area and volume
        total_area = 0
        total_volume = 0
        zone_objects = idf.idfobjects.get('ZONE', [])
        
        for zone in zone_objects:
            # Try to get floor area (may not be explicitly set)
            if hasattr(zone, 'Floor_Area') and zone.Floor_Area:
                try:
                    total_area += float(zone.Floor_Area)
                except (ValueError, TypeError):
                    pass
            
            # Try to get volume
            if hasattr(zone, 'Volume') and zone.Volume:
                try:
                    total_volume += float(zone.Volume)
                except (ValueError, TypeError):
                    pass
        
        # Get building orientation
        orientation = 0
        building_objs = idf.idfobjects.get('BUILDING', [])
        if building_objs:
            building = building_objs[0]
            if hasattr(building, 'North_Axis') and building.North_Axis:
                try:
                    orientation = float(building.North_Axis)
                except (ValueError, TypeError):
                    pass
        
        # Check for internal loads
        has_people = len(idf.idfobjects.get('PEOPLE', [])) > 0
        has_lights = len(idf.idfobjects.get('LIGHTS', [])) > 0
        has_equipment = len(idf.idfobjects.get('ELECTRICEQUIPMENT', [])) > 0
        
        # Get construction type (if available)
        construction_type = "Unknown"
        construction_objs = idf.idfobjects.get('CONSTRUCTION', [])
        if construction_objs:
            construction_type = f"{len(construction_objs)} constructions defined"
        
        # Get weather file reference (if available)
        weather_file = "Not specified"
        site_location = idf.idfobjects.get('SITE:LOCATION', [])
        if site_location:
            weather_file = site_location[0].Name if hasattr(site_location[0], 'Name') else "Not specified"
        
        return {
            'num_zones': len(zones),
            'zone_names': zones,
            'total_area': total_area,
            'total_volume': total_volume,
            'orientation': orientation,
            'has_internal_loads': has_people or has_lights or has_equipment,
            'has_people': has_people,
            'has_lights': has_lights,
            'has_equipment': has_equipment,
            'construction_type': construction_type,
            'weather_file': weather_file,
        }
    
    def validate_zones(self, idf, requested_zones):
        """
        Validate that requested zones exist in the IDF.
        
        Args:
            idf: Loaded IDF object
            requested_zones: List of zone names to validate
            
        Returns:
            bool: True if all zones are valid
            
        Raises:
            ValueError: If any requested zone is not found in IDF
        """
        available = self.get_zones(idf)
        available_set = set(available)
        requested_set = set(requested_zones)
        
        invalid = requested_set - available_set
        
        if invalid:
            raise ValueError(
                f"❌ Zones not found in IDF: {sorted(invalid)}\n"
                f"✓ Available zones: {sorted(available)}"
            )
        
        return True
    
    def validate_base_idf(self, idf):
        """
        Check if base IDF is suitable for HVAC generation.
        
        Args:
            idf: Loaded IDF object
            
        Returns:
            List[str]: List of validation issues (empty if valid)
        """
        issues = []
        
        # Check 1: Has zones
        zones = self.get_zones(idf)
        if not zones:
            issues.append("❌ No zones found in IDF")
        
        # Check 2: No existing HVAC templates (should use clean base)
        if idf.idfobjects.get('HVACTEMPLATE:SYSTEM:VRF'):
            issues.append("⚠ IDF already has VRF system (recommend using clean base IDF)")
        
        if idf.idfobjects.get('HVACTEMPLATE:ZONE:VRF'):
            issues.append("⚠ IDF already has VRF zone assignments (recommend using clean base IDF)")
        
        # Check 3: Has simulation control
        if not idf.idfobjects.get('SIMULATIONCONTROL'):
            issues.append("⚠ Missing SimulationControl object (may affect sizing)")
        
        # Check 4: Recommend having internal loads
        has_loads = (len(idf.idfobjects.get('PEOPLE', [])) > 0 or 
                    len(idf.idfobjects.get('LIGHTS', [])) > 0 or 
                    len(idf.idfobjects.get('ELECTRICEQUIPMENT', [])) > 0)
        
        if not has_loads:
            issues.append("⚠ No internal loads found (People, Lights, Equipment). May affect HVAC sizing.")
        
        return issues
