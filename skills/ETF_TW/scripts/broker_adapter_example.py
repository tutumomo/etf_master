#!/usr/bin/env python3
from __future__ import annotations


class BrokerAdapterExample:
    """Example contract only. Live trading is not implemented in this version."""

    def get_quote(self, symbol: str):
        raise NotImplementedError

    def get_account(self, account_id: str):
        raise NotImplementedError

    def preview_order(self, order: dict):
        raise NotImplementedError

    def submit_order(self, order: dict):
        raise NotImplementedError("Live trading is future work")

    def cancel_order(self, order_id: str):
        raise NotImplementedError

    def get_order_status(self, order_id: str):
        raise NotImplementedError

    def list_positions(self, account_id: str):
        raise NotImplementedError
