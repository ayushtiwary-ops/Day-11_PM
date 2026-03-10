"""
program2_sales_pipeline.py
Day 11 PM — Part A: Bulletproof Sales Pipeline
Refactored from Day 11 AM sales_pipeline.py

Changes made:
  - Custom PipelineError hierarchy
  - try/except/else/finally in the main pipeline runner
  - logging with levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Each step fails independently — one bad file doesn't stop others
"""

import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("pipeline_errors.log", mode="a", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("SalesPipeline")


# ─────────────────────────────────────────────────────────────────
# Custom Exceptions
# ─────────────────────────────────────────────────────────────────

class PipelineError(Exception):
    """Base exception for all pipeline errors."""
    pass

class EmptyFileError(PipelineError):
    """Raised when a CSV file has no data rows."""
    pass

class MissingColumnsError(PipelineError):
    """Raised when required columns are absent from the CSV."""
    def __init__(self, missing: list, filename: str):
        super().__init__(
            f"File '{filename}' is missing required columns: {missing}"
        )
        self.missing  = missing
        self.filename = filename

class InvalidRowError(PipelineError):
    """Raised when a row has unparseable numeric fields."""
    pass


# ─────────────────────────────────────────────────────────────────
# Core functions — each raises specific exceptions
# ─────────────────────────────────────────────────────────────────

REQUIRED_COLUMNS = {"date", "product", "qty", "price"}


def read_csv_file(path: Path) -> list[dict]:
    """
    Read and validate a single CSV file.

    Raises:
        FileNotFoundError:   If the file does not exist.
        EmptyFileError:      If the file has a header but no data rows.
        MissingColumnsError: If required columns are absent.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # DictReader.fieldnames is None on empty file
        if reader.fieldnames is None:
            raise EmptyFileError(f"File is completely empty: {path.name}")

        # Check for required columns
        actual  = {col.strip().lower() for col in reader.fieldnames}
        missing = list(REQUIRED_COLUMNS - actual)
        if missing:
            raise MissingColumnsError(missing, path.name)

        rows = list(reader)

    if not rows:
        raise EmptyFileError(f"File has a header but no data rows: {path.name}")

    return rows


def parse_row(row: dict, filename: str) -> dict:
    """
    Parse and type-convert a single row.

    Raises:
        InvalidRowError: If qty or price cannot be converted to numbers.
    """
    try:
        return {
            "date":    row["date"].strip(),
            "product": row["product"].strip(),
            "qty":     int(row["qty"]),
            "price":   float(row["price"]),
        }
    except (ValueError, KeyError) as e:
        raise InvalidRowError(
            f"Cannot parse row in '{filename}': {dict(row)} — {e}"
        ) from e  # exception chaining: preserves the original error


def calculate_revenue(rows: list[dict]) -> dict[str, float]:
    revenue: dict = defaultdict(float)
    for row in rows:
        revenue[row["product"]] += row["qty"] * row["price"]
    return dict(revenue)


# ─────────────────────────────────────────────────────────────────
# Resilient pipeline runner
# ─────────────────────────────────────────────────────────────────

def run_pipeline(data_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    all_rows:   list[dict] = []
    bad_rows:   int        = 0
    files_ok:   list[str]  = []
    files_fail: list[str]  = []

    csv_files = sorted(data_dir.glob("data*.csv"))

    if not csv_files:
        log.warning(f"No data*.csv files found in {data_dir}")
        return

    log.info(f"Found {len(csv_files)} files to process")

    for csv_path in csv_files:
        log.info(f"Processing: {csv_path.name}")

        try:
            raw_rows = read_csv_file(csv_path)

        except FileNotFoundError as e:
            # Should not happen after glob — but be defensive
            log.error(f"File disappeared: {e}")
            files_fail.append(csv_path.name)
            continue

        except (EmptyFileError, MissingColumnsError) as e:
            # File exists but is unusable — log it, skip it, move on
            log.error(f"Skipping {csv_path.name}: {e}")
            files_fail.append(csv_path.name)
            continue

        except PermissionError as e:
            log.critical(f"Permission denied for {csv_path.name}: {e}")
            files_fail.append(csv_path.name)
            continue

        else:
            # else block: only runs if NO exception was raised in try
            # Good place for "success path" logic
            parsed = []
            for row in raw_rows:
                try:
                    parsed.append(parse_row(row, csv_path.name))
                except InvalidRowError as e:
                    log.warning(f"Skipping bad row: {e}")
                    bad_rows += 1

            all_rows.extend(parsed)
            files_ok.append(csv_path.name)
            log.info(f"  ✅ {len(parsed)} valid rows from {csv_path.name}")

        finally:
            # finally always runs — used here for audit/cleanup
            log.debug(f"Finished attempt to process {csv_path.name}")

    # Export results
    if all_rows:
        revenue = calculate_revenue(all_rows)
        summary = {
            "metadata": {
                "files_processed": len(files_ok),
                "files_failed":    len(files_fail),
                "total_rows":      len(all_rows),
                "bad_rows_skipped": bad_rows,
                "generated_at":    datetime.now().isoformat()[:19],
            },
            "revenue_by_product": {
                k: round(v, 2)
                for k, v in sorted(revenue.items(), key=lambda x: x[1], reverse=True)
            },
        }
        out = output_dir / "revenue_summary.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        log.info(f"Output written to {out}")
    else:
        log.error("No valid rows found across all files. No output generated.")


if __name__ == "__main__":
    HERE = Path(__file__).parent
    run_pipeline(HERE / "data", HERE / "output2")
