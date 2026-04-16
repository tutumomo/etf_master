#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from typing import Any

from order_lifecycle import normalize_order_status


def normalize_sinopac_callback(api: Any, order: Any, status: Any) -> dict:
    order_id = str(getattr(status, 'id', '') or getattr(status, 'order_id', '') or getattr(order, 'id', ''))
    symbol = getattr(getattr(order, 'contract', None), 'code', '') or getattr(order, 'symbol', '')
    action = str(getattr(getattr(order, 'order', None), 'action', '') or getattr(order, 'action', '')).lower()
    quantity_raw = getattr(getattr(order, 'order', None), 'quantity', None)
    quantity = int(quantity_raw) * 1000 if quantity_raw is not None else int(getattr(order, 'quantity', 0) or 0)
    price = getattr(getattr(order, 'order', None), 'price', None) or getattr(order, 'price', None)
    raw_status = str(getattr(status, 'status', '') or getattr(order, 'status', '')).lower()
    normalized_status = normalize_order_status(raw_status)
    filled_quantity = getattr(status, 'deal_quantity', None)
    total_quantity = getattr(status, 'qty', None)
    if filled_quantity is not None:
        filled_quantity = int(filled_quantity)
    if total_quantity is not None:
        total_quantity = int(total_quantity)
    remaining_quantity = None
    if filled_quantity is not None and total_quantity is not None:
        remaining_quantity = total_quantity - filled_quantity

    row = {
        'order_id': order_id,
        'symbol': symbol,
        'action': action,
        'quantity': quantity,
        'price': price,
        'mode': 'live',
        'status': normalized_status,
        'raw_status': raw_status,
        'source': 'live_broker',
        'source_type': 'broker_callback',
        'observed_at': datetime.now().astimezone().isoformat(),
        'event_time': getattr(status, 'ts', None) or getattr(status, 'event_time', None),
        'verified': True,
        'broker_order_id': order_id,
        'broker_status': normalized_status,
        'broker_seq': getattr(status, 'seq', None) or getattr(status, 'seqno', None),
    }
    if filled_quantity is not None:
        row['filled_quantity'] = filled_quantity
    if total_quantity is not None:
        row['total_quantity'] = total_quantity
    if remaining_quantity is not None:
        row['remaining_quantity'] = remaining_quantity
    return row
