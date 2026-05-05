---
slug: module-storage
title: "Storage Module Documentation"
section: core-components
tags: [modules, data-storage]
pin: false
importance: 50
created_at: 2026-05-05T03:44:45Z
rekipedia_version: 0.10.1
---

# Storage Module Documentation

## Overview

The Storage module in the Rekipedia project is primarily responsible for managing data persistence and retrieval using a SQLite-based storage system. This module is encapsulated within the `SqliteStore` class, which provides a robust interface for interacting with the database. The design of this module ensures that data operations are efficient and reliable, leveraging SQLite's capabilities to handle complex queries and transactions.

The `SqliteStore` class is designed to be flexible and can be used in various contexts, including as a standalone instance or within a context manager. This flexibility allows for seamless integration into different parts of the application, ensuring that data management is consistent and reliable across the board.

## Key Functions

### Initialization and Connection Management

- **`SqliteStore.__init__(self, path)`**: Initializes the `SqliteStore` instance with the specified database path. This function sets up the necessary configurations for the database connection but does not open the connection itself.

- **`SqliteStore.open(self)`**: Opens a connection to the SQLite database. This method is crucial for preparing the store for data operations. It ensures that the database is ready to accept queries and transactions.

- **`SqliteStore.close(self)`**: Closes the database connection. This method is essential for resource management, ensuring that connections are not left open, which could lead to resource leaks.

### Data Operations

- **`SqliteStore.upsert_run(self, run_id, repo_path, status)`**: Inserts or updates a run record in the database. This function is used to track the status of various operations within the application, providing a way to monitor and log activities.

- **`SqliteStore.upsert_file(self, run_id, path, sha256, size_bytes, language)`**: Inserts or updates file metadata in the database. This function is critical for maintaining an accurate record of files processed by the application, including their checksums and sizes.

- **`SqliteStore.upsert_symbols(self, run_id, symbols)`**: Inserts or updates symbol data in the database. This method is used to store information about the symbols extracted during analysis, which is crucial for subsequent queries and operations.

- **`SqliteStore.get_all_symbols(self, run_id)`**: Retrieves all symbols associated with a specific run. This function is used to fetch symbol data for analysis or reporting purposes.

### Context Management

- **`SqliteStore.__enter__(self)`** and **`SqliteStore.__exit__(self)`**: These methods allow the `SqliteStore` to be used as a context manager, providing a convenient way to ensure that the database connection is properly opened and closed within a `with` statement.

```python
with SqliteStore(path) as store:
    store.upsert_run(run_id, repo_path)
```

This usage pattern ensures that the connection is automatically closed when the block is exited, even if an exception occurs.

> **Sources:** `src/rekipedia/storage/sqlite_store.py` · L56–L554 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39)

## Data Models

The Storage module utilizes several data models to structure and manage the data stored in the SQLite database. These models are defined using Pydantic's `BaseModel`, which provides data validation and serialization capabilities.

### `Symbol`

The `Symbol` model represents a code symbol extracted during analysis. It includes attributes such as the symbol's name, file location, and type. This model is crucial for storing and querying symbol data efficiently.

### `Relationship`

The `Relationship` model captures the relationships between different symbols, such as imports, calls, and inheritance. This model is essential for understanding the dependencies and interactions within the codebase.

### `FileManifest`

The `FileManifest` model stores metadata about files processed during analysis, including their paths and checksums. This model helps track changes and ensure data integrity across different runs.

> **Sources:** `src/rekipedia/models/contracts.py` · L30–L100 · [`Symbol`](src/rekipedia/models/contracts.py#L49), [`Relationship`](src/rekipedia/models/contracts.py#L59), [`FileManifest`](src/rekipedia/models/contracts.py#L30)

## Configuration Options

The Storage module does not have extensive configuration options exposed directly through the `SqliteStore` class. However, it relies on the configuration of the SQLite database path and the optional use of Turso (pyturso) for enhanced database operations.

### Database Path

The path to the SQLite database file is specified during the initialization of the `SqliteStore` instance. This path determines where the database file is stored and accessed.

### Turso Integration

If Turso (pyturso) is available, the `SqliteStore` can leverage its capabilities for improved performance and scalability. This integration is seamless and does not require additional configuration from the user.

### Contextual Usage

The `SqliteStore` can be used within a context manager to ensure that database connections are managed efficiently. This usage pattern is recommended to prevent resource leaks and ensure that connections are closed properly.

```python
store = SqliteStore(Path(".rekipedia/store.db"))
store.open()
# Perform operations
store.close()
```

> **Sources:** `src/rekipedia/storage/sqlite_store.py` · L56–L554 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39)

## Conclusion

The Storage module in Rekipedia is a critical component that ensures data persistence and retrieval are handled efficiently. By leveraging SQLite and integrating with Turso when available, the module provides a robust and flexible solution for managing data within the application. The use of Pydantic models for data validation and serialization further enhances the reliability and maintainability of the storage system.