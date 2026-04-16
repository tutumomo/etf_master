#!/usr/bin/env python3
from __future__ import annotations


def calculate_dca(monthly_amount: float, years: int, annual_return: float = 0.06) -> dict:
    months = years * 12
    monthly_rate = annual_return / 12
    future_value = 0.0
    for _ in range(months):
        future_value = (future_value + monthly_amount) * (1 + monthly_rate)
    principal = monthly_amount * months
    gain = future_value - principal
    return {
        "monthly_amount": monthly_amount,
        "years": years,
        "months": months,
        "assumed_annual_return": annual_return,
        "principal": round(principal, 2),
        "projected_value": round(future_value, 2),
        "estimated_gain": round(gain, 2),
    }
