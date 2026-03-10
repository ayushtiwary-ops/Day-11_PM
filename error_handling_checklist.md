# Error Handling Checklist
**Day 11 PM — Part A Documentation**

---

## Program 1 — Student Management System

### Exceptions Caught

| Exception | Where | Recovery Action | User Sees | What Gets Logged |
|---|---|---|---|---|
| `ValueError` | Name input | Loop repeats, ask again | "Name cannot be empty" / "Letters only" | `WARNING: Invalid name input: ...` |
| `ValueError` | Marks input (non-integer) | Loop repeats | "Please enter a whole number" | `WARNING: Non-integer marks input: '...'` |
| `InvalidMarksError` | Marks input (out of range) | Loop repeats | "Marks must be between 0 and 100" | `WARNING: Out-of-range marks: ...` |
| `ValueError` | Subject input | Loop repeats | "Not a recognised subject" | `WARNING: Invalid subject: ...` |
| `DuplicateStudentError` | add_student() | Operation aborted | "Student already has a record for this subject" | `ERROR: Duplicate entry attempt` |
| `StudentNotFoundError` | remove_student() | Operation aborted | "No records found for student" | `WARNING: Remove failed` |
| `ValueError` | get_toppers() | Displays error | "No records found for subject" | `WARNING: Toppers query failed` |
| `IOError` | save_to_file() | Exit without saving | "Could not save records" | `CRITICAL: Could not save records` |

### try/except/else/finally usage

```
add_student():
  try     → call add_student()
  except  → DuplicateStudentError → show error message
  else    → print "Added successfully"         ← only if no exception
  finally → log "operation completed"          ← always, even on error
```

### Custom Exceptions Created

- `StudentError` — base class for all domain errors
- `DuplicateStudentError(name, subject)` — preserves offending values as attributes
- `InvalidMarksError(value)` — preserves the bad value
- `StudentNotFoundError(name)` — preserves the search name

---

## Program 2 — Sales Pipeline

### Exceptions Caught

| Exception | Where | Recovery Action | User Sees | What Gets Logged |
|---|---|---|---|---|
| `FileNotFoundError` | read_csv_file() | Skip file, continue | (pipeline continues silently) | `ERROR: File disappeared` |
| `EmptyFileError` | read_csv_file() | Skip file, continue | (pipeline continues silently) | `ERROR: Skipping [file]: ...` |
| `MissingColumnsError` | read_csv_file() | Skip file, continue | (pipeline continues silently) | `ERROR: Skipping [file]: missing columns` |
| `PermissionError` | read_csv_file() | Skip file, continue | (pipeline continues silently) | `CRITICAL: Permission denied` |
| `InvalidRowError` | parse_row() | Skip row, continue | (bad row count in report) | `WARNING: Skipping bad row` |

### try/except/else/finally usage

```
for each csv_file:
  try     → read_csv_file(csv_path)
  except  → FileNotFoundError / EmptyFileError / PermissionError → skip file
  else    → parse rows, collect valid ones        ← only if file read succeeded
  finally → log "finished attempt for this file" ← always, for audit trail
```

### Exception Chaining

`parse_row()` uses `raise InvalidRowError(...) from e` — this chains the
`ValueError`/`KeyError` from `int()` / `float()` onto the `InvalidRowError`.
The original traceback is preserved in `e.__cause__` for debugging.

---

## Program 3 — GPA Calculator

### Exceptions Caught

| Exception | Where | Recovery Action | User Sees | What Gets Logged |
|---|---|---|---|---|
| `ValueError` | Subject name input | Loop repeats | "Subject name cannot be empty" | `DEBUG: ...` |
| `NoSubjectsError` | done with 0 subjects | Loop repeats | "Must enter at least one subject" | `WARNING: User tried to finish with no subjects` |
| `InvalidGradeError` | Mark input | Loop repeats | "Invalid marks for '[subject]': expected 0–100" | `WARNING: ...` |
| `ValueError` | Non-numeric mark | Loop repeats | "Please enter a number" | `DEBUG: Non-numeric mark input` |
| `NoSubjectsError` | calculate_gpa() | Break out of loop | "Cannot calculate GPA with no subjects" | `INFO: Session ended with no data` |
| `GPAError` (base) | calculate_gpa() | Continue session | "Could not calculate GPA: ..." | `ERROR: GPA computation failed` |
| `KeyboardInterrupt` | main loop | Exit gracefully | "Session interrupted by user" | `INFO: Session interrupted by KeyboardInterrupt` |

### Why catch KeyboardInterrupt separately?

Bare `except:` would also catch `KeyboardInterrupt` and `SystemExit`, preventing
the user from closing the program with Ctrl+C. Always let those propagate or
handle them explicitly.

---

## Logging Levels Used and Why

| Level | Used For | Example |
|---|---|---|
| `DEBUG` | Detailed trace info for developers | "Finished attempt to process data1.csv" |
| `INFO` | Normal successful operations | "Records saved to students.txt" |
| `WARNING` | Expected problems, program continues | "Invalid marks input: out of range" |
| `ERROR` | Serious problem, one operation failed | "Skipping file: missing columns" |
| `CRITICAL` | System-level problem, may need intervention | "Permission denied reading file" |

### Two-handler pattern (used in Program 1)

```python
# Developer gets full detail in the log file
file_handler.setLevel(logging.DEBUG)

# User only sees WARNING and above on screen
console_handler.setLevel(logging.WARNING)
```

This separates "what the user needs to know" from "what the developer needs to debug."
A user does not need to see "DEBUG: Finished attempt for data1.csv" — that's noise.
But the developer debugging at 2am absolutely needs that.
