#!/usr/bin/env python3
"""
Multi-Instance Dashboard Manager for ETF_TW.
2026.3.31 Family Isolation Update.
Scans 'instances/' and spawns independent uvicorn services.
"""

import os
import subprocess
import time
import socket
import logging
import json
import sys
from pathlib import Path

# Root Discovery
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context

HOST = "127.0.0.1"
CHECK_INTERVAL = 30  # Seconds between health checks

# Global Manager Log (Optional, but let's make it agent-aware or global)
LOG_FILE = ROOT / "instances/dashboard_manager.log"

# Ensure instances dir exists
ROOT.joinpath("instances").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DashboardManager")

def is_port_open(port):
    """Check if the dashboard port is responding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((HOST, int(port)))
            return True
        except:
            return False

def start_instance(agent_id, port):
    """Execute the dashboard startup for a specific agent."""
    instance_log_dir = context.INSTANCES_DIR / agent_id / "logs"
    instance_log_dir.mkdir(exist_ok=True)
    instance_log = instance_log_dir / "uvicorn.log"
    
    logger.info(f"🚀 Launching Dashboard for {agent_id} on port {port}...")
    
    # Environment Isolation
    env = os.environ.copy()
    env["OPENCLAW_AGENT_NAME"] = agent_id
    env["AGENT_ID"] = agent_id
    
    python_exe = ROOT / ".venv/bin/python3"
    if not python_exe.exists():
        python_exe = Path(sys.executable)
        
    cmd = [
        str(python_exe), "-m", "uvicorn", 
        "dashboard.app:app", 
        "--host", HOST, 
        "--port", str(port),
        "--access-log", # Enable access logging to the file
    ]
    
    try:
        # Each agent gets its own log file for uvicorn access
        with open(instance_log, "a") as f:
            proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=f,
                stderr=f,
                env=env,
                start_new_session=True
            )
        logger.info(f"✅ {agent_id} spawned successfully (PID: {proc.pid})")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to spawn {agent_id}: {e}")
        return False

def manage():
    """Main management loop."""
    instances_dir = ROOT / "instances"
    
    # Support for the legacy 'state' if etf_master hasn't been migrated yet
    # (But we already migrated it in step 1)
    
    while True:
        logger.info("--- Dashboard Health Check Sweep ---")
        for agent_dir in instances_dir.iterdir():
            if not agent_dir.is_dir(): continue
            
            agent_id = agent_dir.name
            config_path = agent_dir / "instance_config.json"
            
            if not config_path.exists():
                continue
                
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                port = config.get("port", 5055)
                
                if not is_port_open(port):
                    logger.warning(f"⚠️ {agent_id} (Port {port}) is DOWN. Restarting...")
                    start_instance(agent_id, port)
                else:
                    logger.info(f"🟢 {agent_id} (Port {port}) is healthy.")
            except Exception as e:
                logger.error(f"Error managing {agent_id}: {e}")
                
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        manage()
    except KeyboardInterrupt:
        logger.info("Manager stopped by user.")
