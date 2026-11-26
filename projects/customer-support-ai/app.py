"""Authenticated customer-support API and local web application.

The service uses only Python's standard library. It is intentionally small enough
to run locally or in the included container while keeping the important safety
boundaries explicit: users only see their own orders and tickets, policy answers
are grounded in versioned fixture data, and unresolved requests can be handed to
a human through a persisted ticket.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DEFAULT_DB = ROOT / "support.sqlite3"
SESSION_TTL_SECONDS = 60 * 60 * 24
MAX_BODY = 64 * 1024
EMAIL_RE = re.compile(r"^[^@\s]{1,80}@[^@\s]{1,80}\.[^@\s]{2,80}$")


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('customer', 'agent', 'admin')) DEFAULT 'customer',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user_idx ON sessions(user_id);
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status TEXT NOT NULL,
  carrier TEXT,
  tracking_number TEXT,
  purchased_on TEXT NOT NULL,
  delivery_date TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS orders_user_idx ON orders(user_id);
CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  order_id TEXT REFERENCES orders(id) ON DELETE SET NULL,
  subject TEXT NOT NULL,
  message TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open', 'in_progress', 'resolved')) DEFAULT 'open',
  priority TEXT NOT NULL CHECK (priority IN ('normal', 'high')) DEFAULT 'normal',
  resolution_note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS tickets_user_idx ON tickets(user_id, status);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  resource TEXT,
  created_at TEXT NOT NULL
);
"""


