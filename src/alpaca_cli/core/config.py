import os
import json
from pathlib import Path
from typing import Optional, Dict, Any


CONFIG_FILE = Path.home() / ".alpaca.json"


class Config:
    def __init__(self) -> None:
        self.file_config: Dict[str, Any] = self._load_file_config()

        # Priority: Env Var > Config File (Standard) > Config File (Legacy) > Default
        env_key = os.getenv("APCA_API_KEY_ID")
        file_key = self.file_config.get("APCA_API_KEY_ID") or self.file_config.get(
            "key"
        )

        self.SOURCE: str = "None"
        if env_key:
            self.API_KEY = env_key
            self.SOURCE = "Environment Variable"
        elif file_key:
            self.API_KEY = file_key
            self.SOURCE = "Config File"
        else:
            self.API_KEY = None

        self.API_SECRET: Optional[str] = (
            os.getenv("APCA_API_SECRET_KEY")
            or self.file_config.get("APCA_API_SECRET_KEY")
            or self.file_config.get("secret")
        )

        self.PAPER_URL: str = self.file_config.get(
            "paper_endpoint", "https://paper-api.alpaca.markets"
        )
        self.LIVE_URL: str = self.file_config.get(
            "live_endpoint", "https://api.alpaca.markets"
        )

        default_base_url = self.PAPER_URL
        self.BASE_URL: str = (
            os.getenv("APCA_API_BASE_URL")
            or self.file_config.get("APCA_API_BASE_URL")
            or default_base_url
        )
        self.IS_PAPER: bool = "paper" in self.BASE_URL

    def _load_file_config(self) -> Dict[str, Any]:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self, key: str, value: str) -> None:
        """Save a configuration value to the JSON file."""
        self.file_config[key] = value
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.file_config, f, indent=4)

        # Update instance immediately
        if key == "APCA_API_KEY_ID":
            self.API_KEY = value
        elif key == "APCA_API_SECRET_KEY":
            self.API_SECRET = value
        elif key == "APCA_API_BASE_URL":
            self.BASE_URL = value
            self.IS_PAPER = "paper" in value

    def validate(self) -> None:
        if not self.API_KEY or not self.API_SECRET:
            error_msg = (
                "\n[bold red]Error: API credentials not found.[/bold red]\n\n"
                "You can load credentials via:\n"
                "1. [yellow]Environment Variables[/yellow]:\n"
                "   export APCA_API_KEY_ID='your_key'\n"
                "   export APCA_API_SECRET_KEY='your_secret'\n\n"
                "2. [yellow]Config File[/yellow] (~/.alpaca.json):\n"
                "   {\n"
                '       "key": "your_key",\n'
                '       "secret": "your_secret",\n'
                '       "paper_endpoint": "https://paper-api.alpaca.markets",\n'
                '       "live_endpoint": "https://api.alpaca.markets"\n'
                "   }"
            )
            # raising ValueError usually catches by click and prints "Error: <message>"
            # To preserve rich formatting we print directly here if we expect it to be caught by our own logic?
            # Or just return plain text. The user wants "good message".
            # I'll stick to plain text for ValueError to avoid ANSI code issues in standard logs,
            # but format it nicely.
            plain_error = (
                "API credentials not found.\n\n"
                "You can load credentials via:\n"
                "1. Environment Variables:\n"
                "   export APCA_API_KEY_ID='your_key'\n"
                "   export APCA_API_SECRET_KEY='your_secret'\n\n"
                "2. Config File (~/.alpaca.json):\n"
                "   {\n"
                '       "key": "your_key",\n'
                '       "secret": "your_secret",\n'
                '       "paper_endpoint": "https://paper-api.alpaca.markets",\n'
                '       "live_endpoint": "https://api.alpaca.markets"\n'
                "   }"
            )
            raise ValueError(plain_error)


config = Config()
