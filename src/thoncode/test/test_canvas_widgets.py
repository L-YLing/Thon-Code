#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - canvas_widgets",
    "Path": ".main.test.test_canvas_widgets",
    "Entrance": "main.py"
}

"""
Headless structural tests for the Canvas-based themed widget library.

These tests verify import-ability, class hierarchy, interface compliance,
package declarations, and the pure-Python create_rounded_rect helper. They
do not require a running Tk display, so they run in any CI/headless
environment alongside the rest of the backend suite.
"""

import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

logger = get_logger("test_canvas_widgets")


# ---------------------------------------------------------------------------
# Widget classes under test and the shared interfaces they must implement.
# ---------------------------------------------------------------------------
WIDGET_SPECS = [
    # (module_path, class_name, expected_public_methods)
    (
        "libs.gui_libs.widgets.canvas_button",
        "CanvasButton",
        ["create_widget", "pack", "grid", "destroy", "get_widget",
         "set_text", "set_enabled", "set_command", "configure_style",
         "apply_style", "get_style_value", "set_style_value"],
    ),
    (
        "libs.gui_libs.widgets.canvas_label",
        "CanvasLabel",
        ["create_widget", "pack", "grid", "destroy", "get_widget",
         "set_text", "set_icon", "set_alignment",
         "apply_style", "get_style_value", "set_style_value"],
    ),
    (
        "libs.gui_libs.widgets.canvas_frame",
        "CanvasFrame",
        ["create_widget", "pack", "grid", "destroy", "get_widget",
         "get_content",
         "apply_style", "get_style_value", "set_style_value"],
    ),
    (
        "libs.gui_libs.widgets.canvas_entry",
        "CanvasEntry",
        ["create_widget", "pack", "grid", "destroy", "get_widget",
         "get_entry",
         "apply_style", "get_style_value", "set_style_value"],
    ),
    (
        "libs.gui_libs.widgets.canvas_panel",
        "CanvasPanel",
        ["create_widget", "pack", "grid", "destroy", "get_widget",
         "get_content", "toggle", "set_expanded", "is_expanded",
         "set_title", "set_on_toggle",
         "apply_style", "get_style_value", "set_style_value"],
    ),
    (
        "libs.gui_libs.widgets.canvas_scrollbar",
        "CanvasScrollbar",
        ["create_widget", "pack", "grid", "destroy", "get_widget",
         "set", "configure",
         "apply_style", "get_style_value", "set_style_value"],
    ),
    (
        "libs.gui_libs.widgets.canvas_statusbar",
        "CanvasStatusBar",
        ["create_widget", "pack", "grid", "destroy", "get_widget",
         "set_text", "get_text", "clear",
         "apply_style", "get_style_value", "set_style_value"],
    ),
]


class WidgetPackageTests(unittest.TestCase):
    """Verify every widget module carries a valid package declaration."""

    def test_widgets_package_init_declaration(self):
        """Verify the widgets __init__ package declaration is valid."""
        import libs.gui_libs.widgets as pkg
        self.assertTrue(hasattr(pkg, 'package'))
        self.assertEqual(pkg.package['ID'], 'thon-code-gui-libs')
        logger.info("widgets_package_init: package declaration valid")
        print("[PASS] test_widgets_package_init_declaration: package valid")

    def test_all_widget_modules_have_package(self):
        """Verify each widget module exposes a package dict with required keys."""
        import importlib
        modules = [
            "canvas_button", "canvas_label", "canvas_frame",
            "canvas_entry", "canvas_panel", "canvas_scrollbar",
            "canvas_statusbar",
        ]
        for name in modules:
            mod = importlib.import_module(f"libs.gui_libs.widgets.{name}")
            self.assertTrue(hasattr(mod, 'package'),
                            f"{name} missing package declaration")
            pkg = mod.package
            self.assertIn('ID', pkg, f"{name} package missing ID")
            self.assertIn('Name', pkg, f"{name} package missing Name")
            self.assertIn('Path', pkg, f"{name} package missing Path")
        logger.info("all_widget_modules_have_package: %d modules verified",
                    len(modules))
        print(f"[PASS] test_all_widget_modules_have_package: "
              f"{len(modules)} modules verified")

    def test_package_init_exports(self):
        """Verify __all__ lists every public widget class and helper."""
        import libs.gui_libs.widgets as pkg
        expected = [
            "CanvasButton", "CanvasLabel", "CanvasFrame", "CanvasEntry",
            "CanvasPanel", "CanvasScrollbar", "CanvasStatusBar",
            "create_rounded_rect",
        ]
        for name in expected:
            self.assertIn(name, pkg.__all__,
                          f"{name} should be exported by widgets package")
            self.assertTrue(hasattr(pkg, name),
                           f"{name} not importable from widgets package")
        logger.info("package_init_exports: all %d exports present", len(expected))
        print(f"[PASS] test_package_init_exports: {len(expected)} exports present")


