import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, Literal


# Credentials file - contains paper/live API credentials
CREDENTIALS_FILE = Path.home() / ".alpaca.json"

# Runtime config directory and state file
CONFIG_DIR = Path.home() / ".config" / "alpaca-cli"
STATE_FILE = CONFIG_DIR / "config.json"

# Valid modes
ModeType = Literal["paper", "live"]

# Default endpoints
DEFAULT_ENDPOINTS = {
    "paper": "https://paper-api.alpaca.markets",
    "live": "https://api.alpaca.markets",
}


class Config:
    def __init__(self) -> None:
        self._credentials: Dict[str, Any] = self._load_credentials()
        self._state: Dict[str, Any] = self._load_state()

        # Get active mode and load credentials
        self._mode: ModeType = self._get_active_mode()
        self._load_mode_credentials()

    def _load_credentials(self) -> Dict[str, Any]:
        """Load credentials from ~/.alpaca.json"""
        if CREDENTIALS_FILE.exists():
            try:
                with open(CREDENTIALS_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _load_state(self) -> Dict[str, Any]:
        """Load runtime state from ~/.config/alpaca-cli/config.json"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_state(self) -> None:
        """Save runtime state to ~/.config/alpaca-cli/config.json"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(self._state, f, indent=4)

    def _get_active_mode(self) -> ModeType:
        """Get the active mode from environment variable or state file."""
        env_mode = os.getenv("ALPACA_MODE")
        if env_mode and env_mode.lower() in ("paper", "live"):
            return env_mode.lower()  # type: ignore
        return self._state.get("mode", "paper")

    def _load_mode_credentials(self) -> None:
        """Load credentials for the active mode and set environment variables."""
        mode_config = self._credentials.get(self._mode, {})

        # Priority: Environment Variable > Config File
        env_key = os.getenv("APCA_API_KEY_ID")
        env_secret = os.getenv("APCA_API_SECRET_KEY")
        env_endpoint = os.getenv("APCA_ENDPOINT_URL")

        self.SOURCE: str = "None"

        if env_key and env_secret:
            self.API_KEY: Optional[str] = env_key
            self.API_SECRET: Optional[str] = env_secret
            self.BASE_URL: str = env_endpoint or DEFAULT_ENDPOINTS[self._mode]
            self.SOURCE = "Environment Variable"
        elif mode_config:
            self.API_KEY = mode_config.get("api_key")
            self.API_SECRET = mode_config.get("secret")
            self.BASE_URL = mode_config.get("endpoint", DEFAULT_ENDPOINTS[self._mode])
            self.SOURCE = "Config File"

            # Set environment variables for downstream use
            if self.API_KEY:
                os.environ["APCA_API_KEY_ID"] = self.API_KEY
            if self.API_SECRET:
                os.environ["APCA_API_SECRET_KEY"] = self.API_SECRET
            if self.BASE_URL:
                os.environ["APCA_ENDPOINT_URL"] = self.BASE_URL
        else:
            self.API_KEY = None
            self.API_SECRET = None
            self.BASE_URL = DEFAULT_ENDPOINTS[self._mode]

        self.IS_PAPER: bool = self._mode == "paper"

    @property
    def mode(self) -> ModeType:
        """Get the current active mode."""
        return self._mode

    def has_mode_credentials(self, mode: ModeType) -> bool:
        """Check if credentials exist for a given mode."""
        mode_config = self._credentials.get(mode, {})
        return bool(mode_config.get("api_key") and mode_config.get("secret"))

    def set_mode(self, mode: ModeType) -> None:
        """Set the active mode and reload credentials."""
        if mode not in ("paper", "live"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'paper' or 'live'.")

        if not self.has_mode_credentials(mode):
            raise ValueError(
                f"No credentials found for '{mode}' mode.\n\n"
                f"Please add {mode} credentials to ~/.alpaca.json:\n"
                "{\n"
                f'    "{mode}": {{\n'
                f'        "api_key": "YOUR_{mode.upper()}_API_KEY",\n'
                f'        "secret": "YOUR_{mode.upper()}_SECRET",\n'
                f'        "endpoint": "{DEFAULT_ENDPOINTS[mode]}"\n'
                "    }\n"
                "}"
            )

        self._state["mode"] = mode
        self._save_state()
        self._mode = mode
        self._load_mode_credentials()

        # Reset cached clients to use new credentials
        # Import here to avoid circular dependency
        from alpaca_cli.core.client import reset_all_clients

        reset_all_clients()

    def validate(self) -> None:
        """Validate that API credentials are configured."""
        if not self.API_KEY or not self.API_SECRET:
            plain_error = (
                f"API credentials not found for '{self._mode}' mode.\n\n"
                "You can load credentials via:\n"
                "1. Environment Variables:\n"
                "   export APCA_API_KEY_ID='your_key'\n"
                "   export APCA_API_SECRET_KEY='your_secret'\n\n"
                "2. Config File (~/.alpaca.json):\n"
                "   {\n"
                '       "paper": {\n'
                '           "api_key": "your_paper_key",\n'
                '           "secret": "your_paper_secret",\n'
                '           "endpoint": "https://paper-api.alpaca.markets"\n'
                "       },\n"
                '       "live": {\n'
                '           "api_key": "your_live_key",\n'
                '           "secret": "your_live_secret",\n'
                '           "endpoint": "https://api.alpaca.markets"\n'
                "       }\n"
                "   }"
            )
            raise ValueError(plain_error)


config = Config()
