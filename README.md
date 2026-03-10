# Day 11 PM — Exception Handling, Logging & Custom Exceptions

Week 2, Day 11 · IIT Gandhinagar PG Diploma in AI-ML

---

## Files in this folder

| File | Part | What it does |
|---|---|---|
| `program1_student_system.py` | A | Student system with custom exceptions + logging to file |
| `program2_sales_pipeline.py` | A | Sales pipeline with try/except/else/finally per file |
| `program3_gpa_calculator.py` | A | GPA calculator with KeyboardInterrupt handling |
| `error_handling_checklist.md` | A | Full table: what's caught, recovery, user msg, log msg |
| `file_processor_resilient.py` | B | Resilient processor: corrupted files, retry, JSON report |
| `interview_answers.md` | C | Execution flow, safe_json_load, three-bug fix |
| `ai_retry_decorator.md` | D | AI critique + improved retry with functools.wraps |

## How to run

```bash
# Part B — processes 6 test files (good, empty, corrupted, wrong format, etc.)
python file_processor_resilient.py

# Parts A — interactive demos (you'll need to type inputs)
python program1_student_system.py
python program3_gpa_calculator.py
```

---

# 📚 Everything You Can Learn From This Assignment

This is the most important session of the whole program for writing real
production code. Every professional Python codebase uses everything here.

---

## 1. Why Exception Handling Exists

Without it, your program crashes and the user sees a 30-line traceback.
With it, your program recovers gracefully and the user sees a clear message.

```python
# Without exception handling
age = int(input("Enter age: "))   # user types "abc" → program crashes

# With exception handling
while True:
    try:
        age = int(input("Enter age: "))
        if age < 0 or age > 150:
            raise ValueError(f"Age {age} is not realistic.")
    except ValueError as e:
        print(f"Invalid input: {e}. Try again.")
    else:
        print(f"In 10 years you'll be {age + 10}.")
        break
```

The only difference is that the second version stays alive. That's the entire
point of exception handling in interactive programs.

---

## 2. The Four Keywords: try / except / else / finally

Think of a restaurant kitchen as an analogy:

```
try:     → Attempt to cook the dish
except:  → If cooking fails, handle the disaster (cleanup, serve something else)
else:    → If cooking succeeded, plate it beautifully
finally: → Always clean the station when done, success or failure
```

```python
try:
    result = risky_operation()   # attempt this

except ValueError as e:
    handle_value_error(e)        # only runs if try raised ValueError

except FileNotFoundError as e:
    handle_missing_file(e)       # only runs if try raised FileNotFoundError

else:
    use_the_result(result)       # only runs if try SUCCEEDED (no exception)

finally:
    cleanup()                    # ALWAYS runs — no matter what happened above
```

**The `else` block is the "success path".** It separates "what happens when
everything works" from "what happens when something goes wrong." This keeps
the try block focused: just the thing that might fail.

**The `finally` block is for cleanup.** Close files, release database connections,
log audit entries, restore state. It runs even if there's a `return` statement
in try or except.

---

## 3. Specific Exceptions — Never Use Bare `except:`

```python
# WRONG — bare except catches EVERYTHING
try:
    data = int(input("Enter number: "))
except:
    print("Something went wrong")

# What "everything" includes:
# - KeyboardInterrupt (Ctrl+C) → user can't exit!
# - SystemExit (sys.exit()) → program can't terminate!
# - MemoryError → hides critical system failure
# - Your own bugs → ValueError, TypeError silently swallowed
```

```python
# RIGHT — catch only what you expect
try:
    data = int(input("Enter number: "))
except ValueError:
    print("Please enter a whole number.")
# KeyboardInterrupt, SystemExit still propagate naturally
```

**The exception hierarchy** — knowing what catches what:

```
BaseException
├── SystemExit
├── KeyboardInterrupt
└── Exception                   ← catch this or below only
    ├── ValueError               ← wrong value type/range
    ├── TypeError                ← wrong argument type
    ├── FileNotFoundError        ← file doesn't exist
    ├── PermissionError          ← no access to file/resource
    ├── json.JSONDecodeError     ← invalid JSON
    ├── KeyError                 ← dict key missing
    ├── IndexError               ← list index out of range
    └── ...
```

Catching `Exception` is generally OK — it doesn't catch `KeyboardInterrupt`
or `SystemExit`. Bare `except:` catches `BaseException` which includes those.

---

## 4. Raising Exceptions — `raise`

You can raise exceptions yourself to enforce rules:

```python
def set_age(age: int) -> None:
    if age < 0 or age > 150:
        raise ValueError(f"Age must be 0–150, got {age}")
    # if we reach here, age is valid
    self._age = age
```

This is called **input validation by exception**. It makes the function
impossible to misuse silently — callers are forced to handle the error.