class WidgetInterfaceTests(unittest.TestCase):
    """Verify each widget class implements BaseWidget and StyleProvider."""

    def test_all_widgets_implement_base_widget(self):
        """Verify every widget class is a subclass of BaseWidget."""
        from libs.gui_libs.base import BaseWidget
        import importlib
        for module_path, class_name, _ in WIDGET_SPECS:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            self.assertTrue(issubclass(cls, BaseWidget),
                            f"{class_name} should implement BaseWidget")
        logger.info("all_widgets_implement_base_widget: %d widgets verified",
                    len(WIDGET_SPECS))
        print(f"[PASS] test_all_widgets_implement_base_widget: "
              f"{len(WIDGET_SPECS)} widgets verified")

    def test_all_widgets_implement_style_provider(self):
        """Verify every widget class is a subclass of StyleProvider."""
        from libs.gui_libs.base import StyleProvider
        import importlib
        for module_path, class_name, _ in WIDGET_SPECS:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            self.assertTrue(issubclass(cls, StyleProvider),
                            f"{class_name} should implement StyleProvider")
        logger.info("all_widgets_implement_style_provider: %d widgets verified",
                    len(WIDGET_SPECS))
        print(f"[PASS] test_all_widgets_implement_style_provider: "
              f"{len(WIDGET_SPECS)} widgets verified")

    def test_widgets_define_required_abstract_methods(self):
        """Verify each widget class declares the BaseWidget abstract methods."""
        import importlib
        required = ["create_widget", "pack", "grid", "destroy", "get_widget"]
        for module_path, class_name, _ in WIDGET_SPECS:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            for method in required:
                self.assertTrue(hasattr(cls, method),
                                f"{class_name} missing required method {method}")
        logger.info("widgets_define_required_abstract_methods: verified")
        print("[PASS] test_widgets_define_required_abstract_methods: verified")

    def test_widgets_define_style_provider_methods(self):
        """Verify each widget class declares the StyleProvider methods."""
        import importlib
        required = ["apply_style", "get_style_value", "set_style_value"]
        for module_path, class_name, _ in WIDGET_SPECS:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            for method in required:
                self.assertTrue(hasattr(cls, method),
                                f"{class_name} missing style method {method}")
        logger.info("widgets_define_style_provider_methods: verified")
        print("[PASS] test_widgets_define_style_provider_methods: verified")


class WidgetMethodTests(unittest.TestCase):
    """Verify each widget exposes its expected public API surface."""

    def test_widget_public_methods_present(self):
        """Verify every expected public method is present on each class."""
        import importlib
        total = 0
        for module_path, class_name, expected_methods in WIDGET_SPECS:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            for method in expected_methods:
                self.assertTrue(hasattr(cls, method),
                                f"{class_name} should have {method}")
            total += len(expected_methods)
        logger.info("widget_public_methods_present: %d methods across %d widgets",
                    total, len(WIDGET_SPECS))
        print(f"[PASS] test_widget_public_methods_present: "
              f"{total} methods across {len(WIDGET_SPECS)} widgets")


class CanvasButtonStateTests(unittest.TestCase):
    """Verify the CanvasButton state-machine constants are defined."""

    def test_state_constants_exist(self):
        """Verify the four visual state identifiers are class attributes."""
        from libs.gui_libs.widgets.canvas_button import CanvasButton
        self.assertEqual(CanvasButton.STATE_NORMAL, "normal")
        self.assertEqual(CanvasButton.STATE_HOVER, "hover")
        self.assertEqual(CanvasButton.STATE_PRESSED, "pressed")
        self.assertEqual(CanvasButton.STATE_DISABLED, "disabled")
        logger.info("state_constants_exist: four state constants verified")
        print("[PASS] test_state_constants_exist: state constants verified")


