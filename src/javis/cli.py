"""Javis CLI - Diagnostic Doctor, PTT, Service Control & Voice Daemon.
"""

import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional
import typer

from javis.config import load_config

app = typer.Typer(help="Javis OS Voice Assistant CLI")
service_app = typer.Typer(help="Manage Javis background systemd service")
app.add_typer(service_app, name="service")


@app.callback()
def main_callback():
    load_config()


@app.command()
def doctor():
    """Diagnoses system readiness: audio devices, RAM, free providers, and Hermes gateway."""
    typer.secho("\n🔍 Javis OS Diagnostic Doctor (Milestone M0)\n" + "=" * 45, fg=typer.colors.CYAN, bold=True)
    all_ok = True

    # 1. Python Environment
    typer.echo(f"• Python: {sys.version.split()[0]} ({sys.platform})")

    # 2. System RAM & Load
    try:
        import psutil
        ram = psutil.virtual_memory()
        avail_mb = ram.available / (1024 * 1024)
        if avail_mb < 300:
            typer.secho(f"  [✗] RAM Available: {avail_mb:.0f} MB (Critical OOM risk!)", fg=typer.colors.RED)
            all_ok = False
        elif avail_mb < 600:
            typer.secho(f"  [!] RAM Available: {avail_mb:.0f} MB (Low memory caution)", fg=typer.colors.YELLOW)
        else:
            typer.secho(f"  [✓] RAM Available: {avail_mb:.0f} MB (Healthy)", fg=typer.colors.GREEN)
    except ImportError:
        typer.secho("  [!] psutil not installed, skipping memory check", fg=typer.colors.YELLOW)

    # 3. Audio C-Libraries & Devices
    try:
        import sounddevice as sd
        input_dev = sd.query_devices(kind="input")
        output_dev = sd.query_devices(kind="output")
        typer.secho(f"  [✓] Mic (Default Input): {input_dev['name']}", fg=typer.colors.GREEN)
        typer.secho(f"  [✓] Speaker (Default Output): {output_dev['name']}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"  [✗] Audio Device Error: {e}", fg=typer.colors.RED)
        all_ok = False

    # 4. Free Providers & API Keys
    groq_key = os.getenv("GROQ_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    
    if groq_key:
        typer.secho("  [✓] Groq API Key: Detected (Free Whisper STT Ready)", fg=typer.colors.GREEN)
    else:
        typer.secho("  [!] Groq API Key: Not set (Set GROQ_API_KEY in ~/.config/javis/env)", fg=typer.colors.YELLOW)

    if gemini_key:
        typer.secho("  [✓] Gemini API Key: Detected (Google AI Studio Free Tier Ready)", fg=typer.colors.GREEN)
    else:
        typer.secho("  [!] Gemini API Key: Not set (Set GEMINI_API_KEY in ~/.config/javis/env)", fg=typer.colors.YELLOW)

    # 5. Gateway Connectivity Check (Port 8000)
    try:
        import httpx
        with httpx.Client(timeout=1.0) as client:
            resp = client.get("http://127.0.0.1:8000/health")
            if resp.status_code == 200:
                typer.secho("  [✓] Hermes Gateway (port 8000): Online", fg=typer.colors.GREEN)
            else:
                typer.secho(f"  [!] Hermes Gateway: HTTP {resp.status_code}", fg=typer.colors.YELLOW)
    except Exception:
        typer.secho("  [!] Hermes Gateway (port 8000): Offline (Will use Direct Fallback)", fg=typer.colors.YELLOW)

    # 6. Linux System Tools
    tools = ["ffmpeg", "wpctl", "zenity", "notify-send"]
    for cmd in tools:
        if shutil.which(cmd):
            typer.secho(f"  [✓] Tool `{cmd}`: Found", fg=typer.colors.GREEN)
        else:
            typer.secho(f"  [!] Tool `{cmd}`: Not found in PATH", fg=typer.colors.YELLOW)

    # Summary
    typer.echo("-" * 45)
    if all_ok:
        typer.secho("🎉 Javis OS Core M0 checks PASSED!\n", fg=typer.colors.GREEN, bold=True)
    else:
        typer.secho("⚠️ Please resolve the issues marked above.\n", fg=typer.colors.RED)


@app.command()
def run():
    """Runs the Javis Voice Daemon in foreground (ideal for testing and live logs)."""
    from javis.core.daemon import run_daemon
    typer.secho("Starting Javis Voice Orchestrator...", fg=typer.colors.CYAN, bold=True)
    try:
        asyncio.run(run_daemon())
    except KeyboardInterrupt:
        typer.secho("\nStopped Javis Daemon.", fg=typer.colors.YELLOW)


@app.command()
def ptt():
    """Triggers Push-to-Talk toggle via Unix socket (invoked by Shift+Super shortcut)."""
    from javis.audio.hotkey import send_ptt_toggle
    success = asyncio.run(send_ptt_toggle())
    if success:
        typer.secho("PTT Signal Sent successfully", fg=typer.colors.GREEN)
    else:
        typer.secho("Daemon not running or socket unavailable", fg=typer.colors.YELLOW)


@app.command()
def test_voice(
    text: str = "สวัสดีครับเจ้านาย จาวิสพร้อมรับคำสั่งแล้วครับ",
    voice: Optional[str] = None,
):
    """Tests edge-tts voice synthesis (defaults to male voice th-TH-NiwatNeural)."""
    from javis.tts.edge import EdgeTTSClient
    from javis.audio.playback import AudioPlaybackEngine
    from javis.config import load_config
    
    selected_voice = voice or load_config().voice
    typer.echo(f"Testing voice synthesis ({selected_voice}): '{text}'...")
    tts = EdgeTTSClient(voice=selected_voice)
    playback = AudioPlaybackEngine()
    
    async def _run():
        audio_bytes = await tts.synthesize_speech(text)
        if audio_bytes:
            typer.secho(f"Synthesized {len(audio_bytes)} bytes audio successfully!", fg=typer.colors.GREEN)
            typer.echo("Playing audio via playback engine...")
            playback.play_mp3(audio_bytes)
            typer.secho("Playback completed!", fg=typer.colors.GREEN)
    
    asyncio.run(_run())


@app.command()
def mobile(
    port: int = typer.Option(8765, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind host"),
):
    """Starts the iPhone Mobile Companion server (Safari Web UI + Apple Shortcuts API)."""
    from javis.core.daemon import VoicePipelineOrchestrator
    from javis.ui.mobile_api import MobileCompanionServer, get_or_create_mobile_token

    token = get_or_create_mobile_token()
    typer.secho("\n📱 Javis OS Mobile Companion for iPhone", fg=typer.colors.CYAN, bold=True)
    typer.echo("=" * 55)
    typer.secho("• Wi-Fi Local (วงในบ้าน):", fg=typer.colors.YELLOW, bold=True)
    typer.echo(f"  http://192.168.1.23:{port}")
    typer.secho("• Tailscale VPN (ได้ทุกที่นอกบ้าน):", fg=typer.colors.YELLOW, bold=True)
    typer.echo(f"  http://100.89.142.114:{port}")
    typer.secho("• Mobile Secret Token:", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  {token}")
    typer.echo("=" * 55)
    typer.echo("\nเปิด Safari บน iPhone 11 เข้า URL ด้านบนได้ทันทีครับ!")
    typer.echo("กด Ctrl+C เพื่อหยุดการทำงาน\n")

    async def _run():
        orchestrator = VoicePipelineOrchestrator()
        server = MobileCompanionServer(orchestrator=orchestrator, host=host, port=port, token=token)
        await server.start()
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            await server.stop()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        typer.secho("\nMobile server stopped.", fg=typer.colors.YELLOW)


@app.command()
def setup_hotkey():
    """Configures Linux Mint / Cinnamon shortcut (Shift+Super) to trigger Javis PTT."""
    typer.echo("Configuring Cinnamon custom shortcut for Shift+Super...")
    bin_path = str(Path(sys.executable).parent / "javis")
    
    try:
        # 1. Update custom-list
        subprocess.run(["gsettings", "set", "org.cinnamon.desktop.keybindings", "custom-list", "['custom-javis']"], check=True)
        
        # 2. Set keybinding schema
        path = "org.cinnamon.desktop.keybindings.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/custom-javis/"
        subprocess.run(["gsettings", "set", path, "name", "Javis Voice PTT"], check=True)
        subprocess.run(["gsettings", "set", path, "command", f"{bin_path} ptt"], check=True)
        subprocess.run(["gsettings", "set", path, "binding", "['<Shift><Super>']"], check=True)
        
        typer.secho(f"  [✓] Registered: Shift+Super -> {bin_path} ptt", fg=typer.colors.GREEN, bold=True)
        typer.secho("🎉 Hotkey configured successfully!", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Failed to set keybinding via gsettings: {e}", fg=typer.colors.RED)


@service_app.command("install")
def service_install():
    """Installs systemd user service for background execution."""
    bin_path = str(Path(sys.executable).parent / "javis")
    service_dir = Path.home() / ".config/systemd/user"
    service_dir.mkdir(parents=True, exist_ok=True)
    service_file = service_dir / "javis.service"
    
    content = f"""[Unit]
Description=Javis OS Voice Assistant Daemon
After=network.target sound.target

[Service]
Type=simple
ExecStart={bin_path} run
Restart=on-failure
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
"""
    service_file.write_text(content)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "javis"], check=True)
    typer.secho(f"  [✓] Installed and enabled service at: {service_file}", fg=typer.colors.GREEN)
    typer.echo("Run 'javis service start' to start the daemon in the background.")


@service_app.command("start")
def service_start():
    """Starts the background Javis systemd service."""
    subprocess.run(["systemctl", "--user", "start", "javis"], check=True)
    typer.secho("Javis service started in background.", fg=typer.colors.GREEN)


@service_app.command("stop")
def service_stop():
    """Stops the background Javis systemd service."""
    subprocess.run(["systemctl", "--user", "stop", "javis"], check=True)
    typer.secho("Javis service stopped.", fg=typer.colors.YELLOW)


@service_app.command("status")
def service_status():
    """Shows status of the Javis systemd service."""
    subprocess.run(["systemctl", "--user", "status", "javis", "--no-pager"])


if __name__ == "__main__":
    app()
