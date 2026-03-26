"""
Flask Backend API for EnergyPlus HVAC-LLM UI
Provides REST API and WebSocket support for IDF generation
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from routes.upload import upload_bp
from routes.pipeline import pipeline_bp
from routes.files import files_bp
from backend_config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for React frontend
CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}})

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins=Config.CORS_ORIGINS, async_mode='threading')

# Register blueprints
app.register_blueprint(upload_bp, url_prefix='/api/upload')
app.register_blueprint(pipeline_bp, url_prefix='/api/pipeline')
app.register_blueprint(files_bp, url_prefix='/api/files')

# Store socketio instance in app config for access in routes
app.config['SOCKETIO'] = socketio

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'EnergyPlus HVAC-LLM API',
        'version': '1.0.0'
    })

@app.route('/', methods=['GET'])
def serve_frontend():
    """Serve the HTML frontend"""
    return send_from_directory('../', 'simple_frontend.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get available configurations"""
    try:
        # Import from main project config
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
        from config.settings import LLM_PROVIDER, USE_RAG
        return jsonify({
            'llm_provider': LLM_PROVIDER,
            'rag_enabled': USE_RAG,
            'available_providers': ['mistral', 'claude-opus-4.6', 'gemini', 'mistral-pretrained', 'mistral-api']
        })
    except ImportError as e:
        return jsonify({
            'llm_provider': 'mistral',
            'rag_enabled': True,
            'available_providers': ['mistral', 'claude-opus-4.6', 'gemini', 'mistral-pretrained', 'mistral-api'],
            'error': f'Config import error: {str(e)}'
        })

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    print('Client disconnected')

if __name__ == '__main__':
    # Ensure required directories exist
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.OUTPUT_FOLDER, exist_ok=True)

    # Run with SocketIO support
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
