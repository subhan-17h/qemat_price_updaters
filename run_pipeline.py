#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


DEFAULT_EXPORT_URL = "https://asia-south1-qemat-a2a2c.cloudfunctions.net/exportAllProducts"
DEFAULT_METADATA_URL = "https://asia-south1-qemat-a2a2c.cloudfunctions.net/getProductMetadata"


def run_command(cmd: List[str], cwd: Path, dry_run: bool = False) -> None:
    pretty = " ".join(cmd)
    print(f"\n▶ Running: {pretty}", flush=True)
    if dry_run:
        print("  (dry-run) skipped", flush=True)
        return
    subprocess.run(cmd, cwd=str(cwd), check=True)


@contextmanager
def pipeline_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"Another price pipeline is already running ({lock_path})") from exc
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


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


def fetch_json(url: str, timeout: float) -> dict:
    separator = "&" if "?" in url else "?"
    cache_busted_url = f"{url}{separator}{urlencode({'_': int(time.time() * 1000)})}"
    request = Request(cache_busted_url, headers={"Accept": "application/json", "User-Agent": "qemat-price-updater/1.0"})
    with urlopen(request, timeout=timeout) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError(f"HTTP {response.status} from {url}")
        return json.loads(response.read().decode("utf-8"))


def normalize_metadata(payload: dict) -> dict:
    metadata = payload.get("metadata", payload)
    if not isinstance(metadata, dict):
        raise ValueError("Metadata response is not an object")
    return metadata


def get_metadata(metadata_url: str, timeout: float = 30.0) -> dict:
    return normalize_metadata(fetch_json(metadata_url, timeout))


def metadata_is_new_and_valid(metadata: dict, previous_version: str) -> bool:
    version = str(metadata.get("version", "")).strip()
    file_url = str(metadata.get("fileUrl", "")).strip()
    try:
        product_count = int(metadata.get("productCount", 0))
    except (TypeError, ValueError):
        product_count = 0
    return bool(version and version != previous_version and file_url and product_count > 0)


def wait_for_metadata_change(
    metadata_url: str,
    previous_version: str,
    wait_seconds: float,
    poll_seconds: float,
) -> dict:
    deadline = time.monotonic() + wait_seconds
    last_metadata: dict = {}
    last_error: Exception | None = None
    while True:
        try:
            last_metadata = get_metadata(metadata_url)
            if metadata_is_new_and_valid(last_metadata, previous_version):
                return last_metadata
            last_error = None
        except Exception as exc:  # transient metadata/network errors are retried until deadline
            last_error = exc

        if time.monotonic() >= deadline:
            detail = f" Last error: {last_error}" if last_error else f" Last metadata: {last_metadata}"
            raise TimeoutError("Timed out waiting for a new valid product bundle metadata version." + detail)
        time.sleep(min(poll_seconds, max(0.0, deadline - time.monotonic())))


def invoke_export(export_url: str, timeout: float) -> None:
    request = Request(export_url, headers={"Accept": "application/json", "User-Agent": "qemat-price-updater/1.0"})
    with urlopen(request, timeout=timeout) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError(f"Bundle export returned HTTP {response.status}")
        response.read()


