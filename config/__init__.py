import json
from pathlib import Path
CONFIG_DIR = Path(__file__).parent
AGENT_CONFIG_PATH = CONFIG_DIR / "agent_config.json"
def load_agent_config():
    with open(AGENT_CONFIG_PATH) as f:
        return json.load(f)
