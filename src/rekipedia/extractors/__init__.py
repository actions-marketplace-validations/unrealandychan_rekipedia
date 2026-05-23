"""rekipedia.extractors package."""
from rekipedia.extractors.config_extractor import ConfigExtractor
from rekipedia.extractors.go_extractor import GoExtractor
from rekipedia.extractors.java_extractor import JavaExtractor
from rekipedia.extractors.python_extractor import PythonExtractor
from rekipedia.extractors.rust_extractor import RustExtractor
from rekipedia.extractors.typescript_extractor import TypeScriptExtractor

ALL_EXTRACTORS = [
    PythonExtractor(),
    TypeScriptExtractor(),
    GoExtractor(),
    RustExtractor(),
    JavaExtractor(),
    ConfigExtractor(),
]

__all__ = [
    "ALL_EXTRACTORS",
    "ConfigExtractor",
    "GoExtractor",
    "JavaExtractor",
    "PythonExtractor",
    "RustExtractor",
    "TypeScriptExtractor",
]
