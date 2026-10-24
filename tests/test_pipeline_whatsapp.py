import asyncio, httpx
from kiranavoice.pipeline import CallSession
from kiranavoice.adapters.mock import MockTTS
from kiranavoice import whatsapp as W

def test_pipecat_session_end_to_end():
    evs = []
    async def emit(e): evs.append(e)
    async def go():
        s = CallSession(MockTTS(), W.WaMeSender(), emit)
        await s.start()
        for l in ["2 kilo atta aur ek packet maggi", "haan", "Ramesh", "9876543210"]:
            await s.user_text(l); await asyncio.sleep(0.2)
        await s.stop(); await asyncio.sleep(0.2)
    asyncio.run(go())
    o = [e for e in evs if e["type"] == "order"][0]
    assert o["order"]["items"][1] == {"name": "Maggi", "qty": 1, "unit": "packet"}
    assert o["send"]["wa_me"].startswith("https://wa.me/")

def test_twilio_request_shape(monkeypatch):
    for k, v in {"TWILIO_ACCOUNT_SID": "ACtest", "TWILIO_AUTH_TOKEN": "t", "TWILIO_WHATSAPP_FROM": "+14155238886",
                 "OWNER_WHATSAPP_TO": "+919000000000"}.items(): monkeypatch.setenv(k, v)
    seen = {}
    def fake_post(url, data, auth, timeout):
        seen.update(url=url, data=data); return httpx.Response(201, json={"sid": "SM1"})
    monkeypatch.setattr(W.httpx, "post", fake_post)
    r = W.TwilioSender().send("hi")
    assert r["ok"] and seen["data"]["From"] == "whatsapp:+14155238886" and seen["data"]["To"] == "whatsapp:+919000000000"
    assert seen["url"].endswith("/Accounts/ACtest/Messages.json")
