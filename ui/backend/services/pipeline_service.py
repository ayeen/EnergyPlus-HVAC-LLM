"""
Pipeline service for executing HVAC generation with real-time progress updates
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.pipeline import HVACLLMPipeline


class PipelineService:
    """
    Service class for running HVAC generation pipeline with WebSocket progress updates
    """

    def __init__(self, execution_id, socketio):
        """
        Initialize pipeline service

        Args:
            execution_id: Unique ID for this execution
            socketio: Flask-SocketIO instance for emitting progress
        """
        self.execution_id = execution_id
        self.socketio = socketio
        self.status = 'initialized'
        self.progress = 0
        self.current_step = ''
        self.logs = []
        self.results = {}
        self.error = None
        self.start_time = None
        self.end_time = None
        self.cancelled = False

    def emit_progress(self, step, progress, message, details=None):
        """
        Emit progress update via WebSocket

        Args:
            step: Current step name
            progress: Progress percentage (0-100)
            message: Progress message
            details: Optional additional details
        """
        self.current_step = step
        self.progress = progress
        self.logs.append({
            'timestamp': datetime.now().isoformat(),
            'step': step,
            'message': message,
            'details': details
        })

        self.socketio.emit('pipeline_progress', {
            'execution_id': self.execution_id,
            'step': step,
            'progress': progress,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })

    def cancel(self):
        """Cancel pipeline execution"""
        self.cancelled = True
        self.status = 'cancelled'
        self.emit_progress('cancelled', self.progress, 'Pipeline execution cancelled')

    def run_pipeline(self, base_idf_path, zones, system_name, user_request, use_rag, llm_provider):
        """
        Execute the HVAC generation pipeline

        Args:
            base_idf_path: Path to base IDF file
            zones: List of zones or None for auto-detect
            system_name: Name for HVAC system
            user_request: Natural language HVAC request
            use_rag: Enable RAG
            llm_provider: LLM provider to use
        """
        try:
            self.start_time = datetime.now()
            self.status = 'running'
            self.emit_progress('initialization', 5, 'Initializing pipeline...', {
                'llm_provider': llm_provider,
                'use_rag': use_rag,
                'system_name': system_name
            })

            if self.cancelled:
                return

            # Create pipeline instance
            # Import Config here to avoid circular imports
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from backend_config import Config
            pipeline = HVACLLMPipeline(
                use_rag=use_rag,
                llm_provider=llm_provider
            )

            self.emit_progress('base_idf_loading', 10, 'Loading and validating base IDF file...')

            if self.cancelled:
                return

            # Run Step 0: Load and validate base IDF
            self.emit_progress('base_idf_analysis', 15, 'Analyzing building zones and context...')

            if self.cancelled:
                return

            # Run Step 1: HVAC Generation (Agent 1)
            self.emit_progress('agent1_generation', 25, 'Agent 1: Generating HVAC system configuration...', {
                'agent': 'Agent 1 (HVAC Generator)',
                'action': 'Querying RAG knowledge base and generating HVACTemplate objects'
            })

            if self.cancelled:
                return

            # Run Step 1.5: Quick Validation (Agent 1.5)
            self.emit_progress('agent1_5_validation', 45, 'Agent 1.5: Performing quick validation...', {
                'agent': 'Agent 1.5 (Quick Validator)',
                'action': 'Checking for common errors before simulation'
            })

            if self.cancelled:
                return

            # Run Step 2: Assemble IDF
            self.emit_progress('idf_assembly', 55, 'Assembling complete IDF file...')

            if self.cancelled:
                return

            # Override progress callback if it exists
            original_callback = getattr(pipeline, '_progress_callback', None)
            if hasattr(pipeline, '_progress_callback') or hasattr(pipeline, 'set_progress_callback'):
                if hasattr(pipeline, 'set_progress_callback'):
                    pipeline.set_progress_callback(self._create_pipeline_callback())
                else:
                    pipeline._progress_callback = self._create_pipeline_callback()

            # Run pipeline
            results = pipeline.run(
                base_idf=base_idf_path,
                zones=zones,
                output_name=self.execution_id,
                user_request=user_request if user_request else None
            )

            if self.cancelled:
                return

            # Restore original callback if it was set
            if original_callback is not None:
                if hasattr(pipeline, 'set_progress_callback'):
                    pipeline.set_progress_callback(original_callback)
                else:
                    pipeline._progress_callback = original_callback

            # Process results
            self.results = {
                'status': results.get('final_status', 'unknown'),
                'success': results.get('final_status') == 'SUCCESS',
                'final_idf_path': results.get('final_idf_path', ''),
                'iterations': results.get('correction_iterations', 0),
                'simulation_results': results.get('simulation_results', {}),
                'errors': results.get('errors', []),
                'execution_time': results.get('total_execution_time_seconds', 0)
            }

            if results.get('final_status') == 'SUCCESS':
                self.status = 'completed'
                self.emit_progress('completed', 100, 'Pipeline completed successfully!', {
                    'final_idf': results.get('final_idf_path'),
                    'iterations': results.get('correction_iterations', 0),
                    'execution_time': f"{results.get('total_execution_time_seconds', 0):.1f}s"
                })
            else:
                self.status = 'failed'
                self.error = results.get('errors', ['Unknown error'])
                self.emit_progress('failed', self.progress, 'Pipeline failed', {
                    'errors': results.get('errors', []),
                    'iterations_attempted': results.get('correction_iterations', 0)
                })

            self.end_time = datetime.now()

        except Exception as e:
            self.status = 'error'
            self.error = str(e)
            self.emit_progress('error', self.progress, f'Pipeline error: {str(e)}')
            self.end_time = datetime.now()

    def _create_pipeline_callback(self):
        """Create a progress callback for the pipeline"""
        def callback(stage, details):
            """Custom progress callback"""
            if self.cancelled:
                return

            stage_progress = {
                'base_idf_loading': 15,
                'hvac_generation': 35,
                'quick_validation': 50,
                'idf_assembly': 60,
                'simulation': 70,
                'error_correction_iteration_1': 75,
                'error_correction_iteration_2': 85,
                'error_correction_iteration_3': 95
            }

            progress = stage_progress.get(stage, self.progress)

            if stage == 'hvac_generation':
                self.emit_progress('agent1_generation', progress, 'Generating HVAC configuration...', details)
            elif stage == 'quick_validation':
                self.emit_progress('agent1_5_validation', progress, 'Quick validation...', details)
            elif stage == 'simulation':
                self.emit_progress('simulation', progress, 'Running EnergyPlus simulation...', details)
            elif 'error_correction' in stage:
                iteration = stage.split('_')[-1] if '_' in stage else '1'
                self.emit_progress('agent3_correction', progress,
                                 f'Agent 3: Correcting errors (iteration {iteration})...', {
                    'agent': 'Agent 3 (Error Corrector)',
                    'iteration': iteration,
                    'details': details
                })
            else:
                self.emit_progress(stage, progress, stage.replace('_', ' ').title(), details)

        return callback
