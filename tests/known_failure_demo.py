"""Intentionally failing test; run separately with `python tests/known_failure_demo.py`.

The assertion captures a tempting but incorrect expectation: reversing the debit
should erase all consequences of that debit. It fails because overdraft fees are
separate append-only ledger entries and the rules provide no automatic fee reversal.
"""
import unittest
from decimal import Decimal as D
from ledger import Ledger, event_stream


class KnownFailureDemo(unittest.TestCase):
    def test_wrong_expectation_reversal_erases_fees(self):
        ledger = Ledger()
        for event in event_stream():
            ledger.process(event)
        # INTENTIONALLY FAILS: E9 compensates E7, but cannot delete fee entries.
        self.assertEqual(ledger.base_balance('ACC-001', 2), D('250.00'))


if __name__ == '__main__':
    unittest.main()
