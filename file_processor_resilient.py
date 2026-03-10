"""
file_processor_resilient.py
Day 11 PM — Part B: Resilient CSV Processor with Retry Logic

Processes a directory of CSV files. Handles:
  - Corrupted/empty/wrong-format files (logged + skipped)
  - PermissionError (retried up to 3 times with 1s delay)
Exports a processing_report.json with full details.

Usage:
    python file_processor_resilient.py
"""

import csv
import json
import logging
import time
import traceback
from datetime import datetime
from pathlib import Path
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("processor.log", mode="a", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("FileProcessor")


# ─────────────────────────────────────────────────────────────────
# Custom Exceptions
# ─────────────────────────────────────────────────────────────────

class ProcessorError(Exception):
    """Base exception for file processor."""
    pass

class CorruptedFileError(ProcessorError):
    """File cannot be parsed as valid CSV."""
    pass

class EmptyFileError(ProcessorError):
    """File has no data rows."""
    pass

class WrongFormatError(ProcessorError):
    """File is missing required columns."""
    pass


# ─────────────────────────────────────────────────────────────────
# Retry logic — wraps any callable, retries on PermissionError
# ─────────────────────────────────────────────────────────────────

def with_retry(func, *args, max_attempts: int = 3, delay: float = 1.0, **kwargs):
    """
    Call func(*args, **kwargs), retrying up to max_attempts times if a
    PermissionError is raised. Waits `delay` seconds between attempts.

    Only PermissionError is retried — other exceptions propagate immediately.
    This is an important design choice: don't retry programming errors
    like ValueError or TypeError.

    Args:
        func:         Callable to attempt.
        *args:        Positional args for func.
        max_attempts: Maximum number of tries. Default 3.
        delay:        Seconds between retries. Default 1.
        **kwargs:     Keyword args for func.

    Returns:
        Whatever func returns on success.

    Raises:
        PermissionError: If all attempts fail.
        Any other exception: Propagates immediately without retry.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except PermissionError as e:
            if attempt == max_attempts:
                log.error(f"All {max_attempts} attempts failed: {e}")
                raise  # re-raise after exhausting retries
            log.warning(
                f"PermissionError on attempt {attempt}/{max_attempts}. "
                f"Retrying in {delay}s..."
            )
            time.sleep(delay)
        # Other exceptions are NOT caught here — they propagate immediately


# ─────────────────────────────────────────────────────────────────
# File reading and parsing
# ─────────────────────────────────────────────────────────────────

REQUIRED_COLUMNS = {"date", "product", "qty", "price"}


def _read_file(path: Path) -> list[dict]:
    """
    Internal: open and parse a CSV file. Called via with_retry().
    Raises PermissionError, CorruptedFileError, EmptyFileError, WrongFormatError.
    """
    # PermissionError raised here naturally by open() on restricted files
    with open(path, newline="", encoding="utf-8") as f:
        try:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise EmptyFileError(f"{path.name} is completely empty")

            cols = {c.strip().lower() for c in reader.fieldnames}
            missing = REQUIRED_COLUMNS - cols
            if missing:
                raise WrongFormatError(
                    f"{path.name} missing columns: {sorted(missing)}"
                )

            rows = list(reader)

        except csv.Error as e:
            # csv.Error means the file content is malformed CSV
            raise CorruptedFileError(f"{path.name} is corrupted: {e}") from e

    if not rows:
        raise EmptyFileError(f"{path.name} has header but no data rows")

    return rows


def parse_rows(raw: list[dict], filename: str) -> tuple[list[dict], list[str]]:
    """
    Convert raw string rows to typed dicts. Returns (good_rows, skipped_messages).
    """
    good    = []
    skipped = []

    for row in raw:
        try:
            good.append({
                "date":    row["date"].strip(),
                "product": row["product"].strip(),
                "qty":     int(row["qty"]),
                "price":   float(row["price"]),
            })
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            msg = f"Bad row in {filename}: {dict(row)} — {e}"
            skipped.append(msg)
            log.warning(msg)

    return good, skipped


def aggregate(rows: list[dict]) -> dict:
    """Compute total qty and revenue per product."""
    totals: dict = defaultdict(lambda: {"qty": 0, "revenue": 0.0})
    for row in rows:
        p = row["product"]
        totals[p]["qty"]     += row["qty"]
        totals[p]["revenue"] += row["qty"] * row["price"]
    return {k: {**v, "revenue": round(v["revenue"], 2)} for k, v in totals.items()}


# ─────────────────────────────────────────────────────────────────
# Main processor
# ─────────────────────────────────────────────────────────────────

def process_directory(data_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        log.warning(f"No CSV files found in {data_dir}")
        return

    log.info(f"Starting processor. Files to process: {len(csv_files)}")

    # Report structure
    report = {
        "metadata": {
            "generated_at":    datetime.now().isoformat()[:19],
            "directory":       str(data_dir),
            "files_found":     len(csv_files),
            "files_processed": 0,
            "files_failed":    0,
            "total_rows":      0,
        },
        "aggregates":    {},
        "error_details": {},
    }

    all_rows: list[dict] = []

    for csv_path in csv_files:
        log.info(f"  Processing: {csv_path.name}")

        try:
            # with_retry wraps the read: retries on PermissionError, not others
            raw_rows = with_retry(_read_file, csv_path)

        except PermissionError as e:
            # All retries exhausted
            log.error(f"FAILED (permission): {csv_path.name}")
            report["error_details"][csv_path.name] = {
                "error_type": "PermissionError",
                "message":    str(e),
                "traceback":  traceback.format_exc(),
            }
            report["metadata"]["files_failed"] += 1
            continue

        except (CorruptedFileError, EmptyFileError, WrongFormatError) as e:
            # These are non-retryable — log full traceback, skip file
            log.error(f"FAILED ({type(e).__name__}): {e}")
            report["error_details"][csv_path.name] = {
                "error_type": type(e).__name__,
                "message":    str(e),
                "traceback":  traceback.format_exc(),
            }
            report["metadata"]["files_failed"] += 1
            continue

        except Exception as e:
            # Catch-all for truly unexpected errors — log and move on
            log.exception(f"UNEXPECTED error processing {csv_path.name}: {e}")
            report["error_details"][csv_path.name] = {
                "error_type": type(e).__name__,
                "message":    str(e),
                "traceback":  traceback.format_exc(),
            }
            report["metadata"]["files_failed"] += 1
            continue

        else:
            # File read succeeded — parse rows
            parsed, skipped = parse_rows(raw_rows, csv_path.name)
            all_rows.extend(parsed)
            report["metadata"]["files_processed"] += 1
            report["metadata"]["total_rows"]      += len(parsed)
            log.info(f"  ✅ {len(parsed)} rows OK, {len(skipped)} skipped")

            if skipped:
                report["error_details"].setdefault(csv_path.name, {})["skipped_rows"] = skipped

        finally:
            log.debug(f"  Finished processing attempt: {csv_path.name}")

    # Aggregates
    if all_rows:
        report["aggregates"] = aggregate(all_rows)

    # Write report
    report_path = output_dir / "processing_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    log.info(f"Report written to {report_path}")
    log.info(
        f"Summary: {report['metadata']['files_processed']} OK, "
        f"{report['metadata']['files_failed']} failed"
    )


# ─────────────────────────────────────────────────────────────────
# Setup test data (good, empty, corrupted, wrong format)
# ─────────────────────────────────────────────────────────────────

def setup_test_data(data_dir: Path) -> None:
    """Create a mix of good and bad files for testing."""
    data_dir.mkdir(parents=True, exist_ok=True)

    # Good file
    (data_dir / "good.csv").write_text(
        "date,product,qty,price\n"
        "2026-01-10,Laptop,2,45000\n"
        "2026-01-11,Mouse,5,600\n",
        encoding="utf-8"
    )

    # Empty file
    (data_dir / "empty.csv").write_text("", encoding="utf-8")

    # Corrupted CSV (unmatched quotes)
    (data_dir / "corrupted.csv").write_text(
        'date,product,qty,price\n'
        '"2026-01-10,"Laptop,2,45000\n',  # malformed quote
        encoding="utf-8"
    )

    # Wrong format — missing 'price' column
    (data_dir / "wrong_format.csv").write_text(
        "date,product,qty,discount\n"
        "2026-01-10,Keyboard,3,10\n",
        encoding="utf-8"
    )

    # Has header but no rows
    (data_dir / "header_only.csv").write_text(
        "date,product,qty,price\n",
        encoding="utf-8"
    )

    # Good file with one bad row
    (data_dir / "mostly_good.csv").write_text(
        "date,product,qty,price\n"
        "2026-01-12,Monitor,1,12000\n"
        "2026-01-12,Earbuds,not_a_number,2500\n"  # bad qty
        "2026-01-13,Keyboard,2,1800\n",
        encoding="utf-8"
    )


if __name__ == "__main__":
    HERE     = Path(__file__).parent
    DATA_DIR = HERE / "processor_test_data"
    OUT_DIR  = HERE / "processor_output"

    setup_test_data(DATA_DIR)
    process_directory(DATA_DIR, OUT_DIR)
