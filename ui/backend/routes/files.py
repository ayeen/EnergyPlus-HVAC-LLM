"""
File management routes for viewing and downloading generated IDFs
"""

from flask import Blueprint, request, jsonify, send_file
import os
from pathlib import Path

from backend_config import Config

files_bp = Blueprint('files', __name__)


@files_bp.route('/download/<execution_id>', methods=['GET'])
def download_idf(execution_id):
    """
    Download the final generated IDF file

    Args:
        execution_id: Pipeline execution ID

    Returns:
        IDF file download
    """
    try:
        # Check in generated_idfs directory first (main output location)
        project_root = Path(__file__).parent.parent.parent.parent
        generated_idfs_folder = project_root / 'outputs' / 'generated_idfs'

        matching_files = []

        # Look for files with execution_id in generated_idfs
        if generated_idfs_folder.exists():
            for filename in os.listdir(generated_idfs_folder):
                if execution_id in filename and filename.endswith('.idf'):
                    matching_files.append((str(generated_idfs_folder / filename), filename))

        # Also check ui_generated folder as fallback
        ui_generated_folder = project_root / 'outputs' / 'ui_generated'
        if ui_generated_folder.exists():
            for filename in os.listdir(ui_generated_folder):
                if execution_id in filename and filename.endswith('.idf'):
                    matching_files.append((str(ui_generated_folder / filename), filename))

        if not matching_files:
            return jsonify({'error': 'Generated IDF file not found'}), 404

        # Prioritize FINAL files, then regular files
        final_files = [f for f in matching_files if '_FINAL' in f[1]]
        if final_files:
            file_path, original_name = final_files[0]
        else:
            file_path, original_name = matching_files[0]

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f'{execution_id}_generated.idf',
            mimetype='text/plain'
        )

    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


@files_bp.route('/preview/<execution_id>', methods=['GET'])
def preview_idf(execution_id):
    """
    Preview the generated IDF file content

    Args:
        execution_id: Pipeline execution ID

    Query params:
        lines: Number of lines to return (default: 100)
        offset: Line offset to start from (default: 0)

    Returns:
        JSON with IDF content preview
    """
    try:
        lines = int(request.args.get('lines', 100))
        offset = int(request.args.get('offset', 0))

        # Check in generated_idfs directory first (main output location)
        project_root = Path(__file__).parent.parent.parent.parent
        generated_idfs_folder = project_root / 'outputs' / 'generated_idfs'

        file_path = None
        filename = None

        # Look for files with execution_id in generated_idfs
        if generated_idfs_folder.exists():
            for fname in os.listdir(generated_idfs_folder):
                if execution_id in fname and fname.endswith('.idf'):
                    # Prioritize FINAL files
                    if '_FINAL' in fname:
                        file_path = str(generated_idfs_folder / fname)
                        filename = fname
                        break
                    elif file_path is None:  # Take first match if no FINAL found yet
                        file_path = str(generated_idfs_folder / fname)
                        filename = fname

        # Also check ui_generated folder as fallback
        if file_path is None:
            ui_generated_folder = project_root / 'outputs' / 'ui_generated'
            if ui_generated_folder.exists():
                for fname in os.listdir(ui_generated_folder):
                    if execution_id in fname and fname.endswith('.idf'):
                        file_path = str(ui_generated_folder / fname)
                        filename = fname
                        break

        if file_path is None:
            return jsonify({'error': 'Generated IDF file not found'}), 404

        # Read file content
        with open(file_path, 'r') as f:
            all_lines = f.readlines()

        total_lines = len(all_lines)
        preview_lines = all_lines[offset:offset + lines]

        return jsonify({
            'success': True,
            'filename': filename,
            'total_lines': total_lines,
            'offset': offset,
            'lines_returned': len(preview_lines),
            'content': ''.join(preview_lines),
            'has_more': (offset + lines) < total_lines
        }), 200

    except Exception as e:
        return jsonify({'error': f'Preview failed: {str(e)}'}), 500


@files_bp.route('/list/<execution_id>', methods=['GET'])
def list_execution_files(execution_id):
    """
    List all files generated for a specific execution

    Args:
        execution_id: Pipeline execution ID

    Returns:
        JSON with list of files (IDFs, logs, simulation results)
    """
    try:
        output_folder = Config.OUTPUT_FOLDER
        project_root = Path(__file__).parent.parent.parent.parent

        files = {
            'idfs': [],
            'logs': [],
            'simulation_results': []
        }

        # Find IDF files in generated_idfs directory
        generated_idfs_folder = project_root / 'outputs' / 'generated_idfs'
        if generated_idfs_folder.exists():
            for filename in os.listdir(generated_idfs_folder):
                if execution_id in filename and filename.endswith('.idf'):
                    file_path = generated_idfs_folder / filename
                    files['idfs'].append({
                        'filename': filename,
                        'size_kb': round(os.path.getsize(file_path) / 1024, 2),
                        'is_final': '_FINAL' in filename
                    })

        # Also check ui_generated folder
        ui_generated_folder = project_root / 'outputs' / 'ui_generated'
        if ui_generated_folder.exists():
            for filename in os.listdir(ui_generated_folder):
                if execution_id in filename and filename.endswith('.idf'):
                    file_path = ui_generated_folder / filename
                    files['idfs'].append({
                        'filename': filename,
                        'size_kb': round(os.path.getsize(file_path) / 1024, 2),
                        'is_final': '_FINAL' in filename
                    })

        # Find log files
        log_folder = project_root / 'outputs' / 'logs'
        if log_folder.exists():
            for filename in os.listdir(log_folder):
                if execution_id in filename:
                    file_path = log_folder / filename
                    files['logs'].append({
                        'filename': filename,
                        'size_kb': round(os.path.getsize(file_path) / 1024, 2)
                    })

        # Find simulation results
        sim_folder = project_root / 'outputs' / 'simulations'
        if sim_folder.exists():
            for dirname in os.listdir(sim_folder):
                if execution_id in dirname:
                    dir_path = sim_folder / dirname
                    if dir_path.is_dir():
                        files['simulation_results'].append({
                            'folder': dirname,
                            'files': os.listdir(dir_path)
                        })

        return jsonify(files), 200

    except Exception as e:
        return jsonify({'error': f'Failed to list files: {str(e)}'}), 500


@files_bp.route('/log/<execution_id>', methods=['GET'])
def get_log(execution_id):
    """
    Get JSON log file for execution

    Args:
        execution_id: Pipeline execution ID

    Returns:
        JSON log content
    """
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        log_folder = project_root / 'outputs' / 'logs'

        # Find log file
        matching_files = [f for f in os.listdir(log_folder)
                         if execution_id in f and f.endswith('.json')]

        if not matching_files:
            return jsonify({'error': 'Log file not found'}), 404

        log_path = log_folder / matching_files[0]

        import json
        with open(log_path, 'r') as f:
            log_data = json.load(f)

        return jsonify(log_data), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get log: {str(e)}'}), 500
