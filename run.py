#!/usr/bin/env python3
"""
Page2PDF — Application Entry Point
Run with: python run.py
"""

import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    env = os.getenv("APP_ENV", "development")

    print(f"""
    ╔══════════════════════════════════════════╗
    ║           Page2PDF Server                ║
    ║   Turn Any Webpage Into a Clean PDF      ║
    ╠══════════════════════════════════════════╣
    ║   URL: http://{host}:{port}              ║
    ║   Env: {env:<33s}║
    ╚══════════════════════════════════════════╝
    """)

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=(env == "development"),
        log_level="info",
    )
