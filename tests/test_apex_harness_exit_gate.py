"""Harness must fail closed; child transport success is not gate success."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('harness_cycle', Path(__file__).resolve().parents[1] / 'scripts/apex_harness_cycle.py')
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)

class HarnessExitGate(unittest.TestCase):
    def check_case(self, change=None, expected=0):
        children = [
            {'registry': {'ok': True}},
            {'decision': 'allow', 'risk_score': 0.24},
            {'V_H': True, 'I_continue': False},
        ]
        results = [{'returncode': 0, 'stdout': json.dumps(x), 'stderr': ''} for x in children]
        if change:
            change(results)
        out = io.StringIO()
        with patch.object(harness, 'run', side_effect=results), contextlib.redirect_stdout(out):
            code = harness.main()
        self.assertEqual(code, expected)
        self.assertEqual(json.loads(out.getvalue())['verification_ok'], expected == 0)

    def test_healthy(self): self.check_case()
    def test_nonzero_child_with_valid_json(self):
        self.check_case(lambda r: r[1].update(returncode=7), 1)
    def test_malformed_json(self):
        self.check_case(lambda r: r[2].update(stdout='broken JSON'), 1)
    def test_denied(self):
        self.check_case(lambda r: r[1].update(stdout='{"decision":"deny"}'), 1)
    def test_unhealthy_indicator(self):
        self.check_case(lambda r: r[2].update(stdout='{"V_H":false,"I_continue":true}'), 1)
    def test_registry_failure(self):
        self.check_case(lambda r: r[0].update(stdout='{"registry":{"ok":false}}'), 1)

if __name__ == '__main__': unittest.main()
