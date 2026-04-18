import os
from pathlib import Path

# Base Paths (Relative to the skill root)
ROOT = Path(__file__).resolve().parents[2]
INSTANCES_DIR = ROOT / "instances"

_WARNED_DEFAULT_INSTANCE = False


def get_instance_id():
    """Detect the current agent instance from environment variables.

    NOTE:
    - AGENT_ID is the primary env var in Hermes multi-instance mode.
    - OPENCLAW_AGENT_NAME is legacy-compatible fallback from migration period.
    - If both are missing, we fall back to "etf_master" but emit a warning once to avoid silent state contamination.
    """
    global _WARNED_DEFAULT_INSTANCE

    instance_id = os.environ.get("AGENT_ID") or os.environ.get("OPENCLAW_AGENT_NAME")
    if instance_id:
        return instance_id

    if not _WARNED_DEFAULT_INSTANCE:
        _WARNED_DEFAULT_INSTANCE = True
        try:
            import sys

            print(
                "WARN: AGENT_ID missing; fallback to legacy OPENCLAW_AGENT_NAME also not found; defaulting instance_id=etf_master. "
                "Set AGENT_ID=<instance_id> to avoid cross-instance state contamination.",
                file=sys.stderr,
            )
        except Exception:
            pass

    return "etf_master"

def get_instance_dir():
    """Returns the directory for the current agent instance."""
    instance_id = get_instance_id()
    instance_dir = INSTANCES_DIR / instance_id
    # Auto-create directory structure if missing (for the first run/migration)
    if not instance_dir.exists():
        instance_dir.mkdir(parents=True, exist_ok=True)
        (instance_dir / "state").mkdir(exist_ok=True)
        (instance_dir / "logs").mkdir(exist_ok=True)
        (instance_dir / "temp").mkdir(exist_ok=True)
        (instance_dir / "runtime").mkdir(exist_ok=True)
        (instance_dir / "private").mkdir(exist_ok=True)
    return instance_dir

def get_state_dir():
    """Returns the state directory for the current instance."""
    d = get_instance_dir() / "state"
    d.mkdir(exist_ok=True)
    return d

def get_private_dir():
    """Returns the private directory for certificates and secrets."""
    d = get_instance_dir() / "private"
    d.mkdir(exist_ok=True)
    return d

def get_log_dir():
    """Returns the log directory for the current instance."""
    d = get_instance_dir() / "logs"
    d.mkdir(exist_ok=True)
    return d

def get_temp_dir():
    """Returns the temp directory for the current instance."""
    d = get_instance_dir() / "temp"
    d.mkdir(exist_ok=True)
    return d

def get_runtime_dir():
    """Returns the runtime (PID, lock) directory for the current instance."""
    d = get_instance_dir() / "runtime"
    d.mkdir(exist_ok=True)
    return d

def get_instance_config():
    """Returns the config file path for the current instance."""
    return get_instance_dir() / "instance_config.json"

def get_broker_config():
    """Loads the broker configuration for the current instance."""
    config_path = get_instance_config()
    if config_path.exists():
        import json
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except:
            pass
    return {}

def get_port():
    """Returns the locked port for the current instance, defaults to 5055 in Hermes."""
    return get_broker_config().get("port", 5055)
