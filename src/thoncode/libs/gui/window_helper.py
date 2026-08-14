#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Window Helper",
    "Path": ".main.libs.gui.window_helper",
    "Entrance": "main.py"
}

"""Shared helpers to avoid the two most common Toplevel defects:

    1. *Fixed-aspect clipping* – ``geometry("1280x720")`` plus
       ``resizable(False, False)`` clips content on small screens and
       on non-16:9 DPI scalings. We wrap every project dialog so it
       is (a) resizable, (b) uses a min-size instead of a hard size,
       and (c) wraps its body in a scrollable frame so even tiny
       windows reveal every control.

    2. *Broken z-order / modality* – callers often sprinkle
       ``transient`` / ``grab_set`` / ``lift`` / ``focus_force`` in
       random order on random threads. The correct sequence for a
       modal child of ``parent`` is:

           1. Transient(parent)                 – taskbar grouping + stays on top
           2. Lift() above parent                – visual z-order
           3. Focus_force()                      – route input
           4. Grab_set() / grab_release()        – modal input capture

   ``apply_modal_window_order`` centralises this ordering and
   ``ScrollableFrame`` provides a single resizable content area.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from libs.gui import theme


class ScrollableFrame(ttk.Frame):
    """A ttk.Frame whose content scrolls when its natural size exceeds
    the allocated area. Works with both grid and pack callers.

    Usage:
        body = ScrollableFrame(dialog)
        body.pack(fill="both", expand=True)
        ttk.Label(body.interior, ...).pack()
    """

    def __init__(self, master: tk.Misc, **kwargs):
        super().__init__(master, **kwargs)
        colors = theme.get_colors()
        bg = colors.get("bg_panel", colors.get("bg", "#ffffff"))

        self._canvas = tk.Canvas(
            self, highlightthickness=0,
            borderwidth=0, background=bg,
        )
        self._vsb = ttk.Scrollbar(
            self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vsb.set)

        self._canvas.pack(side="left", fill="both", expand=True)
        self._vsb.pack(side="right", fill="y")

        self.interior = ttk.Frame(self._canvas)
        self._interior_id = self._canvas.create_window(
            (0, 0), window=self.interior, anchor="nw")

        self.interior.bind("<Configure>", self._on_interior_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel scrolling on common platforms.
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self._canvas.bind_all("<Button-4>",
                              lambda e: self._canvas.yview_scroll(-1, "units"), add="+")
        self._canvas.bind_all("<Button-5>",
                              lambda e: self._canvas.yview_scroll(1, "units"), add="+")

    # ------------------------------------------------------------------
    def _on_interior_configure(self, _event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # Keep the interior frame width matched so interior widgets
        # that pack(fill="x") span the whole dialog width.
        self._canvas.itemconfigure(self._interior_id, width=event.width)

    def _on_mousewheel(self, event):
        # Only scroll when the cursor is over this scrollable area.
        try:
            w = event.widget.winfo_containing(event.x_root, event.y_root)
        except Exception:
            return
        target = self._canvas
        while w is not None:
            if w is target or w is self.interior:
                delta = -1 if event.delta > 0 else 1
                target.yview_scroll(delta, "units")
                return
            w = getattr(w, "master", None)

    def destroy(self):  # type: ignore[override]
        try:
            self._canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass
        super().destroy()


# ---------------------------------------------------------------------------
# Z-order / modality helpers
# ---------------------------------------------------------------------------


def apply_modal_window_order(
    window: tk.Toplevel,
    parent: Optional[tk.Misc] = None,
    *,
    modal: bool = True,
) -> None:
    """Apply the canonical z-ordering + modality steps.

    Call *after* the window has been fully created and given a size
    (so WM decorations exist already). The ``window`` argument should
    be a Toplevel; for the SettingsWindow subclass of Toplevel this
    is the instance itself.
    """
    if parent is not None:
        try:
            window.transient(parent)
        except Exception:
            pass
    try:
        window.lift()
    except Exception:
        pass
    try:
        window.focus_force()
    except Exception:
        pass
    if modal:
        try:
            window.grab_set()
        except Exception:
            pass


def release_modal_grab(window: tk.Toplevel) -> None:
    """Pair with apply_modal_window_order in cleanup paths."""
    try:
        window.grab_release()
    except Exception:
        pass


def set_window_minimum_size(window: tk.Toplevel, *,
                            min_width: int = 480,
                            min_height: int = 320) -> None:
    """Set a user-friendly minimum size and mark the window resizable.

    We do not force a 16:9 ratio: users with portrait or ultrawide
    displays should still be able to see every control.
    """
    try:
        window.resizable(True, True)
    except Exception:
        pass
    try:
        window.minsize(min_width, min_height)
    except Exception:
        pass