class CreateRoundedRectTests(unittest.TestCase):
    """Verify the create_rounded_rect helper enforces geometric invariants.

    The helper is pure-Python but needs a Canvas to draw on, so a lightweight
    FakeCanvas records the create_* calls it receives. This keeps the test
    headless while still exercising the branch logic (radius clamp, fallback
    to a plain rectangle, corner arc count).
    """

    class FakeCanvas:
        """Minimal Canvas double recording primitive creation calls."""

        def __init__(self):
            self.calls = []

        def create_rectangle(self, x1, y1, x2, y2, **kwargs):
            self.calls.append(("rectangle", (x1, y1, x2, y2), kwargs))
            return len(self.calls)

        def create_arc(self, x1, y1, x2, y2, **kwargs):
            self.calls.append(("arc", (x1, y1, x2, y2), kwargs))
            return len(self.calls)

    def test_zero_radius_falls_back_to_rectangle(self):
        """Verify a zero radius produces a single rectangle, no arcs."""
        from libs.gui_libs.widgets.canvas_button import create_rounded_rect
        canvas = self.FakeCanvas()
        items = create_rounded_rect(canvas, 0, 0, 50, 30, radius=0, fill="#fff")
        self.assertEqual(len(items), 1)
        kinds = [c[0] for c in canvas.calls]
        self.assertEqual(kinds, ["rectangle"])
        logger.info("zero_radius_fallback: single rectangle drawn")
        print("[PASS] test_zero_radius_falls_back_to_rectangle: single rectangle")

    def test_radius_larger_than_half_clamped(self):
        """Verify a radius exceeding half the smaller side is clamped safely."""
        from libs.gui_libs.widgets.canvas_button import create_rounded_rect
        canvas = self.FakeCanvas()
        # Width=40, height=20 -> max safe radius is 10. Pass 100 to force clamp.
        create_rounded_rect(canvas, 0, 0, 40, 20, radius=100, fill="#fff")
        # 2 center bands + 4 corner arcs = 6 primitives.
        self.assertEqual(len(canvas.calls), 6)
        arcs = [c for c in canvas.calls if c[0] == "arc"]
        self.assertEqual(len(arcs), 4)
        logger.info("radius_clamped: 6 primitives drawn with clamped radius")
        print("[PASS] test_radius_larger_than_half_clamped: radius clamped")

    def test_normal_radius_draws_six_primitives(self):
        """Verify a normal radius draws 2 bands + 4 corner arcs."""
        from libs.gui_libs.widgets.canvas_button import create_rounded_rect
        canvas = self.FakeCanvas()
        create_rounded_rect(canvas, 0, 0, 100, 60, radius=8, fill="#abc")
        rectangles = [c for c in canvas.calls if c[0] == "rectangle"]
        arcs = [c for c in canvas.calls if c[0] == "arc"]
        self.assertEqual(len(rectangles), 2)
        self.assertEqual(len(arcs), 4)
        logger.info("normal_radius: 2 rectangles + 4 arcs drawn")
        print("[PASS] test_normal_radius_draws_six_primitives: 2 + 4 primitives")

    def test_arc_extents_cover_full_circle(self):
        """Verify the four corner arcs together span 360 degrees."""
        from libs.gui_libs.widgets.canvas_button import create_rounded_rect
        canvas = self.FakeCanvas()
        create_rounded_rect(canvas, 0, 0, 80, 40, radius=6, fill="#fff")
        arcs = [c for c in canvas.calls if c[0] == "arc"]
        extents = [a[2].get("extent", 0) for a in arcs]
        self.assertEqual(len(arcs), 4)
        # Each corner arc is a 90-degree quarter; sum is 360.
        self.assertEqual(sum(extents), 360)
        # Starts should be 0, 90, 180, 270 in some order.
        starts = sorted(a[2].get("start", 0) for a in arcs)
        self.assertEqual(starts, [0, 90, 180, 270])
        logger.info("arc_extents: four arcs span 360 degrees")
        print("[PASS] test_arc_extents_cover_full_circle: 360 degrees total")

    def test_fill_propagated_to_all_primitives(self):
        """Verify the fill color is applied to every drawn primitive."""
        from libs.gui_libs.widgets.canvas_button import create_rounded_rect
        canvas = self.FakeCanvas()
        create_rounded_rect(canvas, 0, 0, 60, 40, radius=5, fill="#ff0000")
        for _, _, kwargs in canvas.calls:
            self.assertEqual(kwargs.get("fill"), "#ff0000")
        logger.info("fill_propagated: fill applied to all primitives")
        print("[PASS] test_fill_propagated_to_all_primitives: fill applied")

    def test_outline_defaults_to_empty(self):
        """Verify outline defaults to an empty string (no border)."""
        from libs.gui_libs.widgets.canvas_button import create_rounded_rect
        canvas = self.FakeCanvas()
        create_rounded_rect(canvas, 0, 0, 60, 40, radius=5, fill="#fff")
        for _, _, kwargs in canvas.calls:
            # All primitives should have outline="" so no border is drawn.
            self.assertEqual(kwargs.get("outline", ""), "")
        logger.info("outline_defaults_empty: no outline by default")
        print("[PASS] test_outline_defaults_to_empty: no outline by default")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Canvas-based themed widget library")
    print("=" * 60)
    unittest.main(verbosity=2)