def export_and_verify(
    export_url: str,
    metadata_url: str,
    previous_version: str,
    attempts: int = 3,
    request_timeout: float = 900.0,
    metadata_wait_seconds: float = 600.0,
    poll_seconds: float = 15.0,
) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        print(f"\n▶ Exporting grocery bundle (attempt {attempt}/{attempts})", flush=True)
        try:
            invoke_export(export_url, request_timeout)
            metadata = wait_for_metadata_change(
                metadata_url, previous_version, metadata_wait_seconds, poll_seconds
            )
            print(
                f"✅ Bundle export verified (version {metadata['version']}, "
                f"products {metadata['productCount']})",
                flush=True,
            )
            return metadata
        except Exception as exc:
            last_error = exc
            print(f"⚠️ Export attempt {attempt} did not verify: {exc}", flush=True)

            # A timed-out request may have completed remotely. Check before invoking it again.
            try:
                metadata = get_metadata(metadata_url)
                if metadata_is_new_and_valid(metadata, previous_version):
                    print(f"✅ Bundle export verified after request error (version {metadata['version']})")
                    return metadata
            except Exception as metadata_error:
                print(f"⚠️ Metadata check after export error failed: {metadata_error}")

            if attempt < attempts:
                time.sleep(30 * attempt)

    raise RuntimeError(f"Bundle export failed after {attempts} attempts: {last_error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run full Firebase -> price updater -> Firebase -> bundle pipeline.")
    parser.add_argument("--products-csv", default="products.csv", help="Path for products CSV used by main.py")
    parser.add_argument("--consolidated-csv", default="consolidated.csv", help="Path for consolidated CSV used by Firebase updater")
    parser.add_argument("--no-headless", action="store_true", help="Disable headless mode for Selenium stores")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip Step 1 (Firebase export to CSV)")
    parser.add_argument("--skip-price-update", action="store_true", help="Skip Step 2 (Python price update pipeline)")
    parser.add_argument("--skip-firebase-update", action="store_true", help="Skip Step 3 (Firebase price update)")
    parser.add_argument("--skip-bundle-export", action="store_true", help="Skip Step 4 (Cloud Function bundle export)")
    parser.add_argument("--require-all-stores", action="store_true", help="Abort before publishing if any populated store fails")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing or calling HTTP endpoints")
    parser.add_argument("--lock-file", default=".pipeline.lock", help="Non-blocking process lock path")
    parser.add_argument("--export-url", default=os.getenv("QEMAT_EXPORT_URL", DEFAULT_EXPORT_URL))
    parser.add_argument("--metadata-url", default=os.getenv("QEMAT_METADATA_URL", DEFAULT_METADATA_URL))
    return parser


def run_pipeline(args: argparse.Namespace, root: Path) -> int:
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
    print(f"   Require all populated stores: {'YES' if args.require_all_stores else 'NO'}")

    if not args.skip_fetch:
        run_command(["node", "getProducts/getMatchedProductsFromFirbase.js"], cwd=root, dry_run=args.dry_run)
        if not args.dry_run:
            if not products_csv.exists():
                raise FileNotFoundError(f"Expected products CSV not found after export: {products_csv}")
            validate_products_csv(products_csv)
            print(f"✅ Step 1 complete: {products_csv}")

    if not args.skip_price_update:
        if not args.dry_run and not products_csv.exists():
            raise FileNotFoundError(f"Products CSV not found: {products_csv}")
        if consolidated_csv.exists() and not args.dry_run:
            consolidated_csv.unlink()
            print(f"🧹 Removed stale consolidated output: {consolidated_csv}")

        cmd = ["python", "main.py", str(products_csv)]
        if not args.no_headless:
            cmd.append("--headless")
        if args.require_all_stores:
            cmd.append("--require-all-stores")
        run_command(cmd, cwd=root, dry_run=args.dry_run)

        if not args.dry_run:
            if consolidated_csv.exists():
                validate_consolidated_csv(consolidated_csv)
                print(f"✅ Step 2 complete: {consolidated_csv}")
            else:
                print("✅ Step 2 complete: no price changes to publish")

    if not args.skip_firebase_update:
        if consolidated_csv.exists():
            if not args.dry_run:
                validate_consolidated_csv(consolidated_csv)
            run_command(["node", "updateProducts/update_prices.js"], cwd=root, dry_run=args.dry_run)
            print("✅ Step 3 complete")
        elif args.skip_price_update and not args.dry_run:
            raise FileNotFoundError(f"Consolidated CSV not found: {consolidated_csv}")
        else:
            print("✅ Step 3 skipped: no price changes")

    should_export = not args.skip_bundle_export and not args.skip_firebase_update
    if should_export:
        if args.dry_run:
            print(f"\n▶ Would export bundle via: {args.export_url}\n  (dry-run) skipped")
        else:
            previous_metadata = get_metadata(args.metadata_url)
            previous_version = str(previous_metadata.get("version", "")).strip()
            if not previous_version:
                raise ValueError("Current product metadata has no version; refusing unverified export")
            export_and_verify(args.export_url, args.metadata_url, previous_version)

    full_run_completed = not args.skip_fetch and not args.skip_price_update and not args.skip_firebase_update
    if full_run_completed:
        clear_directory_contents(root / "reports", dry_run=args.dry_run)
        clear_directory_contents(root / "price_updates", dry_run=args.dry_run)
        print("✅ Cleanup complete: reports/ and price_updates/ cleared")

    print("\n🎉 Pipeline finished")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    root = Path(__file__).resolve().parent
    lock_path = Path(args.lock_file)
    if not lock_path.is_absolute():
        lock_path = root / lock_path
    with pipeline_lock(lock_path):
        return run_pipeline(args, root)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\n❌ Pipeline failed: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
