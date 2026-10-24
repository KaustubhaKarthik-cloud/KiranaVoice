"""Hinglish order conversation state machine. Pure logic; no I/O."""
from datetime import datetime, timezone, timedelta
from . import parser as P

IST = timezone(timedelta(hours=5, minutes=30))
UNIT_SPOKEN = {"kg": "kilo", "L": "litre", "g": "gram", "packet": "packet", "pcs": "", "box": "dabba", "bottle": "bottle"}

def speak_item(i):
    u = UNIT_SPOKEN.get(i.unit, i.unit)
    return " ".join(x for x in [P.fmt_qty(i.qty), u, i.name] if x)

class OrderFlow:
    """States: greeting -> taking_items -> (clarify) -> confirm -> ask_name -> ask_phone -> done."""

    def __init__(self, shop="Sharma Kirana", caller_id=None):
        self.shop, self.state = shop, "start"
        self.items: list[P.Item] = []
        self.pending: P.Item | None = None
        self.customer_name = None
        self.phone = caller_id
        self.order = None

    def greet(self):
        self.state = "taking_items"
        return f"Namaste! {self.shop} se bol rahe hain. Bataiye, kya bhejna hai?"

    def _merge(self, new, replace=True):
        for n in new:
            for i, old in enumerate(self.items):
                if old.name == n.name:
                    self.items[i] = n if replace else old
                    break
            else:
                self.items.append(n)

    def _readback(self):
        self.state = "confirm"
        return "Theek hai, " + ", ".join(speak_item(i) for i in self.items) + ". Sahi hai?"

    def handle(self, text: str) -> str:
        if self.state == "start":
            return self.greet()
        if self.state == "done":
            return "Order already ho gaya hai. Dhanyavaad!"
        items, unknown = P.find_items(text)

        if self.state == "clarify" and self.pending:
            q = items[0].qty if items else None
            if q is None:
                toks = [P._num(t) for t in P.normalize(text).split()]
                q = next((t for t in toks if t is not None), None)
            if q is None:
                return f"Sorry, {self.pending.name} kitne {UNIT_SPOKEN.get(self.pending.unit) or 'chahiye'}?"
            self.pending.qty = q
            self._merge([self.pending]); self.pending = None
            return self._next_after_items([], [])

        if self.state in ("taking_items", "confirm"):
            if self.state == "confirm" and P.is_removal(text) and items:
                names = {i.name for i in items}
                self.items = [i for i in self.items if i.name not in names]
                return "Hata diya. " + (self._readback() if self.items else "Aur kya chahiye?")
            if self.state == "confirm" and items:
                # correction: "nahi nahi, 12 ande"
                self._merge([i for i in items if i.qty is not None])
                missing = [i for i in items if i.qty is None]
                changed = ", ".join(speak_item(i) for i in items if i.qty is not None)
                if missing:
                    return self._next_after_items(missing, unknown)
                self.state = "confirm"
                return f"Done, {changed}. Aur kuch?"
            if self.state == "confirm" and P.is_yes(text) and not P.is_negation(text):
                return self._ask_name()
            if self.state == "confirm" and P.is_negation(text) and not items:
                self.state = "taking_items"
                return "Koi baat nahi, kya badalna hai?"
            if self.state == "confirm" and P.normalize(text) in ("bas", "bas itna", "nahi bas", "aur kuch nahi", "nahi"):
                return self._ask_name()
            return self._next_after_items(items, unknown)

        if self.state == "ask_name":
            self.customer_name = P.extract_name(text) or P.normalize(text).split()[-1].title()
            if self.customer_name.isascii(): self.customer_name = self.customer_name.title()
            return self._ask_phone()
        if self.state == "ask_phone":
            ph = P.extract_phone(text)
            if not ph:
                return "Sorry, number dobara boliye? Das digit."
            self.phone = ph
            return self._close()
        return "Sorry, samajh nahi aaya. Dobara boliye?"

    def _next_after_items(self, items, unknown):
        known_qty = [i for i in items if i.qty is not None]
        self._merge(known_qty)
        missing = [i for i in items if i.qty is None]
        if missing:
            self.pending, self.state = missing[0], "clarify"
            u = UNIT_SPOKEN.get(missing[0].unit) or ""
            return f"Sorry, {missing[0].name} kitne {u or 'chahiye'}?".replace("  ", " ")
        if unknown and not items:
            return f"Sorry, {unknown[0]} abhi stock mein nahi hai. Aur kuch?"
        if unknown:
            self.state = "confirm"
            return f"{unknown[0].title()} abhi nahi hai. " + self._readback()
        if not self.items:
            return "Sorry, samajh nahi aaya. Kya chahiye, jaise '2 kilo atta'?"
        return self._readback()

    def _ask_name(self):
        if self.customer_name:
            return self._ask_phone()
        self.state = "ask_name"
        return "Aapka naam bata dijiye?"

    def _ask_phone(self):
        if self.phone:
            return self._close()
        self.state = "ask_phone"
        return "Aur phone number?"

    def _close(self):
        self.state = "done"
        self.order = {
            "customer_name": self.customer_name,
            "phone": self.phone,
            "items": [P.item_dict(i) for i in self.items],
            "timestamp": datetime.now(IST).isoformat(timespec="seconds"),
        }
        return f"Shukriya {self.customer_name or ''} ji! Order note ho gaya, thodi der mein bhej denge.".replace("  ", " ")
