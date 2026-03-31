#!/usr/bin/env python3
"""
Merge local GUI stock entries with Robinhood positions.

Rules:
1) Read GUI data from env variable GUI_DATA_PATH
2) Read Robinhood data from:
   ./robinhood_positions.json
3) If a ticker exists in both, keep Robinhood row and discard GUI row.
4) Merge into ./merged_data.json using a unified schema.
   Missing fields are written as null.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

load_dotenv("local.env")

GUI_DATA_PATH_RAW = os.getenv("GUI_DATA_PATH", None)
ROBINHOOD_DATA_PATH = Path("robinhood_positions.json")
OUTPUT_PATH = Path("merged_data.json")

# How to handle overlapping symbols between Robinhood and GUI data.
# "combine": merge overlap into one row (current merged logic)
# "separate": keep both rows as separate records
OVERLAP_MODE = "separate"


def resolve_path(raw_path: str) -> Path:
    cleaned = raw_path.strip().strip('"').strip("'")
    expanded = os.path.expandvars(os.path.expanduser(cleaned))
    path = Path(expanded)

    return path


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "").replace("$", "")
            if cleaned == "":
                return None
            return float(cleaned)
        return float(value)
    except (TypeError, ValueError):
        return None


def load_gui_data(path: Path) -> dict[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, dict):
        # Original format: { "QQQ": { ... }, ... }
        return {str(ticker).upper(): payload for ticker, payload in data.items()}

    if isinstance(data, list):
        # Newer tolerant format: [ {"symbol":"QQQ", ...}, ... ]
        normalized: dict[str, dict[str, Any]] = {}
        for row in data:
            if not isinstance(row, dict):
                continue
            ticker = row.get("symbol") or row.get("ticker")
            if not ticker:
                continue
            normalized[str(ticker).upper()] = row
        if normalized:
            return normalized

    raise ValueError(
        "Unsupported GUI data format. Expected dict keyed by ticker or list of objects."
    )


def load_robinhood_data(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("Expected Robinhood JSON to be a list of objects.")
    return [row for row in data if isinstance(row, dict)]


def normalize_gui_rows(gui_data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ticker, payload in gui_data.items():
        row: dict[str, Any] = {
            "symbol": ticker,
            "name": None,
            "quantity": None,
            "average_buy_price": None,
            "cost_basis": None,
            "current_price": None,
            "market_value": None,
            "total_return": None,
            "total_return_pct": None,
            "totalCost": None,
            "source": "vanguard",
        }

        if isinstance(payload, dict):
            quantity = _safe_float(payload.get("quantity", payload.get("qty")))
            total_cost = _safe_float(
                payload.get("totalCost", payload.get("total_cost", payload.get("cost_basis")))
            )
            current_price = _safe_float(
                payload.get("current_price", payload.get("currentPrice", payload.get("price")))
            )
            row["quantity"] = quantity
            row["totalCost"] = total_cost
            row["cost_basis"] = total_cost
            row["current_price"] = current_price
            if quantity not in (None, 0.0) and total_cost is not None:
                row["average_buy_price"] = total_cost / quantity
            if quantity is not None and current_price is not None:
                row["market_value"] = quantity * current_price
                row["total_return"] = row["market_value"] - (total_cost or 0.0)
                row["total_return_pct"] = (
                    (row["total_return"] / total_cost * 100.0) if total_cost else 0.0
                )
        rows.append(row)
    return rows


def normalize_robinhood_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        cleaned = dict(row)
        cleaned.setdefault("totalCost", None)
        cleaned["source"] = "robinhood"
        normalized.append(cleaned)
    return normalized


def ticker_set(rows: list[dict[str, Any]]) -> set[str]:
    tickers: set[str] = set()
    for row in rows:
        symbol = row.get("symbol")
        if symbol is not None:
            tickers.add(str(symbol).upper())
    return tickers


def unify_schema(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    all_columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                all_columns.append(key)
    return [{column: row.get(column, None) for column in all_columns} for row in rows]


def merge_rows_by_symbol(
    robinhood_rows: list[dict[str, Any]], gui_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    robinhood_by_symbol: dict[str, dict[str, Any]] = {
        str(row.get("symbol", "")).upper(): row
        for row in robinhood_rows
        if row.get("symbol") is not None
    }
    merged_tickers: list[str] = []
    non_overlap_gui_rows: list[dict[str, Any]] = []

    for gui_row in gui_rows:
        symbol = str(gui_row.get("symbol", "")).upper()
        if symbol in robinhood_by_symbol:
            rh_row = robinhood_by_symbol[symbol]

            rh_quantity = _safe_float(rh_row.get("quantity")) or 0.0
            gui_quantity = _safe_float(gui_row.get("quantity")) or 0.0
            merged_quantity = rh_quantity + gui_quantity

            rh_cost = _safe_float(rh_row.get("cost_basis")) or 0.0
            gui_cost = _safe_float(gui_row.get("cost_basis")) or 0.0
            merged_cost_basis = rh_cost + gui_cost

            gui_current_price = _safe_float(gui_row.get("current_price"))
            merged_current_price = gui_current_price

            merged_market_value = (
                merged_quantity * merged_current_price
                if merged_current_price is not None
                else None
            )
            merged_total_return = (
                (merged_market_value - merged_cost_basis)
                if merged_market_value is not None
                else None
            )
            merged_total_return_pct = (
                (merged_market_value / merged_cost_basis * 100.0)
                if (merged_market_value is not None and merged_cost_basis)
                else 0.0
            )

            rh_row["quantity"] = merged_quantity
            rh_row["cost_basis"] = merged_cost_basis
            rh_row["totalCost"] = merged_cost_basis
            rh_row["current_price"] = merged_current_price
            rh_row["average_buy_price"] = (
                (merged_cost_basis / merged_quantity) if merged_quantity else None
            )
            rh_row["market_value"] = merged_market_value
            rh_row["total_return"] = merged_total_return
            rh_row["total_return_pct"] = merged_total_return_pct
            rh_row["source"] = gui_row.get("source")
            merged_tickers.append(symbol)
        else:
            non_overlap_gui_rows.append(gui_row)

    merged_rows = robinhood_rows + non_overlap_gui_rows
    return merged_rows, merged_tickers, non_overlap_gui_rows


def keep_rows_separate(
    robinhood_rows: list[dict[str, Any]], gui_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    robinhood_symbols = {
        str(row.get("symbol", "")).upper()
        for row in robinhood_rows
        if row.get("symbol") is not None
    }
    overlap_tickers = sorted(
        str(row.get("symbol", "")).upper()
        for row in gui_rows
        if str(row.get("symbol", "")).upper() in robinhood_symbols
    )
    # Keep all rows in output, including overlaps, as separate records.
    merged_rows = robinhood_rows + gui_rows
    return merged_rows, overlap_tickers, gui_rows


def main() -> None:
    gui_data_path = GUI_DATA_PATH_RAW
    if not gui_data_path:
        raise FileNotFoundError(
            f"GUI data file not found at: {gui_data_path}. "
            "Set GUI_DATA_PATH to the full path of your GUI JSON file."
        )

    print(f"Using GUI_DATA_PATH: {gui_data_path}")
    gui_data = load_gui_data(Path(gui_data_path))
    robinhood_rows = normalize_robinhood_rows(load_robinhood_data(ROBINHOOD_DATA_PATH))
    gui_rows = normalize_gui_rows(gui_data)

    if OVERLAP_MODE == "separate":
        merged_rows, merged_tickers, non_overlap_gui_rows = keep_rows_separate(
            robinhood_rows, gui_rows
        )
    else:
        merged_rows, merged_tickers, non_overlap_gui_rows = merge_rows_by_symbol(
            robinhood_rows, gui_rows
        )

    merged_rows = unify_schema(merged_rows)
    non_overlap_tickers = [
        str(row.get("symbol", "")).upper() for row in non_overlap_gui_rows if row.get("symbol")
    ]

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(merged_rows, file, indent=2)
        file.write("\n")

    print(f"GUI rows loaded: {len(gui_rows)}")
    print(f"Robinhood rows loaded: {len(robinhood_rows)}")
    print(f"Overlap mode: {OVERLAP_MODE}")
    print(
        f"Overlapping tickers found: {len(merged_tickers)} "
        f"{sorted(merged_tickers)}"
    )
    if OVERLAP_MODE == "combine":
        print(
            f"GUI non-overlap rows kept: {len(non_overlap_gui_rows)} "
            f"{sorted(non_overlap_tickers)}"
        )
    else:
        print(f"GUI rows kept as separate records: {len(non_overlap_gui_rows)}")
    print(f"Merged rows written: {len(merged_rows)}")
    print(f"Output file: {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
