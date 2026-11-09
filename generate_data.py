"""generate_data.py -- deterministic synthetic data generator
Run: python generate_data.py         (writes ./data/raw/...)
Uses only the Python standard library. All data is synthetic.
"""
import csv, math, os, random
from datetime import datetime, timedelta

rng = random.Random(42)
RAW = os.path.join("data", "raw")
POL = os.path.join("data", "policies")
os.makedirs(RAW, exist_ok=True)
os.makedirs(POL, exist_ok=True)

CITIES = ["Chennai", "Mumbai", "Bengaluru", "Delhi", "Pune", "Hyderabad"]
PRODUCTS = [
    ("Basmati Rice 1kg", "Grocery", 129), ("Toor Dal 1kg", "Grocery", 145),
    ("Sunflower Oil 1L", "Grocery", 155), ("Sugar 1kg", "Grocery", 48),
    ("Tea Powder 250g", "Grocery", 120), ("Poha 500g", "Grocery", 42),
    ("Toned Milk 500ml", "Dairy", 29), ("Curd 400g", "Dairy", 35),
    ("Butter 100g", "Dairy", 58), ("Cheese Slices 200g", "Dairy", 130),
    ("Eggs 12 Pack", "Dairy", 84), ("Lassi 200ml", "Dairy", 22),
    ("Potato Chips 52g", "Snacks", 20), ("Namkeen 200g", "Snacks", 65),
    ("Dark Chocolate 80g", "Snacks", 150), ("Instant Noodles 4-Pack", "Snacks", 56),
    ("Peanut Butter 340g", "Snacks", 210), ("Cold Drink 750ml", "Snacks", 45),
    ("Shampoo 340ml", "Personal Care", 280), ("Face Wash 100ml", "Personal Care", 175),
    ("Toothpaste 150g", "Personal Care", 98), ("Soap 3-Pack", "Personal Care", 115),
    ("Hand Wash 250ml", "Personal Care", 99), ("Body Lotion 200ml", "Personal Care", 190),
    ("Deodorant 150ml", "Personal Care", 220), ("Sunscreen 50ml", "Personal Care", 299),
    ("Wireless Earbuds", "Electronics", 1499), ("Power Bank 10000mAh", "Electronics", 899),
    ("USB-C Cable 1m", "Electronics", 299), ("Phone Charger 20W", "Electronics", 499),
    ("Smart Bulb", "Electronics", 599), ("Bluetooth Speaker", "Electronics", 1299),
    ("Phone Stand", "Electronics", 349), ("Memory Card 64GB", "Electronics", 450)
]

CAT_IDX = {}
for i, (_, c, _) in enumerate(PRODUCTS):
    CAT_IDX.setdefault(c, []).append(i)

