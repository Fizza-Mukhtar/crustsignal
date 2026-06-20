"""Start the CrustSignal web server and open browser automatically."""
import sys, os, time, threading, webbrowser
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import uvicorn

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")

threading.Thread(target=open_browser, daemon=True).start()
uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=False)