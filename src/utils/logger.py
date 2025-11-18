"""
Logging utilities
"""

import logging
import os
from datetime import datetime
from config import Config

def setup_logger(name, log_file=None):
    """Setup logger"""
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file is None:
        log_file = os.path.join(
            Config.OUTPUT_DIR, 
            'logs', 
            f'hvac_llm_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
    
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger
