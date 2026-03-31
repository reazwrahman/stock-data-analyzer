#!/usr/bin/env python3
"""
Robinhood investment data accessor.

This script logs into Robinhood using the open-source `robin_stocks` library,
fetches investment/account data, and prints a readable summary.

Security notes:
- Credentials are requested interactively (not hardcoded).
- Password is entered via getpass (hidden input).
- Login uses store_session=False so this script does not persist auth locally.
- No credentials are written to disk by this script.

Usage:
  1) Install dependency:
       pip install robin-stocks
  2) Run:
       python robinhood_accessor.py
"""

from __future__ import annotations

import getpass
import json
from dataclasses import dataclass, asdict
from typing import Any

from robin_stocks import robinhood as rh



@dataclass
class PositionSummary:
    symbol: str
    name: str
    quantity: float
    average_buy_price: float
    cost_basis: float
    current_price: float
    market_value: float
    total_return: float
    total_return_pct: float


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def login() -> None:
    username = input("Robinhood username/email: ").strip()
    password = getpass.getpass("Robinhood password: ")
    mfa_code = input("MFA code (press Enter if not prompted): ").strip() or None

    rh.authentication.login(
        username=username,
        password=password,
        mfa_code=mfa_code,
        store_session=False,
    )


def build_positions() -> list[PositionSummary]:
    holdings = rh.account.build_holdings()
    positions: list[PositionSummary] = []

    for symbol, data in holdings.items():
        name = data.get("name") or symbol
        quantity = _safe_float(data.get("quantity"))
        average_buy_price = _safe_float(data.get("average_buy_price"))
        current_price = _safe_float(data.get("price"))
        cost_basis = quantity * average_buy_price
        market_value = quantity * current_price
        total_return = market_value - cost_basis
        total_return_pct = (total_return / cost_basis * 100.0) if cost_basis else 0.0

        positions.append(
            PositionSummary(
                symbol=symbol,
                name=name,
                quantity=quantity,
                average_buy_price=average_buy_price,
                cost_basis=cost_basis,
                current_price=current_price,
                market_value=market_value,
                total_return=total_return,
                total_return_pct=total_return_pct,
            )
        )

    positions.sort(key=lambda p: p.market_value, reverse=True)
    return positions


def get_additional_info() -> dict[str, Any]:
    account_profile = rh.account.load_account_profile(info=None)
    portfolio_profile = rh.account.load_portfolio_profile(info=None)
    open_positions = rh.account.get_open_stock_positions()

    return {
        "account_profile": account_profile,
        "portfolio_profile": portfolio_profile,
        "open_positions_count": len(open_positions) if isinstance(open_positions, list) else 0,
    }


def dump_positions_to_json(
    positions: list[PositionSummary], output_path: str = "robinhood_positions.json"
) -> None:
    payload = [asdict(position) for position in positions]
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, indent=2)
        json_file.write("\n")
    print(f"\nSaved {len(payload)} position records to {output_path}")


def print_report(positions: list[PositionSummary]) -> None:
    print("\n=== POSITION SUMMARY ===")
    if not positions:
        print("No active positions found.")
    else:
        for p in positions:
            print(
                f"{p.symbol:6} | {p.name[:30]:30} | qty={p.quantity:.4f} | "
                f"cost=${p.cost_basis:,.2f} | value=${p.market_value:,.2f} | price=${p.current_price:,.2f} |"
                f"return=${p.total_return:,.2f} ({p.total_return_pct:.2f}%)"
            )

    total_cost = sum(p.cost_basis for p in positions)
    total_value = sum(p.market_value for p in positions)
    total_return = total_value - total_cost
    total_return_pct = (total_return / total_cost * 100.0) if total_cost else 0.0

    print("\n=== PORTFOLIO TOTALS ===")
    print(f"Total Cost Basis : ${total_cost:,.2f}")
    print(f"Total Market Value: ${total_value:,.2f}")
    print(f"Total Return     : ${total_return:,.2f} ({total_return_pct:.2f}%)")


def main() -> None:
    print("Robinhood Accessor")
    print("This script does not store credentials or local login sessions.")
    login()
    positions = build_positions()
    dump_positions_to_json(positions)
    print_report(positions)

    # Explicitly clear auth token after use.
    rh.authentication.logout()

    # Keep a machine-readable output ready in-memory for extension if needed.
    _ = [asdict(p) for p in positions]


if __name__ == "__main__":
    main()
