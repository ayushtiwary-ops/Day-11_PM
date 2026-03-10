"""
program3_gpa_calculator.py
Day 11 PM — Part A: Bulletproof GPA Calculator
Refactored from Day 10 PM student_analytics.py

Demonstrates: custom exceptions, try/except/else/finally,
logging to file, user-friendly error separation.
"""

import logging
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────

log = logging.getLogger("GPACalc")
log.setLevel(logging.DEBUG)

fh = logging.FileHandler("gpa_errors.log", mode="a", encoding="utf-8")
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
log.addHandler(fh)


# ─────────────────────────────────────────────────────────────────
# Custom Exceptions
# ─────────────────────────────────────────────────────────────────

class GPAError(Exception):
    """Base exception for GPA computation errors."""
    pass

class NoSubjectsError(GPAError):
    """Raised when attempting GPA calculation with zero subjects."""
    pass

class SubjectLimitError(GPAError):
    """Raised when more than 10 subjects are attempted."""
    def __init__(self, count: int):
        super().__init__(f"Cannot register more than 10 subjects, attempted {count}.")

class InvalidGradeError(GPAError):
    """Raised when a grade/mark is not in a valid range."""
    def __init__(self, subject: str, value):
        super().__init__(
            f"Invalid marks for '{subject}': expected 0–100, got {value!r}"
        )


# ─────────────────────────────────────────────────────────────────
# Business logic
# ─────────────────────────────────────────────────────────────────

def calculate_gpa(marks: dict[str, float], scale: float = 10.0) -> float:
    """
    Calculate GPA from a dict of subject:mark pairs.

    Raises:
        NoSubjectsError:    If marks dict is empty.
        InvalidGradeError:  If any mark is outside 0–100.
        SubjectLimitError:  If more than 10 subjects provided.
        ValueError:         If scale is not positive.
    """
    if not marks:
        raise NoSubjectsError("Cannot calculate GPA with no subjects.")
    if len(marks) > 10:
        raise SubjectLimitError(len(marks))
    if scale <= 0:
        raise ValueError(f"GPA scale must be positive, got {scale}")

    for subject, mark in marks.items():
        if not isinstance(mark, (int, float)) or not (0 <= mark <= 100):
            raise InvalidGradeError(subject, mark)

    avg = sum(marks.values()) / len(marks)
    return round((avg / 100) * scale, 2)


def grade_letter(gpa: float, scale: float = 10.0) -> str:
    pct = (gpa / scale) * 100
    if pct >= 85:   return "A"
    elif pct >= 70: return "B"
    elif pct >= 55: return "C"
    else:           return "D"


# ─────────────────────────────────────────────────────────────────
# Input collection with validation
# ─────────────────────────────────────────────────────────────────

def collect_subjects() -> dict[str, float]:
    """
    Interactively collect subject names and marks from the user.
    Loops until the user types 'done' or enters up to 10 subjects.
    """
    marks = {}
    print("\n  Enter subjects and marks. Type 'done' when finished.\n")

    while len(marks) < 10:
        # Get subject name
        try:
            subject = input(f"  Subject {len(marks)+1} name (or 'done'): ").strip()
            if subject.lower() == "done":
                if not marks:
                    raise NoSubjectsError(
                        "You must enter at least one subject before finishing."
                    )
                break
            if not subject:
                raise ValueError("Subject name cannot be empty.")
            if subject in marks:
                raise ValueError(f"'{subject}' was already entered.")
        except NoSubjectsError as e:
            print(f"  ❌ {e}")
            log.warning(f"User tried to finish with no subjects: {e}")
            continue
        except ValueError as e:
            print(f"  ❌ {e}")
            continue

        # Get mark for this subject
        while True:
            try:
                raw  = input(f"  Mark for {subject} (0–100): ").strip()
                mark = float(raw)          # float to allow 85.5 etc.
                if not 0 <= mark <= 100:
                    raise InvalidGradeError(subject, mark)
            except ValueError:
                print(f"  ❌ Please enter a number, not '{raw}'.")
                log.debug(f"Non-numeric mark input for '{subject}': '{raw}'")
            except InvalidGradeError as e:
                print(f"  ❌ {e}")
                log.warning(str(e))
            else:
                # Only reached if no exception — store the valid mark
                marks[subject] = mark
                break

    return marks


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 45)
    print("   GPA CALCULATOR — Bulletproof Edition")
    print("=" * 45)

    session_open = True
    while session_open:
        try:
            marks = collect_subjects()
            gpa   = calculate_gpa(marks)
        except NoSubjectsError as e:
            # User exited without entering data
            log.info(f"Session ended with no data: {e}")
            print(f"\n  ℹ️  {e}")
            break
        except GPAError as e:
            # Catches any other GPAError subclass
            log.error(f"GPA computation failed: {e}")
            print(f"\n  ❌ Could not calculate GPA: {e}")
        except KeyboardInterrupt:
            # User pressed Ctrl+C — exit gracefully
            print("\n\n  Session interrupted by user.")
            log.info("Session interrupted by KeyboardInterrupt")
            break
        else:
            # Success path — only runs if no exception
            letter = grade_letter(gpa)
            print("\n  " + "─"*38)
            print(f"  GPA Result: {gpa} / 10.0  →  Grade {letter}")
            print(f"  Subjects:   {len(marks)}")
            for subj, mark in marks.items():
                print(f"    {subj:<20} {mark}")
            print("  " + "─"*38)
            log.info(f"GPA calculated: {gpa} ({len(marks)} subjects)")
        finally:
            # Always runs — whether success or failure
            again = input("\n  Calculate another? (y/n): ").strip().lower()
            if again != "y":
                session_open = False
                print("  👋 Goodbye!\n")

if __name__ == "__main__":
    main()
