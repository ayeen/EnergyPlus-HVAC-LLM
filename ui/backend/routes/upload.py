"""
File upload routes for base IDF files
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

from backend_config import Config

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/idf', methods=['POST'])
def upload_idf():
    """
    Upload a base IDF file (building without HVAC)

    Returns:
        JSON with file_id, filename, upload_path
    """
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        # Check if filename is empty
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file extension
        if not Config.allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only .idf files allowed'}), 400

        # Generate unique file ID
        file_id = str(uuid.uuid4())
        original_filename = secure_filename(file.filename)

        # Create timestamped filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        stored_filename = f"{file_id}_{timestamp}_{original_filename}"
        file_path = os.path.join(Config.UPLOAD_FOLDER, stored_filename)

        # Save file
        file.save(file_path)

        # Attempt to validate IDF structure
        from src.core.idf_handler import IDFHandler
        try:
            handler = IDFHandler(file_path)
            zones = handler.get_zones()
            zone_count = len(zones) if zones else 0

            validation = {
                'valid': True,
                'zone_count': zone_count,
                'zones': zones[:10] if zones else []  # Return first 10 zones
            }
        except Exception as e:
            validation = {
                'valid': False,
                'error': str(e),
                'zone_count': 0,
                'zones': []
            }

        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': original_filename,
            'stored_filename': stored_filename,
            'upload_path': file_path,
            'size_kb': round(os.path.getsize(file_path) / 1024, 2),
            'timestamp': timestamp,
            'validation': validation
        }), 200

    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@upload_bp.route('/validate/<file_id>', methods=['GET'])
def validate_idf(file_id):
    """
    Validate an uploaded IDF file and extract zone information

    Args:
        file_id: UUID of uploaded file

    Returns:
        JSON with validation results and zone list
    """
    try:
        # Find file by ID
        upload_folder = Config.UPLOAD_FOLDER
        matching_files = [f for f in os.listdir(upload_folder) if f.startswith(file_id)]

        if not matching_files:
            return jsonify({'error': 'File not found'}), 404

        file_path = os.path.join(upload_folder, matching_files[0])

        # Validate with IDFHandler
        from src.core.idf_handler import IDFHandler
        handler = IDFHandler(file_path)
        zones = handler.get_zones()

        # Get building context
        building_context = handler.get_building_context()

        return jsonify({
            'success': True,
            'valid': True,
            'zones': zones,
            'zone_count': len(zones),
            'building_context': {
                'total_floor_area': building_context.get('total_floor_area_m2'),
                'total_volume': building_context.get('total_volume_m3'),
                'orientation': building_context.get('north_axis_degrees'),
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'valid': False,
            'error': str(e),
            'zones': []
        }), 200  # Return 200 even on validation failure


@upload_bp.route('/list', methods=['GET'])
def list_uploads():
    """
    List all uploaded IDF files

    Returns:
        JSON with list of uploaded files
    """
    try:
        upload_folder = Config.UPLOAD_FOLDER

        if not os.path.exists(upload_folder):
            return jsonify({'files': []}), 200

        files = []
        for filename in os.listdir(upload_folder):
            if filename.endswith('.idf'):
                file_path = os.path.join(upload_folder, filename)
                file_id = filename.split('_')[0]

                files.append({
                    'file_id': file_id,
                    'filename': filename,
                    'size_kb': round(os.path.getsize(file_path) / 1024, 2),
                    'upload_time': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                })

        # Sort by upload time, newest first
        files.sort(key=lambda x: x['upload_time'], reverse=True)

        return jsonify({'files': files}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to list files: {str(e)}'}), 500
