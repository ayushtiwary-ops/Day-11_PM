# AI Retry Decorator — Analysis & Improvement
**Day 11 PM — Part D: AI-Augmented Task**

---

## 1. Prompt Used

> "Write a Python decorator called @retry(max_attempts=3, delay=1) that automatically
> retries a function if it raises an exception, with exponential backoff."

---

## 2. AI-Generated Code

```python
import time
import functools

def retry(max_attempts=3, delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    wait = delay * (2 ** attempt)
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                    time.sleep(wait)
        return wrapper
    return decorator
```

---

## 3. Testing with a flaky function

```python
import random

@retry(max_attempts=4, delay=0.1)
def flaky_service():
    """Simulates an API that fails ~50% of the time."""
    if random.random() < 0.5:
        raise ConnectionError("Service temporarily unavailable")
    return {"status": "ok", "data": [1, 2, 3]}

# Run it
result = flaky_service()
print(result)
# Output varies — sometimes succeeds first try, sometimes retries 1–3 times
```

**Test with always-failing function:**
```python
@retry(max_attempts=3, delay=0)
def always_fails():
    raise RuntimeError("Broken forever")

try:
    always_fails()
except RuntimeError as e:
    print(f"Failed after all retries: {e}")  # ✅ correct behaviour
```

---

## 4. Critical Evaluation (200 words)

The AI's decorator works for the happy path and implements exponential backoff
correctly (`delay * 2^attempt` gives 1s, 2s, 4s). It raises on the final attempt
rather than swallowing the error. The structure — decorator factory returning
decorator returning wrapper — is textbook correct.

However it has several real gaps. First and most importantly: **missing
`functools.wraps`**. Without it, the wrapper steals the original function's
`__name__`, `__doc__`, and `__module__`. `help(flaky_service)` would show
"wrapper" and no docstring — a subtle bug that breaks documentation and
introspection tools.

Second: **no distinction between retryable and non-retryable exceptions**.
Catching `Exception` means it retries `ValueError`, `TypeError`, `AttributeError`
— programming errors that will fail identically every time. There is no point
retrying those. The decorator should accept a `retryable` parameter specifying
which exception types warrant a retry (`ConnectionError`, `TimeoutError`, etc.).

Third: **no logging** — print statements aren't appropriate in library code.
A production decorator should use the `logging` module so callers can control
output level.

Fourth: **`wrapper` can return `None` implicitly** if `func` returns `None`
on success and then the loop ends. The current structure handles this correctly
but only by accident — the final `raise` on the last attempt covers it.

---

## 5. Improved Version

```python
import time
import logging
import functools

log = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    retryable: tuple = (Exception,),
):
    """
    Decorator factory: retry a function on specified exceptions with exponential backoff.

    Args:
        max_attempts: Total number of attempts (including the first). Default 3.
        delay:        Initial wait in seconds before first retry. Default 1.0.
        backoff:      Multiplier applied to delay on each retry. Default 2.0
                      (exponential: 1s, 2s, 4s, ...).
        retryable:    Tuple of exception types that should trigger a retry.
                      Exceptions NOT in this tuple propagate immediately.
                      Default: (Exception,) — retries on anything.

    Example:
        @retry(max_attempts=4, delay=0.5, retryable=(ConnectionError, TimeoutError))
        def call_external_api():
            ...
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")

    def decorator(func):
        @functools.wraps(func)   # Fix 1: preserves __name__, __doc__, __module__
        def wrapper(*args, **kwargs):
            wait = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        log.info(f"{func.__name__}: succeeded on attempt {attempt}")
                    return result

                except retryable as e:
                    # Fix 2: only retry the exceptions we expect (retryable)
                    if attempt == max_attempts:
                        log.error(
                            f"{func.__name__}: all {max_attempts} attempts failed. "
                            f"Last error: {type(e).__name__}: {e}"
                        )
                        raise  # re-raise original exception, not a new one

                    log.warning(
                        f"{func.__name__}: attempt {attempt}/{max_attempts} failed "
                        f"({type(e).__name__}: {e}). Retrying in {wait:.1f}s..."
                    )
                    time.sleep(wait)
                    wait *= backoff  # exponential backoff

                except Exception as e:
                    # Fix 3: non-retryable exception — propagate immediately
                    log.error(
                        f"{func.__name__}: non-retryable error "
                        f"({type(e).__name__}: {e}). Not retrying."
                    )
                    raise

        return wrapper
    return decorator


# ── Test Suite ────────────────────────────────────────────────────

if __name__ == "__main__":
    import random
    logging.basicConfig(level=logging.INFO, format="  %(levelname)s %(message)s")

    # Test 1: flaky function (retryable error)
    attempt_count = {"n": 0}

    @retry(max_attempts=5, delay=0, retryable=(ConnectionError,))
    def flaky_api():
        attempt_count["n"] += 1
        if random.random() < 0.6:
            raise ConnectionError("Gateway timeout")
        return "success"

    print("\n[Test 1 — Flaky API]")
    try:
        result = flaky_api()
        print(f"  Result: {result} (took {attempt_count['n']} attempts)")
    except ConnectionError:
        print(f"  Failed after {attempt_count['n']} attempts")

    # Test 2: non-retryable error propagates immediately
    call_count = {"n": 0}

    @retry(max_attempts=5, delay=0, retryable=(ConnectionError,))
    def bad_logic():
        call_count["n"] += 1
        raise ValueError("Programming error — not retryable")

    print("\n[Test 2 — Non-retryable error]")
    try:
        bad_logic()
    except ValueError as e:
        print(f"  Propagated immediately after {call_count['n']} call(s): {e}")

    # Test 3: functools.wraps — __name__ is preserved
    print(f"\n[Test 3 — functools.wraps]")
    print(f"  flaky_api.__name__ = {flaky_api.__name__}")  # "flaky_api", not "wrapper"
    assert flaky_api.__name__ == "flaky_api", "functools.wraps not working!"
    print("  ✅ __name__ preserved correctly")
```

---

## 6. Summary of Improvements

| Issue | AI Code | Improved Version |
|---|---|---|
| `functools.wraps` | ❌ Missing — steals `__name__` and `__doc__` | ✅ Added |
| Retryable distinction | ❌ Retries all `Exception` subclasses | ✅ `retryable` param — only specified types |
| Non-retryable propagation | ❌ `ValueError` would be retried 3 times uselessly | ✅ Propagates immediately |
| Logging | ❌ `print()` only | ✅ `logging` module with WARNING/ERROR levels |
| Configurable backoff | ❌ Hard-coded `2x` | ✅ `backoff` parameter |
| Input validation | ❌ None | ✅ `ValueError` if `max_attempts < 1` |
| Attempt numbering | ❌ 0-indexed (confusing in messages) | ✅ 1-indexed ("attempt 1/3") |
