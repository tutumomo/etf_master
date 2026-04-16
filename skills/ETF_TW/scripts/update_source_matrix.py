#!/usr/bin/env python3
"""
Utility script to update source_health_matrix.md.
Usage: python update_source_matrix.py
"""

import datetime
import re
from pathlib import Path

MATRIX_PATH = Path(__file__).parent.parent / "references" / "source_health_matrix.md"

def update_checked_date():
    if not MATRIX_PATH.exists():
        print(f"Error: {MATRIX_PATH} not found.")
        return
    
    content = MATRIX_PATH.read_text(encoding="utf-8")
    today = datetime.date.today().isoformat()
    
    # Simple regex to update all dates in the table rows (assuming YYYY-MM-DD format)
    new_content = re.sub(r"\d{4}-\d{2}-\d{2}", today, content)
    
    MATRIX_PATH.write_text(new_content, encoding="utf-8")
    print(f"✓ Updated matrix last checked date to {today}")

if __name__ == "__main__":
    update_checked_date()