POLICIES = [
    {
        "policy_id": "returns",
        "version": "v1",
        "country": "US",
        "category": "footwear",
        "purchase_from": "2026-01-01",
        "purchase_before": "2026-11-01",
        "source_id": "fictional-store-handbook/returns/v1",
        "window": 30,
        "condition": "Returned footwear must be unused and in its original packaging.",
    },
    {
        "policy_id": "returns",
        "version": "v2",
        "country": "US",
        "category": "footwear",
        "purchase_from": "2026-11-01",
        "purchase_before": None,
        "source_id": "fictional-store-handbook/returns/v2",
        "window": 14,
        "condition": "Returned footwear must be unused and in its original packaging.",
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(db_path), timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db(db_path: str | Path, seed: bool = False) -> None:
    with connect(db_path) as db:
        db.executescript(SCHEMA)
        if seed:
            seed_demo(db)


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return f"pbkdf2_sha256$260000${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def validate_credentials(email: object, password: object) -> tuple[str, str]:
    if not isinstance(email, str) or not EMAIL_RE.fullmatch(email.strip()):
        raise ValueError("Enter a valid email address.")
    if not isinstance(password, str) or not 10 <= len(password) <= 128:
        raise ValueError("Password must be between 10 and 128 characters.")
    return email.strip().lower(), password


def seed_demo(db: sqlite3.Connection) -> None:
    """Create safe demo identities and orders only when the database is empty."""
    if db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        return
    created = now_iso()
    users = [
        ("demo@example.com", _password_hash("demo-password-123"), "customer"),
        ("agent@example.com", _password_hash("agent-password-123"), "agent"),
    ]
    db.executemany("INSERT INTO users(email,password_hash,role,created_at) VALUES (?,?,?,?)",
                   [(email, password, role, created) for email, password, role in users])
    customer_id = db.execute("SELECT id FROM users WHERE email=?", ("demo@example.com",)).fetchone()[0]
    orders = [
        ("order-1001", customer_id, "Delivered", "ParcelPost", "PP1001", "2026-10-25", "2026-10-29"),
        ("order-1002", customer_id, "In transit", "ParcelPost", "PP1002", "2026-11-10", None),
    ]
    db.executemany(
        "INSERT INTO orders(id,user_id,status,carrier,tracking_number,purchased_on,delivery_date,created_at) VALUES (?,?,?,?,?,?,?,?)",
        [row + (created,) for row in orders],
    )
    db.commit()


def user_public(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {"id": row["id"], "email": row["email"], "role": row["role"]}


def create_session(db: sqlite3.Connection, user_id: int) -> str:
    raw = secrets.token_urlsafe(32)
    current = int(time.time())
    db.execute("DELETE FROM sessions WHERE expires_at < ?", (current,))
    db.execute("INSERT INTO sessions(token_hash,user_id,expires_at,created_at) VALUES (?,?,?,?)",
               (token_hash(raw), user_id, current + SESSION_TTL_SECONDS, now_iso()))
    db.commit()
    return raw


def session_user(db: sqlite3.Connection, token: str | None) -> sqlite3.Row | None:
    if not token:
        return None
    row = db.execute(
        "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>=?",
        (token_hash(token), int(time.time())),
    ).fetchone()
    return row


def policy_for(purchase_date: str, country: str, category: str) -> dict | None:
    try:
        purchased = date.fromisoformat(purchase_date)
    except (TypeError, ValueError):
        raise ValueError("purchase_date must use YYYY-MM-DD.")
    matches = []
    for policy in POLICIES:
        if policy["country"] != country.upper() or policy["category"] != category.lower():
            continue
        start = date.fromisoformat(policy["purchase_from"])
        end = date.fromisoformat(policy["purchase_before"]) if policy["purchase_before"] else None
        if start <= purchased and (end is None or purchased < end):
            matches.append(policy)
    if len(matches) > 1:
        raise RuntimeError("Multiple policy versions apply; a reviewer must resolve the conflict.")
    return matches[0] if matches else None


def answer_policy(question: str, context: dict) -> dict:
    """Return a grounded, bounded answer; no free-form model output is trusted."""
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError("question must be non-empty text of at most 2000 characters.")
    if not isinstance(context, dict):
        raise ValueError("context must be an object.")
    query = question.lower()
    if re.search(r"\b(order|tracking|shipment|parcel)\b", query):
        return {"status": "unavailable", "answer": "Use Order lookup for live order status, or open a ticket for help."}
    if re.search(r"\b(guarantee|guaranteed|promise)\b", query):
        return {"status": "unsupported", "answer": "I cannot guarantee refund approval or execute a refund."}
    if not re.search(r"\b(return|refund|defective|used|packaging|condition)\b", query):
        return {"status": "clarify", "answer": "Please ask one specific return-policy question."}
    missing = [key for key in ("purchase_date", "country", "category") if not context.get(key)]
    if missing:
        return {"status": "clarify", "answer": "Please provide: " + ", ".join(missing), "missing": missing}
    policy = policy_for(context["purchase_date"], context["country"], context["category"])
    if policy is None:
        return {"status": "insufficient_evidence", "answer": "No applicable policy was found for that date and scope."}
    if re.search(r"\b(defective|damaged|exception)\b", query):
        return {"status": "insufficient_evidence", "answer": "The supplied policy does not specify an exception for defective products.",
                "source": policy["source_id"], "version": policy["version"]}
    if re.search(r"\b(used|worn|packaging|condition)\b", query):
        text = policy["condition"]
        passage_id = f"returns-{policy['version']}-condition"
    else:
        text = f"For covered purchases, request a return within {policy['window']} days after delivery."
        passage_id = f"returns-{policy['version']}-window"
    if re.search(r"\b(deadline|exact date|last day|final day|calendar date)\b", query):
        return {"status": "clarify", "answer": text + " Exact deadline calculation needs the store cutoff and timezone rules.",
                "source": policy["source_id"], "version": policy["version"], "passage_id": passage_id}
    return {"status": "answered", "answer": text, "source": policy["source_id"],
            "version": policy["version"], "passage_id": passage_id,
            "facts": {"return_days": policy["window"], "starts_from": "delivery"}}


def order_public(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in ("id", "status", "carrier", "tracking_number", "purchased_on", "delivery_date")}


def ticket_public(row: sqlite3.Row) -> dict:
    result = {key: row[key] for key in ("id", "order_id", "subject", "message", "status", "priority", "resolution_note", "created_at", "updated_at")}
    if "customer_email" in row.keys():
        result["customer_email"] = row["customer_email"]
    return result


class App:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        init_db(self.db_path, seed=os.getenv("SEED_DEMO", "1") == "1")

    def db(self) -> sqlite3.Connection:
        return connect(self.db_path)

    def register(self, payload: dict) -> dict:
        email, password = validate_credentials(payload.get("email"), payload.get("password"))
        with self.db() as db:
            try:
                cursor = db.execute("INSERT INTO users(email,password_hash,role,created_at) VALUES (?,?,?,?)",
                                    (email, _password_hash(password), "customer", now_iso()))
                user = db.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
                token = create_session(db, cursor.lastrowid)
            except sqlite3.IntegrityError:
                raise ValueError("An account with that email already exists.")
        return {"user": user_public(user), "token": token}

    def login(self, payload: dict) -> dict:
        email, password = validate_credentials(payload.get("email"), payload.get("password"))
        with self.db() as db:
            user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if user is None or not verify_password(password, user["password_hash"]):
                raise PermissionError("Email or password is incorrect.")
            token = create_session(db, user["id"])
        return {"user": user_public(user), "token": token}

    def logout(self, token: str | None) -> None:
        if token:
            with self.db() as db:
                db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(token),))

    def current_user(self, token: str | None) -> sqlite3.Row:
        with self.db() as db:
            user = session_user(db, token)
        if user is None:
            raise PermissionError("Authentication required.")
        return user

    def orders(self, token: str | None, order_id: str | None = None) -> list[dict]:
        user = self.current_user(token)
        with self.db() as db:
            if order_id:
                rows = db.execute("SELECT * FROM orders WHERE user_id=? AND id=?", (user["id"], order_id)).fetchall()
            else:
                rows = db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY purchased_on DESC", (user["id"],)).fetchall()
        return [order_public(row) for row in rows]

    def create_ticket(self, token: str | None, payload: dict) -> dict:
        user = self.current_user(token)
        subject = payload.get("subject")
        message = payload.get("message")
        if not isinstance(subject, str) or not 3 <= len(subject.strip()) <= 160:
            raise ValueError("subject must be between 3 and 160 characters.")
        if not isinstance(message, str) or not 5 <= len(message.strip()) <= 5000:
            raise ValueError("message must be between 5 and 5000 characters.")
        order_id = payload.get("order_id")
        priority = payload.get("priority", "normal")
        if priority not in {"normal", "high"}:
            raise ValueError("priority must be normal or high.")
        with self.db() as db:
            if order_id:
                owned = db.execute("SELECT 1 FROM orders WHERE id=? AND user_id=?", (order_id, user["id"])).fetchone()
                if owned is None:
                    raise ValueError("That order was not found for this account.")
            created = now_iso()
            cursor = db.execute(
                "INSERT INTO tickets(user_id,order_id,subject,message,priority,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                (user["id"], order_id, subject.strip(), message.strip(), priority, created, created),
            )
            row = db.execute("SELECT * FROM tickets WHERE id=?", (cursor.lastrowid,)).fetchone()
            db.execute("INSERT INTO audit_log(user_id,action,resource,created_at) VALUES (?,?,?,?)",
                       (user["id"], "ticket.created", str(cursor.lastrowid), created))
        return ticket_public(row)

    def tickets(self, token: str | None) -> list[dict]:
        user = self.current_user(token)
        with self.db() as db:
            if user["role"] in {"agent", "admin"}:
                rows = db.execute(
                    "SELECT t.*,u.email AS customer_email FROM tickets t "
                    "JOIN users u ON u.id=t.user_id "
                    "ORDER BY CASE t.priority WHEN 'high' THEN 0 ELSE 1 END,t.created_at"
                ).fetchall()
            else:
                rows = db.execute("SELECT * FROM tickets WHERE user_id=? ORDER BY created_at DESC", (user["id"],)).fetchall()
        return [ticket_public(row) for row in rows]

    def resolve_ticket(self, token: str | None, ticket_id: int, payload: dict) -> dict:
        user = self.current_user(token)
        if user["role"] not in {"agent", "admin"}:
            raise PermissionError("Only support agents can resolve tickets.")
        note = payload.get("resolution_note")
        if not isinstance(note, str) or not 3 <= len(note.strip()) <= 2000:
            raise ValueError("resolution_note must be between 3 and 2000 characters.")
        with self.db() as db:
            changed = now_iso()
            cursor = db.execute("UPDATE tickets SET status='resolved',resolution_note=?,updated_at=? WHERE id=? AND status!='resolved'",
                                (note.strip(), changed, ticket_id))
            if cursor.rowcount != 1:
                raise LookupError("Ticket not found or already resolved.")
            row = db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
            db.execute("INSERT INTO audit_log(user_id,action,resource,created_at) VALUES (?,?,?,?)",
                       (user["id"], "ticket.resolved", str(ticket_id), changed))
        return ticket_public(row)

    def audit_events(self, token: str | None, limit: int = 100) -> list[dict]:
        user = self.current_user(token)
        if user["role"] not in {"agent", "admin"}:
            raise PermissionError("Only support agents can view audit events.")
        limit = max(1, min(int(limit), 200))
        with self.db() as db:
            rows = db.execute(
                "SELECT id,user_id,action,resource,created_at FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]


class Handler(BaseHTTPRequestHandler):
    server_version = "CustomerSupportAI/1.0"
    sys_version = ""

    def __init__(self, *args, app: App, **kwargs):
        self.app = app
        super().__init__(*args, **kwargs)

    def log_message(self, fmt: str, *args: object) -> None:
        if os.getenv("ACCESS_LOG", "0") == "1":
            super().log_message(fmt, *args)

    def send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path: Path) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid Content-Length.")
        if not 0 < length <= MAX_BODY:
            raise ValueError("Request body must be between 1 byte and 64 KiB.")
        if self.headers.get_content_type() != "application/json":
            raise ValueError("Send application/json.")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object.")
        return value

    def token(self) -> str | None:
        header = self.headers.get("Authorization", "")
        return header[7:].strip() if header.lower().startswith("bearer ") else None

    def route(self) -> tuple[str, dict[str, str]]:
        parsed = urlparse(self.path)
        query = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}
        return parsed.path, query

    def do_GET(self) -> None:
        path, query = self.route()
        if path in {"/", "/index.html"}:
            self.send_file(STATIC / "index.html")
            return
        try:
            if path == "/health":
                self.send_json(200, {"status": "ok", "service": "customer-support-ai"})
            elif path == "/api/me":
                self.send_json(200, {"user": user_public(self.app.current_user(self.token()))})
            elif path == "/api/orders":
                self.send_json(200, {"orders": self.app.orders(self.token(), query.get("id"))})
            elif path == "/api/tickets":
                self.send_json(200, {"tickets": self.app.tickets(self.token())})
            elif path == "/api/audit":
                self.send_json(200, {"events": self.app.audit_events(self.token(), int(query.get("limit", "100")))})
            else:
                self.send_json(404, {"error": "Not found."})
        except PermissionError as error:
            self.send_json(401, {"error": str(error)})
        except LookupError as error:
            self.send_json(404, {"error": str(error)})
        except (ValueError, RuntimeError) as error:
            self.send_json(400, {"error": str(error)})

    def do_POST(self) -> None:
        path, _ = self.route()
        try:
            if path == "/api/auth/register":
                self.send_json(201, self.app.register(self.body()))
            elif path == "/api/auth/login":
                self.send_json(200, self.app.login(self.body()))
            elif path == "/api/auth/logout":
                self.app.logout(self.token())
                self.send_json(200, {"ok": True})
            elif path == "/api/policy/answer":
                self.app.current_user(self.token())
                payload = self.body()
                self.send_json(200, answer_policy(payload.get("question"), payload.get("context", {})))
            elif path == "/api/tickets":
                self.send_json(201, {"ticket": self.app.create_ticket(self.token(), self.body())})
            else:
                self.send_json(404, {"error": "Not found."})
        except PermissionError as error:
            self.send_json(401, {"error": str(error)})
        except (ValueError, RuntimeError) as error:
            self.send_json(400, {"error": str(error)})

    def do_PATCH(self) -> None:
        path, _ = self.route()
        match = re.fullmatch(r"/api/tickets/(\d+)", path)
        if not match:
            self.send_json(404, {"error": "Not found."})
            return
        try:
            self.send_json(200, {"ticket": self.app.resolve_ticket(self.token(), int(match.group(1)), self.body())})
        except PermissionError as error:
            self.send_json(401, {"error": str(error)})
        except LookupError as error:
            self.send_json(404, {"error": str(error)})
        except ValueError as error:
            self.send_json(400, {"error": str(error)})


def serve(db_path: str | Path, host: str = "127.0.0.1", port: int = 8766) -> None:
    app = App(db_path)
    from functools import partial
    handler = partial(Handler, app=app)
    with ThreadingHTTPServer((host, port), handler) as server:
        print(f"Customer Support AI: http://{host}:{port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", default=int(os.getenv("PORT", "8766")), type=int)
    parser.add_argument("--db", default=os.getenv("DATABASE_PATH", str(DEFAULT_DB)))
    parser.add_argument("--no-seed", action="store_true")
    args = parser.parse_args()
    if args.no_seed:
        os.environ["SEED_DEMO"] = "0"
    serve(args.db, args.host, args.port)
