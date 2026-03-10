# Interview Answers
**Day 11 PM — Part C: Exception Handling**

---

## Q1 — try / except / else / finally Execution Flow

### The four blocks

```python
try:
    # The code you WANT to run
    # Python enters here first, always

except SomeError as e:
    # Runs ONLY if try raised SomeError (or a subclass of it)
    # Skipped entirely if try succeeds

else:
    # Runs ONLY if try completed WITHOUT raising any exception
    # Skipped if any exception occurred
    # Think of it as "the success path"

finally:
    # ALWAYS runs — success OR failure, exception or not
    # Even if there's a return inside try or except
    # Used for cleanup: close files, release locks, log audit trail
```

### Complete example

```python
import json

def load_config(filepath: str) -> dict | None:
    f = None
    try:
        f = open(filepath, "r")
        config = json.load(f)           # could raise json.JSONDecodeError

    except FileNotFoundError:
        print(f"Config file not found: {filepath}")
        return None

    except json.JSONDecodeError as e:
        print(f"Config file is not valid JSON: {e}")
        return None

    else:
        # Only runs if open() and json.load() both succeeded
        print(f"Config loaded: {len(config)} keys")
        return config                   # SUCCESS path

    finally:
        # Always runs — even if we returned inside except or else
        if f:
            f.close()
        print("load_config() finished.")  # always printed
```

### Step-by-step execution traces

**Scenario A — file exists and is valid JSON:**
```
1. try: open() succeeds → json.load() succeeds
2. except: SKIPPED
3. else: RUNS → prints "Config loaded", returns config
4. finally: RUNS → closes file, prints "finished"
```

**Scenario B — file does not exist:**
```
1. try: open() raises FileNotFoundError
2. except FileNotFoundError: RUNS → prints "not found", returns None
3. else: SKIPPED (exception occurred)
4. finally: RUNS → f is None so no close, prints "finished"
```

**Scenario C — file exists but invalid JSON:**
```
1. try: open() succeeds, json.load() raises JSONDecodeError
2. except FileNotFoundError: SKIPPED (wrong type)
3. except JSONDecodeError: RUNS → prints "not valid JSON", returns None
4. else: SKIPPED (exception occurred)
5. finally: RUNS → closes file, prints "finished"
```

### What if an exception occurs inside the else block?

```python
try:
    x = 1
except ValueError:
    print("value error")
else:
    raise RuntimeError("oops")  # this is NOT caught by the above except
finally:
    print("finally runs")       # this still runs
```

An exception raised in the `else` block is **not caught** by the `except` blocks
in the same try statement. It propagates up to the caller. The `finally` block
still runs before propagation.

---

## Q2 — safe_json_load

```python
import json
import logging

log = logging.getLogger(__name__)


def safe_json_load(filepath: str) -> dict | None:
    """
    Safely read and parse a JSON file.

    Returns the parsed dict on success, or None on any failure.
    All errors are logged with full detail — the caller gets None without
    needing to handle exceptions themselves.

    Args:
        filepath: Path to the JSON file to read.

    Returns:
        Parsed dict, or None if any error occurred.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

    except FileNotFoundError:
        log.error(f"safe_json_load: file not found: '{filepath}'")
        return None

    except PermissionError:
        log.error(f"safe_json_load: permission denied reading '{filepath}'")
        return None

    except json.JSONDecodeError as e:
        # e.lineno and e.colno tell us exactly where the JSON broke
        log.error(
            f"safe_json_load: invalid JSON in '{filepath}' "
            f"at line {e.lineno}, col {e.colno}: {e.msg}"
        )
        return None

    except OSError as e:
        # Catches remaining OS-level errors: disk errors, network paths, etc.
        log.error(f"safe_json_load: OS error reading '{filepath}': {e}")
        return None

    else:
        log.debug(f"safe_json_load: successfully loaded '{filepath}'")
        return data  # only returned here, on clean success


# Tests
if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    logging.basicConfig(level=logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # 1. valid JSON
        (root / "good.json").write_text('{"a": 1, "b": 2}')
        assert safe_json_load(root / "good.json") == {"a": 1, "b": 2}
        print("✅ Valid JSON: passed")

        # 2. file not found
        assert safe_json_load(root / "missing.json") is None
        print("✅ Missing file: returned None")

        # 3. invalid JSON
        (root / "bad.json").write_text("{not valid json")
        assert safe_json_load(root / "bad.json") is None
        print("✅ Invalid JSON: returned None")

        # 4. empty file
        (root / "empty.json").write_text("")
        assert safe_json_load(root / "empty.json") is None
        print("✅ Empty file: returned None")
```

---

## Q3 — Debug: process_data

### Buggy Code

```python
def process_data(data_list):
    results = []
    for item in data_list:
        try:
            value = int(item)
            results.append(value * 2)
        except:                     # Bug 1
            print("Error occurred") # Bug 3
            continue
        finally:
            return results          # Bug 2
    return results
```

---

### Bug 1 — Bare `except:`

`except:` catches **everything** — including `KeyboardInterrupt` (Ctrl+C),
`SystemExit` (sys.exit()), and `MemoryError`. These are not errors in your
code — they are signals from the OS or the Python runtime.

Catching them silently breaks Ctrl+C, swallows program exit requests, and
hides critical failures. Always catch the specific exception you expect.

---

### Bug 2 — `return` inside `finally` exits on the first iteration

`finally` runs on every loop iteration. The `return results` executes after
processing just the first item and exits the entire function — the loop
never reaches items 2, 3, 4, etc.

Rule: **never put `return`, `break`, or `continue` inside a `finally` block.**
They suppress any exception that was propagating and short-circuit control flow
in confusing ways.

---

### Bug 3 — Uninformative error message

`"Error occurred"` tells you nothing. Which item failed? What was the error?
What was the value? Without this information you can't debug the problem.

---

### Fixed Implementation

```python
def process_data(data_list: list) -> list[int]:
    """
    Convert items to int and double them. Skips non-convertible items with logging.

    Args:
        data_list: List of values to process.

    Returns:
        List of successfully processed (doubled) integers.
    """
    results = []

    for item in data_list:
        try:
            value = int(item)               # may raise ValueError or TypeError
            results.append(value * 2)

        except (ValueError, TypeError) as e:
            # Fix 1: specific exception types
            # Fix 3: informative message with the actual item and error
            print(f"Skipping {item!r}: cannot convert to int ({e})")
            # no `continue` needed — loop continues naturally after except

        # Fix 2: finally block removed — it served no purpose here
        # (no resources to clean up per-iteration)

    return results  # return is here at the end of the function, not in finally


# Demo
print(process_data(["1", "2", "abc", "4", None, "5"]))
# Skipping 'abc': cannot convert to int (invalid literal for int()...)
# Skipping None: cannot convert to int (int() argument must be...)
# [2, 4, 8, 10]
```
