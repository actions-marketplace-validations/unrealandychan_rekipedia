---
slug: python-api
title: "Python API Reference"
section: api-reference
tags: [api, python, reference]
pin: false
importance: 50
created_at: 2026-05-05T03:45:02Z
rekipedia_version: 0.10.1
---

# Python API Reference

## Function List

### `read_checksums_from_dist()`
**File:** `.github/scripts/update-homebrew-tap.py`  
**Lines:** 36-55  
**Signature:** `read_checksums_from_dist()`  
**Description:**  
Reads sha256 checksums from `goreleaser`'s `dist/checksums.txt` without needing to download the file.

```python
def read_checksums_from_dist():
    # Implementation here
```

> **Sources:** `.github/scripts/update-homebrew-tap.py` · L36–L55 · [`read_checksums_from_dist`](.github/scripts/update-homebrew-tap.py#L36)

### `gh_get_sha(path)`
**File:** `.github/scripts/update-homebrew-tap.py`  
**Lines:** 58-68  
**Signature:** `gh_get_sha(path)`  
**Description:**  
Fetches the SHA value for a given path from GitHub.

```python
def gh_get_sha(path):
    # Implementation here
```

> **Sources:** `.github/scripts/update-homebrew-tap.py` · L58–L68 · [`gh_get_sha`](.github/scripts/update-homebrew-tap.py#L58)

### `gh_put(path, content, sha, message)`
**File:** `.github/scripts/update-homebrew-tap.py`  
**Lines:** 71-87  
**Signature:** `gh_put(path, content, sha, message)`  
**Description:**  
Updates content on GitHub at the specified path with the given SHA and commit message.

```python
def gh_put(path, content, sha, message):
    # Implementation here
```

> **Sources:** `.github/scripts/update-homebrew-tap.py` · L71–L87 · [`gh_put`](.github/scripts/update-homebrew-tap.py#L71)

### `tryRun(cmd, cmdArgs)`
**File:** `bin/rekipedia.js`  
**Lines:** 4-  
**Signature:** `tryRun(cmd, cmdArgs)`  
**Description:**  
Attempts to run a command with the provided arguments.

```javascript
function tryRun(cmd, cmdArgs) {
    // Implementation here
}
```

> **Sources:** `bin/rekipedia.js` · L4– · [`tryRun`](bin/rekipedia.js#L4)

### `debounce(callback, wait)`
**File:** `htmlcov/coverage_html_cb_dd2e7eb5.js`  
**Lines:** 4-  
**Signature:** `debounce(callback, wait)`  
**Description:**  
Creates a debounced function that delays invoking `callback` until after `wait` milliseconds have elapsed since the last time the debounced function was invoked.

```javascript
function debounce(callback, wait) {
    // Implementation here
}
```

> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L4– · [`debounce`](htmlcov/coverage_html_cb_dd2e7eb5.js#L4)

### `checkVisible(element)`
**File:** `htmlcov/coverage_html_cb_dd2e7eb5.js`  
**Lines:** 11-  
**Signature:** `checkVisible(element)`  
**Description:**  
Checks if the specified element is visible in the viewport.

```javascript
function checkVisible(element) {
    // Implementation here
}
```

> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L11– · [`checkVisible`](htmlcov/coverage_html_cb_dd2e7eb5.js#L11)

### `on_click(sel, fn)`
**File:** `htmlcov/coverage_html_cb_dd2e7eb5.js`  
**Lines:** 22-  
**Signature:** `on_click(sel, fn)`  
**Description:**  
Attaches a click event listener to elements matching the selector `sel` and executes the function `fn` when clicked.

```javascript
function on_click(sel, fn) {
    // Implementation here
}
```

> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L22– · [`on_click`](htmlcov/coverage_html_cb_dd2e7eb5.js#L22)

### `getCellValue(row, column = 0)`
**File:** `htmlcov/coverage_html_cb_dd2e7eb5.js`  
**Lines:** 24-  
**Signature:** `getCellValue(row, column = 0)`  
**Description:**  
Retrieves the value of a cell in the specified row and column.

```javascript
function getCellValue(row, column = 0) {
    // Implementation here
}
```

> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L24– · [`getCellValue`](htmlcov/coverage_html_cb_dd2e7eb5.js#L24)

### `rowComparator(rowA, rowB, column = 0)`
**File:** `htmlcov/coverage_html_cb_dd2e7eb5.js`  
**Lines:** 39-  
**Signature:** `rowComparator(rowA, rowB, column = 0)`  
**Description:**  
Compares two rows based on the values in the specified column.

```javascript
function rowComparator(rowA, rowB, column = 0) {
    // Implementation here
}
```

> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L39– · [`rowComparator`](htmlcov/coverage_html_cb_dd2e7eb5.js#L39)

### `sortColumn(th)`
**File:** `htmlcov/coverage_html_cb_dd2e7eb5.js`  
**Lines:** 50-  
**Signature:** `sortColumn(th)`  
**Description:**  
Sorts the table column represented by the header `th`.

```javascript
function sortColumn(th) {
    // Implementation here
}
```

> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L50– · [`sortColumn`](htmlcov/coverage_html_cb_dd2e7eb5.js#L50)

### `updateHeader()`
**File:** `htmlcov/coverage_html_cb_dd2e7eb5.js`  
**Lines:** 572-  
**Signature:** `updateHeader()`  
**Description:**  
Updates the table header based on the current sorting state.

```javascript
function updateHeader() {
    // Implementation here
}
```

> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L572– · [`updateHeader`](htmlcov/coverage_html_cb_dd2e7eb5.js#L572)

## Class List

### `RefactorConfig`
**File:** `src/rekipedia/analysis/refactor_detector.py`  
**Lines:** 13-19  
**Description:**  
Defines thresholds for refactor checks, which can be overridden via `.rekipedia/config.yml` refactor block.

```python
class RefactorConfig:
    # Implementation here
```

> **Sources:** `src/rekipedia/analysis/refactor_detector.py` · L13–L19 · [`RefactorConfig`](src/rekipedia/analysis/refactor_detector.py#L13)

### `RefactorIssue`
**File:** `src/rekipedia/analysis/refactor_enricher.py`  
**Lines:** 41-70  
**Description:**  
Represents a single detected refactoring issue.

```python
class RefactorIssue:
    # Implementation here
```

> **Sources:** `src/rekipedia/analysis/refactor_enricher.py` · L41–L70 · [`RefactorIssue`](src/rekipedia/analysis/refactor_enricher.py#L41)

### `RefactorEnricher`
**File:** `src/rekipedia/analysis/refactor_enricher.py`  
**Lines:** 374-461  
**Description:**  
Enriches static-analysis issues with LLM explanations and suggestions.

```python
class RefactorEnricher:
    # Implementation here
```

> **Sources:** `src/rekipedia/analysis/refactor_enricher.py` · L374–L461 · [`RefactorEnricher`](src/rekipedia/analysis/refactor_enricher.py#L374)

### `Calculator`
**File:** `tests/fixtures/mini-py-repo/core.py`  
**Lines:** 5-9  
**Description:**  
A simple calculator using shared utilities.

```python
class Calculator:
    # Implementation here
```

> **Sources:** `tests/fixtures/mini-py-repo/core.py` · L5–L9 · [`Calculator`](tests/fixtures/mini-py-repo/core.py#L5)

## Parameters

### `gh_get_sha(path)`
- **path**: The path for which the SHA value is to be fetched.

### `gh_put(path, content, sha, message)`
- **path**: The path to update on GitHub.
- **content**: The content to be updated.
- **sha**: The SHA value.
- **message**: The commit message.

### `tryRun(cmd, cmdArgs)`
- **cmd**: The command to run.
- **cmdArgs**: The arguments for the command.

### `debounce(callback, wait)`
- **callback**: The function to debounce.
- **wait**: The delay in milliseconds.

### `checkVisible(element)`
- **element**: The element to check visibility for.

### `on_click(sel, fn)`
- **sel**: The selector for elements to attach the click event.
- **fn**: The function to execute on click.

### `getCellValue(row, column = 0)`
- **row**: The row from which to get the cell value.
- **column**: The column index (default is 0).

### `rowComparator(rowA, rowB, column = 0)`
- **rowA**: The first row to compare.
- **rowB**: The second row to compare.
- **column**: The column index (default is 0).

### `sortColumn(th)`
- **th**: The table header element representing the column to sort.

## Return Values

### `read_checksums_from_dist()`
- **Returns**: The sha256 checksums from `dist/checksums.txt`.

### `gh_get_sha(path)`
- **Returns**: The SHA value for the specified path.

### `gh_put(path, content, sha, message)`
- **Returns**: None.

### `tryRun(cmd, cmdArgs)`
- **Returns**: None.

### `debounce(callback, wait)`
- **Returns**: The debounced function.

### `checkVisible(element)`
- **Returns**: Boolean indicating visibility.

### `on_click(sel, fn)`
- **Returns**: None.

### `getCellValue(row, column = 0)`
- **Returns**: The value of the specified cell.

### `rowComparator(rowA, rowB, column = 0)`
- **Returns**: Comparison result.

### `sortColumn(th)`
- **Returns**: None.

### `updateHeader()`
- **Returns**: None.

## Examples

### Example of `read_checksums_from_dist()`

```python
checksums = read_checksums_from_dist()
print(checksums)
```

### Example of `gh_get_sha(path)`

```python
sha_value = gh_get_sha('/path/to/file')
print(sha_value)
```

### Example of `gh_put(path, content, sha, message)`

```python
gh_put('/path/to/file', 'new content', 'abc123', 'Updated content')
```

### Example of `tryRun(cmd, cmdArgs)`

```javascript
tryRun('echo', ['Hello, World!'])
```

### Example of `debounce(callback, wait)`

```javascript
const debouncedFunction = debounce(() => console.log('Debounced!'), 300)
debouncedFunction()
```

### Example of `checkVisible(element)`

```javascript
const isVisible = checkVisible(document.getElementById('myElement'))
console.log(isVisible)
```

### Example of `on_click(sel, fn)`

```javascript
on_click('.myButton', () => alert('Button clicked!'))
```

### Example of `getCellValue(row, column = 0)`

```javascript
const value = getCellValue(myRow, 1)
console.log(value)
```

### Example of `rowComparator(rowA, rowB, column = 0)`

```javascript
const result = rowComparator(rowA, rowB, 1)
console.log(result)
```

### Example of `sortColumn(th)`

```javascript
sortColumn(document.querySelector('th'))
```

### Example of `updateHeader()`

```javascript
updateHeader()
```

## Sources

> **Sources:** `.github/scripts/update-homebrew-tap.py` · L36–L55 · [`read_checksums_from_dist`](.github/scripts/update-homebrew-tap.py#L36)  
> **Sources:** `.github/scripts/update-homebrew-tap.py` · L58–L68 · [`gh_get_sha`](.github/scripts/update-homebrew-tap.py#L58)  
> **Sources:** `.github/scripts/update-homebrew-tap.py` · L71–L87 · [`gh_put`](.github/scripts/update-homebrew-tap.py#L71)  
> **Sources:** `bin/rekipedia.js` · L4– · [`tryRun`](bin/rekipedia.js#L4)  
> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L4– · [`debounce`](htmlcov/coverage_html_cb_dd2e7eb5.js#L4)  
> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L11– · [`checkVisible`](htmlcov/coverage_html_cb_dd2e7eb5.js#L11)  
> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L22– · [`on_click`](htmlcov/coverage_html_cb_dd2e7eb5.js#L22)  
> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L24– · [`getCellValue`](htmlcov/coverage_html_cb_dd2e7eb5.js#L24)  
> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L39– · [`rowComparator`](htmlcov/coverage_html_cb_dd2e7eb5.js#L39)  
> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L50– · [`sortColumn`](htmlcov/coverage_html_cb_dd2e7eb5.js#L50)  
> **Sources:** `htmlcov/coverage_html_cb_dd2e7eb5.js` · L572– · [`updateHeader`](htmlcov/coverage_html_cb_dd2e7eb5.js#L572)  
> **Sources:** `src/rekipedia/analysis/refactor_detector.py` · L13–L19 · [`RefactorConfig`](src/rekipedia/analysis/refactor_detector.py#L13)  
> **Sources:** `src/rekipedia/analysis/refactor_enricher.py` · L41–L70 · [`RefactorIssue`](src/rekipedia/analysis/refactor_enricher.py#L41)  
> **Sources:** `src/rekipedia/analysis/refactor_enricher.py` · L374–L461 · [`RefactorEnricher`](src/rekipedia/analysis/refactor_enricher.py#L374)  
> **Sources:** `tests/fixtures/mini-py-repo/core.py` · L5–L9 · [`Calculator`](tests/fixtures/mini-py-repo/core.py#L5)