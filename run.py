#!/usr/bin/env python3
"""One command: python run.py --mock   (default: mock, zero Gnani credits)."""
import argparse, os, sys
from kiranavoice.envload import load_env_local; load_env_local()
p = argparse.ArgumentParser()
g = p.add_mutually_exclusive_group()
g.add_argument("--mock", action="store_true", help="mock STT/TTS (default)")
g.add_argument("--live", action="store_true", help="real Gnani Prisma/Timbre (needs GNANI_API_KEY)")
p.add_argument("--whatsapp", choices=["mock", "wame", "twilio"], default=os.getenv("WHATSAPP_SENDER", "mock"))
p.add_argument("--port", type=int, default=8000)
p.add_argument("--host", default="127.0.0.1")
a = p.parse_args()
mode = "live" if a.live else "mock"
if mode == "live" and not os.getenv("GNANI_API_KEY"):
    sys.exit("GNANI_API_KEY not set. Run with --mock or export the key.")
import uvicorn
from kiranavoice.server import make_app
print(f"KiranaVoice [{mode}] whatsapp={a.whatsapp}  ->  http://{a.host}:{a.port}/   (vertical: /?layout=vertical)")
uvicorn.run(make_app(mode, a.whatsapp), host=a.host, port=a.port, log_level="warning")
