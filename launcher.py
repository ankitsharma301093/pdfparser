"""
Launcher for the PDF Parser app.
Run directly with: python launcher.py
Package with PyInstaller: see build_exe.bat / build_exe.sh
"""
import sys
import os
import threading
import webbrowser
import time


def _open_browser():
    time.sleep(3)
    webbrowser.open("http://localhost:8501")


def main():
    threading.Thread(target=_open_browser, daemon=True).start()

    if getattr(sys, "frozen", False):
        app_path = os.path.join(sys._MEIPASS, "app.py")  # type: ignore[attr-defined]
    else:
        app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")

    from streamlit.web import cli as stcli
    sys.argv = [
        "streamlit", "run", app_path,
        "--server.headless=true",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
