#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from progress_tracker import ProgressTracker  # noqa: E402
from updaters import carrefour_price_updater as carrefour  # noqa: E402
from updaters import imtiaz_price_updater as imtiaz  # noqa: E402


UPDATERS = {
    "Imtiaz": imtiaz.generate_price_comparison,
    "Carrefour": carrefour.generate_price_comparison,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape one Imtiaz and one Carrefour product without publishing")
    parser.add_argument("--products-csv", default=str(ROOT / "products.csv"))
    args = parser.parse_args()

    products = pd.read_csv(args.products_csv)
    with tempfile.TemporaryDirectory(prefix="qemat-selenium-smoke-") as temp:
        temp_dir = Path(temp)
        for store, updater in UPDATERS.items():
            candidates = products[
                (products["store_id"] == store)
                & products["original_url"].notna()
                & (products["original_url"].astype(str).str.strip() != "")
            ]
            if candidates.empty:
                raise RuntimeError(f"No {store} product with a URL was found in {args.products_csv}")

            input_csv = temp_dir / f"{store.lower()}_input.csv"
            output_csv = temp_dir / f"{store.lower()}_comparison.csv"
            candidates.head(1).to_csv(input_csv, index=False)
            tracker = ProgressTracker(str(temp_dir / f"{store.lower()}_progress.csv"), store)
            print(f"▶ Smoke testing {store}: {candidates.iloc[0]['name']}", flush=True)
            updater(
                csv_file_path=str(input_csv),
                output_path=str(output_csv),
                delay_seconds=0,
                progress_tracker=tracker,
                headless=True,
            )
            if not output_csv.exists() or pd.read_csv(output_csv).empty:
                raise RuntimeError(f"{store} smoke test did not produce a comparison row")
            print(f"✅ {store} one-product smoke test passed", flush=True)

    print("✅ Selenium smoke test passed without publishing data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
