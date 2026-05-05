---
slug: data-structures
title: "Data Structures in Rekipedia"
section: internals
tags: [internals, data-structures]
pin: false
importance: 50
created_at: 2026-05-05T03:45:07Z
rekipedia_version: 0.10.1
---

# Data Structures in Rekipedia

## Overview

In the Rekipedia project, data structures are fundamental to organizing and managing the various components and functionalities. This documentation provides a comprehensive overview of the key data structures used in the project, their implementation details, and usage examples. Understanding these data structures is crucial for developers working on the Rekipedia project, as they form the backbone of the system's architecture and data flow.

## Key Data Structures

### `Symbol`

The `Symbol` class represents individual symbols extracted from the source code. These symbols can be functions, classes, or other entities that are identified during the analysis process.

```python
class Symbol(BaseModel):
    name: str
    kind: str
    file: str
    line_start: int
    line_end: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
```

### `Relationship`

The `Relationship` class models the relationships between symbols, such as imports, calls, and inheritance. This class is essential for understanding the interactions and dependencies within the codebase.

```python
class Relationship(BaseModel):
    from_: str
    to: str
    kind: str
    file: str
    confidence: float
    evidence_tag: str
```

### `AnalysisResult`

The `AnalysisResult` class aggregates the results of the analysis, including symbols and relationships. It serves as a container for the data extracted from the source code.

```python
class AnalysisResult(BaseModel):
    symbols: List[Symbol]
    relationships: List[Relationship]
    files_seen: List[str]
    entry_points: List[str]
```

### `FileManifest`

The `FileManifest` class represents metadata about files in the repository, including their paths, sizes, and checksums. This class is used to track changes and manage file-level operations.

```python
class FileManifest(BaseModel):
    path: str
    sha256: str
    size_bytes: int
    language: Optional[str] = None
```

### `Shard`

The `Shard` class is used to group files into manageable chunks for processing. Sharding helps in distributing the workload and optimizing the analysis process.

```python
class Shard(BaseModel):
    id: str
    files: List[str]
```

### `RefactorIssue`

The `RefactorIssue` class represents issues detected during the refactoring analysis. These issues can include god classes, circular dependencies, dead code, and more.

```python
class RefactorIssue(BaseModel):
    kind: str
    symbol: str
    file: str
    severity: str
    metrics: Dict[str, Any]
    suggestion: Optional[str] = None
    callers: Optional[List[str]] = None
```

### `LLMConfig`

The `LLMConfig` class holds configuration settings for the language model used in the project. This includes parameters for model selection, API keys, and other relevant settings.

```python
class LLMConfig(BaseModel):
    model: str
    api_key: str
    base_url: Optional[str] = None
    timeout: Optional[int] = None
```

## Implementation Details

### `Symbol` Class

The `Symbol` class is implemented using Pydantic's `BaseModel`, which provides data validation and serialization capabilities. Each symbol has attributes such as `name`, `kind`, `file`, `line_start`, `line_end`, `signature`, and `docstring`.

```python
class Symbol(BaseModel):
    name: str
    kind: str
    file: str
    line_start: int
    line_end: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
```

### `Relationship` Class

Similar to the `Symbol` class, the `Relationship` class uses Pydantic's `BaseModel`. It includes attributes to define the source and target of the relationship, the type of relationship, the file where it was found, and confidence and evidence tags.

```python
class Relationship(BaseModel):
    from_: str
    to: str
    kind: str
    file: str
    confidence: float
    evidence_tag: str
```

### `AnalysisResult` Class

The `AnalysisResult` class aggregates symbols and relationships into a single structure. It also includes lists of files seen and entry points.

```python
class AnalysisResult(BaseModel):
    symbols: List[Symbol]
    relationships: List[Relationship]
    files_seen: List[str]
    entry_points: List[str]
```

### `FileManifest` Class

The `FileManifest` class provides metadata about files, including their paths, checksums, sizes, and languages.

```python
class FileManifest(BaseModel):
    path: str
    sha256: str
    size_bytes: int
    language: Optional[str] = None
```

### `Shard` Class

