set -e
mkdir -p app tests
cat > app/__init__.py <<'EOF'
EOF
cat > tests/__init__.py <<'EOF'
EOF
cat > app/billing.py <<'EOF'
"""Nightly usage billing: turns a day of usage records into invoice lines."""


def unit_price(plan):
    return {"basic": 0.02, "pro": 0.015}[plan]


def line_total(units, plan):
    return round(units * unit_price(plan), 2)


def invoice(records):
    """records: list of (customer, plan, units). Returns {customer: total}."""
    out = {}
    for customer, plan, units in records:
        out[customer] = round(out.get(customer, 0) + line_total(units, plan), 2)
    return out
EOF
cat > tests/test_billing.py <<'EOF'
import unittest

from app.billing import invoice, line_total


class BillingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(1000, "basic"), 20.0)
        self.assertEqual(line_total(333, "pro"), 5.0)

    def test_invoice_sums_per_customer(self):
        recs = [("acme", "basic", 1000), ("acme", "basic", 500), ("zed", "pro", 1000)]
        self.assertEqual(invoice(recs), {"acme": 30.0, "zed": 15.0})


if __name__ == "__main__":
    unittest.main()
EOF
cat > README.md <<'EOF'
# nightly-billing

Turns a day of usage records into invoice lines. Tests: `python3 -m unittest`.
EOF
git add -A && git commit -qm "billing: nightly invoice lines"
# the first breaking commit: rounding moved to the wrong place
python3 - <<'EOF'
p = "app/billing.py"
s = open(p).read().replace("return round(units * unit_price(plan), 2)",
                           "return round(units, 2) * unit_price(plan)")
open(p, "w").write(s)
EOF
git add -A && git commit -qm "billing: round units before pricing"
# the second breaking commit: a renamed key
python3 - <<'EOF'
p = "app/billing.py"
s = open(p).read().replace('{"basic": 0.02, "pro": 0.015}', '{"basic": 0.02, "professional": 0.015}')
open(p, "w").write(s)
EOF
git add -A && git commit -qm "billing: plan name professional"
