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
    
    print(f"\nTotal objects removed: {total_removed}")
    print(f"Saving to: {output_path}")
    idf.saveas(output_path)
    print("✓ Done!")

if __name__ == "__main__":
    input_file = "data/base_idfs/4ZoneWithShading_Simple_2.idf"
    output_file = "data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf"
    
    clean_hvac_from_idf(input_file, output_file)
