import os

from dotenv import load_dotenv

## Load tests/.env if present
_here = os.path.dirname(__file__)
env_path = os.path.join(_here, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path, override=False)
