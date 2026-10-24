from kiranavoice.parser import find_items, normalize
from kiranavoice.flow import OrderFlow

def d(text):
    return {i.name: (i.qty, i.unit) for i in find_items(text)[0]}

def test_script_line():
    assert d("Bhaiya, 2 kilo atta, 1 litre Fortune oil aur 6 ande bhej do") == {
        "atta": (2, "kg"), "Fortune oil": (1, "L"), "ande": (6, "pcs")}

def test_words():
    assert d("do kilo atta")["atta"] == (2, "kg")
    assert d("aadha kilo cheeni")["cheeni"] == (0.5, "kg")
    assert d("ek packet maggi")["Maggi"] == (1, "packet")
    assert d("dedh kilo chawal")["chawal"] == (1.5, "kg")
    assert d("500 gram dal")["dal"] == (0.5, "kg")
    assert d("ek darjan ande")["ande"] == (12, "pcs")

def test_devanagari():
    assert normalize("२ किलो") == "2 किलो"
    assert d("२ किलो आटा")["atta"] == (2, "kg")
    assert d("दो किलो चीनी")["cheeni"] == (2, "kg")

def test_bhej_do_not_two():
    assert d("maggi bhej do") == {"Maggi": (None, "packet")}

def test_unknown():
    assert find_items("2 kilo kaju")[1] == ["kaju"]

def run(lines, caller=None):
    f = OrderFlow(caller_id=caller); out = [f.greet()]
    for l in lines: out.append(f.handle(l))
    return f, out

def test_demo_script():
    f, out = run(["Bhaiya, 2 kilo atta, 1 litre Fortune oil aur 6 ande bhej do", "Nahi nahi, 12 ande",
                  "bas", "mera naam Ramesh", "98765 43210"])
    assert "2 kilo atta" in out[1] and "6 ande" in out[1]
    assert out[2].startswith("Done, 12 ande")
    o = f.order
    assert o["customer_name"] == "Ramesh" and o["phone"] == "9876543210"
    assert {i["name"]: i["qty"] for i in o["items"]} == {"atta": 2, "Fortune oil": 1, "ande": 12}

def test_correction_teen_kilo():
    f, out = run(["do kilo atta", "nahi, teen kilo atta"])
    assert f.items[0].qty == 3

def test_unclear_qty():
    f, out = run(["atta bhej do", "do"])
    assert out[1] == "Sorry, atta kitne kilo?"
    assert f.items[0].qty == 2

def test_unclear_qty_repeat():
    f, out = run(["atta chahiye", "umm"])
    assert "kitne kilo" in out[2]

def test_unknown_item_reply():
    f, out = run(["2 kilo kaju"])
    assert "stock mein nahi" in out[1]

def test_gibberish():
    f, out = run(["hello hello"])
    assert "samajh nahi" in out[1]

def test_remove_and_yes():
    f, out = run(["2 kilo atta aur ek packet maggi", "maggi hata do", "haan sahi hai", "Suresh", "9000012345"])
    assert [i.name for i in f.items] == ["atta"] and f.state == "done"
    assert f.order["customer_name"] == "Suresh"

def test_caller_id_skips_phone():
    f, out = run(["2 kilo atta", "haan", "naam Priya"], caller="9999900000")
    assert f.state == "done" and f.order["phone"] == "9999900000"
