import html
import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "cme_cover.py"
SPEC = importlib.util.spec_from_file_location("cme_cover", MODULE_PATH)
cme_cover = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cme_cover
assert SPEC.loader is not None
SPEC.loader.exec_module(cme_cover)


class CmeCoverTests(unittest.TestCase):
    def test_paperback_spine_width_uses_lulu_formula(self) -> None:
        self.assertAlmostEqual(cme_cover.paperback_spine_width_in(80), 80 / 444 + 0.06)

    def test_plan_cover_dimensions_for_5x8_paperback(self) -> None:
        plan = cme_cover.plan_cover(pages=80, trim="5x8", binding="paperback-perfect")

        self.assertAlmostEqual(plan.spine_width_in, 80 / 444 + 0.06)
        self.assertAlmostEqual(plan.cover_width_in, 10 + (80 / 444 + 0.06) + 0.25)
        self.assertAlmostEqual(plan.cover_height_in, 8.25)
        self.assertFalse(plan.spine_text_allowed)
        self.assertEqual(plan.barcode["width"], 2.0)
        self.assertEqual(plan.barcode["height"], 1.2)
        payload = plan.to_json()
        json.dumps(payload, ensure_ascii=False)
        self.assertIn("Do not include spine text", " ".join(payload["warnings"]))

    def test_plan_allows_spine_text_at_100_pages(self) -> None:
        self.assertTrue(cme_cover.plan_cover(pages=100).spine_text_allowed)

    def test_template_svg_contains_regions_and_dimensions(self) -> None:
        plan = cme_cover.plan_cover(pages=80)
        svg = cme_cover.cover_template_svg(
            plan,
            title="Sir Gawain and the Green Knight",
            author="Kyvero Press",
        )

        self.assertIn('width="10.49018in"', svg)
        self.assertIn('height="8.25in"', svg)
        self.assertIn("BACK COVER", svg)
        self.assertIn("SPINE", svg)
        self.assertIn("FRONT COVER", svg)
        self.assertIn("ISBN barcode area", svg)
        self.assertIn("Sir Gawain and the Green", svg)
        self.assertIn("Knight", svg)

    def test_template_footer_labels_have_distinct_y_positions_and_avoid_barcode(self) -> None:
        plan = cme_cover.plan_cover(pages=80)
        svg = cme_cover.cover_template_svg(plan, title="Sir Gawain", author="Kyvero Press")

        footer_x = plan.back["x"] + 0.15
        small_text_matches = re.findall(
            rf'<text class="small" x="{footer_x:g}" y="([^"]+)"[^>]*>([^<]+)</text>',
            svg,
        )
        self.assertGreaterEqual(len(small_text_matches), 4)
        y_values = [match[0] for match in small_text_matches]
        self.assertEqual(len(y_values), len(set(y_values)))
        for _, text in small_text_matches:
            self.assertLessEqual(len(html.unescape(text)), 48)
        self.assertLess(footer_x, plan.barcode["x"])

    def test_write_svg_template(self) -> None:
        plan = cme_cover.plan_cover(pages=80)
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "cover.svg"
            cme_cover.write_template(plan, output)
            self.assertTrue(output.exists())
            self.assertIn("<svg", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