**Re-raising** — catching just to log, then re-raising:

```python
try:
    connect_to_db()
except ConnectionError as e:
    log.error(f"DB connection failed: {e}")
    raise   # re-raise the same exception with the same traceback
```

**Exception chaining** — linking a low-level error to a higher-level one:

```python
try:
    value = int(row["qty"])
except ValueError as e:
    raise InvalidRowError(f"Bad qty in row: {row}") from e
    # The "from e" preserves the original ValueError as __cause__
    # Traceback shows both the high-level and low-level errors
```

---

## 5. Custom Exceptions — Building Your Own

Custom exceptions make code self-documenting. Instead of a generic `ValueError`,
you get a `DuplicateStudentError` that tells you exactly what went wrong.

```python
# Base exception for your whole application
class AppError(Exception):
    """All application-specific errors inherit from this."""
    pass

# Specific errors inherit from the base
class DuplicateStudentError(AppError):
    """When a student+subject combo already exists."""
    def __init__(self, name: str, subject: str):
        # Call parent's __init__ with the message
        super().__init__(f"'{name}' already has a '{subject}' record.")
        # Store values as attributes so callers can inspect them
        self.name    = name
        self.subject = subject

class InvalidMarksError(AppError):
    """When marks are outside 0–100."""
    def __init__(self, value):
        super().__init__(f"Marks must be 0–100, got {value!r}")
        self.value = value
```

Why have a base class (`AppError`)? So callers can catch all your exceptions
with one clause if they want: `except AppError`. But they can also catch specific
ones like `DuplicateStudentError` for fine-grained handling.

---

## 6. Logging — The Professional Alternative to print()

`print()` is for demos. `logging` is for production. The difference:

| `print()` | `logging` |
|---|---|
| All output looks the same | Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| Goes to screen only | Can go to screen, file, both, or a remote server |
| No timestamps | Automatic timestamps |
| Can't silence verbose output | Filter by level — show only WARNING+ in prod |
| Can't route to different destinations | Different handlers for file vs screen |

```python
import logging

# Set up once at the top of your program
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("app.log"),  # all DEBUG+ goes to file
        logging.StreamHandler(),         # all DEBUG+ goes to screen too
    ]
)
log = logging.getLogger(__name__)

# Use the appropriate level:
log.debug("Entering function with args: x=5, y=10")      # fine detail
log.info("User logged in: Ayush")                        # normal event
log.warning("Config file missing, using defaults")       # unexpected but OK
log.error("Could not connect to database")               # something failed
log.critical("Payment service completely down")          # needs immediate action
```

**Two-handler pattern** (used in Program 1):

```python
# Developers see everything in the log file
file_handler.setLevel(logging.DEBUG)

# Users only see warnings on screen (no noise)
console_handler.setLevel(logging.WARNING)
```

This is how real applications work. The user gets clean, friendly messages.
Developers get full debug trails to investigate issues.

---

## 7. Retry Logic — Handling Transient Failures

Some failures are permanent (file not found, invalid data) and some are
*transient* — they might succeed if you try again (network blip, temporary
lock on a file). Only retry transient errors:

```python
import time

def with_retry(func, *args, max_attempts=3, delay=1.0):
    """Call func, retrying on PermissionError up to max_attempts times."""
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args)
        except PermissionError as e:
            if attempt == max_attempts:
                raise  # give up after max attempts
            print(f"Attempt {attempt} failed, retrying in {delay}s...")
            time.sleep(delay)
        # ValueError, KeyError, etc. are NOT caught — they propagate immediately
        # because retrying won't fix a programming error
```

**Exponential backoff** — waiting longer between each retry:
```
Attempt 1 fails → wait 1 second
Attempt 2 fails → wait 2 seconds
Attempt 3 fails → wait 4 seconds
```

This is considerate to the failing service — you don't hammer it with
rapid retries when it's already struggling.

---

## 8. Graceful Degradation

The `file_processor_resilient.py` demonstrates this perfectly. It processes 6 files:
3 succeed, 3 fail. But it doesn't stop when one fails — it logs the error,
skips the file, and continues with the rest.

This is "graceful degradation": the system does less work than intended, but
it keeps running and delivers whatever it can rather than crashing completely.

Real production systems are designed this way. A broken product page shouldn't
take down the entire e-commerce site.

---

## How This Connects to TIS

In the Tender Intelligence System, every downloaded tender document could be:
- A corrupted PDF
- An empty file
- A format you haven't seen before
- A file you don't have permission to read

The patterns from this session — specific exception handling, per-file try/except,
retry on transient failures, logging full tracebacks, generating a processing report
— are exactly how you'd build the document ingestion pipeline. One bad tender PDF
should never stop the pipeline from processing the other 47.
