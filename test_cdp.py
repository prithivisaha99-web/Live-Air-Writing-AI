import subprocess
import time
import json
import urllib.request
import websockets
import asyncio

async def inspect_browser():
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    cmd = [
        chrome_path,
        "--headless=new",
        "--remote-debugging-port=9222",
        "--no-first-run",
        "--no-default-browser-check",
        "http://127.0.0.1:8000/"
    ]
    proc = subprocess.Popen(cmd)
    time.sleep(2)

    try:
        req = urllib.request.urlopen("http://127.0.0.1:9222/json")
        targets = json.loads(req.read().decode())
        ws_url = None
        for t in targets:
            if t.get("type") == "page":
                ws_url = t.get("webSocketDebuggerUrl")
                break

        if not ws_url:
            print("No WebSocket debugger URL found.")
            proc.kill()
            return

        print(f"Connecting to Chrome CDP at: {ws_url}")
        async with websockets.connect(ws_url) as ws:
            # Enable Runtime, Log, Page, and Network domains
            await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
            await ws.send(json.dumps({"id": 2, "method": "Log.enable"}))
            await ws.send(json.dumps({"id": 3, "method": "Network.enable"}))
            await ws.send(json.dumps({"id": 4, "method": "Page.enable"}))

            print("--- CHROME DEVTOOLS CAPTURE START ---")
            start_time = time.time()
            while time.time() - start_time < 6.0:
                try:
                    msg_str = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg = json.loads(msg_str)
                    method = msg.get("method", "")
                    params = msg.get("params", {})

                    if method == "Runtime.consoleAPICalled":
                        type_ = params.get("type")
                        args = [a.get("value") or a.get("description") for a in params.get("args", [])]
                        print(f"[CONSOLE.{type_.upper()}]", *args)
                    elif method == "Runtime.exceptionThrown":
                        details = params.get("exceptionDetails", {})
                        text = details.get("text")
                        exp = details.get("exception", {}).get("description")
                        url = details.get("url")
                        line = details.get("lineNumber")
                        col = details.get("columnNumber")
                        print(f"[JS EXCEPTION] {text}: {exp} at {url}:{line}:{col}")
                    elif method == "Log.entryAdded":
                        entry = params.get("entry", {})
                        print(f"[LOG.{entry.get('level', '').upper()}] {entry.get('text')}")
                    elif method == "Network.responseReceived":
                        resp = params.get("response", {})
                        url = resp.get("url", "")
                        status = resp.get("status")
                        mime = resp.get("mimeType")
                        if "127.0.0.1" in url or "jsdelivr" in url or "mediapipe" in url:
                            print(f"[NETWORK {status}] {url} ({mime})")
                except asyncio.TimeoutError:
                    pass
            print("--- CHROME DEVTOOLS CAPTURE END ---")
    finally:
        proc.kill()

if __name__ == "__main__":
    asyncio.run(inspect_browser())
