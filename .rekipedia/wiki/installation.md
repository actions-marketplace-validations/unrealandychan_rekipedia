---
slug: installation
title: "Installation Instructions"
section: getting-started
tags: [getting-started, configuration]
pin: false
importance: 50
created_at: 2026-05-05T03:44:24Z
rekipedia_version: 0.10.1
---

# Installation Instructions

Welcome to the installation guide for the Rekipedia project. This document will walk you through the prerequisites, installation steps, configuration, and verification processes to ensure that you can set up and run Rekipedia successfully.

## Prerequisites

Before you begin the installation, ensure that your system meets the following prerequisites:

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 4 GB RAM
- **Disk Space**: Minimum 2 GB free space

### Software Requirements

- **Python**: Version 3.8 or higher
- **Node.js**: Version 14 or higher
- **Go**: Version 1.16 or higher
- **Docker**: Version 20.10 or higher (optional for Docker-based setup)

### Environment Variables

Set up the following environment variables for the installation process:

```bash
export REKIPEDIA_HOME=/path/to/rekipedia
export PYTHONPATH=$REKIPEDIA_HOME/src
export NODE_ENV=production
export GO111MODULE=on
```

### Dependencies

Ensure that the following dependencies are installed:

- **Python Packages**:
  ```bash
  pip install -r requirements.txt
  ```

- **Node.js Packages**:
  ```bash
  npm install
  ```

- **Go Modules**:
  ```bash
  go mod tidy
  ```

> **Sources:** `requirements.txt` · `package.json` · `go.mod`

## Installation Steps

Follow these steps to install Rekipedia:

### Step 1: Clone the Repository

Clone the Rekipedia repository from GitHub:

```bash
git clone https://github.com/yourusername/rekipedia.git
cd rekipedia
```

### Step 2: Set Up Python Environment

Create and activate a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### Step 3: Set Up Node.js Environment

Install Node.js dependencies:

```bash
npm install
```

Build the Node.js project:

```bash
npm run build
```

### Step 4: Set Up Go Environment

Install Go modules:

```bash
go mod tidy
```

Build the Go project:

```bash
CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia
```

### Step 5: Docker Setup (Optional)

If you prefer to use Docker, build the Docker image:

```bash
docker build -t rekipedia .
```

> **Sources:** `src/rekipedia/__init__.py` · `src/rekipedia/cli/__init__.py` · `Dockerfile`

## Configuration

Rekipedia requires some configuration to run correctly. Follow these steps to configure the project:

### Step 1: Environment Configuration

Copy the sample environment file and update it with your settings:

```bash
cp .env.sample .env
```

Edit the `.env` file to set the necessary environment variables:

```ini
REKIPEDIA_HOME=/path/to/rekipedia
PYTHONPATH=$REKIPEDIA_HOME/src
NODE_ENV=production
GO111MODULE=on
```

### Step 2: Pre-Commit Hooks

Set up pre-commit hooks to ensure code quality:

```bash
pre-commit install
```

### Step 3: Linting and Code Style

Configure linting and code style checks:

```bash
npm run lint
```

```bash
golangci-lint run
```

```bash
ruff check .
```

> **Sources:** `.env.sample` · `.pre-commit-config.yaml` · `.eslintrc.json` · `.golangci.yml`

## Verification

After completing the installation and configuration, verify that Rekipedia is set up correctly:

### Step 1: Run Unit Tests

Run the unit tests to ensure everything is working:

```bash
pytest
```

### Step 2: Start the Application

Start the Rekipedia application:

```bash
python src/rekipedia/__main__.py
```

### Step 3: Check the Application

Open your browser and navigate to `http://localhost:8000` to check if the application is running.

### Step 4: Docker Verification (Optional)

If using Docker, run the container and verify:

```bash
docker run -p 8000:8000 rekipedia
```

Navigate to `http://localhost:8000` to verify the Docker setup.

> **Sources:** `src/rekipedia/__main__.py` · `tests/test_ask.py` · `Dockerfile`

---

By following these steps, you should have Rekipedia installed and running on your system. If you encounter any issues, refer to the project's documentation or seek help from the community.