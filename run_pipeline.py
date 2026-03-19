#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

import pandas as pd


def run_command(cmd: List[str], cwd: Path, dry_run: bool = False) -> None:
    pretty = " ".join(cmd)
    print(f"\n▶ Running: {pretty}")
    if dry_run:
        print("  (dry-run) skipped")
        return
    subprocess.run(cmd, cwd=str(cwd), check=True)


def clear_directory_contents(directory: Path, dry_run: bool = False) -> None:
    """Delete all files/subdirectories inside a directory but keep the directory."""
    if not directory.exists():
        return
    if not directory.is_dir():
        raise NotADirectoryError(f"Expected directory, got: {directory}")

    print(f"\n🧹 Clearing directory: {directory}")
    if dry_run:
        print("  (dry-run) skipped")
        return

    for item in directory.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def validate_products_csv(products_csv: Path) -> None:
    required_columns = {"product_id", "store_id", "original_url", "price"}
    df = pd.read_csv(products_csv, nrows=5)
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(f"{products_csv} missing required columns: {', '.join(missing)}")


def validate_consolidated_csv(consolidated_csv: Path) -> None:
    required_columns = {"product_id", "price", "price_history"}
    df = pd.read_csv(consolidated_csv, nrows=5)
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(f"{consolidated_csv} missing required columns: {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run full Firebase -> price updater -> Firebase pipeline."
    )
    parser.add_argument("--products-csv", default="products.csv", help="Path for products CSV used by main.py")
    parser.add_argument("--consolidated-csv", default="consolidated.csv", help="Path for consolidated CSV used by Firebase updater")
    parser.add_argument("--no-headless", action="store_true", help="Disable headless mode for Selenium stores")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip Step 1 (Firebase export)")
    parser.add_argument("--skip-price-update", action="store_true", help="Skip Step 2 (Python price update pipeline)")
    parser.add_argument("--skip-firebase-update", action="store_true", help="Skip Step 3 (Firebase price update)")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    products_csv = (root / args.products_csv).resolve() if not Path(args.products_csv).is_absolute() else Path(args.products_csv)
    consolidated_csv = (root / args.consolidated_csv).resolve() if not Path(args.consolidated_csv).is_absolute() else Path(args.consolidated_csv)
    service_account = root / "serviceAccountKey.json"

    if shutil.which("node") is None:
        raise RuntimeError("node is not installed or not in PATH")
    if shutil.which("python") is None:
        raise RuntimeError("python is not installed or not in PATH")

    if (not args.skip_fetch or not args.skip_firebase_update) and not service_account.exists():
        raise FileNotFoundError(f"Missing Firebase key: {service_account}")

    print("🚀 Starting full pipeline")
    print(f"   Root: {root}")
    print(f"   Products CSV: {products_csv}")
    print(f"   Consolidated CSV: {consolidated_csv}")
    print(f"   Headless: {'NO' if args.no_headless else 'YES'}")

    # Step 1: fetch products from Firebase to products.csv
    if not args.skip_fetch:
        run_command(["node", "getProducts/getMatchedProductsFromFirbase.js"], cwd=root, dry_run=args.dry_run)
        if not args.dry_run:
            if not products_csv.exists():
                raise FileNotFoundError(f"Expected products CSV not found after export: {products_csv}")
            validate_products_csv(products_csv)
            print(f"✅ Step 1 complete: {products_csv}")

    # Step 2: run Python price update flow
    if not args.skip_price_update:
        if not args.dry_run and not products_csv.exists():
            raise FileNotFoundError(f"Products CSV not found: {products_csv}")

        cmd = ["python", "main.py", str(products_csv)]
        if not args.no_headless:
            cmd.append("--headless")
        run_command(cmd, cwd=root, dry_run=args.dry_run)

        if not args.dry_run:
            if not consolidated_csv.exists():
                raise FileNotFoundError(f"Expected consolidated CSV not found after price updates: {consolidated_csv}")
            validate_consolidated_csv(consolidated_csv)
            print(f"✅ Step 2 complete: {consolidated_csv}")

    # Step 3: update Firebase prices using consolidated.csv
    if not args.skip_firebase_update:
        if not args.dry_run and not consolidated_csv.exists():
            raise FileNotFoundError(f"Consolidated CSV not found: {consolidated_csv}")
        run_command(["node", "updateProducts/update_prices.js"], cwd=root, dry_run=args.dry_run)
        print("✅ Step 3 complete")

    # Post-success cleanup only after full run (all 3 steps executed)
    full_run_completed = (
        not args.skip_fetch
        and not args.skip_price_update
        and not args.skip_firebase_update
    )
    if full_run_completed:
        clear_directory_contents(root / "reports", dry_run=args.dry_run)
        clear_directory_contents(root / "price_updates", dry_run=args.dry_run)
        print("✅ Cleanup complete: reports/ and price_updates/ cleared")

    print("\n🎉 Pipeline finished")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\n❌ Pipeline failed: {exc}")
        raise SystemExit(1)
