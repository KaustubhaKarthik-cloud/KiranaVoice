"""Real Prisma v2.5 outputs observed on 2026-10-22 (synthetic clips) must parse."""
from kiranavoice.parser import find_items
from kiranavoice.flow import OrderFlow
def test_prisma_outputs_flow():
    f = OrderFlow(caller_id="9876543210"); f.greet()
    r1 = f.handle("भैया, 2 किलो आता, एक लिट्रेट फॉर्च्यून ऑयल और 6 अंडे भेज दो।")
    assert {i.name: i.qty for i in f.items} == {"atta": 2, "Fortune oil": 1, "ande": 6}, r1
    r2 = f.handle("नहीं नहीं 12 आंद।"); assert r2.startswith("Done, 12 ande")
    f.handle("बस इतना"); f.handle("मेरा नाम रमेश।")
    assert f.state == "done" and f.order["customer_name"] == "रमेश"
