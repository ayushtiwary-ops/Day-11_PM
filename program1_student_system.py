"""
program1_student_system.py
Day 11 PM — Part A: Bulletproof Student Management System
Refactored from Day 9 AM student_system.py

Changes made:
  - Custom exceptions for domain-specific errors
  - try/except/else/finally on every user input
  - logging to student_errors.log
  - Meaningful error messages (user-facing vs developer-facing)
"""

import logging
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────
# Logging setup
#   - File handler: full DEBUG detail to student_errors.log
#   - Console handler: only user-friendly WARNING+ messages
# ─────────────────────────────────────────────────────────────────

logger = logging.getLogger("StudentSystem")
logger.setLevel(logging.DEBUG)

# File handler — detailed logs for developers
file_handler = logging.FileHandler("student_errors.log", mode="a", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(funcName)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))

# Console handler — clean messages for the user
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter("  ⚠️  %(message)s"))

logger.addHandler(file_handler)
logger.addHandler(console_handler)


# ─────────────────────────────────────────────────────────────────
# Custom Exceptions — specific errors for this domain
# ─────────────────────────────────────────────────────────────────

class StudentError(Exception):
    """Base exception for all student system errors."""
    pass


class DuplicateStudentError(StudentError):
    """Raised when attempting to add a student that already exists."""
    def __init__(self, name: str, subject: str):
        super().__init__(f"Student '{name}' already has a record for '{subject}'.")
        self.name    = name
        self.subject = subject


class InvalidMarksError(StudentError):
    """Raised when marks are outside the valid 0–100 range."""
    def __init__(self, value):
        super().__init__(f"Marks must be between 0 and 100, got: {value!r}")
        self.value = value


class StudentNotFoundError(StudentError):
    """Raised when a requested student does not exist."""
    def __init__(self, name: str):
        super().__init__(f"No records found for student '{name}'.")
        self.name = name


# ─────────────────────────────────────────────────────────────────
# Core data and functions
# ─────────────────────────────────────────────────────────────────

records: list[list] = [
    ["Aman",    "Math",    88],
    ["Priya",   "Physics", 91],
    ["Rahul",   "Math",    76],
    ["Sneha",   "Chemistry", 84],
    ["Vikram",  "Physics", 67],
]


def add_student(name: str, subject: str, marks: int) -> None:
    """Add a student record with full validation.

    Raises:
        DuplicateStudentError: If the name+subject combo already exists.
        InvalidMarksError:     If marks are outside 0–100.
    """
    # Validate marks first — raise BEFORE touching the data
    if not isinstance(marks, (int, float)) or not (0 <= marks <= 100):
        raise InvalidMarksError(marks)

    # Check for duplicates
    existing = [r for r in records if r[0] == name and r[1] == subject]
    if existing:
        raise DuplicateStudentError(name, subject)

    records.append([name, subject, marks])
    logger.debug(f"Added student: {name} | {subject} | {marks}")


def remove_student(name: str) -> int:
    """Remove all records for a student.

    Raises:
        StudentNotFoundError: If no records exist for this name.
    """
    global records
    before = len(records)
    records = [r for r in records if r[0] != name]
    removed = before - len(records)

    if removed == 0:
        raise StudentNotFoundError(name)

    logger.debug(f"Removed {removed} record(s) for '{name}'")
    return removed


def get_toppers(subject: str) -> list:
    """Return top 3 students for a subject.

    Raises:
        ValueError: If no records exist for the given subject.
    """
    subject_records = [r for r in records if r[1] == subject]
    if not subject_records:
        raise ValueError(f"No records found for subject '{subject}'.")
    return sorted(subject_records, key=lambda x: x[2], reverse=True)[:3]


