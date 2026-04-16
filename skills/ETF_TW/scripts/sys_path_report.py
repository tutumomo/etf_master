import os
import sys

def get_report():
    # HERMES_HOME (環境變數或預設路徑)
    hermes_home = os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes'))
    
    # ACTIVE_PROFILE (由工作目錄推論或環境變數)
    # The profile is usually the basename of the profile directory if it's a profile root.
    cwd = os.getcwd()
    active_profile = os.environ.get('ACTIVE_PROFILE', os.path.basename(cwd))
    
    # ETF_TW_WORKDIR (目前腳本所在的技能目錄)
    # The script is in skills/ETF_TW/scripts/sys_path_report.py
    # So the skill root is .. from script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    etf_tw_workdir = os.path.abspath(os.path.join(script_dir, '..'))
    
    # CONFIG_PATH (active profile 下的 config.yaml)
    # Config.yaml should be in the profile root
    config_path = os.path.abspath(os.path.join(cwd, 'config.yaml'))
    
    # Check if config exists, fallback to home-based config if needed
    if not os.path.exists(config_path):
        config_path = os.path.join(hermes_home, 'profiles', active_profile, 'config.yaml')
    
    report = {
        "HERMES_HOME": hermes_home,
        "ACTIVE_PROFILE": active_profile,
        "ETF_TW_WORKDIR": etf_tw_workdir,
        "CONFIG_PATH": config_path
    }
    return report

if __name__ == "__main__":
    report = get_report()
    for key, value in report.items():
        print(f"{key}: {value}")
