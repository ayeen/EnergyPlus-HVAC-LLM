"""
Test HVAC-LLM Pipeline
"""

import unittest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import HVACLLMPipeline
from src.core.idf_handler import IDFHandler
from src.core.validator import IDFValidator
from src.agents.llm_interface import UniversalLLM

class TestPipeline(unittest.TestCase):
    """Test pipeline components"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.pipeline = HVACLLMPipeline()
    
    def test_idf_handler(self):
        """Test IDF handler"""
        handler = IDFHandler()
        idf = handler.create_new()
        self.assertIsNotNone(idf)
    
    def test_llm_interface(self):
        """Test LLM interface"""
        llm = UniversalLLM(provider="mock")
        response = llm.generate("system", "test prompt")
        self.assertIsNotNone(response)
    
    def test_validator(self):
        """Test validator"""
        validator = IDFValidator()
        # Would need a test IDF file
        # is_valid = validator.validate("test.idf")
        # self.assertIsInstance(is_valid, bool)
        pass

if __name__ == "__main__":
    unittest.main()
