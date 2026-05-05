---
slug: integrations
title: "Third-Party Integrations"
section: ecosystem
tags: [ecosystem, integrations]
pin: false
importance: 50
created_at: 2026-05-05T03:45:19Z
rekipedia_version: 0.10.1
---

# Third-Party Integrations

## Overview

Third-party integrations are essential for extending the functionality of the Rekipedia system. These integrations allow Rekipedia to interact with external services, tools, and platforms, enhancing its capabilities and providing a seamless experience for users. This document provides a comprehensive overview of the supported third-party integrations, their configuration, and usage examples.

## Supported Integrations

Rekipedia supports a variety of third-party integrations, each serving different purposes. The primary integrations include:

1. **GitHub Actions**: Used for continuous integration and deployment.
2. **Docker**: Facilitates containerization and sandboxing.
3. **NPM**: Manages JavaScript dependencies.
4. **Python Package Index (PyPI)**: Manages Python dependencies.
5. **Tree-sitter**: Provides language parsing capabilities.

### GitHub Actions

GitHub Actions is used for automating workflows such as CI/CD. The configuration files for GitHub Actions are located in the `.github/workflows` directory. Key workflows include:

- `go-ci.yml`: Handles continuous integration for Go projects.
- `go-release.yml`: Manages the release process for Go projects.
- `npm-publish.yml`: Automates the publishing of NPM packages.
- `python-ci.yml`: Manages continuous integration for Python projects.
- `python-release.yml`: Handles the release process for Python projects.

### Docker

Docker is used to create isolated environments for running Rekipedia tasks. The Docker configuration files include:

- `Dockerfile.sandbox`: Defines the Docker image for sandboxing.
- `go/Dockerfile`: Specifies the Docker image for Go projects.

### NPM

NPM is used for managing JavaScript dependencies. The `package.json` file in the root directory specifies the dependencies and scripts for the project.

### Python Package Index (PyPI)

PyPI is used for managing Python dependencies. The `pyproject.toml` file in the root directory defines the dependencies and configuration for Python projects.

### Tree-sitter

Tree-sitter is a library for parsing programming languages. It is used by Rekipedia to analyze code and extract symbols. The relevant files include:

- `tree_sitter_go`
- `tree_sitter_java`
- `tree_sitter_rust`

## Configuration

Configuring third-party integrations involves setting up the necessary files and environment variables. Below are detailed steps for configuring each integration.

### GitHub Actions

To configure GitHub Actions, create YAML files in the `.github/workflows` directory. Example configuration for `python-ci.yml`:

```yaml
name: Python CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run tests
      run: |
        pytest
```

### Docker

To configure Docker, create a `Dockerfile` in the project directory. Example configuration for `Dockerfile.sandbox`:

```Dockerfile
FROM python:3.8-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
```

### NPM

To configure NPM, create a `package.json` file in the project directory. Example configuration:

```json
{
  "name": "rekipedia",
  "version": "0.0.1",
  "description": "Rekipedia project",
  "main": "index.js",
  "scripts": {
    "test": "jest"
  },
  "dependencies": {
    "express": "^4.17.1"
  },
  "devDependencies": {
    "jest": "^26.6.3"
  }
}
```

### Python Package Index (PyPI)

To configure PyPI, create a `pyproject.toml` file in the project directory. Example configuration:

```toml
[tool.poetry]
name = "rekipedia"
version = "0.0.1"
description = "Rekipedia project"
authors = ["Author <author@example.com>"]

[tool.poetry.dependencies]
python = "^3.8"
flask = "^1.1.2"

[tool.poetry.dev-dependencies]
pytest = "^6.2.2"
```

### Tree-sitter

Tree-sitter requires specific language parsers. Install the necessary parsers using the following commands:

```bash
npm install tree-sitter
npm install tree-sitter-go
npm install tree-sitter-java
npm install tree-sitter-rust
```

## Usage Examples

Below are examples demonstrating how to use the configured integrations in Rekipedia.

### GitHub Actions

Triggering a CI workflow on push:

```bash
git push origin main
```

This will automatically trigger the `python-ci.yml` workflow, running tests and checking the code quality.

### Docker

Building and running a Docker container:

```bash
docker build -t rekipedia-sandbox -f Dockerfile.sandbox .
docker run -it rekipedia-sandbox
```

### NPM

Installing dependencies and running tests:

```bash
npm install
npm test
```

### Python Package Index (PyPI)

Installing dependencies and running tests:

```bash
pip install -r requirements.txt
pytest
```

### Tree-sitter

Using Tree-sitter to parse a Go file:

```javascript
const Parser = require('tree-sitter');
const Go = require('tree-sitter-go');

const parser = new Parser();
parser.setLanguage(Go);

const sourceCode = `
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
`;

const tree = parser.parse(sourceCode);
console.log(tree.rootNode.toString());
```

## Sources

> **Sources:** `.github/workflows/python-ci.yml` · `.github/workflows/go-ci.yml` · `.github/workflows/npm-publish.yml` · `.github/workflows/python-release.yml` · `Dockerfile.sandbox` · `go/Dockerfile` · `package.json` · `pyproject.toml`