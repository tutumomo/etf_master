#!/usr/bin/env python3
import subprocess
import os

# Define the family members to be synced
FAMILY_MEMBERS = ["etf_master", "etf_wife", "etf_son", "etf_daughter"]

# Path to the setup_agent.py tool
SETUP_TOOL = os.path.join(os.path.dirname(__file__), "setup_agent.py")

def sync_family():
    print(f"\n--- 🚀 Starting Full Family Financial Ecosystem Sync ---")
    for agent in FAMILY_MEMBERS:
        print(f"\n[Processing {agent}]")
        cmd = ["python3", SETUP_TOOL, "--link", agent]
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            print(f"Error syncing {agent}: {e.stderr}")

    print(f"\n--- ✅ Family Synchronization Complete ---")
    print(f"Master, Wife, Son, and Daughter are now aligned with:")
    print(f"1. ETF_TW (Execution)")
    print(f"2. Stock Analysis (Quantitative)")
    print(f"3. Stock Market Pro (Charting)")
    print(f"4. Taiwan Finance (Strategy)")

if __name__ == "__main__":
    sync_family()
