import ast
import json
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def _to_float(value: Any) -> Optional[float]:
    """Convert value to float safely."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_price_history(raw_history: Any) -> List[Dict[str, Any]]:
    """Parse price_history from JSON string/list into a list of dicts."""
    if raw_history is None or (isinstance(raw_history, float) and pd.isna(raw_history)):
        return []

    if isinstance(raw_history, list):
        return [item for item in raw_history if isinstance(item, dict)]

    if isinstance(raw_history, str):
        text = raw_history.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except Exception:
            try:
                parsed = ast.literal_eval(text)
            except Exception:
                return []

        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]

    return []


def _get_previous_price_from_history(history: List[Dict[str, Any]]) -> Optional[float]:
    """
    Return previous price from history (entry before the latest one).
    Expected structure after update: [... old ..., new_current]
    """
    prices: List[float] = []
    for entry in history:
        price = _to_float(entry.get("price"))
        if price is not None and price > 0:
            prices.append(price)

    if len(prices) < 2:
        return None
    return prices[-2]


def filter_consolidated_by_price_history(
    consolidated_df: pd.DataFrame, max_change_pct: float = 50.0
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Drop records where price change vs previous history price is outside +/- max_change_pct.
    """
    if consolidated_df.empty:
        return consolidated_df, {"total": 0, "checked": 0, "dropped": 0, "kept": 0, "skipped_no_history": 0}

    drop_indices: List[int] = []
    checked = 0
    skipped_no_history = 0

    for idx, row in consolidated_df.iterrows():
        current_price = _to_float(row.get("price"))
        if current_price is None or current_price <= 0:
            skipped_no_history += 1
            continue

        history = _parse_price_history(row.get("price_history"))
        previous_price = _get_previous_price_from_history(history)
        if previous_price is None or previous_price <= 0:
            skipped_no_history += 1
            continue

        checked += 1
        pct_change = ((current_price - previous_price) / previous_price) * 100.0
        if pct_change > max_change_pct or pct_change < -max_change_pct:
            drop_indices.append(idx)

    filtered_df = consolidated_df.drop(index=drop_indices).reset_index(drop=True)
    stats = {
        "total": len(consolidated_df),
        "checked": checked,
        "dropped": len(drop_indices),
        "kept": len(filtered_df),
        "skipped_no_history": skipped_no_history,
    }
    return filtered_df, stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify consolidated.csv and remove updates outside allowed percentage change."
    )
    parser.add_argument("input_csv", help="Path to input consolidated CSV")
    parser.add_argument("--output-csv", default="consolidated_verified.csv", help="Path to output verified CSV")
    parser.add_argument("--max-change-pct", type=float, default=50.0, help="Maximum allowed absolute percentage change")
    args = parser.parse_args()

    df = pd.read_csv(args.input_csv)
    verified_df, stats = filter_consolidated_by_price_history(df, max_change_pct=args.max_change_pct)
    verified_df.to_csv(args.output_csv, index=False)

    print(
        f"Verification complete: total={stats['total']}, checked={stats['checked']}, "
        f"dropped={stats['dropped']}, kept={stats['kept']}, skipped_no_history={stats['skipped_no_history']}"
    )
