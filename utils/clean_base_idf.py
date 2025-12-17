"""
Clean base IDF file by removing existing HVAC equipment
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.idf_handler import IDFHandler

def clean_hvac_from_idf(input_path, output_path):
    """Remove all HVAC equipment from IDF file"""
    
    handler = IDFHandler()
    idf = handler.load(input_path)
    
    print(f"Loading: {input_path}")
    print(f"Zones found: {len(idf.idfobjects.get('ZONE', []))}")
    
    # Objects to remove
    hvac_objects_to_remove = [
        'ZONEHVAC:IDEALLOADSAIRSYSTEM',
        'ZONEHVAC:EQUIPMENTCONNECTIONS',
        'ZONEHVAC:EQUIPMENTLIST',
        # Thermostat related objects
        'ZONECONTROL:THERMOSTAT',
        'THERMOSTATSETPOINT:SINGLEHEATING',
        'THERMOSTATSETPOINT:SINGLECOOLING', 
        'THERMOSTATSETPOINT:DUALSETPOINT',
        'THERMOSTATSETPOINT:SINGLEHEATINGORCOOLING',
    ]
    
    total_removed = 0
    for obj_type in hvac_objects_to_remove:
        objects = idf.idfobjects.get(obj_type, [])
        count = len(objects)
        if count > 0:
            print(f"Removing {count} {obj_type} objects...")
            # Remove all objects of this type
            idf.idfobjects[obj_type] = []
            total_removed += count
    
    # Remove HVAC-specific schedules (check names that include thermostat/setpoint keywords)
    schedules = idf.idfobjects.get('SCHEDULE:COMPACT', [])
    hvac_schedules = [s for s in schedules if any(kw in s.Name.upper() for kw in 
                     ['ZONE CONTROL TYPE', 'SETPOINT', 'HEATING SETPOINTS', 'COOLING SETPOINTS'])]
    if hvac_schedules:
        print(f"Removing {len(hvac_schedules)} HVAC-related schedules...")
        for sched in hvac_schedules:
            print(f"  - {sched.Name}")
        # Keep non-HVAC schedules
        idf.idfobjects['SCHEDULE:COMPACT'] = [s for s in schedules if s not in hvac_schedules]
        total_removed += len(hvac_schedules)
    
    print(f"\nTotal objects removed: {total_removed}")
    print(f"Saving to: {output_path}")
    idf.saveas(output_path)
    print("✓ Done!")

if __name__ == "__main__":
    input_file = "data/base_idfs/4ZoneWithShading_Simple_2.idf"
    output_file = "data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf"
    
    clean_hvac_from_idf(input_file, output_file)
