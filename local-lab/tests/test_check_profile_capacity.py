import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "local-lab/scripts/check-profile-capacity.py"
spec = importlib.util.spec_from_file_location("profile_capacity", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProfileCapacityTests(unittest.TestCase):
    def test_memory_quantity_parser_handles_binary_and_decimal_units(self):
        self.assertEqual(module.memory_bytes("2Gi"), 2 * 1024 ** 3)
        self.assertEqual(module.memory_bytes("1500Mi"), 1500 * 1024 ** 2)
        self.assertEqual(module.memory_bytes("2G"), 2 * 1000 ** 3)

    def test_headroom_is_allocatable_minus_metrics_usage(self):
        nodes = {"items": [
            {"metadata": {"name": "cks-control"},
             "status": {"allocatable": {"memory": "4Gi"}}},
            {"metadata": {"name": "cks-worker"},
             "status": {"allocatable": {"memory": "4Gi"}}},
        ]}
        metrics = {"items": [
            {"metadata": {"name": "cks-control"}, "usage": {"memory": "2Gi"}},
            {"metadata": {"name": "cks-worker"}, "usage": {"memory": "1Gi"}},
        ]}
        result = module.calculate_headroom(nodes, metrics)
        self.assertEqual(result["cks-control"], 2 * 1024 ** 3)
        self.assertEqual(result["cks-worker"], 3 * 1024 ** 3)

    def test_optional_profile_thresholds_fail_closed(self):
        barely_enough = {
            "cks-control": 1024 * module.MIB,
            "cks-worker": 2200 * module.MIB,
        }
        self.assertEqual(module.evaluate(barely_enough), [])
        self.assertEqual(module.evaluate(barely_enough, include_opencost=True), [
            ("cks-worker", 2200 * module.MIB, 2560 * module.MIB),
        ])
        low_control = {**barely_enough, "cks-control": 900 * module.MIB}
        self.assertEqual(module.evaluate(low_control), [
            ("cks-control", 900 * module.MIB, 1024 * module.MIB),
        ])

    def test_missing_node_metrics_is_an_error(self):
        nodes = {"items": [{"metadata": {"name": "cks-control"},
                            "status": {"allocatable": {"memory": "4Gi"}}}]}
        with self.assertRaisesRegex(ValueError, "missing allocatable memory or Metrics API usage"):
            module.calculate_headroom(nodes, {"items": []})


if __name__ == "__main__":
    unittest.main()
