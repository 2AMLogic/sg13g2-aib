#!/usr/bin/env python3
"""Self-tests: each checker must accept a good input and reject a seeded-bad one.

Runs every suite: python3 -I scripts/ci/test_checkers.py

The entry point `npm test` and signoff/attest/item10.inventory.json invoke by
name. It only loads the four sibling suites and runs them; CI runs each sibling
on its own through scripts/ci/check_local.sh. python3 -I drops this directory
from sys.path, hence the insert below.
"""
import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SUITES = ("test_evidence_checkers", "test_signoff_pins", "test_sim_infra", "test_ci_guards")


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    for name in SUITES:
        suite.addTests(loader.loadTestsFromModule(importlib.import_module(name)))
    return suite


if __name__ == "__main__":
    unittest.main(verbosity=2)
