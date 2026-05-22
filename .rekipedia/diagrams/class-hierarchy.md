```mermaid
classDiagram
  BaseModel <|-- AnalysisResult
  ABC <|-- BaseExtractor
  ABC <|-- BaseRunner
  VectorStore <|-- ChromaStore
  BaseExtractor <|-- ConfigExtractor
  BaseRunner <|-- DockerSandboxRunner
  VectorStore <|-- FaissStore
  BaseModel <|-- FileManifest
  BaseExtractor <|-- GoExtractor
  BaseExtractor <|-- JavaExtractor
  Protocol <|-- LLMCaller
  BaseModel <|-- LLMConfig
  BaseRunner <|-- LocalRunner
  BaseExtractor <|-- PythonExtractor
  VectorStore <|-- QdrantStore
  BaseModel <|-- RationaleNote
  BaseModel <|-- Relationship
  BaseExtractor <|-- RustExtractor
  BaseModel <|-- Shard
  BaseModel <|-- Symbol
```
