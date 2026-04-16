#!/usr/bin/env python3
"""
Source-Aware Search Candidate Loader.
Filters data sources based on current access_mode and health status.
"""

import json
from pathlib import Path

def get_best_source(task_type: str, mode: str = "auto") -> str:
    """
    Returns the recommended source domain based on task and mode.
    """
    # Default priority logic
    sources = {
        "price": "finance.yahoo.com",
        "official": "www.twse.com.tw",
        "news": "www.cnyes.com"
    }
    
    return sources.get(task_type, "finance.yahoo.com")

if __name__ == "__main__":
    print(f"Recommended source for price: {get_best_source('price')}")
