"""Local demo API for an explainable fraud investigation workbench.

All records and policy excerpts are fabricated for demonstration. No payment
or account action is performed by this server.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent

TRANSACTIONS = [
    {"id":"TX-10482","time":"2026-11-26T14:42:00Z","customer":"C-2081","merchant":"Northstar Electronics","category":"Electronics","amount":1849.90,"currency":"USD","country":"US","device":"New device","channel":"Card-not-present","velocity_1h":5,"usual_amount":210,"chargebacks_30d":0,"status":"Review"},
    {"id":"TX-10481","time":"2026-11-26T14:39:00Z","customer":"C-2081","merchant":"Metro Fuel 018","category":"Fuel","amount":46.21,"currency":"USD","country":"US","device":"Known device","channel":"Card-present","velocity_1h":3,"usual_amount":65,"chargebacks_30d":0,"status":"Cleared"},
    {"id":"TX-10480","time":"2026-11-26T14:31:00Z","customer":"C-9930","merchant":"Luma Digital Goods","category":"Digital goods","amount":799.00,"currency":"USD","country":"GB","device":"New device","channel":"Card-not-present","velocity_1h":7,"usual_amount":95,"chargebacks_30d":1,"status":"Review"},
    {"id":"TX-10479","time":"2026-11-26T14:21:00Z","customer":"C-5512","merchant":"Greenway Market","category":"Grocery","amount":82.40,"currency":"USD","country":"US","device":"Known device","channel":"Card-present","velocity_1h":1,"usual_amount":74,"chargebacks_30d":0,"status":"Cleared"},
    {"id":"TX-10478","time":"2026-11-26T14:16:00Z","customer":"C-1477","merchant":"AeroLink Travel","category":"Travel","amount":2340.00,"currency":"USD","country":"SG","device":"New device","channel":"Card-not-present","velocity_1h":4,"usual_amount":380,"chargebacks_30d":0,"status":"Review"},
    {"id":"TX-10477","time":"2026-11-26T14:03:00Z","customer":"C-4402","merchant":"Harbor Pharmacy","category":"Pharmacy","amount":28.65,"currency":"USD","country":"US","device":"Known device","channel":"Card-present","velocity_1h":1,"usual_amount":42,"chargebacks_30d":0,"status":"Cleared"},
    {"id":"TX-10476","time":"2026-11-26T13:58:00Z","customer":"C-9930","merchant":"Luma Digital Goods","category":"Digital goods","amount":699.00,"currency":"USD","country":"GB","device":"New device","channel":"Card-not-present","velocity_1h":6,"usual_amount":95,"chargebacks_30d":1,"status":"Review"},
    {"id":"TX-10475","time":"2026-11-26T13:48:00Z","customer":"C-8173","merchant":"Oak & Stone Home","category":"Home","amount":129.00,"currency":"USD","country":"US","device":"Known device","channel":"Card-not-present","velocity_1h":1,"usual_amount":155,"chargebacks_30d":0,"status":"Cleared"},
    {"id":"TX-10474","time":"2026-11-26T13:32:00Z","customer":"C-3029","merchant":"QuickCart Online","category":"General retail","amount":1199.00,"currency":"USD","country":"US","device":"New device","channel":"Card-not-present","velocity_1h":4,"usual_amount":190,"chargebacks_30d":0,"status":"Review"},
]

POLICIES = [
    {"id":"POL-07","title":"Unusual transaction review","source":"Demo Risk Operations Standard · §4.2","tags":["amount","velocity","device"],"text":"Review transactions when the amount is materially above the customer's observed pattern or when several authorization attempts occur in a short period. Corroborate with device and channel signals before escalation."},
    {"id":"POL-12","title":"Cross-border card-not-present activity","source":"Demo Card Risk Playbook · §3.1","tags":["cross-border","device","card-not-present"],"text":"For cross-border card-not-present activity on a newly observed device, collect the authorization timeline and compare recent customer activity. Route unresolved high-risk cases to a human investigator."},
    {"id":"POL-18","title":"Repeat dispute indicator","source":"Demo Disputes Procedure · §2.6","tags":["chargeback","repeat-dispute"],"text":"A recent dispute is a supporting signal only. Do not treat a prior dispute as proof that a new transaction is unauthorized. Include the dispute history in the case context for reviewer assessment."},
]


def analyze(tx: dict) -> dict:
    signals = []
    score = 0
    ratio = tx["amount"] / max(tx["usual_amount"], 1)
    if ratio >= 5:
        score += 28; signals.append({"label":"Amount far above observed pattern","detail":f"${tx['amount']:,.2f} vs. typical ${tx['usual_amount']:,.2f} ({ratio:.1f}×)","weight":"High"})
    elif ratio >= 2.5:
        score += 16; signals.append({"label":"Amount above observed pattern","detail":f"${tx['amount']:,.2f} vs. typical ${tx['usual_amount']:,.2f} ({ratio:.1f}×)","weight":"Medium"})
    if tx["velocity_1h"] >= 6:
        score += 24; signals.append({"label":"High authorization velocity","detail":f"{tx['velocity_1h']} transactions in the last hour","weight":"High"})
    elif tx["velocity_1h"] >= 4:
        score += 13; signals.append({"label":"Elevated authorization velocity","detail":f"{tx['velocity_1h']} transactions in the last hour","weight":"Medium"})
    if tx["device"] == "New device":
        score += 18; signals.append({"label":"New device","detail":"Device has not been observed for this customer","weight":"Medium"})
    if tx["country"] != "US":
        score += 16; signals.append({"label":"Cross-border activity","detail":f"Transaction country: {tx['country']}","weight":"Medium"})
    if tx["channel"] == "Card-not-present":
        score += 8; signals.append({"label":"Card-not-present channel","detail":"Card was not physically present at authorization","weight":"Low"})
    if tx["chargebacks_30d"]:
        score += 8; signals.append({"label":"Recent dispute history","detail":f"{tx['chargebacks_30d']} dispute(s) recorded in 30 days; context only","weight":"Low"})
    score = min(score, 99)
    level = "High" if score >= 60 else "Medium" if score >= 35 else "Low"
    tags = set()
    if ratio >= 2.5: tags.add("amount")
    if tx["velocity_1h"] >= 4: tags.add("velocity")
    if tx["device"] == "New device": tags.add("device")
    if tx["country"] != "US": tags.add("cross-border")
    if tx["channel"] == "Card-not-present": tags.add("card-not-present")
    if tx["chargebacks_30d"]: tags.update(("chargeback", "repeat-dispute"))
    evidence = [p for p in POLICIES if tags.intersection(p["tags"])]
    recommendation = "Escalate for human review" if level == "High" else "Verify customer context" if level == "Medium" else "Continue standard monitoring"
    if tx["chargebacks_30d"]:
        recommendation += "; treat dispute history as context, not proof"
    return {"transaction":tx,"score":score,"level":level,"signals":signals,"evidence":evidence,"recommendation":recommendation,
            "summary":f"{level.lower()} risk score ({score}/100) based on {len(signals)} explainable signal(s). The score is a demonstration heuristic, not a validated production model."}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: object, content_type="application/json; charset=utf-8"):
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/transactions":
            self._send(200, [analyze(t) for t in TRANSACTIONS])
        elif path == "/api/policies":
            self._send(200, POLICIES)
        elif path == "/" or path == "/index.html":
            self._send(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/style.css":
            self._send(200, (ROOT / "style.css").read_bytes(), "text/css; charset=utf-8")
        elif path == "/app.js":
            self._send(200, (ROOT / "app.js").read_bytes(), "text/javascript; charset=utf-8")
        else:
            self._send(404, {"error":"Not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/investigate":
            self._send(404, {"error":"Not found"}); return
        try:
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            tx_id = payload.get("transaction_id")
        except (ValueError, AttributeError):
            self._send(400, {"error":"Send JSON with transaction_id"}); return
        tx = next((t for t in TRANSACTIONS if t["id"] == tx_id), None)
        if not tx:
            self._send(404, {"error":"Transaction not found"}); return
        self._send(200, analyze(tx))

    def log_message(self, fmt, *args):
        print(f"{self.log_date_time_string()} {self.address_string()} {fmt % args}")


if __name__ == "__main__":
    port = 8000
    print(f"Fraud Intelligence demo: http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()