"""
Pipeline execution routes for HVAC generation
"""

from flask import Blueprint, request, jsonify, current_app
import os
import threading
import uuid
from datetime import datetime

from backend_config import Config
from services.pipeline_service import PipelineService

pipeline_bp = Blueprint('pipeline', __name__)

# Store active pipeline executions
active_pipelines = {}


@pipeline_bp.route('/run', methods=['POST'])
def run_pipeline():
    """
    Execute HVAC generation pipeline

    Request JSON:
        {
            "file_id": "uuid-of-uploaded-file",
            "user_request": "Natural language HVAC request",
            "zones": ["Zone1", "Zone2"] or null for auto-detect,
            "system_name": "My_HVAC_System",
            "use_rag": true,
            "llm_provider": "claude-opus-4.6"
        }

    Returns:
        JSON with execution_id for tracking progress
    """
    try:
        data = request.get_json()

        # Validate required fields
        if 'file_id' not in data:
            return jsonify({'error': 'file_id is required'}), 400

        file_id = data['file_id']
        user_request = data.get('user_request', '')
        zones = data.get('zones', None)  # None = auto-detect
        system_name = data.get('system_name', f'HVAC_System_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        use_rag = data.get('use_rag', True)
        llm_provider = data.get('llm_provider', Config.DEFAULT_LLM_PROVIDER)

        # Find uploaded file
        upload_folder = Config.UPLOAD_FOLDER
        matching_files = [f for f in os.listdir(upload_folder) if f.startswith(file_id)]

        if not matching_files:
            return jsonify({'error': 'Uploaded file not found'}), 404

        base_idf_path = os.path.join(upload_folder, matching_files[0])

        # Generate execution ID
        execution_id = str(uuid.uuid4())

        # Create pipeline service instance
        pipeline_service = PipelineService(
            execution_id=execution_id,
            socketio=current_app.config['SOCKETIO']
        )

        # Store in active pipelines
        active_pipelines[execution_id] = {
            'status': 'starting',
            'progress': 0,
            'service': pipeline_service
        }

        # Run pipeline in background thread
        thread = threading.Thread(
            target=pipeline_service.run_pipeline,
            args=(base_idf_path, zones, system_name, user_request, use_rag, llm_provider)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'execution_id': execution_id,
            'message': 'Pipeline execution started'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to start pipeline: {str(e)}'}), 500


@pipeline_bp.route('/status/<execution_id>', methods=['GET'])
def get_status(execution_id):
    """
    Get status of pipeline execution

    Returns:
        JSON with current status, progress, and results
    """
    try:
        if execution_id not in active_pipelines:
            return jsonify({'error': 'Execution not found'}), 404

        pipeline_info = active_pipelines[execution_id]
        service = pipeline_info['service']

        return jsonify({
            'execution_id': execution_id,
            'status': service.status,
            'progress': service.progress,
            'current_step': service.current_step,
            'logs': service.logs,
            'results': service.results,
            'error': service.error
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get status: {str(e)}'}), 500


@pipeline_bp.route('/cancel/<execution_id>', methods=['POST'])
def cancel_pipeline(execution_id):
    """
    Cancel a running pipeline execution

    Returns:
        JSON with cancellation status
    """
    try:
        if execution_id not in active_pipelines:
            return jsonify({'error': 'Execution not found'}), 404

        pipeline_info = active_pipelines[execution_id]
        service = pipeline_info['service']
        service.cancel()

        return jsonify({
            'success': True,
            'message': 'Pipeline cancelled'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to cancel pipeline: {str(e)}'}), 500


@pipeline_bp.route('/list', methods=['GET'])
def list_executions():
    """
    List all pipeline executions (active and completed)

    Returns:
        JSON with list of executions
    """
    try:
        executions = []
        for exec_id, pipeline_info in active_pipelines.items():
            service = pipeline_info['service']
            executions.append({
                'execution_id': exec_id,
                'status': service.status,
                'progress': service.progress,
                'current_step': service.current_step,
                'start_time': service.start_time.isoformat() if service.start_time else None,
                'end_time': service.end_time.isoformat() if service.end_time else None
            })

        return jsonify({'executions': executions}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to list executions: {str(e)}'}), 500


@pipeline_bp.route('/examples', methods=['GET'])
def get_examples():
    """
    Get example HVAC requests from config

    Returns:
        JSON with example requests
    """
    try:
        import json
        from pathlib import Path

        # Load hvac_requests.json
        config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'hvac_requests.json'

        if not config_path.exists():
            return jsonify({'examples': []}), 200

        with open(config_path, 'r') as f:
            hvac_requests = json.load(f)

        # Format examples for frontend
        examples = []
        for key, config in hvac_requests.items():
            examples.append({
                'id': key,
                'title': key.replace('_', ' ').title(),
                'request': config.get('user_request', ''),
                'zones': config.get('zones', None),
                'description': config.get('description', '')
            })

        return jsonify({'examples': examples}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to load examples: {str(e)}'}), 500