The `Shard` class groups files into chunks for processing. Each shard has an ID and a list of files.

```python
class Shard(BaseModel):
    id: str
    files: List[str]
```

### `RefactorIssue` Class

The `RefactorIssue` class represents issues detected during refactoring analysis. It includes attributes for the type of issue, the symbol involved, the file, severity, metrics, suggestions, and callers.

```python
class RefactorIssue(BaseModel):
    kind: str
    symbol: str
    file: str
    severity: str
    metrics: Dict[str, Any]
    suggestion: Optional[str] = None
    callers: Optional[List[str]] = None
```

### `LLMConfig` Class

The `LLMConfig` class holds configuration settings for the language model. It includes attributes for model selection, API keys, base URL, and timeout.

```python
class LLMConfig(BaseModel):
    model: str
    api_key: str
    base_url: Optional[str] = None
    timeout: Optional[int] = None
```

## Usage Examples

### Example: Creating a `Symbol` Instance

To create a `Symbol` instance, you can use the following code:

```python
symbol = Symbol(
    name="compute_god_nodes",
    kind="function",
    file="src/rekipedia/analysis/graph_analysis.py",
    line_start=11,
    line_end=34,
    signature="compute_god_nodes(relationships, top_n)",
    docstring="Compute in+out degree for each symbol name and return top_n sorted by degree."
)
```

### Example: Creating a `Relationship` Instance

To create a `Relationship` instance, you can use the following code:

```python
relationship = Relationship(
    from_="src/rekipedia/analysis/graph_analysis.py",
    to="rekipedia.models.contracts",
    kind="import",
    file="src/rekipedia/analysis/graph_analysis.py",
    confidence=1.0,
    evidence_tag="EXTRACTED"
)
```

### Example: Creating an `AnalysisResult` Instance

To create an `AnalysisResult` instance, you can use the following code:

```python
analysis_result = AnalysisResult(
    symbols=[symbol],
    relationships=[relationship],
    files_seen=["src/rekipedia/analysis/graph_analysis.py"],
    entry_points=["src/rekipedia/__main__.py"]
)
```

### Example: Creating a `FileManifest` Instance

To create a `FileManifest` instance, you can use the following code:

```python
file_manifest = FileManifest(
    path="src/rekipedia/analysis/graph_analysis.py",
    sha256="abc123",
    size_bytes=1024,
    language="python"
)
```

### Example: Creating a `Shard` Instance

To create a `Shard` instance, you can use the following code:

```python
shard = Shard(
    id="shard_1",
    files=["src/rekipedia/analysis/graph_analysis.py", "src/rekipedia/models/contracts.py"]
)
```

### Example: Creating a `RefactorIssue` Instance

To create a `RefactorIssue` instance, you can use the following code:

```python
refactor_issue = RefactorIssue(
    kind="god_class",
    symbol="compute_god_nodes",
    file="src/rekipedia/analysis/graph_analysis.py",
    severity="high",
    metrics={"degree": 10},
    suggestion="Consider breaking down the function into smaller, more manageable pieces.",
    callers=["src/rekipedia/cli/__init__.py"]
)
```

### Example: Creating an `LLMConfig` Instance

To create an `LLMConfig` instance, you can use the following code:

```python
llm_config = LLMConfig(
    model="gpt-4",
    api_key="your_api_key_here",
    base_url="https://api.openai.com/v1",
    timeout=30
)
```

## Sources

> **Sources:** `src/rekipedia/models/contracts.py` · L49–L56 · [`Symbol`](src/rekipedia/models/contracts.py#L49) · L59–L67 · [`Relationship`](src/rekipedia/models/contracts.py#L59) · L77–L88 · [`AnalysisResult`](src/rekipedia/models/contracts.py#L77) · L30–L34 · [`FileManifest`](src/rekipedia/models/contracts.py#L30) · L95–L100 · [`Shard`](src/rekipedia/models/contracts.py#L95) · L41–L70 · [`RefactorIssue`](src/rekipedia/models/contracts.py#L41) · L13–L23 · [`LLMConfig`](src/rekipedia/models/contracts.py#L13)