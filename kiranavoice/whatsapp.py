"""Pluggable WhatsApp order-summary senders."""
import json, os, logging, urllib.parse
import httpx

log = logging.getLogger("whatsapp")
UNIT = {"kg": "kg", "L": "L", "pcs": "", "packet": "packet"}

def format_summary(order: dict, shop="Sharma Kirana") -> str:
    lines = [f"🛒 *Naya order — {shop}*", f"👤 {order.get('customer_name') or '-'}  📞 {order.get('phone') or '-'}", ""]
    for i, it in enumerate(order["items"], 1):
        q = it["qty"]; q = int(q) if float(q).is_integer() else q
        lines.append(f"{i}. {it['name']} — {q} {UNIT.get(it['unit'], it['unit'])}".rstrip())
    lines += ["", f"🕒 {order['timestamp']}", "_KiranaVoice se aaya (synthetic demo)_"]
    return "\n".join(lines)

def wa_me_link(text: str, to: str | None = None) -> str:
    to = (to or os.getenv("OWNER_WHATSAPP_TO", "")).replace("whatsapp:", "").lstrip("+")
    return f"https://wa.me/{to}?text={urllib.parse.quote(text)}"

class MockSender:
    name = "mock"
    def send(self, text: str) -> dict:
        log.info("WHATSAPP (mock):\n%s", text)
        with open("whatsapp_outbox.log", "a", encoding="utf-8") as f:
            f.write(text + "\n---\n")
        return {"sender": "mock", "ok": True, "wa_me": wa_me_link(text)}

class WaMeSender:
    name = "wame"
    def send(self, text: str) -> dict:
        return {"sender": "wame", "ok": True, "wa_me": wa_me_link(text), "note": "owner taps link to send"}

class TwilioSender:
    """Twilio WhatsApp sandbox via REST (Messages API). NOT executed: no credentials yet."""
    name = "twilio"
    def __init__(self):
        self.sid = os.environ["TWILIO_ACCOUNT_SID"]; self.token = os.environ["TWILIO_AUTH_TOKEN"]
        self.frm = os.environ["TWILIO_WHATSAPP_FROM"]; self.to = os.environ["OWNER_WHATSAPP_TO"]
        for v in ("frm", "to"):
            if not getattr(self, v).startswith("whatsapp:"):
                setattr(self, v, "whatsapp:" + getattr(self, v))
    def send(self, text: str) -> dict:
        r = httpx.post(f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Messages.json",
                       data={"From": self.frm, "To": self.to, "Body": text}, auth=(self.sid, self.token), timeout=15)
        ok = r.status_code in (200, 201)
        return {"sender": "twilio", "ok": ok, "status": r.status_code, "sid": r.json().get("sid") if ok else None,
                "error": None if ok else r.text[:300], "wa_me": wa_me_link(text)}

def get_sender(kind: str):
    return {"mock": MockSender, "wame": WaMeSender, "twilio": TwilioSender}[kind]()
