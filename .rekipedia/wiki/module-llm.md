---
slug: module-llm
title: "LLM Module Documentation"
section: core-components
tags: [modules, llm]
pin: false
importance: 50
created_at: 2026-05-05T03:44:43Z
rekipedia_version: 0.10.1
---

# LLM Module Documentation

## Overview

The LLM module in the Rekipedia project is designed to facilitate interaction with Large Language Models (LLMs). It provides a set of classes and functions to manage LLM calls, handle token usage, and integrate LLM responses into the broader system. This module is crucial for tasks that require natural language processing, such as generating wiki pages, enriching static analysis results, and answering user queries.

### Key Components

- **LLMCaller**: An interface for making LLM calls, allowing test injection via `FakeCaller`.
- **LLMClient**: A stateless LLM caller that is thread-safe and uses the `litellm` library for making API calls.
- **_TokenCounter**: A process-wide accumulator for tracking LLM token usage.

## Key Functions

### `LLMCaller.call(system, prompt)`

This function is responsible for making a synchronous call to the LLM with a given system prompt and user prompt.

```python
def call(self, system, prompt):
    pass
```

### `LLMCaller.stream(system, prompt)`

This function streams the response from the LLM, allowing real-time interaction.

```python
def stream(self, system, prompt):
    pass
```

### `LLMClient.__init__(self, config)`

Initializes the LLMClient with the given configuration.

```python
def __init__(self, config):
    pass
```

### `LLMClient.call(prompt)`

Sends a prompt to the LLM and returns the assistant's text response. It supports history for context and retries on timeout or server errors.

```python
def call(self, prompt):
    pass
```

### `LLMClient.stream(prompt)`

Streams response tokens from the LLM as an iterator of text chunks.

```python
def stream(self, prompt):
    pass
```

### `_TokenCounter.add(usage)`

Adds the token usage to the counter.

```python
def add(self, usage):
    pass
```

### `_TokenCounter.total_tokens()`

Returns the total number of tokens used.

```python
def total_tokens(self):
    pass
```

### `_TokenCounter.reset()`

Resets the token counter.

```python
def reset(self):
    pass
```

### `_TokenCounter.summary()`

Provides a summary of the token usage.

```python
def summary(self):
    pass
```

## Usage Examples

### Example 1: Making a Synchronous LLM Call

```python
from rekipedia.llm.client import LLMClient, LLMConfig

config = LLMConfig(api_key="your_api_key")
client = LLMClient(config)

response = client.call(prompt="What is the capital of France?")
print(response)
```

### Example 2: Streaming LLM Responses

```python
from rekipedia.llm.client import LLMClient, LLMConfig

config = LLMConfig(api_key="your_api_key")
client = LLMClient(config)

for chunk in client.stream(prompt="Tell me a story about a brave knight"):
    print(chunk)
```

### Example 3: Tracking Token Usage

```python
from rekipedia.llm.client import _TokenCounter

counter = _TokenCounter()
counter.add(usage=100)
print(counter.total_tokens())
counter.reset()
print(counter.summary())
```

## Configuration Options

The LLM module relies on configuration settings provided via the `LLMConfig` class. This configuration includes API keys, model settings, and other parameters necessary for making LLM calls.

### Example Configuration

```python
from rekipedia.models.contracts import LLMConfig

config = LLMConfig(
    api_key="your_api_key",
    model="gpt-3",
    timeout=30,
    retries=3
)
```

### Configuration Parameters

| Parameter | Description |
|-----------|-------------|
| `api_key` | The API key for accessing the LLM service. |
| `model` | The model to use for LLM calls (e.g., "gpt-3"). |
| `timeout` | The timeout for each LLM call in seconds. |
| `retries` | The number of retries on timeout or server errors. |

## Sources

> **Sources:** `src/rekipedia/llm/client.py` · L24–L185 · [`LLMCaller`](src/rekipedia/llm/client.py#L75) · [`LLMClient`](src/rekipedia/llm/client.py#L113) · [`_TokenCounter`](src/rekipedia/llm/client.py#L24)