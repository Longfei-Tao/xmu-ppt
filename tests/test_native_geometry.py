"""Regression tests for absolute geometry resolution in the native pipeline.

Two failure modes used to make capacity checks and preview masks wrong:

* Shapes inside ``p:grpSp`` reported child-space coordinates as if they were
  slide coordinates.
* Placeholders without their own ``a:xfrm`` reported no geometry at all.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/xmu-ppt/scripts"
DECKS = ROOT / "skills/xmu-ppt/templates/decks"
sys.path.insert(0, str(SCRIPTS))

from template_fill_pptx.analyzer import analyze_pptx  # noqa: E402
from template_fill_pptx.ooxml import (  # noqa: E402
    NS,
    _resolve_absolute_emu,
    _text_containers,
)

P = NS["p"]
A = NS["a"]


def _group_tree() -> ET.Element:
    """A group at 1in/1in with a 2:1 scale, holding one 0.5in text shape."""
    xml = f"""
    <p:spTree xmlns:p="{P}" xmlns:a="{A}">
      <p:grpSp>
        <p:nvGrpSpPr><p:cNvPr id="7" name="Group 7"/></p:nvGrpSpPr>
        <p:grpSpPr><a:xfrm>
          <a:off x="914400" y="914400"/>
          <a:ext cx="1828800" cy="914400"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="914400" cy="914400"/>
        </a:xfrm></p:grpSpPr>
        <p:sp>
          <p:nvSpPr><p:cNvPr id="9" name="Child"/></p:nvSpPr>
          <p:spPr><a:xfrm>
            <a:off x="457200" y="0"/>
            <a:ext cx="914400" cy="914400"/>
          </a:xfrm></p:spPr>
          <p:txBody><a:bodyPr/><a:p><a:r><a:t>Hi</a:t></a:r></a:p></p:txBody>
        </p:sp>
      </p:grpSp>
    </p:spTree>
    """
    return ET.fromstring(xml)


class GroupTransformTests(unittest.TestCase):
    def test_child_coordinates_are_mapped_through_group_transform(self):
        tree = _group_tree()
        containers = _text_containers(tree)
        self.assertEqual(len(containers), 1)
        absolute = _resolve_absolute_emu(tree)
        rect = absolute[id(containers[0])]

        # 1in = 96px; group scale is 2x horizontally. The child starts at
        # 0.5in in child space -> 96px group offset + 0.5in * 2 = 192px.
        self.assertAlmostEqual(rect["x"] / 914400 * 96, 192, places=4)
        self.assertAlmostEqual(rect["y"] / 914400 * 96, 96, places=4)
        self.assertAlmostEqual(rect["width"] / 914400 * 96, 192, places=4)
        self.assertAlmostEqual(rect["height"] / 914400 * 96, 96, places=4)
        self.assertEqual(rect["group_depth"], 1)
        self.assertEqual(rect["group_path"], ["7"])

    def test_raw_child_coordinates_would_have_been_wrong(self):
        """Guard against silently reverting to the old raw-xfrm behaviour."""
        tree = _group_tree()
        sp = tree.find(".//p:sp", NS)
        raw_off = sp.find("p:spPr/a:xfrm/a:off", NS)
        self.assertEqual(int(raw_off.attrib["x"]), 457200)
        absolute = _resolve_absolute_emu(tree)
        self.assertNotAlmostEqual(absolute[id(sp)]["x"], 457200)


class BaselineTemplateGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DECKS / "厦门大学_主题_厦大蓝" / "source.pptx"
        if not cls.source.exists():
            raise unittest.SkipTest("baseline deck source.pptx is not present")
        cls.library = analyze_pptx(cls.source)

    def test_every_slot_has_a_usable_rectangle(self):
        slots = [s for slide in self.library["slides"] for s in slide["slots"]]
        self.assertEqual(len(slots), 115)
        missing = [
            (s["slot_id"], s["geometry"])
            for s in slots
            if not s["geometry"].get("width") or not s["geometry"].get("height")
        ]
        self.assertEqual(missing, [])

    def test_title_placeholder_inherits_from_slide_layout(self):
        slide = next(s for s in self.library["slides"] if s["slide_index"] == 11)
        slot = next(s for s in slide["slots"] if s["slot_id"] == "s11_sh2")
        geometry = slot["geometry"]
        self.assertEqual(geometry["source"], "placeholder_inherited")
        self.assertEqual(geometry["inherited_from"], "slideLayout")
        self.assertEqual(
            (geometry["x"], geometry["y"], geometry["width"], geometry["height"]),
            (64, 64, 1152, 74),
        )


class MultiDeckGeometryTests(unittest.TestCase):
    def test_group_text_slots_stay_inside_slide_bounds(self):
        """Real decks: group children with text must not land off-canvas."""
        checked = 0
        for deck in sorted(DECKS.iterdir()):
            source = deck / "source.pptx"
            if not source.exists():
                continue
            library = analyze_pptx(source)
            for slide in library["slides"]:
                for slot in slide["slots"]:
                    geometry = slot["geometry"]
                    if not geometry.get("group_depth") or not slot.get("text"):
                        continue
                    x, y = geometry["x"], geometry["y"]
                    self.assertIsNotNone(x)
                    self.assertIsNotNone(y)
                    self.assertGreaterEqual(x, -200, f"{deck.name} P{slide['slide_index']} {slot['slot_id']}")
                    self.assertLessEqual(x, 1480, f"{deck.name} P{slide['slide_index']} {slot['slot_id']}")
                    self.assertGreaterEqual(y, -200, f"{deck.name} P{slide['slide_index']} {slot['slot_id']}")
                    self.assertLessEqual(y, 920, f"{deck.name} P{slide['slide_index']} {slot['slot_id']}")
                    checked += 1
        self.assertGreater(checked, 200)


if __name__ == "__main__":
    unittest.main()
