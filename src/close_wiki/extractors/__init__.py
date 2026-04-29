"""close_wiki.extractors package."""
from close_wiki.extractors.config_extractor import ConfigExtractor
from close_wiki.extractors.python_extractor import PythonExtractor
from close_wiki.extractors.typescript_extractor import TypeScriptExtractor

ALL_EXTRACTORS = [PythonExtractor(), TypeScriptExtractor(), ConfigExtractor()]

__all__ = ["ALL_EXTRACTORS", "PythonExtractor", "TypeScriptExtractor", "ConfigExtractor"]