def write(name, header, rows):
    with open(os.path.join(RAW, name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

def poisson(lam):
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1

def mangle_city(c):
    r = rng.random()
    if r < 0.20:
        return c.lower()
    elif r < 0.35:
        return c.upper()
    elif r < 0.50:
        return " " + c + " "
    return c

def mangle_gender(g):
    opts = {"male": ["male", "Male", "M", "m", "MALE"], "female": ["female", "Female", "F", "f", "FEMALE"]}
    return rng.choice(opts.get(g, ["unknown"]))

# Products
write("products.csv", ["product_id", "product_name", "category", "price_inr"],
      [[f"P{i+1:03d}", n, c, p] for i, (n, c, p) in enumerate(PRODUCTS)])

# Customers
N_CUST = 1200
IMPOSSIBLE_AGE = {10: 280, 110: -4, 210: 0, 310: 150, 410: 999, 510: 5}
cust, arche = [], {}
for i in range(N_CUST):
    cid = f"C{i+1:04d}"
    r = rng.random()
    arche[cid] = "premium" if r < 0.20 else ("frequent" if r < 0.70 else "rare")
    signup = datetime(2024, 1, 1) + timedelta(days=rng.randint(0, 365))
    age = IMPOSSIBLE_AGE.get(i, rng.randint(18, 60))
    if i not in IMPOSSIBLE_AGE and rng.random() < 0.05:
        age = ""
    g = "female" if rng.random() < 0.52 else "male"
    gender = "" if rng.random() < 0.03 else mangle_gender(g)
    cust.append([cid, mangle_city(rng.choice(CITIES)), signup.strftime("%Y-%m-%d"), age, gender])

write("customers.csv", ["customer_id", "city", "signup_date", "age", "gender"], cust)

# Orders
WIN_START, WIN_DAYS = datetime(2025, 4, 1), 183
RATE = {"premium": 1.0, "frequent": 3.5, "rare": 0.5}

def pick_product(a):
    if a == "premium":
        pool = CAT_IDX.get("Electronics", []) + CAT_IDX.get("Personal Care", [])
        return rng.choice(pool), rng.randint(1, 2)
    if a == "frequent":
        pool = CAT_IDX.get("Grocery", []) + CAT_IDX.get("Dairy", []) + CAT_IDX.get("Snacks", [])
        return rng.choice(pool), rng.randint(1, 4)
    return rng.randint(0, len(PRODUCTS)-1), rng.randint(1, 2)

rows, oid = [], 100000
for cid, a in arche.items():
    n_ord = poisson(RATE[a] * 6.0)
    for _ in range(n_ord):
        oid += 1
        pi, qty = pick_product(a)
        ts = WIN_START + timedelta(days=rng.randint(0, WIN_DAYS-1), minutes=rng.randint(0, 1439))
        disc = rng.choice([0, 0, 0, 5, 10, 15, 20])
        status = "cancelled" if rng.random() < 0.10 else "completed"
        amount = round(PRODUCTS[pi][2] * qty * (1 - disc / 100.0), 2)
        if status == "cancelled":
            deliv = ""
        else:
            deliv = rng.randint(46, 75) if rng.random() < 0.15 else rng.randint(12, 40)
            if rng.random() < 0.06:
                deliv = ""
        rows.append({
            "order_id": f"ORD-{oid}", "customer_id": cid, "product_id": f"P{pi+1:03d}",
            "order_ts": ts.strftime("%Y-%m-%d %H:%M:%S"), "status": status,
            "discount_pct": disc, "order_amount": amount, "quantity": qty,
            "delivery_minutes": deliv
        })

out = []
for k, r in enumerate(rows):
    if k % 100 == 7 and r["status"] == "completed":
        r["delivery_minutes"] = -10
    if r["status"] == "completed" and rng.random() < 0.01:
        r["order_amount"] = "N/A" if rng.random() < 0.5 else "INVALID"
    base = [r["order_id"], r["customer_id"], r["product_id"], r["order_ts"],
            r["status"], r["discount_pct"], r["order_amount"], r["quantity"], r["delivery_minutes"]]
    out.append(base)
    if rng.random() < 0.05:
        early = list(base)
        early[4] = "pending"
        early[8] = ""
        out.append(early)
    if rng.random() < 0.01:
        out.append(list(base))

rng.shuffle(out)
write("orders.csv", ["order_id", "customer_id", "product_id", "order_ts", "status", "discount_pct", "order_amount", "quantity", "delivery_minutes"], out)

# Tickets
T = {
    "billing": [
        "I was charged twice for order {o}.", "The invoice for {o} shows a wrong amount.",
        "Extra money was deducted for order {o}."
    ],
    "delivery": [
        "My order {o} has not arrived yet.", "Delivery for {o} is very late.",
        "The rider marked {o} as delivered but I didn't get it."
    ],
    "technical": [
        "The app crashes every time I open it.", "I cannot login, the OTP never arrives.",
        "The payment page shows an error."
    ],
    "fraud": [
        "There is an unauthorized transaction on my account.",
        "Someone hacked my account and used my wallet.",
        "I was charged for order {o} that I never placed."
    ]
}

order_by_cust = {}
for r in out:
    order_by_cust.setdefault(r[1], r[0])
cust_with_orders = sorted(order_by_cust.keys())

tickets = []
cats = list(T.keys())
for n in range(1, 157):
    cat = cats[(n - 1) % 4]
    cid = rng.choice(cust_with_orders)
    txt = rng.choice(T[cat]).format(o=order_by_cust[cid])
    tickets.append([f"T{n:04d}", cid, order_by_cust[cid], txt, cat])

for n in range(157, 161):
    tickets.append([f"T{n:04d}", rng.choice(cust_with_orders), "", "", "billing"])

FILL = "The same problem keeps happening and nobody is resolving my issue. " * 30
for n in range(161, 165):
    tickets.append([f"T{n:04d}", rng.choice(cust_with_orders), "", FILL, "technical"])

rng.shuffle(tickets)
write("tickets.csv", ["ticket_id", "customer_id", "order_id", "text", "true_category"], tickets)

# Policy Documents
DOCS = {
    "refund_policy.txt": """Refund Policy. A refund can be requested for any completed order within 7 days of delivery. Completed orders delivered in more than 45 minutes are eligible for a 100% refund of the order amount. Orders delivered in 45 minutes or less are not eligible for delivery-delay refunds (refund amount is 0). If a refund amount exceeds INR 1000, it cannot be issued automatically and must be escalated to a human supervisor for approval. Wallet balance refunds cannot be cashed out.""",
    "delivery_policy.txt": """Delivery Policy. Standard delivery target time for completed orders is within 45 minutes. Free delivery applies on orders with order value above INR 500; otherwise a delivery fee of INR 35 is charged. Electronics items require signature on delivery.""",
    "payment_policy.txt": """Payment Policy. Customers can pay using UPI, credit/debit cards, net banking, or Instamart Wallet. Cash on delivery is available for orders under INR 1000. Refunds for failed online transactions are credited within 3 to 5 working days.""",
    "privacy_policy.txt": """Privacy Policy. Customer data is stored securely in accordance with Indian data protection regulations. Personal identification information is retained as long as the account is active. Delivery addresses are retained for 30 days post-delivery.""",
    "escalation_policy.txt": """Escalation Policy. A support ticket is escalated to tier-2 human support if the automated assistant cannot resolve it within 3 steps. Fraud tickets must reach the security team within 15 minutes of submission."""
}

for fn, body in DOCS.items():
    with open(os.path.join(POL, fn), "w", encoding="utf-8") as f:
        f.write(body + "
")

# Policy evaluation questions
QA = [
    ("What delivery time makes a completed order eligible for a 100% refund?", "refund_policy.txt", "45 minutes"),
    ("Who must approve a refund above INR 1000?", "refund_policy.txt", "human supervisor"),
    ("How many days do I have to raise a refund request?", "refund_policy.txt", "7 days"),
    ("What is the delivery fee on small orders?", "delivery_policy.txt", "35"),
    ("On orders of what value is delivery free?", "delivery_policy.txt", "500"),
    ("Why does the electronics delivery need a signature?", "delivery_policy.txt", "signature on delivery"),
    ("Is cash on delivery available for a large order above INR 1000?", "payment_policy.txt", "under INR 1000"),
    ("How soon is money returned when a payment fails online?", "payment_policy.txt", "3 to 5 working days"),
    ("Can wallet balance be refunded as cash?", "refund_policy.txt", "cannot be cashed out"),
    ("When are delivery addresses deleted from accounts?", "privacy_policy.txt", "30 days"),
    ("How fast must a fraud ticket reach the security team?", "escalation_policy.txt", "15 minutes"),
    ("After how many steps must an automated assistant escalate?", "escalation_policy.txt", "3 steps"),
    ("What is the favourite colour of the company founder?", "NONE", "NONE"),
    ("Who won the cricket world cup final?", "NONE", "NONE")
]

with open(os.path.join(RAW, "policy_eval.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["question", "expected_doc", "expected_fact"])
    w.writerows(QA)

# Agent scenarios
from collections import Counter
cnt = Counter(r[0] for r in out)
def clean_row(r):
    try:
        return cnt[r[0]] == 1 and r[4] in ("completed", "cancelled") and (r[4] == "cancelled" or (r[8] != "" and float(r[8]) > 0))
    except ValueError:
        return False

ok_rows = sorted((r for r in out if clean_row(r)), key=lambda x: x[0])
def first(pred):
    return next(r for r in ok_rows if pred(r))

late_small = [r for r in ok_rows if r[4] == "completed" and float(r[8]) > 45 and float(r[6]) <= 1000]
late_big = first(lambda r: r[4] == "completed" and float(r[8]) > 45 and float(r[6]) > 1000)
on_time = first(lambda r: r[4] == "completed" and float(r[8]) <= 45)
cancelled = first(lambda r: r[4] == "cancelled")

SC = []
for r in late_small[:2]:
    SC.append((r[1], f"My order {r[0]} reached me late. I want a refund.", r[0], float(r[6])))

SC.append((late_big[1], f"Order {late_big[0]} arrived very late, please refund.", late_big[0], float(late_big[6])))
SC.append((on_time[1], f"Please refund order {on_time[0]}.", on_time[0], float(on_time[6])))
SC.append((cancelled[1], f"I want my money back for order {cancelled[0]}.", cancelled[0], 0.0))
SC.append(("C0001", "Refund for order ORD-999999 please.", "ORD-999999", 0.0))
SC.append((late_small[0][1], f"[LOOP] Refund order {late_small[0][0]}", late_small[0][0], float(late_small[0][6])))

with open(os.path.join(RAW, "agent_scenarios.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["scenario_id", "customer_id", "user_message", "order_id", "expected_refund_inr"])
    for i, (cid, msg, oc, amt) in enumerate(SC, 1):
        w.writerow([f"S{i}", cid, msg, oc, amt])

print("generated: customers=%d products=%d orders_raw=%d tickets=%d" % (len(cust), len(PRODUCTS), len(out), len(tickets)))