def save_to_file(filename: str = "students.txt") -> None:
    """Save records to file.

    Raises:
        IOError: If file cannot be written (permissions, disk full, etc.)
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.write("Name,Subject,Marks\n")
        for r in records:
            f.write(f"{r[0]},{r[1]},{r[2]}\n")
    logger.info(f"Records saved to '{filename}' ({len(records)} rows)")


# ─────────────────────────────────────────────────────────────────
# Input helpers — all validated, all looping until correct input
# ─────────────────────────────────────────────────────────────────

def input_name(prompt: str) -> str:
    """Get a non-empty name from the user."""
    while True:
        try:
            name = input(prompt).strip().title()
            if not name:
                raise ValueError("Name cannot be empty.")
            if not all(c.isalpha() or c.isspace() for c in name):
                raise ValueError(f"Name should only contain letters, got: '{name}'")
        except ValueError as e:
            logger.warning(f"Invalid name input: {e}")
            print(f"  ❌ {e} Please try again.")
        else:
            return name   # else only runs if no exception was raised


def input_marks() -> int:
    """Get a valid integer mark 0–100 from the user."""
    while True:
        try:
            raw = input("  Marks (0–100): ").strip()
            marks = int(raw)           # raises ValueError if not an integer
            if not 0 <= marks <= 100:
                raise InvalidMarksError(marks)
        except ValueError:
            # int() failed — user typed letters
            logger.warning(f"Non-integer marks input: '{raw}'")
            print("  ❌ Please enter a whole number.")
        except InvalidMarksError as e:
            logger.warning(f"Out-of-range marks: {e}")
            print(f"  ❌ {e}")
        else:
            return marks


def input_subject() -> str:
    """Get a valid subject name from the user."""
    valid = {"Math", "Physics", "Chemistry"}
    while True:
        try:
            subject = input(f"  Subject ({'/'.join(sorted(valid))}): ").strip().title()
            if subject not in valid:
                raise ValueError(f"'{subject}' is not a recognised subject.")
        except ValueError as e:
            logger.warning(f"Invalid subject: {e}")
            print(f"  ❌ {e}")
        else:
            return subject


# ─────────────────────────────────────────────────────────────────
# Menu
# ─────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*45)
    print("   STUDENT MANAGEMENT SYSTEM (Bulletproof)")
    print("="*45)

    while True:
        print("\n  1 · Add student")
        print("  2 · Show toppers (by subject)")
        print("  3 · Remove student")
        print("  4 · View all records")
        print("  5 · Exit")

        try:
            choice = input("\n  Choice: ").strip()
            if choice not in {"1","2","3","4","5"}:
                raise ValueError(f"'{choice}' is not a valid menu option (1–5).")
        except ValueError as e:
            print(f"  ❌ {e}")
            continue

        if choice == "1":
            name    = input_name("  Name: ")
            subject = input_subject()
            marks   = input_marks()
            try:
                add_student(name, subject, marks)
            except DuplicateStudentError as e:
                logger.error(f"Duplicate entry attempt: {e}")
                print(f"  ❌ {e}")
            except StudentError as e:
                logger.error(f"Unexpected student error: {e}")
                print(f"  ❌ Something went wrong: {e}")
            else:
                print(f"  ✅ Added {name} | {subject} | {marks}")
            finally:
                # finally always runs — good for cleanup or audit
                logger.debug(f"Add student operation completed for '{name}'")

        elif choice == "2":
            subject = input_subject()
            try:
                toppers = get_toppers(subject)
            except ValueError as e:
                logger.warning(f"Toppers query failed: {e}")
                print(f"  ❌ {e}")
            else:
                print(f"\n  Top students in {subject}:")
                for r in toppers:
                    print(f"    {r[0]:<15} {r[2]}")

        elif choice == "3":
            name = input_name("  Student name to remove: ")
            try:
                removed = remove_student(name)
            except StudentNotFoundError as e:
                logger.warning(f"Remove failed: {e}")
                print(f"  ❌ {e}")
            else:
                print(f"  ✅ Removed {removed} record(s) for '{name}'.")

        elif choice == "4":
            if not records:
                print("  (no records)")
            else:
                print(f"\n  {'Name':<15} {'Subject':<12} Marks")
                print("  " + "─"*35)
                for r in records:
                    print(f"  {r[0]:<15} {r[1]:<12} {r[2]}")

        elif choice == "5":
            try:
                save_to_file()
            except IOError as e:
                logger.critical(f"Could not save records: {e}")
                print(f"  ⚠️  Could not save records: {e}")
                print("  Exiting without saving.")
            else:
                print("  💾 Records saved.")
            finally:
                print("  👋 Goodbye!\n")
                break


if __name__ == "__main__":
    main()
