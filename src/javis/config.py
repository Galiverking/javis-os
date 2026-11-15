"""Configuration loader for Javis OS."""

import os
from pathlib import Path
from pydantic import BaseModel, Field


class JavisConfig(BaseModel):
    # Voice (Male: th-TH-NiwatNeural, Female: th-TH-PremwadeeNeural)
    voice: str = Field(
        default_factory=lambda: os.getenv("JAVIS_VOICE", "th-TH-NiwatNeural"),
        description="edge-tts voice",
    )
    sample_rate: int = Field(default=16000, description="Capture sample rate in Hz")
    playback_rate: int = Field(default=24000, description="Playback sample rate in Hz")
    
    # Providers (100% Free Stack)
    groq_api_key: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    hermes_url: str = Field(default="http://127.0.0.1:8000")
    
    # IPC / Sockets
    socket_path: str = Field(
        default=str(Path.home() / ".local" / "share" / "javis" / "javis.sock")
    )
    data_dir: str = Field(
        default=str(Path.home() / ".local" / "share" / "javis")
    )


def load_config() -> JavisConfig:
    """Loads configuration from environment or defaults."""
    env_file = Path.home() / ".config" / "javis" / "env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    
    return JavisConfig()
