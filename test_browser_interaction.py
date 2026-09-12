import subprocess
import time
import json
import urllib.request
import websockets
import asyncio

async def test_real_browser_clicks():
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
            return

        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
            await ws.send(json.dumps({"id": 2, "method": "DOM.enable"}))

            async def eval_js(expression):
                req_id = int(time.time() * 1000) % 100000
                await ws.send(json.dumps({
                    "id": req_id,
                    "method": "Runtime.evaluate",
                    "params": {"expression": expression, "returnByValue": True}
                }))
                while True:
                    msg_str = await ws.recv()
                    msg = json.loads(msg_str)
                    if msg.get("id") == req_id:
                        return msg.get("result", {}).get("result", {}).get("value")

            # 1. Test Settings Modal Open
            res_open = await eval_js("""
                (() => {
                    const btn = document.getElementById('btn-settings');
                    const modal = document.getElementById('settings-modal');
                    if (!btn || !modal) return 'BUTTON_MISSING';
                    btn.click();
                    return !modal.classList.contains('hidden') ? 'MODAL_OPENED' : 'MODAL_STILL_HIDDEN';
                })()
            """)
            print(f"[TEST 1: Settings Button Click] -> {res_open}")

            # 2. Test Modal Close
            res_close = await eval_js("""
                (() => {
                    const btn = document.getElementById('btn-close-modal');
                    const modal = document.getElementById('settings-modal');
                    if (!btn || !modal) return 'BUTTON_MISSING';
                    btn.click();
                    return modal.classList.contains('hidden') ? 'MODAL_CLOSED' : 'MODAL_STILL_OPEN';
                })()
            """)
            print(f"[TEST 2: Close Modal Click] -> {res_close}")

            # 3. Test Camera Toggle
            res_cam = await eval_js("""
                (() => {
                    const btn = document.getElementById('btn-toggle-cam');
                    if (!btn) return 'BUTTON_MISSING';
                    btn.click();
                    return btn.textContent;
                })()
            """)
            print(f"[TEST 3: Start Camera Button Click] -> Text: '{res_cam.encode('ascii', 'ignore').decode()}'")

            # 4. Test Color Preset Click
            res_color = await eval_js("""
                (() => {
                    const greenBtn = document.querySelector('.color-btn[data-color="#10B981"]');
                    if (!greenBtn) return 'BUTTON_MISSING';
                    greenBtn.click();
                    return greenBtn.classList.contains('active') ? 'COLOR_ACTIVATED' : 'NOT_ACTIVE';
                })()
            """)
            print(f"[TEST 4: Green Color Button Click] -> {res_color}")

            # 5. Test Clear Canvas Click
            res_clear = await eval_js("""
                (() => {
                    const btnClear = document.getElementById('btn-clear');
                    if (!btnClear) return 'BUTTON_MISSING';
                    btnClear.click();
                    return 'CLEAR_CLICKED';
                })()
            """)
            print(f"[TEST 5: Clear Canvas Button Click] -> {res_clear}")

    finally:
        proc.kill()

if __name__ == "__main__":
    asyncio.run(test_real_browser_clicks())
