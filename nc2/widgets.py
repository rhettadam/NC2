"""
Custom tkinter widgets and dialog windows for the NC2 control panel.
"""

import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

from .constants import PLAYBACK_MIN_INTERVAL_MS, PLAYBACK_MAX_INTERVAL_MS
from .playback import PlaybackMode


# ===========================================================================
# DimensionSlider -- slider + entry + dropdown for dimension navigation
# ===========================================================================

class DimensionSlider(tb.Frame):
    """
    Dimension navigator with three input methods:
      - Slider for quick scrubbing
      - Entry field to type an index or coordinate value directly
      - Dropdown combobox showing coordinate values (scrollable)
    """

    def __init__(self, parent, label, num_values, coord_values=None,
                 on_change=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.num_values = num_values
        self.coord_values = coord_values
        self.on_change = on_change
        self._updating = False

        row = tb.Frame(self)
        row.pack(fill="x", padx=4, pady=2)

        # Label
        self._header = tb.Label(row, text=label, font=("", 9, "bold"), width=6)
        self._header.pack(side="left")

        # Slider
        self._var = tk.IntVar(value=0)
        self._slider = tb.Scale(
            row, from_=0, to=max(0, num_values - 1),
            orient="horizontal", variable=self._var,
            command=self._on_slide,
        )
        self._slider.pack(side="left", fill="x", expand=True, padx=4)

        # Index entry (type a number to jump)
        self._entry_var = tk.StringVar(value="0")
        self._entry = tb.Entry(row, textvariable=self._entry_var, width=5,
                               font=("Consolas", 8), justify="center")
        self._entry.pack(side="left", padx=(2, 4))
        self._entry.bind("<Return>", self._on_entry_submit)
        self._entry.bind("<FocusOut>", self._on_entry_submit)

        # Coordinate dropdown (shows values, scrollable via combobox)
        dropdown_values = self._make_dropdown_values()
        self._combo = tb.Combobox(row, values=dropdown_values, state="readonly",
                                  width=18, font=("Consolas", 8))
        if dropdown_values:
            self._combo.current(0)
        self._combo.pack(side="left", padx=(0, 2))
        self._combo.bind("<<ComboboxSelected>>", self._on_combo_select)

    @property
    def index(self):
        return self._var.get()

    @index.setter
    def index(self, val):
        self._updating = True
        val = max(0, min(val, self.num_values - 1))
        self._var.set(val)
        self._entry_var.set(str(val))
        self._sync_combo(val)
        self._updating = False

    def set_range(self, num_values, coord_values=None):
        self.num_values = num_values
        self.coord_values = coord_values
        self._slider.config(to=max(0, num_values - 1))
        self._var.set(0)
        self._entry_var.set("0")
        dropdown_values = self._make_dropdown_values()
        self._combo.config(values=dropdown_values)
        if dropdown_values:
            self._combo.current(0)
        else:
            self._combo.set("")

    def _on_slide(self, value):
        idx = int(float(value))
        if self._updating:
            return
        self._updating = True
        self._var.set(idx)
        self._entry_var.set(str(idx))
        self._sync_combo(idx)
        self._updating = False
        if self.on_change:
            self.on_change(idx)

    def _on_entry_submit(self, event=None):
        """Handle typed index or coordinate value."""
        if self._updating:
            return
        text = self._entry_var.get().strip()
        idx = self._parse_input(text)
        if idx is not None:
            self._updating = True
            idx = max(0, min(idx, self.num_values - 1))
            self._var.set(idx)
            self._entry_var.set(str(idx))
            self._sync_combo(idx)
            self._updating = False
            if self.on_change:
                self.on_change(idx)

    def _on_combo_select(self, event=None):
        """Handle dropdown selection."""
        if self._updating:
            return
        sel = self._combo.current()
        if sel < 0:
            return
        self._updating = True
        self._var.set(sel)
        self._entry_var.set(str(sel))
        self._updating = False
        if self.on_change:
            self.on_change(sel)

    def _parse_input(self, text):
        """
        Parse typed input -- accepts either an integer index or a
        coordinate value (finds nearest match).
        """
        # Try as integer index first
        try:
            idx = int(text)
            if 0 <= idx < self.num_values:
                return idx
        except ValueError:
            pass

        # Try as float coordinate value (find nearest)
        if self.coord_values is not None:
            try:
                import numpy as np
                target = float(text)
                coords = np.array([float(v) for v in self.coord_values])
                return int(np.argmin(np.abs(coords - target)))
            except (ValueError, TypeError):
                pass

        return None

    def _sync_combo(self, idx):
        """Sync the combobox selection to the current index."""
        values = self._combo.cget("values")
        if values and 0 <= idx < len(values):
            self._combo.current(idx)

    def _make_dropdown_values(self):
        """Build the list of strings shown in the dropdown."""
        if self.coord_values is None:
            if self.num_values <= 1:
                return []
            return [str(i) for i in range(self.num_values)]
        return [f"{i}: {v}" for i, v in enumerate(self.coord_values)]


# ===========================================================================
# PlaybackBar -- transport controls
# ===========================================================================

class PlaybackBar(tb.Frame):
    """Compact playback transport bar."""

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller

        btn_opts = {"width": 3, "bootstyle": "secondary"}

        self._btn_stop = tb.Button(self, text="||<", command=controller.stop, **btn_opts)
        self._btn_stop.pack(side="left", padx=1)

        self._btn_rev = tb.Button(self, text="<", command=controller.step_backward, **btn_opts)
        self._btn_rev.pack(side="left", padx=1)

        self._btn_play_rev = tb.Button(self, text="<<", command=controller.play_reverse, **btn_opts)
        self._btn_play_rev.pack(side="left", padx=1)

        self._btn_play = tb.Button(self, text=">", command=self._toggle_play, width=4, bootstyle="success")
        self._btn_play.pack(side="left", padx=1)

        self._btn_play_fwd = tb.Button(self, text=">>", command=controller.play, **btn_opts)
        self._btn_play_fwd.pack(side="left", padx=1)

        self._btn_fwd = tb.Button(self, text=">|", command=controller.step_forward, **btn_opts)
        self._btn_fwd.pack(side="left", padx=1)

        # Speed controls
        tb.Button(self, text="-", command=self._speed_down, width=2,
                  bootstyle="outline-secondary").pack(side="left", padx=(8, 1))
        self._speed_label = tb.Label(self, text=controller.speed_label, font=("Consolas", 8), width=8)
        self._speed_label.pack(side="left", padx=2)
        tb.Button(self, text="+", command=self._speed_up, width=2,
                  bootstyle="outline-secondary").pack(side="left", padx=1)

        # Loop mode
        self._mode_var = tk.StringVar(value=PlaybackMode.LOOP)
        mode_btn = tb.Menubutton(self, text="Loop", bootstyle="outline-info", width=6)
        mode_btn.pack(side="left", padx=(8, 0))
        menu = tk.Menu(mode_btn, tearoff=0)
        for val, label in [(PlaybackMode.LOOP, "Loop"),
                           (PlaybackMode.BOUNCE, "Bounce"),
                           (PlaybackMode.ONCE, "Once")]:
            menu.add_radiobutton(label=label, variable=self._mode_var, value=val,
                                 command=lambda m=val: controller.set_mode(m))
        mode_btn["menu"] = menu

    def _toggle_play(self):
        if self.controller.playing:
            self.controller.pause()
            self._btn_play.config(text=">", bootstyle="success")
        else:
            self.controller.play()
            self._btn_play.config(text="||", bootstyle="warning")

    def _speed_up(self):
        self.controller.speed_up()
        self._speed_label.config(text=self.controller.speed_label)

    def _speed_down(self):
        self.controller.speed_down()
        self._speed_label.config(text=self.controller.speed_label)


# ===========================================================================
# StatsDisplay -- compact one-row stats
# ===========================================================================

class StatsDisplay(tb.Frame):
    """Single-row statistics display."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._labels = {}
        for key in ["mean", "std", "min", "max"]:
            tb.Label(self, text=f"{key}:", font=("", 8)).pack(side="left", padx=(6, 0))
            lbl = tb.Label(self, text="--", font=("Consolas", 8), width=10, anchor="w")
            lbl.pack(side="left")
            self._labels[key] = lbl

    def update_stats(self, stats_dict):
        for key, label in self._labels.items():
            val = stats_dict.get(key, "--")
            if isinstance(val, float):
                if abs(val) < 0.01 or abs(val) > 99999:
                    text = f"{val:.3e}"
                else:
                    text = f"{val:.3f}"
            else:
                text = str(val)
            label.config(text=text)

    def clear(self):
        for label in self._labels.values():
            label.config(text="--")


# ===========================================================================
# Dialog: Color Limits
# ===========================================================================

class ColorLimitsDialog:
    """Dialog for setting vmin, vmax, and symmetric colorbar."""

    def __init__(self, parent, config_state, callback=None):
        self.callback = callback
        self._state = config_state

        self.dialog = tb.Toplevel(parent)
        self.dialog.title("Color Limits")
        self.dialog.minsize(280, 180)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        pad = {"padx": 12, "pady": 4}

        tb.Label(self.dialog, text="Vmin (blank=auto):").pack(anchor="w", **pad)
        self._vmin_var = tk.StringVar(value=str(config_state.get("vmin") or ""))
        tb.Entry(self.dialog, textvariable=self._vmin_var, width=16).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="Vmax (blank=auto):").pack(anchor="w", **pad)
        self._vmax_var = tk.StringVar(value=str(config_state.get("vmax") or ""))
        tb.Entry(self.dialog, textvariable=self._vmax_var, width=16).pack(anchor="w", padx=12)

        self._sym_var = tk.BooleanVar(value=config_state.get("symmetric", False))
        tb.Checkbutton(self.dialog, text="Symmetric (center at 0)",
                       variable=self._sym_var).pack(anchor="w", padx=12, pady=6)

        btn_row = tb.Frame(self.dialog)
        btn_row.pack(fill="x", padx=12, pady=8)
        tb.Button(btn_row, text="Apply", command=self._apply,
                  bootstyle="success").pack(side="left", padx=4)
        tb.Button(btn_row, text="Cancel", command=self.dialog.destroy,
                  bootstyle="secondary").pack(side="left", padx=4)

    def _apply(self):
        def float_or_none(s):
            s = s.strip()
            if not s:
                return None
            try:
                return float(s)
            except ValueError:
                return None

        updates = {
            "vmin": float_or_none(self._vmin_var.get()),
            "vmax": float_or_none(self._vmax_var.get()),
            "symmetric": self._sym_var.get(),
        }
        self.dialog.destroy()
        if self.callback:
            self.callback(updates)


# ===========================================================================
# Dialog: Map Features
# ===========================================================================

class MapFeaturesDialog:
    """Dialog for toggling map features (coastlines, land, ocean, etc.)."""

    def __init__(self, parent, config_state, callback=None):
        self.callback = callback

        self.dialog = tb.Toplevel(parent)
        self.dialog.title("Map Features")
        self.dialog.minsize(260, 280)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        features = [
            ("coastlines", "Coastlines"),
            ("gridlines", "Gridlines"),
            ("land", "Land"),
            ("ocean", "Ocean"),
            ("borders", "Country Borders"),
            ("rivers", "Rivers"),
        ]

        self._vars = {}
        for key, label in features:
            var = tk.BooleanVar(value=config_state.get(key, False))
            tb.Checkbutton(self.dialog, text=label, variable=var,
                           bootstyle="round-toggle").pack(anchor="w", padx=12, pady=3)
            self._vars[key] = var

        # Gridline alpha
        tb.Label(self.dialog, text="Gridline alpha:").pack(anchor="w", padx=12, pady=(8, 0))
        self._alpha_var = tk.StringVar(value=str(config_state.get("gridline_alpha", 0.3)))
        tb.Entry(self.dialog, textvariable=self._alpha_var, width=8).pack(anchor="w", padx=12)

        btn_row = tb.Frame(self.dialog)
        btn_row.pack(fill="x", padx=12, pady=10)
        tb.Button(btn_row, text="Apply", command=self._apply,
                  bootstyle="success").pack(side="left", padx=4)
        tb.Button(btn_row, text="Cancel", command=self.dialog.destroy,
                  bootstyle="secondary").pack(side="left", padx=4)

    def _apply(self):
        updates = {key: var.get() for key, var in self._vars.items()}
        try:
            updates["gridline_alpha"] = float(self._alpha_var.get())
        except ValueError:
            updates["gridline_alpha"] = 0.3
        self.dialog.destroy()
        if self.callback:
            self.callback(updates)


# ===========================================================================
# Dialog: Labels & Title
# ===========================================================================

class LabelsDialog:
    """Dialog for setting plot title, axis labels, and DPI."""

    def __init__(self, parent, config_state, callback=None):
        self.callback = callback

        self.dialog = tb.Toplevel(parent)
        self.dialog.title("Labels & Title")
        self.dialog.minsize(320, 240)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        pad = {"padx": 12, "pady": 3}

        tb.Label(self.dialog, text="Title (blank=auto):").pack(anchor="w", **pad)
        self._title_var = tk.StringVar(value=config_state.get("title", ""))
        tb.Entry(self.dialog, textvariable=self._title_var, width=30).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="X Label:").pack(anchor="w", **pad)
        self._xlabel_var = tk.StringVar(value=config_state.get("xlabel", ""))
        tb.Entry(self.dialog, textvariable=self._xlabel_var, width=30).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="Y Label:").pack(anchor="w", **pad)
        self._ylabel_var = tk.StringVar(value=config_state.get("ylabel", ""))
        tb.Entry(self.dialog, textvariable=self._ylabel_var, width=30).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="DPI:").pack(anchor="w", **pad)
        self._dpi_var = tk.StringVar(value=str(config_state.get("dpi", 150)))
        tb.Entry(self.dialog, textvariable=self._dpi_var, width=8).pack(anchor="w", padx=12)

        btn_row = tb.Frame(self.dialog)
        btn_row.pack(fill="x", padx=12, pady=10)
        tb.Button(btn_row, text="Apply", command=self._apply,
                  bootstyle="success").pack(side="left", padx=4)
        tb.Button(btn_row, text="Cancel", command=self.dialog.destroy,
                  bootstyle="secondary").pack(side="left", padx=4)

    def _apply(self):
        updates = {
            "title": self._title_var.get().strip(),
            "xlabel": self._xlabel_var.get().strip(),
            "ylabel": self._ylabel_var.get().strip(),
        }
        try:
            updates["dpi"] = int(self._dpi_var.get())
        except ValueError:
            updates["dpi"] = 150
        self.dialog.destroy()
        if self.callback:
            self.callback(updates)


# ===========================================================================
# Dialog: Section Position
# ===========================================================================

class SectionDialog:
    """Dialog to pick section type and position before creating a section plot."""

    def __init__(self, parent, dataset, callback=None):
        self.callback = callback
        self.dataset = dataset

        self.dialog = tb.Toplevel(parent)
        self.dialog.title("Section Position")
        self.dialog.minsize(340, 200)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Section type
        type_row = tb.Frame(self.dialog)
        type_row.pack(fill="x", padx=12, pady=8)
        self._type_var = tk.StringVar(value="lon")
        tb.Radiobutton(type_row, text="Along Lon (fix Lat)", value="lon",
                       variable=self._type_var,
                       command=self._update_slider).pack(side="left", padx=4)
        tb.Radiobutton(type_row, text="Along Lat (fix Lon)", value="lat",
                       variable=self._type_var,
                       command=self._update_slider).pack(side="left", padx=4)

        # Position slider
        self._pos_var = tk.IntVar(value=0)
        slider_row = tb.Frame(self.dialog)
        slider_row.pack(fill="x", padx=12, pady=4)
        tb.Label(slider_row, text="Position:").pack(side="left")
        self._slider = tb.Scale(slider_row, from_=0, to=1, orient="horizontal",
                                variable=self._pos_var, command=self._on_slide)
        self._slider.pack(side="left", fill="x", expand=True, padx=8)
        self._pos_label = tb.Label(slider_row, text="[0]", font=("Consolas", 8), width=12)
        self._pos_label.pack(side="left")

        self._update_slider()

        # Buttons
        btn_row = tb.Frame(self.dialog)
        btn_row.pack(fill="x", padx=12, pady=12)
        tb.Button(btn_row, text="OK", command=self._ok,
                  bootstyle="success").pack(side="left", padx=4)
        tb.Button(btn_row, text="Cancel", command=self.dialog.destroy,
                  bootstyle="secondary").pack(side="left", padx=4)

    def _update_slider(self):
        """Update slider range based on section type."""
        section_type = self._type_var.get()
        if section_type == "lon":
            coord = self.dataset.lat
        else:
            coord = self.dataset.lon

        if coord is not None:
            n = len(coord)
            self._slider.config(to=max(0, n - 1))
            self._coord = coord
        else:
            self._slider.config(to=0)
            self._coord = None
        self._pos_var.set(0)
        self._on_slide(0)

    def _on_slide(self, value):
        idx = int(float(value))
        self._pos_var.set(idx)
        if self._coord is not None and idx < len(self._coord):
            self._pos_label.config(text=f"[{idx}] {self._coord[idx]:.2f}")
        else:
            self._pos_label.config(text=f"[{idx}]")

    def _ok(self):
        section_type = self._type_var.get()
        position_idx = self._pos_var.get()
        self.dialog.destroy()
        if self.callback:
            self.callback(section_type, position_idx)


# ===========================================================================
# Dialog: Colorbar Options
# ===========================================================================

class ColorbarDialog:
    """Dialog for colorbar orientation, shrink, label, and extend."""

    def __init__(self, parent, config_state, callback=None):
        self.callback = callback

        self.dialog = tb.Toplevel(parent)
        self.dialog.title("Colorbar Options")
        self.dialog.minsize(320, 280)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        pad = {"padx": 12, "pady": 3}

        # Orientation
        tb.Label(self.dialog, text="Orientation:").pack(anchor="w", **pad)
        self._orient_var = tk.StringVar(value=config_state.get("colorbar_orientation", "vertical"))
        orient_row = tb.Frame(self.dialog)
        orient_row.pack(anchor="w", padx=12)
        tb.Radiobutton(orient_row, text="Vertical", value="vertical",
                       variable=self._orient_var).pack(side="left", padx=4)
        tb.Radiobutton(orient_row, text="Horizontal", value="horizontal",
                       variable=self._orient_var).pack(side="left", padx=4)

        # Shrink
        tb.Label(self.dialog, text="Shrink (0.3-1.0):").pack(anchor="w", **pad)
        self._shrink_var = tk.StringVar(value=str(config_state.get("colorbar_shrink", 0.8)))
        tb.Entry(self.dialog, textvariable=self._shrink_var, width=8).pack(anchor="w", padx=12)

        # Label
        tb.Label(self.dialog, text="Label (blank=units):").pack(anchor="w", **pad)
        self._label_var = tk.StringVar(value=config_state.get("colorbar_label", ""))
        tb.Entry(self.dialog, textvariable=self._label_var, width=24).pack(anchor="w", padx=12)

        # Extend
        from .constants import COLORBAR_EXTENDS
        tb.Label(self.dialog, text="Extend:").pack(anchor="w", **pad)
        self._extend_var = tk.StringVar(value=config_state.get("colorbar_extend", "neither"))
        tb.Combobox(self.dialog, values=COLORBAR_EXTENDS, textvariable=self._extend_var,
                    state="readonly", width=10).pack(anchor="w", padx=12)

        btn_row = tb.Frame(self.dialog)
        btn_row.pack(fill="x", padx=12, pady=10)
        tb.Button(btn_row, text="Apply", command=self._apply,
                  bootstyle="success").pack(side="left", padx=4)
        tb.Button(btn_row, text="Cancel", command=self.dialog.destroy,
                  bootstyle="secondary").pack(side="left", padx=4)

    def _apply(self):
        try:
            shrink = float(self._shrink_var.get())
            shrink = max(0.3, min(1.0, shrink))
        except ValueError:
            shrink = 0.8
        updates = {
            "colorbar_orientation": self._orient_var.get(),
            "colorbar_shrink": shrink,
            "colorbar_label": self._label_var.get().strip(),
            "colorbar_extend": self._extend_var.get(),
        }
        self.dialog.destroy()
        if self.callback:
            self.callback(updates)


# ===========================================================================
# Dialog: Contour Options
# ===========================================================================

class ContourDialog:
    """Dialog for contour levels, linewidths, and linestyles."""

    def __init__(self, parent, config_state, callback=None):
        self.callback = callback

        self.dialog = tb.Toplevel(parent)
        self.dialog.title("Contour Options")
        self.dialog.minsize(300, 220)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        pad = {"padx": 12, "pady": 3}

        tb.Label(self.dialog, text="Number of levels:").pack(anchor="w", **pad)
        self._levels_var = tk.StringVar(value=str(config_state.get("contour_levels", 20)))
        tb.Entry(self.dialog, textvariable=self._levels_var, width=8).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="Linewidth:").pack(anchor="w", **pad)
        self._lw_var = tk.StringVar(value=str(config_state.get("contour_linewidths", 1.0)))
        tb.Entry(self.dialog, textvariable=self._lw_var, width=8).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="Linestyle:").pack(anchor="w", **pad)
        self._ls_var = tk.StringVar(value=config_state.get("contour_linestyles", "solid"))
        tb.Combobox(self.dialog, values=["solid", "dashed", "dotted", "dashdot"],
                    textvariable=self._ls_var, state="readonly", width=10).pack(anchor="w", padx=12)

        btn_row = tb.Frame(self.dialog)
        btn_row.pack(fill="x", padx=12, pady=10)
        tb.Button(btn_row, text="Apply", command=self._apply,
                  bootstyle="success").pack(side="left", padx=4)
        tb.Button(btn_row, text="Cancel", command=self.dialog.destroy,
                  bootstyle="secondary").pack(side="left", padx=4)

    def _apply(self):
        try:
            levels = int(self._levels_var.get())
        except ValueError:
            levels = 20
        try:
            lw = float(self._lw_var.get())
        except ValueError:
            lw = 1.0
        updates = {
            "contour_levels": levels,
            "contour_linewidths": lw,
            "contour_linestyles": self._ls_var.get(),
        }
        self.dialog.destroy()
        if self.callback:
            self.callback(updates)


# ===========================================================================
# Dialog: Quiver Options
# ===========================================================================

class QuiverDialog:
    """Dialog for quiver plot parameters."""

    def __init__(self, parent, config_state, callback=None):
        self.callback = callback

        self.dialog = tb.Toplevel(parent)
        self.dialog.title("Quiver Options")
        self.dialog.minsize(300, 300)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        pad = {"padx": 12, "pady": 3}

        tb.Label(self.dialog, text="Scale:").pack(anchor="w", **pad)
        self._scale_var = tk.StringVar(value=str(config_state.get("quiver_scale", 1.0)))
        tb.Entry(self.dialog, textvariable=self._scale_var, width=8).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="Step (subsample):").pack(anchor="w", **pad)
        self._step_var = tk.StringVar(value=str(config_state.get("quiver_step", 3)))
        tb.Entry(self.dialog, textvariable=self._step_var, width=8).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="Pivot:").pack(anchor="w", **pad)
        self._pivot_var = tk.StringVar(value=config_state.get("quiver_pivot", "middle"))
        tb.Combobox(self.dialog, values=["tail", "middle", "tip"],
                    textvariable=self._pivot_var, state="readonly", width=10).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="Head width:").pack(anchor="w", **pad)
        self._hw_var = tk.StringVar(value=str(config_state.get("quiver_headwidth", 3.0)))
        tb.Entry(self.dialog, textvariable=self._hw_var, width=8).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="Head length:").pack(anchor="w", **pad)
        self._hl_var = tk.StringVar(value=str(config_state.get("quiver_headlength", 5.0)))
        tb.Entry(self.dialog, textvariable=self._hl_var, width=8).pack(anchor="w", padx=12)

        btn_row = tb.Frame(self.dialog)
        btn_row.pack(fill="x", padx=12, pady=10)
        tb.Button(btn_row, text="Apply", command=self._apply,
                  bootstyle="success").pack(side="left", padx=4)
        tb.Button(btn_row, text="Cancel", command=self.dialog.destroy,
                  bootstyle="secondary").pack(side="left", padx=4)

    def _apply(self):
        def safe_float(s, default):
            try:
                return float(s)
            except ValueError:
                return default

        def safe_int(s, default):
            try:
                return int(s)
            except ValueError:
                return default

        updates = {
            "quiver_scale": safe_float(self._scale_var.get(), 1.0),
            "quiver_step": safe_int(self._step_var.get(), 3),
            "quiver_pivot": self._pivot_var.get(),
            "quiver_headwidth": safe_float(self._hw_var.get(), 3.0),
            "quiver_headlength": safe_float(self._hl_var.get(), 5.0),
        }
        self.dialog.destroy()
        if self.callback:
            self.callback(updates)


# ===========================================================================
# Dialog: Streamplot Options
# ===========================================================================

class StreamplotDialog:
    """Dialog for streamplot parameters."""

    def __init__(self, parent, config_state, callback=None):
        self.callback = callback

        self.dialog = tb.Toplevel(parent)
        self.dialog.title("Streamplot Options")
        self.dialog.minsize(300, 220)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        pad = {"padx": 12, "pady": 3}

        tb.Label(self.dialog, text="Density:").pack(anchor="w", **pad)
        self._density_var = tk.StringVar(value=str(config_state.get("streamplot_density", 1.0)))
        tb.Entry(self.dialog, textvariable=self._density_var, width=8).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="Linewidth:").pack(anchor="w", **pad)
        self._lw_var = tk.StringVar(value=str(config_state.get("streamplot_linewidth", 1.0)))
        tb.Entry(self.dialog, textvariable=self._lw_var, width=8).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="Arrow size:").pack(anchor="w", **pad)
        self._arrow_var = tk.StringVar(value=str(config_state.get("streamplot_arrowsize", 1.0)))
        tb.Entry(self.dialog, textvariable=self._arrow_var, width=8).pack(anchor="w", padx=12)

        btn_row = tb.Frame(self.dialog)
        btn_row.pack(fill="x", padx=12, pady=10)
        tb.Button(btn_row, text="Apply", command=self._apply,
                  bootstyle="success").pack(side="left", padx=4)
        tb.Button(btn_row, text="Cancel", command=self.dialog.destroy,
                  bootstyle="secondary").pack(side="left", padx=4)

    def _apply(self):
        def safe_float(s, default):
            try:
                return float(s)
            except ValueError:
                return default

        updates = {
            "streamplot_density": safe_float(self._density_var.get(), 1.0),
            "streamplot_linewidth": safe_float(self._lw_var.get(), 1.0),
            "streamplot_arrowsize": safe_float(self._arrow_var.get(), 1.0),
        }
        self.dialog.destroy()
        if self.callback:
            self.callback(updates)


# ===========================================================================
# Dialog: Alpha / Transparency
# ===========================================================================

class AlphaDialog:
    """Dialog for plot alpha (transparency)."""

    def __init__(self, parent, config_state, callback=None):
        self.callback = callback

        self.dialog = tb.Toplevel(parent)
        self.dialog.title("Alpha / Transparency")
        self.dialog.minsize(300, 140)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        tb.Label(self.dialog, text="Alpha (0.0 transparent - 1.0 opaque):").pack(
            anchor="w", padx=12, pady=8)
        self._alpha_var = tk.StringVar(value=str(config_state.get("alpha", 1.0)))
        tb.Entry(self.dialog, textvariable=self._alpha_var, width=8).pack(anchor="w", padx=12)

        btn_row = tb.Frame(self.dialog)
        btn_row.pack(fill="x", padx=12, pady=10)
        tb.Button(btn_row, text="Apply", command=self._apply,
                  bootstyle="success").pack(side="left", padx=4)
        tb.Button(btn_row, text="Cancel", command=self.dialog.destroy,
                  bootstyle="secondary").pack(side="left", padx=4)

    def _apply(self):
        try:
            alpha = float(self._alpha_var.get())
            alpha = max(0.0, min(1.0, alpha))
        except ValueError:
            alpha = 1.0
        self.dialog.destroy()
        if self.callback:
            self.callback({"alpha": alpha})


# ===========================================================================
# Dialog: Normalization Settings
# ===========================================================================

class NormDialog:
    """Dialog for norm-specific parameters (linthresh, gamma, etc.)."""

    def __init__(self, parent, config_state, callback=None):
        self.callback = callback

        self.dialog = tb.Toplevel(parent)
        self.dialog.title("Normalization Settings")
        self.dialog.minsize(300, 260)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        pad = {"padx": 12, "pady": 3}

        tb.Label(self.dialog, text="SymLog linthresh (linear region):").pack(anchor="w", **pad)
        self._linthresh_var = tk.StringVar(value=str(config_state.get("norm_linthresh", 1.0)))
        tb.Entry(self.dialog, textvariable=self._linthresh_var, width=8).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="PowerNorm gamma:").pack(anchor="w", **pad)
        self._gamma_var = tk.StringVar(value=str(config_state.get("norm_gamma", 1.0)))
        tb.Entry(self.dialog, textvariable=self._gamma_var, width=8).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="Norm vmin (blank=auto):").pack(anchor="w", **pad)
        self._vmin_var = tk.StringVar(value=str(config_state.get("norm_vmin") or ""))
        tb.Entry(self.dialog, textvariable=self._vmin_var, width=10).pack(anchor="w", padx=12)

        tb.Label(self.dialog, text="Norm vmax (blank=auto):").pack(anchor="w", **pad)
        self._vmax_var = tk.StringVar(value=str(config_state.get("norm_vmax") or ""))
        tb.Entry(self.dialog, textvariable=self._vmax_var, width=10).pack(anchor="w", padx=12)

        btn_row = tb.Frame(self.dialog)
        btn_row.pack(fill="x", padx=12, pady=10)
        tb.Button(btn_row, text="Apply", command=self._apply,
                  bootstyle="success").pack(side="left", padx=4)
        tb.Button(btn_row, text="Cancel", command=self.dialog.destroy,
                  bootstyle="secondary").pack(side="left", padx=4)

    def _apply(self):
        def float_or_none(s):
            s = s.strip()
            if not s:
                return None
            try:
                return float(s)
            except ValueError:
                return None

        def safe_float(s, default):
            try:
                return float(s)
            except ValueError:
                return default

        updates = {
            "norm_linthresh": safe_float(self._linthresh_var.get(), 1.0),
            "norm_gamma": safe_float(self._gamma_var.get(), 1.0),
            "norm_vmin": float_or_none(self._vmin_var.get()),
            "norm_vmax": float_or_none(self._vmax_var.get()),
        }
        self.dialog.destroy()
        if self.callback:
            self.callback(updates)


# ===========================================================================
# Dialog: Dimension Assignment
# ===========================================================================

class DimensionAssignDialog:
    """
    Dialog to view and override the automatically-detected dimension roles.
    Shows all dimensions for the current file with their sizes and assigned
    roles. User can reassign any dimension to any role or mark it unassigned.
    """

    ROLES = ["Time", "Depth/Z", "Latitude", "Longitude", "Unassigned"]
    ROLE_MAP = {
        "Time": "time",
        "Depth/Z": "depth",
        "Latitude": "lat",
        "Longitude": "lon",
        "Unassigned": None,
    }
    REVERSE_MAP = {v: k for k, v in ROLE_MAP.items()}

    def __init__(self, parent, dataset, callback=None):
        self.callback = callback
        self.dataset = dataset

        self.dialog = tb.Toplevel(parent)
        self.dialog.title("Dimension Assignment")
        self.dialog.minsize(440, 320)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Build table header
        header = tb.Frame(self.dialog)
        header.pack(fill="x", padx=12, pady=(10, 2))
        tb.Label(header, text="Dimension", width=14, font=("", 9, "bold")).pack(side="left")
        tb.Label(header, text="Size", width=8, font=("", 9, "bold")).pack(side="left")
        tb.Label(header, text="Role", width=14, font=("", 9, "bold")).pack(side="left")

        # Scrollable frame for dimensions
        canvas_frame = tb.Frame(self.dialog)
        canvas_frame.pack(fill="both", expand=True, padx=12)

        self._role_vars = {}
        all_dims = dataset.get_all_dimensions()

        for dim_name, dim_size in all_dims.items():
            row = tb.Frame(canvas_frame)
            row.pack(fill="x", pady=1)

            tb.Label(row, text=dim_name, width=14, anchor="w").pack(side="left")
            tb.Label(row, text=str(dim_size), width=8, anchor="w").pack(side="left")

            current_role = dataset.get_dim_role(dim_name)
            display_role = self.REVERSE_MAP.get(current_role, "Unassigned")

            var = tk.StringVar(value=display_role)
            combo = tb.Combobox(row, values=self.ROLES, textvariable=var,
                                state="readonly", width=12)
            combo.pack(side="left", padx=4)
            self._role_vars[dim_name] = var

        # Buttons
        btn_row = tb.Frame(self.dialog)
        btn_row.pack(fill="x", padx=12, pady=10)
        tb.Button(btn_row, text="Apply", command=self._apply,
                  bootstyle="success").pack(side="left", padx=4)
        tb.Button(btn_row, text="Cancel", command=self.dialog.destroy,
                  bootstyle="secondary").pack(side="left", padx=4)

    def _apply(self):
        for dim_name, var in self._role_vars.items():
            role = self.ROLE_MAP[var.get()]
            self.dataset.set_dim_role(dim_name, role)
        self.dialog.destroy()
        if self.callback:
            self.callback()
