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
    
    # Zone name substrings (case-insensitive) that identify zones which should NOT
    # receive a VRF terminal unit.  Derived from a full audit of all 16 DOE/ASHRAE
    # prototype buildings in data/base_idfs/FinaIDF/:
    #
    #   plenum       — return/supply air plenums (MediumOffice, OfficeLarge)
    #                  Adding VRF to a plenum causes an EnergyPlus segfault during
    #                  daylighting factor initialisation.
    #   attic        — unconditioned roof spaces (Restaurant*, SmallOffice)
    #   stair        — stairwells (SmallHotel, HealthCare)
    #   mech         — mechanical/plant rooms (SmallHotel MechanicalRoomFlr*,
    #                  LargeHotel Mech_Flr_*, Schools Mech_ZN_*,
    #                  HealthCare Floor 3 Mechanical*)
    #   elevatorcore — elevator shaft/core (SmallHotel ElevatorCoreFlr*)
    #   elevator pump— elevator pump room (HealthCare Floor 1 Elevator Pump Room)
    #   back_space   — retail back-of-house storage (RetailStandalone)
    #   undeveloped  — unfinished shell space (HealthCare Floor 3 Undeveloped*)
    _NON_HVAC_ZONE_KEYWORDS = (
        'plenum',
        'attic',
        'stair',
        'mech',
        'elevatorcore',
        'elevator pump',
        'back_space',
        'undeveloped',
    )

    def get_zones(self, idf):
        """
        Return conditioned zone names from the IDF, excluding zones that should
        not receive a VRF terminal (plenums, attics, stairwells, mechanical rooms,
        elevator shafts, retail back spaces, undeveloped shells).

        Zones are identified by case-insensitive substring match against
        _NON_HVAC_ZONE_KEYWORDS.  Prints a one-line report of excluded zones so
        unexpected exclusions are visible in the pipeline log.
        """
        excluded_kw = self._NON_HVAC_ZONE_KEYWORDS
        all_zones   = [z.Name for z in idf.idfobjects.get('ZONE', [])]
        excluded    = [z for z in all_zones
                       if any(kw in z.lower() for kw in excluded_kw)]
        kept        = [z for z in all_zones if z not in excluded]
        if excluded:
            print(f"  ↳ Excluded {len(excluded)} non-HVAC zone(s): {excluded}")
        return kept
    
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
                'idf_zones': str,  # Raw IDF text of Zone objects for Mistral
            }
        """
        zones = self.get_zones(idf)
        
        # Calculate total floor area and volume
        total_area = 0
        total_volume = 0
        zone_objects = idf.idfobjects.get('ZONE', [])
        
        # Collect raw IDF zone text for Mistral fine-tuned model
        idf_zones_text = ""
        building_objs = idf.idfobjects.get('BUILDING', [])
        if building_objs:
            idf_zones_text += str(building_objs[0]) + "\n\n"
        
        for zone in zone_objects:
            idf_zones_text += str(zone) + "\n\n"
            
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
            'idf_zones': idf_zones_text.strip(),
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
    
    def enable_sizing(self, idf):
        """
        Enable zone and system sizing in SimulationControl for autosizing HVAC.
        
        Args:
            idf: Loaded IDF object
            
        Returns:
            bool: True if sizing was enabled
        """
        sim_controls = idf.idfobjects.get('SIMULATIONCONTROL', [])
        if sim_controls:
            sim_control = sim_controls[0]
            sim_control.Do_Zone_Sizing_Calculation = 'Yes'
            sim_control.Do_System_Sizing_Calculation = 'Yes'
            sim_control.Do_Plant_Sizing_Calculation = 'Yes'
            return True
        return False
    
    def _generate_zone_geometry(self, idf, zone_names, width=10.0, depth=10.0, height=3.0):
        """
        Generate basic rectangular geometry (6 surfaces) for zones without geometry.
        
        Creates a simple shoebox geometry with:
        - 1 Floor
        - 4 Walls (North, East, South, West)
        - 1 Roof
        
        Args:
            idf: Loaded IDF object
            zone_names: List of zone names to generate geometry for
            width: Zone width in meters (X direction, default 10m)
            depth: Zone depth in meters (Y direction, default 10m)  
            height: Zone height in meters (Z direction, default 3m)
            
        Returns:
            int: Number of surfaces generated
        """
        surfaces_created = 0
        
        # Also need GlobalGeometryRules if not present
        if not idf.idfobjects.get('GLOBALGEOMETRYRULES'):
            ggr = idf.newidfobject('GLOBALGEOMETRYRULES')
            ggr.Starting_Vertex_Position = 'UpperLeftCorner'
            ggr.Vertex_Entry_Direction = 'Counterclockwise'
            ggr.Coordinate_System = 'World'
        
        for i, zone_name in enumerate(zone_names):
            # Use default dimensions - will be updated per zone if valid data exists
            zone_width = width
            zone_depth = depth
            zone_height = height
            
            # Offset each zone to avoid overlap
            x_offset = i * (zone_width + 2)  # 2m gap between zones
            y_offset = 0
            z_offset = 0
            
            # Try to get zone volume for sizing, but enforce reasonable minimums
            zone_objs = [z for z in idf.idfobjects.get('ZONE', []) if z.Name == zone_name]
            if zone_objs:
                zone = zone_objs[0]
                # Try to infer dimensions from volume if available and reasonable
                vol = getattr(zone, 'Volume', None)
                if vol and vol != '':
                    try:
                        vol = float(vol)
                        # Only use zone volume if it's a reasonable size (at least 30 m³)
                        if vol >= 30:
                            # Assume square floor plan
                            zone_height = 3.0
                            floor_area = vol / zone_height
                            zone_width = zone_depth = (floor_area ** 0.5)
                        # Otherwise use defaults (10x10x3 = 300 m³)
                    except (ValueError, TypeError):
                        pass
            
            # Update x_offset with actual zone width (in case it changed)
            x_offset = i * (zone_width + 2)
            
            # Define the 8 corner vertices of the zone box
            # Floor corners (z = 0)
            v0 = (x_offset, y_offset, z_offset)                      # SW bottom
            v1 = (x_offset + zone_width, y_offset, z_offset)         # SE bottom
            v2 = (x_offset + zone_width, y_offset + zone_depth, z_offset)  # NE bottom
            v3 = (x_offset, y_offset + zone_depth, z_offset)         # NW bottom
            
            # Ceiling corners (z = zone_height)
            v4 = (x_offset, y_offset, z_offset + zone_height)             # SW top
            v5 = (x_offset + zone_width, y_offset, z_offset + zone_height)     # SE top
            v6 = (x_offset + zone_width, y_offset + zone_depth, z_offset + zone_height)  # NE top
            v7 = (x_offset, y_offset + zone_depth, z_offset + zone_height)     # NW top
            
            # Create Floor (outward normal should point down for a floor)
            # Vertices counterclockwise when viewed from BELOW (i.e., clockwise from above)
            floor = idf.newidfobject('BUILDINGSURFACE:DETAILED')
            floor.Name = f'{zone_name}_Floor'
            floor.Surface_Type = 'Floor'
            floor.Construction_Name = 'DefaultFloor'
            floor.Zone_Name = zone_name
            floor.Outside_Boundary_Condition = 'Ground'
            floor.Outside_Boundary_Condition_Object = ''
            floor.Sun_Exposure = 'NoSun'
            floor.Wind_Exposure = 'NoWind'
            floor.View_Factor_to_Ground = 1.0
            floor.Number_of_Vertices = 4
            # Clockwise from above = counterclockwise from below (looking up at floor from ground)
            floor.Vertex_1_Xcoordinate, floor.Vertex_1_Ycoordinate, floor.Vertex_1_Zcoordinate = v3  # NW
            floor.Vertex_2_Xcoordinate, floor.Vertex_2_Ycoordinate, floor.Vertex_2_Zcoordinate = v2  # NE
            floor.Vertex_3_Xcoordinate, floor.Vertex_3_Ycoordinate, floor.Vertex_3_Zcoordinate = v1  # SE
            floor.Vertex_4_Xcoordinate, floor.Vertex_4_Ycoordinate, floor.Vertex_4_Zcoordinate = v0  # SW
            surfaces_created += 1
            
            # Create Roof (outward normal should point up for a roof)
            # Vertices counterclockwise when viewed from above
            roof = idf.newidfobject('BUILDINGSURFACE:DETAILED')
            roof.Name = f'{zone_name}_Roof'
            roof.Surface_Type = 'Roof'
            roof.Construction_Name = 'DefaultRoof'
            roof.Zone_Name = zone_name
            roof.Outside_Boundary_Condition = 'Outdoors'
            roof.Outside_Boundary_Condition_Object = ''
            roof.Sun_Exposure = 'SunExposed'
            roof.Wind_Exposure = 'WindExposed'
            roof.View_Factor_to_Ground = 0.0
            roof.Number_of_Vertices = 4
            # Counterclockwise from above (looking down at roof from sky)
            roof.Vertex_1_Xcoordinate, roof.Vertex_1_Ycoordinate, roof.Vertex_1_Zcoordinate = v4  # SW top
            roof.Vertex_2_Xcoordinate, roof.Vertex_2_Ycoordinate, roof.Vertex_2_Zcoordinate = v5  # SE top
            roof.Vertex_3_Xcoordinate, roof.Vertex_3_Ycoordinate, roof.Vertex_3_Zcoordinate = v6  # NE top
            roof.Vertex_4_Xcoordinate, roof.Vertex_4_Ycoordinate, roof.Vertex_4_Zcoordinate = v7  # NW top
            surfaces_created += 1
            
            # Create South Wall (facing south, outdoor)
            south_wall = idf.newidfobject('BUILDINGSURFACE:DETAILED')
            south_wall.Name = f'{zone_name}_Wall_South'
            south_wall.Surface_Type = 'Wall'
            south_wall.Construction_Name = 'DefaultWall'
            south_wall.Zone_Name = zone_name
            south_wall.Outside_Boundary_Condition = 'Outdoors'
            south_wall.Outside_Boundary_Condition_Object = ''
            south_wall.Sun_Exposure = 'SunExposed'
            south_wall.Wind_Exposure = 'WindExposed'
            south_wall.View_Factor_to_Ground = 0.5
            south_wall.Number_of_Vertices = 4
            south_wall.Vertex_1_Xcoordinate, south_wall.Vertex_1_Ycoordinate, south_wall.Vertex_1_Zcoordinate = v4
            south_wall.Vertex_2_Xcoordinate, south_wall.Vertex_2_Ycoordinate, south_wall.Vertex_2_Zcoordinate = v5
            south_wall.Vertex_3_Xcoordinate, south_wall.Vertex_3_Ycoordinate, south_wall.Vertex_3_Zcoordinate = v1
            south_wall.Vertex_4_Xcoordinate, south_wall.Vertex_4_Ycoordinate, south_wall.Vertex_4_Zcoordinate = v0
            surfaces_created += 1
            
            # Create East Wall
            east_wall = idf.newidfobject('BUILDINGSURFACE:DETAILED')
            east_wall.Name = f'{zone_name}_Wall_East'
            east_wall.Surface_Type = 'Wall'
            east_wall.Construction_Name = 'DefaultWall'
            east_wall.Zone_Name = zone_name
            east_wall.Outside_Boundary_Condition = 'Outdoors'
            east_wall.Outside_Boundary_Condition_Object = ''
            east_wall.Sun_Exposure = 'SunExposed'
            east_wall.Wind_Exposure = 'WindExposed'
            east_wall.View_Factor_to_Ground = 0.5
            east_wall.Number_of_Vertices = 4
            east_wall.Vertex_1_Xcoordinate, east_wall.Vertex_1_Ycoordinate, east_wall.Vertex_1_Zcoordinate = v5
            east_wall.Vertex_2_Xcoordinate, east_wall.Vertex_2_Ycoordinate, east_wall.Vertex_2_Zcoordinate = v6
            east_wall.Vertex_3_Xcoordinate, east_wall.Vertex_3_Ycoordinate, east_wall.Vertex_3_Zcoordinate = v2
            east_wall.Vertex_4_Xcoordinate, east_wall.Vertex_4_Ycoordinate, east_wall.Vertex_4_Zcoordinate = v1
            surfaces_created += 1
            
            # Create North Wall
            north_wall = idf.newidfobject('BUILDINGSURFACE:DETAILED')
            north_wall.Name = f'{zone_name}_Wall_North'
            north_wall.Surface_Type = 'Wall'
            north_wall.Construction_Name = 'DefaultWall'
            north_wall.Zone_Name = zone_name
            north_wall.Outside_Boundary_Condition = 'Outdoors'
            north_wall.Outside_Boundary_Condition_Object = ''
            north_wall.Sun_Exposure = 'SunExposed'
            north_wall.Wind_Exposure = 'WindExposed'
            north_wall.View_Factor_to_Ground = 0.5
            north_wall.Number_of_Vertices = 4
            north_wall.Vertex_1_Xcoordinate, north_wall.Vertex_1_Ycoordinate, north_wall.Vertex_1_Zcoordinate = v6
            north_wall.Vertex_2_Xcoordinate, north_wall.Vertex_2_Ycoordinate, north_wall.Vertex_2_Zcoordinate = v7
            north_wall.Vertex_3_Xcoordinate, north_wall.Vertex_3_Ycoordinate, north_wall.Vertex_3_Zcoordinate = v3
            north_wall.Vertex_4_Xcoordinate, north_wall.Vertex_4_Ycoordinate, north_wall.Vertex_4_Zcoordinate = v2
            surfaces_created += 1
            
            # Create West Wall
            west_wall = idf.newidfobject('BUILDINGSURFACE:DETAILED')
            west_wall.Name = f'{zone_name}_Wall_West'
            west_wall.Surface_Type = 'Wall'
            west_wall.Construction_Name = 'DefaultWall'
            west_wall.Zone_Name = zone_name
            west_wall.Outside_Boundary_Condition = 'Outdoors'
            west_wall.Outside_Boundary_Condition_Object = ''
            west_wall.Sun_Exposure = 'SunExposed'
            west_wall.Wind_Exposure = 'WindExposed'
            west_wall.View_Factor_to_Ground = 0.5
            west_wall.Number_of_Vertices = 4
            west_wall.Vertex_1_Xcoordinate, west_wall.Vertex_1_Ycoordinate, west_wall.Vertex_1_Zcoordinate = v7
            west_wall.Vertex_2_Xcoordinate, west_wall.Vertex_2_Ycoordinate, west_wall.Vertex_2_Zcoordinate = v4
            west_wall.Vertex_3_Xcoordinate, west_wall.Vertex_3_Ycoordinate, west_wall.Vertex_3_Zcoordinate = v0
            west_wall.Vertex_4_Xcoordinate, west_wall.Vertex_4_Ycoordinate, west_wall.Vertex_4_Zcoordinate = v3
            surfaces_created += 1
            
            # Update zone Floor_Area and Volume based on generated geometry
            if zone_objs:
                zone = zone_objs[0]
                zone.Floor_Area = zone_width * zone_depth
                zone.Volume = zone_width * zone_depth * zone_height
        
        # Also need default constructions if not present
        self._ensure_default_constructions(idf)
        
        return surfaces_created
    
    def _ensure_default_constructions(self, idf):
        """
        Ensure default constructions exist for auto-generated geometry.
        
        Args:
            idf: Loaded IDF object
        """
        # Check if constructions already exist
        existing_constructions = {c.Name for c in idf.idfobjects.get('CONSTRUCTION', [])}
        existing_materials = {m.Name for m in idf.idfobjects.get('MATERIAL', [])}
        existing_materials.update({m.Name for m in idf.idfobjects.get('MATERIAL:NOMASS', [])})
        
        # Add default materials if needed
        if 'DefaultWallMaterial' not in existing_materials:
            mat = idf.newidfobject('MATERIAL')
            mat.Name = 'DefaultWallMaterial'
            mat.Roughness = 'MediumRough'
            mat.Thickness = 0.2
            mat.Conductivity = 0.9
            mat.Density = 1800
            mat.Specific_Heat = 900
        
        if 'DefaultRoofMaterial' not in existing_materials:
            mat = idf.newidfobject('MATERIAL')
            mat.Name = 'DefaultRoofMaterial'
            mat.Roughness = 'MediumRough'
            mat.Thickness = 0.15
            mat.Conductivity = 0.8
            mat.Density = 1600
            mat.Specific_Heat = 900
        
        if 'DefaultFloorMaterial' not in existing_materials:
            mat = idf.newidfobject('MATERIAL')
            mat.Name = 'DefaultFloorMaterial'
            mat.Roughness = 'MediumRough'
            mat.Thickness = 0.25
            mat.Conductivity = 1.5
            mat.Density = 2400
            mat.Specific_Heat = 900
        
        # Add default constructions if needed
        if 'DefaultWall' not in existing_constructions:
            const = idf.newidfobject('CONSTRUCTION')
            const.Name = 'DefaultWall'
            const.Outside_Layer = 'DefaultWallMaterial'
        
        if 'DefaultRoof' not in existing_constructions:
            const = idf.newidfobject('CONSTRUCTION')
            const.Name = 'DefaultRoof'
            const.Outside_Layer = 'DefaultRoofMaterial'
        
        if 'DefaultFloor' not in existing_constructions:
            const = idf.newidfobject('CONSTRUCTION')
            const.Name = 'DefaultFloor'
            const.Outside_Layer = 'DefaultFloorMaterial'
    
    def check_idd_compliance(self, idf, auto_fix=False):
        """
        Check IDD compliance for common object types and optionally fix issues.
        
        This validates that objects in the base IDF comply with EnergyPlus IDD rules,
        which is crucial for successful simulation.
        
        Args:
            idf: Loaded IDF object
            auto_fix: If True, attempt to automatically fix detected issues
            
        Returns:
            dict: {
                'compliant': bool,
                'issues': List[dict],  # Each with 'object', 'field', 'issue', 'severity', 'fix_applied'
                'warnings': List[str],
                'fixes_applied': List[str],
                'summary': str
            }
        """
        issues = []
        warnings = []
        fixes_applied = []
        
        # ==== ZONE VALIDATION ====
        for zone in idf.idfobjects.get('ZONE', []):
            zone_name = zone.Name if hasattr(zone, 'Name') else 'Unknown'
            
            # Zone Type must be 0 or 1 (1 is default, >1 is invalid per IDD)
            if hasattr(zone, 'Type'):
                try:
                    zone_type = int(zone.Type) if zone.Type else 1
                    if zone_type > 1:
                        issue = {
                            'object': f'Zone: {zone_name}',
                            'field': 'Type',
                            'issue': f'Zone Type = {zone_type}, but IDD maximum is 1',
                            'severity': 'error',
                            'fix_applied': False
                        }
                        if auto_fix:
                            zone.Type = 1
                            issue['fix_applied'] = True
                            fixes_applied.append(f"Fixed Zone '{zone_name}' Type: {zone_type} → 1")
                        issues.append(issue)
                except (ValueError, TypeError):
                    pass
        
        # ==== PEOPLE VALIDATION ====
        valid_people_methods = ['People', 'People/Area', 'Area/Person']
        # EnergyPlus v25.x renamed ZoneAveraged → EnclosureAveraged in the IDD
        valid_mrt_types = ['EnclosureAveraged', 'SurfaceWeighted', 'AngleFactor']
        deprecated_mrt_map = {'ZoneAveraged': 'EnclosureAveraged'}
        for people in idf.idfobjects.get('PEOPLE', []):
            people_name = people.Name if hasattr(people, 'Name') else 'Unknown'

            # Check Mean_Radiant_Temperature_Calculation_Type (v25.x renamed ZoneAveraged → EnclosureAveraged)
            mrt_type = getattr(people, 'Mean_Radiant_Temperature_Calculation_Type', None)
            if mrt_type and mrt_type in deprecated_mrt_map:
                new_mrt = deprecated_mrt_map[mrt_type]
                issue = {
                    'object': f'People: {people_name}',
                    'field': 'Mean_Radiant_Temperature_Calculation_Type',
                    'issue': f'Deprecated value "{mrt_type}" renamed to "{new_mrt}" in EnergyPlus v25.x IDD',
                    'severity': 'error',
                    'fix_applied': False
                }
                if auto_fix:
                    people.Mean_Radiant_Temperature_Calculation_Type = new_mrt
                    issue['fix_applied'] = True
                    fixes_applied.append(
                        f"Fixed People '{people_name}': Mean_Radiant_Temperature_Calculation_Type "
                        f"{mrt_type} → {new_mrt} (EnergyPlus v25.x IDD change)"
                    )
                issues.append(issue)

            # Must have valid Number_of_People_Calculation_Method
            calc_method = getattr(people, 'Number_of_People_Calculation_Method', None)
            if not calc_method or calc_method == '' or calc_method not in valid_people_methods:
                issue = {
                    'object': f'People: {people_name}',
                    'field': 'Number_of_People_Calculation_Method',
                    'issue': f'Invalid/missing calculation method "{calc_method}" (required: {valid_people_methods})',
                    'severity': 'error',
                    'fix_applied': False
                }
                if auto_fix:
                    people.Number_of_People_Calculation_Method = 'People'
                    # Also set Number_of_People if not set
                    num_people = getattr(people, 'Number_of_People', None)
                    if num_people is None or num_people == '':
                        people.Number_of_People = 4
                    issue['fix_applied'] = True
                    fixes_applied.append(f"Fixed People '{people_name}': Set calculation method to 'People'")
                issues.append(issue)
            elif calc_method == 'People':
                # If method is People, must have Number_of_People
                num_people = getattr(people, 'Number_of_People', None)
                if num_people is None or num_people == '':
                    issue = {
                        'object': f'People: {people_name}',
                        'field': 'Number_of_People',
                        'issue': 'Calculation method is "People" but Number_of_People is missing',
                        'severity': 'warning',
                        'fix_applied': False
                    }
                    if auto_fix:
                        people.Number_of_People = 4  # Reasonable default
                        issue['fix_applied'] = True
                        fixes_applied.append(f"Fixed People '{people_name}': Set Number_of_People to 4")
                    issues.append(issue)
            
            # Must have Activity_Level_Schedule_Name (required field)
            activity_schedule = getattr(people, 'Activity_Level_Schedule_Name', None)
            if not activity_schedule or activity_schedule == '':
                issue = {
                    'object': f'People: {people_name}',
                    'field': 'Activity_Level_Schedule_Name',
                    'issue': 'Missing required Activity_Level_Schedule_Name',
                    'severity': 'error',
                    'fix_applied': False
                }
                if auto_fix:
                    # Create a constant activity schedule if it doesn't exist
                    activity_sched_name = 'Activity_Schedule_120W'
                    existing_scheds = {s.Name for s in idf.idfobjects.get('SCHEDULE:CONSTANT', [])}
                    if activity_sched_name not in existing_scheds:
                        sched = idf.newidfobject('SCHEDULE:CONSTANT')
                        sched.Name = activity_sched_name
                        sched.Schedule_Type_Limits_Name = ''
                        sched.Hourly_Value = 120  # 120 W/person typical office activity
                    people.Activity_Level_Schedule_Name = activity_sched_name
                    issue['fix_applied'] = True
                    fixes_applied.append(f"Fixed People '{people_name}': Added Activity_Level_Schedule_Name")
                issues.append(issue)
        
        # ==== LIGHTS VALIDATION ====
        valid_lights_methods = ['LightingLevel', 'Watts/Area', 'Watts/Person']
        for lights in idf.idfobjects.get('LIGHTS', []):
            lights_name = lights.Name if hasattr(lights, 'Name') else 'Unknown'
            
            # Must have valid Design_Level_Calculation_Method
            calc_method = getattr(lights, 'Design_Level_Calculation_Method', None)
            if not calc_method or calc_method == '' or calc_method not in valid_lights_methods:
                issue = {
                    'object': f'Lights: {lights_name}',
                    'field': 'Design_Level_Calculation_Method',
                    'issue': f'Invalid/missing calculation method "{calc_method}" (required: {valid_lights_methods})',
                    'severity': 'error',
                    'fix_applied': False
                }
                if auto_fix:
                    lights.Design_Level_Calculation_Method = 'LightingLevel'
                    # Also set Lighting_Level if not set
                    level = getattr(lights, 'Lighting_Level', None)
                    if level is None or level == '':
                        lights.Lighting_Level = 500
                    issue['fix_applied'] = True
                    fixes_applied.append(f"Fixed Lights '{lights_name}': Set calculation method to 'LightingLevel'")
                issues.append(issue)
            elif calc_method == 'LightingLevel':
                # If method is LightingLevel, must have Lighting_Level
                level = getattr(lights, 'Lighting_Level', None)
                if level is None or level == '':
                    issue = {
                        'object': f'Lights: {lights_name}',
                        'field': 'Lighting_Level',
                        'issue': 'Calculation method is "LightingLevel" but Lighting_Level is missing',
                        'severity': 'warning',
                        'fix_applied': False
                    }
                    if auto_fix:
                        lights.Lighting_Level = 500  # Reasonable default (W)
                        issue['fix_applied'] = True
                        fixes_applied.append(f"Fixed Lights '{lights_name}': Set Lighting_Level to 500W")
                    issues.append(issue)
        
        # ==== ELECTRICEQUIPMENT VALIDATION ====
        valid_equip_methods = ['EquipmentLevel', 'Watts/Area', 'Watts/Person']
        for equip in idf.idfobjects.get('ELECTRICEQUIPMENT', []):
            equip_name = equip.Name if hasattr(equip, 'Name') else 'Unknown'
            
            # Must have valid Design_Level_Calculation_Method
            calc_method = getattr(equip, 'Design_Level_Calculation_Method', None)
            if not calc_method or calc_method == '' or calc_method not in valid_equip_methods:
                issue = {
                    'object': f'ElectricEquipment: {equip_name}',
                    'field': 'Design_Level_Calculation_Method',
                    'issue': f'Invalid/missing calculation method "{calc_method}" (required: {valid_equip_methods})',
                    'severity': 'error',
                    'fix_applied': False
                }
                if auto_fix:
                    equip.Design_Level_Calculation_Method = 'EquipmentLevel'
                    # Also set Design_Level if not set
                    level = getattr(equip, 'Design_Level', None)
                    if level is None or level == '':
                        equip.Design_Level = 1000
                    issue['fix_applied'] = True
                    fixes_applied.append(f"Fixed ElectricEquipment '{equip_name}': Set calculation method to 'EquipmentLevel'")
                issues.append(issue)
            elif calc_method == 'EquipmentLevel':
                # If method is EquipmentLevel, must have Design_Level
                level = getattr(equip, 'Design_Level', None)
                if level is None or level == '':
                    issue = {
                        'object': f'ElectricEquipment: {equip_name}',
                        'field': 'Design_Level',
                        'issue': 'Calculation method is "EquipmentLevel" but Design_Level is missing',
                        'severity': 'warning',
                        'fix_applied': False
                    }
                    if auto_fix:
                        equip.Design_Level = 1000  # Reasonable default (W)
                        issue['fix_applied'] = True
                        fixes_applied.append(f"Fixed ElectricEquipment '{equip_name}': Set Design_Level to 1000W")
                    issues.append(issue)
        
        # ==== SIMULATIONCONTROL VALIDATION ====
        sim_controls = idf.idfobjects.get('SIMULATIONCONTROL', [])
        if not sim_controls:
            issue = {
                'object': 'SimulationControl',
                'field': 'N/A',
                'issue': 'Missing SimulationControl object (required for sizing calculations)',
                'severity': 'error',
                'fix_applied': False
            }
            if auto_fix:
                new_sim = idf.newidfobject('SIMULATIONCONTROL')
                new_sim.Do_Zone_Sizing_Calculation = 'Yes'
                new_sim.Do_System_Sizing_Calculation = 'Yes'
                new_sim.Do_Plant_Sizing_Calculation = 'Yes'
                new_sim.Run_Simulation_for_Sizing_Periods = 'Yes'
                new_sim.Run_Simulation_for_Weather_File_Run_Periods = 'Yes'
                issue['fix_applied'] = True
                fixes_applied.append("Added SimulationControl object with sizing enabled")
            issues.append(issue)
        
        # ==== SITE:LOCATION VALIDATION ====
        site_locations = idf.idfobjects.get('SITE:LOCATION', [])
        if not site_locations:
            issue = {
                'object': 'Site:Location',
                'field': 'N/A',
                'issue': 'Missing Site:Location object (required for simulation)',
                'severity': 'error',
                'fix_applied': False
            }
            if auto_fix:
                # Add default Chicago location
                site = idf.newidfobject('SITE:LOCATION')
                site.Name = 'Chicago_IL_USA'
                site.Latitude = 41.88
                site.Longitude = -87.63
                site.Time_Zone = -6.0
                site.Elevation = 190
                issue['fix_applied'] = True
                fixes_applied.append("Added default Site:Location (Chicago, IL)")
            issues.append(issue)
        
        # ==== DESIGN DAY VALIDATION ====
        design_days = idf.idfobjects.get('SIZINGPERIOD:DESIGNDAY', [])
        if not design_days:
            issue = {
                'object': 'SizingPeriod:DesignDay',
                'field': 'N/A',
                'issue': 'No design days found (required for HVAC sizing)',
                'severity': 'error',
                'fix_applied': False
            }
            if auto_fix:
                # Add default Chicago design days (common for testing)
                winter_dd = idf.newidfobject('SIZINGPERIOD:DESIGNDAY')
                winter_dd.Name = 'Chicago_Winter_Design_Day'
                winter_dd.Month = 1
                winter_dd.Day_of_Month = 21
                winter_dd.Day_Type = 'WinterDesignDay'
                winter_dd.Maximum_DryBulb_Temperature = -17.3
                winter_dd.Daily_DryBulb_Temperature_Range = 0
                winter_dd.DryBulb_Temperature_Range_Modifier_Type = ''
                winter_dd.Humidity_Condition_Type = 'Wetbulb'
                winter_dd.Wetbulb_or_DewPoint_at_Maximum_DryBulb = -17.3
                winter_dd.Barometric_Pressure = 99063
                winter_dd.Wind_Speed = 4.9
                winter_dd.Wind_Direction = 270
                
                summer_dd = idf.newidfobject('SIZINGPERIOD:DESIGNDAY')
                summer_dd.Name = 'Chicago_Summer_Design_Day'
                summer_dd.Month = 7
                summer_dd.Day_of_Month = 21
                summer_dd.Day_Type = 'SummerDesignDay'
                summer_dd.Maximum_DryBulb_Temperature = 33.3
                summer_dd.Daily_DryBulb_Temperature_Range = 10.7
                summer_dd.DryBulb_Temperature_Range_Modifier_Type = ''
                summer_dd.Humidity_Condition_Type = 'Wetbulb'
                summer_dd.Wetbulb_or_DewPoint_at_Maximum_DryBulb = 23.8
                summer_dd.Barometric_Pressure = 99063
                summer_dd.Wind_Speed = 5.3
                summer_dd.Wind_Direction = 230
                
                issue['fix_applied'] = True
                fixes_applied.append("Added default design days (Chicago winter/summer)")
            issues.append(issue)
        
        # ==== BUILDING SURFACE VALIDATION ====
        surfaces = idf.idfobjects.get('BUILDINGSURFACE:DETAILED', [])
        zones = idf.idfobjects.get('ZONE', [])
        
        # Check which zones have geometry
        zones_with_surfaces = set()
        for surface in surfaces:
            zone_name = getattr(surface, 'Zone_Name', None)
            if zone_name:
                zones_with_surfaces.add(zone_name)
        
        zones_without_geometry = []
        for zone in zones:
            zone_name = zone.Name if hasattr(zone, 'Name') else None
            if zone_name and zone_name not in zones_with_surfaces:
                zones_without_geometry.append(zone_name)
        
        if zones_without_geometry:
            issue = {
                'object': 'BuildingSurface:Detailed',
                'field': 'N/A',
                'issue': f'Missing geometry for zones: {", ".join(zones_without_geometry)}',
                'severity': 'error',
                'fix_applied': False
            }
            if auto_fix:
                # Generate basic rectangular geometry for each zone without surfaces
                generated_count = self._generate_zone_geometry(idf, zones_without_geometry)
                if generated_count > 0:
                    issue['fix_applied'] = True
                    fixes_applied.append(f"Generated basic geometry for {len(zones_without_geometry)} zone(s): {', '.join(zones_without_geometry)}")
            issues.append(issue)
        elif not surfaces:
            warnings.append("No BuildingSurface:Detailed objects found - may need geometry")
        
        # Validate existing surfaces
        for surface in surfaces:
                surface_name = surface.Name if hasattr(surface, 'Name') else 'Unknown'
                
                # Check surface type
                surface_type = getattr(surface, 'Surface_Type', None)
                valid_types = ['Floor', 'Wall', 'Ceiling', 'Roof']
                if surface_type and surface_type not in valid_types:
                    issue = {
                        'object': f'BuildingSurface:Detailed: {surface_name}',
                        'field': 'Surface_Type',
                        'issue': f'Invalid surface type "{surface_type}". Valid: {valid_types}',
                        'severity': 'error',
                        'fix_applied': False
                    }
                    issues.append(issue)
        
        # ==== RUNPERIOD VALIDATION ====
        # Note: EnergyPlus 25.2 doesn't accept 'UseWeatherFile' for Day_of_Week_for_Start_Day
        valid_day_of_week = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        run_periods = idf.idfobjects.get('RUNPERIOD', [])
        for rp in run_periods:
            rp_name = rp.Name if hasattr(rp, 'Name') else 'Unknown'
            needs_rebuild = False
            
            # Check for valid month values
            for field in ['Begin_Month', 'End_Month']:
                val = getattr(rp, field, None)
                if val is not None and val != '':
                    try:
                        month = int(val)
                        if month < 1 or month > 12:
                            needs_rebuild = True
                            issue = {
                                'object': f'RunPeriod: {rp_name}',
                                'field': field,
                                'issue': f'{field} = {val}, must be 1-12',
                                'severity': 'error',
                                'fix_applied': False
                            }
                            issues.append(issue)
                    except (ValueError, TypeError):
                        needs_rebuild = True
                        issue = {
                            'object': f'RunPeriod: {rp_name}',
                            'field': field,
                            'issue': f'{field} = "{val}" is not a valid integer (1-12)',
                            'severity': 'error',
                            'fix_applied': False
                        }
                        issues.append(issue)
            
            # Check for valid day values
            for field in ['Begin_Day_of_Month', 'End_Day_of_Month']:
                val = getattr(rp, field, None)
                if val is not None and val != '':
                    try:
                        day = int(val)
                        if day < 1 or day > 31:
                            needs_rebuild = True
                    except (ValueError, TypeError):
                        needs_rebuild = True
                        issue = {
                            'object': f'RunPeriod: {rp_name}',
                            'field': field,
                            'issue': f'{field} = "{val}" is not a valid integer (1-31)',
                            'severity': 'error',
                            'fix_applied': False
                        }
                        issues.append(issue)
            
            # Check Day_of_Week_for_Start_Day
            dow = getattr(rp, 'Day_of_Week_for_Start_Day', None)
            if dow is not None and dow != '' and dow not in valid_day_of_week:
                needs_rebuild = True
                issue = {
                    'object': f'RunPeriod: {rp_name}',
                    'field': 'Day_of_Week_for_Start_Day',
                    'issue': f'Invalid value "{dow}". Valid: {valid_day_of_week}',
                    'severity': 'error',
                    'fix_applied': False
                }
                issues.append(issue)
            
            # If RunPeriod is malformed, rebuild it
            if needs_rebuild and auto_fix:
                # Remove the bad run period
                idf.removeidfobject(rp)
                
                # Create a proper one (EnergyPlus 25.2 compatible)
                new_rp = idf.newidfobject('RUNPERIOD')
                new_rp.Name = rp_name if rp_name != 'Unknown' else 'Annual'
                new_rp.Begin_Month = 1
                new_rp.Begin_Day_of_Month = 1
                new_rp.End_Month = 12
                new_rp.End_Day_of_Month = 31
                new_rp.Day_of_Week_for_Start_Day = 'Sunday'  # Use actual day, not UseWeatherFile
                new_rp.Use_Weather_File_Holidays_and_Special_Days = 'Yes'
                new_rp.Use_Weather_File_Daylight_Saving_Period = 'Yes'
                new_rp.Apply_Weekend_Holiday_Rule = 'No'
                new_rp.Use_Weather_File_Rain_Indicators = 'Yes'
                new_rp.Use_Weather_File_Snow_Indicators = 'Yes'
                
                # Mark issues as fixed
                for issue in issues:
                    if 'RunPeriod' in issue.get('object', ''):
                        issue['fix_applied'] = True
                fixes_applied.append(f"Rebuilt RunPeriod '{rp_name}' with valid fields")
        
        # ==== BUILD SUMMARY ====
        error_count = sum(1 for i in issues if i['severity'] == 'error' and not i.get('fix_applied'))
        warning_count = sum(1 for i in issues if i['severity'] == 'warning' and not i.get('fix_applied'))
        
        if error_count == 0 and warning_count == 0:
            summary = "✅ IDF is IDD-compliant. No issues detected."
        elif error_count == 0:
            summary = f"⚠ IDF has {warning_count} warning(s) but is simulation-ready."
        else:
            summary = f"❌ IDF has {error_count} error(s) and {warning_count} warning(s). Fix before simulation."
        
        if fixes_applied:
            summary += f"\n🔧 Auto-fixed {len(fixes_applied)} issue(s)."
        
        return {
            'compliant': error_count == 0,
            'issues': issues,
            'warnings': warnings,
            'fixes_applied': fixes_applied,
            'summary': summary
        }
    
    def print_compliance_report(self, compliance_result):
        """
        Print a formatted compliance report.
        
        Args:
            compliance_result: Result from check_idd_compliance()
        """
        print("\n" + "="*60)
        print("IDD COMPLIANCE REPORT")
        print("="*60)
        
        print(f"\n{compliance_result['summary']}\n")
        
        if compliance_result['issues']:
            print("-"*60)
            print("ISSUES FOUND:")
            print("-"*60)
            for i, issue in enumerate(compliance_result['issues'], 1):
                status = "✅ FIXED" if issue.get('fix_applied') else ("❌ ERROR" if issue['severity'] == 'error' else "⚠ WARNING")
                print(f"\n{i}. [{status}] {issue['object']}")
                print(f"   Field: {issue['field']}")
                print(f"   Issue: {issue['issue']}")
        
        if compliance_result['warnings']:
            print("-"*60)
            print("GENERAL WARNINGS:")
            print("-"*60)
            for w in compliance_result['warnings']:
                print(f"  ⚠ {w}")
        
        if compliance_result['fixes_applied']:
            print("-"*60)
            print("FIXES APPLIED:")
            print("-"*60)
            for fix in compliance_result['fixes_applied']:
                print(f"  🔧 {fix}")
        
        print("\n" + "="*60)

    @staticmethod
    def upgrade_idf_for_v25(text: str) -> str:
        """
        Upgrade IDF text to EnergyPlus 25.2 field format.

        EnergyPlus 25.2 added new fields to several object types compared to older IDDs.
        IDFs created without these fields have a field-offset mismatch when parsed positionally.

        Fixes applied:
        1. BuildingSurface:Detailed – insert blank Space Name (A5) between Zone Name and
           Outside Boundary Condition.
        2. People – insert blank Sensible Heat Fraction (N5) between Fraction Radiant and
           Activity Level Schedule Name.
        3. ThermostatSetpoint:DualSetpoint – remove any extra (4th+) data fields that exceed
           the IDD maximum of 3.
        """
        import re

        # ── 1. BuildingSurface:Detailed ──────────────────────────────────────────
        # After Zone Name (A4, comment "!- Zone Name"), the next field is either
        # Space Name (A5, new) or Outside BC (A5 in old IDDs).
        # We detect the old format by checking whether the value immediately after
        # "Zone Name" is a recognised Outside BC enum, and if so insert a blank field.

        BC_VALUES = (
            'Adiabatic', 'Surface', 'Zone', 'Space', 'Outdoors', 'Foundation', 'Ground',
            'GroundFCfactorMethod', 'OtherSideCoefficients', 'OtherSideConditionsModel',
            'GroundSlabPreprocessorAverage', 'GroundSlabPreprocessorCore',
            'GroundSlabPreprocessorPerimeter', 'GroundBasementPreprocessorAverageWall',
            'GroundBasementPreprocessorAverageFloor', 'GroundBasementPreprocessorUpperWall',
            'GroundBasementPreprocessorLowerWall',
        )
        bc_alt = '(?:' + '|'.join(re.escape(v) for v in BC_VALUES) + ')'

        def fix_bsd(match):
            obj = match.group(0)
            # Insert blank Space Name where Zone Name comment is followed by a BC value
            return re.sub(
                r'(!-[^\n]*\bZone\s+Name\b[^\n]*\n)(\s*)(' + bc_alt + r')(,)',
                r'\1\2,                                        !- Space Name\n\2\3\4',
                obj,
                flags=re.IGNORECASE,
            )

        text = re.sub(r'BuildingSurface:Detailed,[\s\S]*?;', fix_bsd, text)

        # ── 2. People ────────────────────────────────────────────────────────────
        # Old IDD: Name(1) Zone(2) Sched(3) Method(4) Num(5) PPA(6) FAP(7)
        #          FracRad(8) ActivitySched(9)                            = 9 data fields
        # New IDD: same + SensibleHeatFraction(9) ActivitySched(10)      = 10 data fields
        # Detect old format: exactly 9 data fields (10 tokens including "People" type).

        def fix_people(match):
            obj = match.group(0)
            # Split preserving separators
            tokens = re.split(r'([,;])', obj)
            values = [tokens[i] for i in range(0, len(tokens), 2) if i < len(tokens)]
            seps   = [tokens[i] for i in range(1, len(tokens), 2)]

            if len(values) == 11 and not values[-1].strip() and seps and seps[-1] == ';':
                # Insert blank SensibleHeatFraction between FractionRadiant (idx 8) and
                # ActivitySchedule (idx 9 → now 10).
                values.insert(9, ' ')
                seps.insert(8, ',')

            result = ''
            for v, s in zip(values, seps):
                result += v + s
            if len(values) > len(seps):
                result += values[-1]
            return result

        text = re.sub(r'\bPeople,[\s\S]*?;', fix_people, text, flags=re.IGNORECASE)

        # ── 3. ThermostatSetpoint:DualSetpoint ───────────────────────────────────
        # IDD allows exactly 3 data fields (Name, HeatingSchedule, CoolingSchedule).
        # Some older IDFs include a spurious 4th field.  Remove any fields beyond the 3rd.
        text = re.sub(
            r'(ThermostatSetpoint:DualSetpoint,\s*[^,;]+,\s*[^,;]+,\s*[^,;]+?),\s*[^;]+;',
            r'\1;',
            text,
            flags=re.IGNORECASE,
        )

        # ── 4. Version ───────────────────────────────────────────────────────────
        # Prototype IDFs ship with Version,22.1; or Version,25.1; etc.
        # Replace with the current EnergyPlus version to suppress version warnings.
        text = re.sub(
            r'(?im)^(\s*Version\s*,\s*)\S+(\s*;)',
            r'\g<1>25.2\2',
            text,
        )

        return text

    @staticmethod
    def apply_vrf_coil_type_defaults(hvac_content: str) -> str:
        """
        Apply default VRF coil types to HVACTemplate:Zone:VRF objects when blank.
        
        This fixes a critical issue where generic LLMs (like Gemini) leave the coil type
        fields blank, causing EnergyPlus simulation to fail with "zero rated capacity" errors.
        
        RESEARCH FINDING:
        - Fine-tuned Mistral model explicitly sets coil types to 'VariableRefrigerantFlowDX'
        - Generic Gemini model leaves fields 26 (Cooling Coil Type) and 30 (Heat Pump Heating
          Coil Type) blank in HVACTemplate:Zone:VRF objects
        - EnergyPlus cannot autosize coils when type is blank, resulting in zero capacity
        - This post-processing step applies the required defaults to enable general LLMs to work
        
        HVACTemplate:Zone:VRF field structure (relevant fields):
        - Field 26 (A10): Cooling Coil Type - must be 'VariableRefrigerantFlowDX' for VRF
        - Field 30 (A12): Heat Pump Heating Coil Type - must be 'VariableRefrigerantFlowDX' for VRF
        
        Args:
            hvac_content: Generated HVAC IDF text
            
        Returns:
            HVAC content with default coil types applied where blank
        """
        import re
        
        fixes_applied = []
        
        # Find all HVACTemplate:Zone:VRF objects
        pattern = r'(HVACTemplate:Zone:VRF,)([^;]*)(;)'
        
        def fix_zone_vrf_coil_types(match):
            """Fix Zone:VRF coil types when blank."""
            prefix = match.group(1)
            fields_text = match.group(2)
            suffix = match.group(3)
            
            # Parse fields - each line with !- comment is a field
            lines = fields_text.strip().split('\n')
            modified = False
            new_lines = []
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # Check for Cooling Coil Type field (Field 26, A10)
                if '!- Cooling Coil Type' in stripped or '!- Cooling_Coil_Type' in stripped:
                    # Extract current value
                    if '!-' in stripped:
                        value_part = stripped.split('!-')[0].strip().rstrip(',')
                        if value_part == '' or value_part.lower() == 'blank':
                            # Apply default
                            comment_part = stripped.split('!-')[1]
                            new_line = f"    VariableRefrigerantFlowDX,            !-{comment_part}"
                            new_lines.append(new_line)
                            modified = True
                            fixes_applied.append("Set Cooling Coil Type = VariableRefrigerantFlowDX")
                            continue
                
                # Check for Heat Pump Heating Coil Type field (Field 30, A12)
                if '!- Heat Pump Heating Coil Type' in stripped or '!- Heat_Pump_Heating_Coil_Type' in stripped:
                    # Extract current value
                    if '!-' in stripped:
                        value_part = stripped.split('!-')[0].strip().rstrip(',')
                        if value_part == '' or value_part.lower() == 'blank':
                            # Apply default
                            comment_part = stripped.split('!-')[1]
                            new_line = f"    VariableRefrigerantFlowDX,            !-{comment_part}"
                            new_lines.append(new_line)
                            modified = True
                            fixes_applied.append("Set Heat Pump Heating Coil Type = VariableRefrigerantFlowDX")
                            continue
                
                new_lines.append(line)
            
            if modified:
                return prefix + '\n' + '\n'.join(new_lines) + suffix
            else:
                return match.group(0)
        
        # Apply fixes to all Zone:VRF objects
        result = re.sub(pattern, fix_zone_vrf_coil_types, hvac_content, flags=re.DOTALL | re.IGNORECASE)
        
        if fixes_applied:
            print(f"  🔧 Applied VRF coil type defaults: {len(fixes_applied)} fixes")
            for fix in fixes_applied[:4]:  # Show first 4
                print(f"     - {fix}")
            if len(fixes_applied) > 4:
                print(f"     ... and {len(fixes_applied) - 4} more")
        
        return result

    @staticmethod
    def sanitize_hvac_template_zone_vrf(hvac_content: str) -> str:
        """
        Sanitize HVACTemplate:Zone:VRF objects to fix common formatting issues from generic LLMs.
        
        Fixes:
        1. Misplaced semicolons (e.g., semicolon after Baseboard Heating Type instead of last field)
        2. Line continuation issues where two fields are on same line
        3. Ensures proper 42-field structure
        
        Common Gemini pattern that needs fixing (on SAME LINE):
        ```
        ,  !- Baseboard Heating Type;  !- Baseboard Heating Availability Schedule Name
        ```
        Should become:
        ```
        ,  !- Baseboard Heating Type
        ;  !- Baseboard Heating Availability Schedule Name
        ```
        
        Args:
            hvac_content: Generated HVAC IDF text
            
        Returns:
            Sanitized HVAC content with proper Zone:VRF formatting
        """
        import re
        
        fixes_applied = 0
        
        # Pattern 1: Two fields on same line with misplaced semicolon
        # "!- Baseboard Heating Type;  !- Baseboard Heating Availability Schedule Name"
        # needs to become two lines with proper termination
        pattern1 = r'(!-\s*Baseboard Heating Type);\s*(!-\s*Baseboard Heating Availability Schedule Name)'
        replacement1 = r'\1\n  ;                                              \2'
        
        result, count = re.subn(pattern1, replacement1, hvac_content, flags=re.IGNORECASE)
        fixes_applied += count
        
        # Pattern 2: If semicolon is on a separate orphaned line 
        # (backup pattern for different formatting)
        pattern2 = r',\s*(!-\s*Baseboard Heating Type);\s*\n\s*(!-\s*Baseboard Heating Availability)'
        replacement2 = r',                                              \1\n  ;                                              \2'
        
        result, count = re.subn(pattern2, replacement2, result, flags=re.IGNORECASE)
        fixes_applied += count
        
        if fixes_applied > 0:
            print(f"  🔧 Fixed {fixes_applied} Zone:VRF termination issues")
        
        return result

    @staticmethod
    def sanitize_hvac_template_system_vrf(hvac_content: str) -> str:
        """
        Sanitize HVACTemplate:System:VRF objects to ensure correct field structure.
        
        This fixes a common issue where generic LLMs (like Gemini) generate too many
        fields or wrong field names for HVACTemplate:System:VRF.
        
        EnergyPlus IDD defines HVACTemplate:System:VRF with exactly 39 fields (A1-A11, N1-N28).
        But Gemini often generates 80+ fields with incorrect names like 'Condenser_Type' 
        instead of the template fields.
        
        This function:
        1. Keeps the first 12 basic fields (Name through Min Heat Pump PLR)
        2. Properly terminates with semicolon
        
        Args:
            hvac_content: Generated HVAC IDF text
            
        Returns:
            Sanitized HVAC content with correct field structure
        """
        import re
        
        # Max fields for HVACTemplate:System:VRF is 39 (A1-A11, N1-N28)
        # But we'll truncate to 12 basic fields to avoid field name issues
        MAX_SYSTEM_VRF_FIELDS = 39
        
        # Find all HVACTemplate:System:VRF objects
        pattern = r'(HVACTemplate:System:VRF,)([^;]*)(;)'
        
        def fix_system_vrf(match):
            """Fix System:VRF to have correct field structure."""
            prefix = match.group(1)
            fields_text = match.group(2)
            
            # Count fields - each line with !- comment is a field
            lines = fields_text.strip().split('\n')
            field_lines = [l for l in lines if '!-' in l]
            field_count = len(field_lines)
            
            # Check if we have too many fields (Gemini's typical issue)
            if field_count <= MAX_SYSTEM_VRF_FIELDS:
                # Already correct, return as-is
                return match.group(0)
            
            # Too many fields - rebuild with correct structure (first 12 basic fields)
            print(f"  🔧 Fixing HVACTemplate:System:VRF (had {field_count} fields, reducing to 12)")
            
            # Extract values from field lines
            values = []
            for line in field_lines[:12]:  # First 12 fields
                stripped = line.strip()
                if '!-' in stripped:
                    value_part = stripped.split('!-')[0].strip().rstrip(',')
                    values.append(value_part)
                else:
                    values.append('')
            
            # Ensure we have 12 values
            while len(values) < 12:
                values.append('')
            
            # Build correct HVACTemplate:System:VRF with 12 basic fields
            correct_output = f"""HVACTemplate:System:VRF,
    {values[0]},                     !- Name
    {values[1]},                     !- System Availability Schedule Name
    {values[2]},                     !- Gross Rated Total Cooling Capacity {{W}}
    {values[3]},                     !- Gross Rated Cooling COP {{W/W}}
    {values[4]},                     !- Minimum Outdoor Temperature in Cooling Mode {{C}}
    {values[5]},                     !- Maximum Outdoor Temperature in Cooling Mode {{C}}
    {values[6]},                     !- Gross Rated Heating Capacity {{W}}
    {values[7]},                     !- Rated Heating Capacity Sizing Ratio
    {values[8]},                     !- Gross Rated Heating COP {{W/W}}
    {values[9]},                     !- Minimum Outdoor Temperature in Heating Mode {{C}}
    {values[10]},                    !- Maximum Outdoor Temperature in Heating Mode {{C}}
    {values[11]};                    !- Minimum Heat Pump Part-Load Ratio"""
            
            return correct_output
        
        # Apply fix to all System:VRF objects
        sanitized = re.sub(pattern, fix_system_vrf, hvac_content, flags=re.DOTALL)
        
        return sanitized

