"""
Main control panel for NC2. Compact window with a menubar, a visible toolbar
for colormap/plot-type, dimension sliders, playback, and stats. All advanced
options live in organized menus and popup dialogs.
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import numpy as np

from .dataset import Dataset
from .slicer import Slicer
from .playback import PlaybackController
from .plots.manager import PlotManager
from .plots.config import PlotConfig
from .plots.spatial import SpatialPlot
from .plots.section import SectionPlot, TransectPlot
from .plots.series import TimeseriesPlot, DepthProfilePlot
from .widgets import DimensionSlider, PlaybackBar, StatsDisplay
from .export import export_gif, export_frame
from .constants import (
    SUPPORTED_EXTENSIONS, PLOT_TYPES, PROJECTION_NAMES,
    COLORMAPS, DEFAULTS, NORM_TYPES, INTERPOLATIONS,
    COLORBAR_EXTENDS, ASPECT_RATIOS, get_all_colormaps,
)


class NC2App:
    """
    NC2 control panel. Menu-driven with a visible toolbar for the most
    frequently accessed settings (colormap, plot type).
    """

    def __init__(self, root, file_path=None):
        self.root = root
        self.root.title("NC2")
        self.root.minsize(580, 480)
        self.root.geometry("620x520")
        self.root.resizable(True, True)
        self._set_window_icon()

        # Core state
        self.dataset = None
        self.slicer = None
        self.plot_manager = PlotManager()
        self.playback = None

        # Current selections
        self._current_var = None
        self._time_idx = 0
        self._depth_idx = 0
        self._extra_indices = {}  # dim_name -> current index for unassigned dims

        # Plot configuration state (modified by menus and dialogs)
        self._config_state = dict(DEFAULTS)

        # Runtime colormap list
        self._all_cmaps = get_all_colormaps()

        # Build interface
        self._build_menubar()
        self._build_panel()

        # Keyboard shortcuts
        self.root.bind("<Control-o>", lambda e: self._open_file_dialog())
        self.root.bind("<Control-q>", lambda e: self._on_quit())
        self.root.bind("<Control-s>", lambda e: self._save_image())

        if file_path:
            self._load_file(file_path)

        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)

    # ==================================================================
    # Window icon
    # ==================================================================

    def _set_window_icon(self):
        """Set the window icon for the title bar and taskbar."""
        import sys
        icon_dir = os.path.dirname(__file__)
        try:
            if sys.platform == "win32":
                ico_path = os.path.join(icon_dir, "icon.ico")
                if os.path.isfile(ico_path):
                    self.root.iconbitmap(ico_path)
            else:
                png_path = os.path.join(icon_dir, "icon.png")
                if os.path.isfile(png_path):
                    from PIL import Image, ImageTk
                    img = Image.open(png_path)
                    self._icon_photo = ImageTk.PhotoImage(img)
                    self.root.iconphoto(True, self._icon_photo)
        except Exception:
            pass

    # ==================================================================
    # Menubar
    # ==================================================================

    def _build_menubar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # -- File --
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open File...", command=self._open_file_dialog,
                              accelerator="Ctrl+O")
        file_menu.add_command(label="Dimensions...", command=self._show_dim_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Close File", command=self._close_file)
        file_menu.add_command(label="Quit", command=self._on_quit, accelerator="Ctrl+Q")

        # -- Plot --
        plot_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Plot", menu=plot_menu)
        plot_menu.add_command(label="New Spatial Plot", command=self._open_spatial)
        plot_menu.add_command(label="New Vertical Section...", command=self._open_section_dialog)
        plot_menu.add_command(label="New Horizontal Transect...", command=self._open_transect_dialog)
        plot_menu.add_command(label="New Timeseries", command=self._open_timeseries)
        plot_menu.add_command(label="New Depth Profile", command=self._open_depth_profile)
        plot_menu.add_separator()
        plot_menu.add_command(label="Close All Plots", command=self._close_all_plots)

        # -- View --
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)

        # Projection submenu
        self._proj_var = tk.StringVar(value=self._config_state["projection"])
        proj_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Projection", menu=proj_menu)
        for proj in PROJECTION_NAMES:
            proj_menu.add_radiobutton(label=proj, variable=self._proj_var, value=proj,
                                      command=self._on_view_change)

        # Colormap submenu (curated categories for quick access)
        cmap_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Colormap (Quick)", menu=cmap_menu)
        for category, cmaps in COLORMAPS.items():
            cat_menu = tk.Menu(cmap_menu, tearoff=0)
            cmap_menu.add_cascade(label=category, menu=cat_menu)
            for cm in cmaps:
                cat_menu.add_command(label=cm, command=lambda c=cm: self._set_cmap(c))

        view_menu.add_separator()

        # Normalization submenu
        self._norm_var = tk.StringVar(value="linear")
        norm_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Normalization", menu=norm_menu)
        for nt in NORM_TYPES:
            norm_menu.add_radiobutton(label=nt, variable=self._norm_var, value=nt,
                                      command=self._on_view_change)
        norm_menu.add_separator()
        norm_menu.add_command(label="Norm Settings...", command=self._show_norm_dialog)

        # Interpolation submenu (for imshow)
        self._interp_var = tk.StringVar(value="nearest")
        interp_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Interpolation", menu=interp_menu)
        for ip in INTERPOLATIONS:
            interp_menu.add_radiobutton(label=ip, variable=self._interp_var, value=ip,
                                        command=self._on_view_change)

        # Aspect submenu
        self._aspect_var = tk.StringVar(value="auto")
        aspect_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Aspect Ratio", menu=aspect_menu)
        for ar in ASPECT_RATIOS:
            aspect_menu.add_radiobutton(label=ar, variable=self._aspect_var, value=ar,
                                        command=self._on_view_change)

        view_menu.add_separator()

        # Dialogs for more detailed settings
        view_menu.add_command(label="Color Limits...", command=self._show_color_limits_dialog)
        view_menu.add_command(label="Map Features...", command=self._show_map_features_dialog)
        view_menu.add_command(label="Labels & Title...", command=self._show_labels_dialog)
        view_menu.add_command(label="Colorbar Options...", command=self._show_colorbar_dialog)
        view_menu.add_command(label="Contour Options...", command=self._show_contour_dialog)
        view_menu.add_command(label="Quiver Options...", command=self._show_quiver_dialog)
        view_menu.add_command(label="Streamplot Options...", command=self._show_streamplot_dialog)
        view_menu.add_command(label="Alpha/Transparency...", command=self._show_alpha_dialog)

        # -- Export --
        export_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Export", menu=export_menu)
        export_menu.add_command(label="Save Image...", command=self._save_image,
                                accelerator="Ctrl+S")
        export_menu.add_command(label="Export GIF...", command=self._export_gif_dialog)
        export_menu.add_command(label="Batch Export Frames...", command=self._batch_export)

        # -- Help --
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About NC2", command=self._show_about)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)

    # ==================================================================
    # Main panel
    # ==================================================================

    def _build_panel(self):
        f = tb.Frame(self.root, padding=6)
        f.pack(fill="both", expand=True)

        # -- Variable row --
        var_row = tb.Frame(f)
        var_row.pack(fill="x", pady=(0, 2))

        tb.Label(var_row, text="Variable:", font=("", 9, "bold")).pack(side="left")
        self._var_combo = tb.Combobox(var_row, state="readonly", width=20)
        self._var_combo.pack(side="left", padx=(6, 8))
        self._var_combo.bind("<<ComboboxSelected>>", self._on_var_selected)

        self._var_info_label = tb.Label(var_row, text="", font=("", 8))
        self._var_info_label.pack(side="left", fill="x", expand=True)

        # -- Toolbar row (colormap, plot type, reverse) --
        toolbar = tb.Frame(f)
        toolbar.pack(fill="x", pady=(0, 4))

        tb.Label(toolbar, text="Cmap:", font=("", 8)).pack(side="left")
        self._cmap_combo = tb.Combobox(toolbar, values=self._all_cmaps,
                                       state="readonly", width=14)
        self._cmap_combo.set(self._config_state["colormap"])
        self._cmap_combo.pack(side="left", padx=(2, 8))
        self._cmap_combo.bind("<<ComboboxSelected>>", lambda e: self._on_view_change())

        tb.Label(toolbar, text="Plot:", font=("", 8)).pack(side="left")
        self._type_combo = tb.Combobox(toolbar, values=PLOT_TYPES,
                                       state="readonly", width=12)
        self._type_combo.set(self._config_state["plot_type"])
        self._type_combo.pack(side="left", padx=(2, 8))
        self._type_combo.bind("<<ComboboxSelected>>", lambda e: self._on_view_change())

        self._rev_var = tk.BooleanVar(value=False)
        tb.Checkbutton(toolbar, text="Rev", variable=self._rev_var,
                       command=self._on_view_change,
                       bootstyle="round-toggle").pack(side="left", padx=4)

        # -- Dimension sliders --
        self._time_slider = DimensionSlider(f, "Time", 1, on_change=self._on_time_change)
        self._time_slider.pack(fill="x")

        self._depth_slider = DimensionSlider(f, "Depth", 1, on_change=self._on_depth_change)
        self._depth_slider.pack(fill="x")

        # Frame for extra dimension sliders (auto-generated)
        self._extra_sliders_frame = tb.Frame(f)
        self._extra_sliders_frame.pack(fill="x")
        self._extra_sliders = {}  # dim_name -> DimensionSlider

        # -- Playback --
        self._playback_frame = tb.Frame(f)
        self._playback_frame.pack(fill="x", pady=2)
        self._playback_bar = None

        # -- Stats row --
        self._stats_display = StatsDisplay(f)
        self._stats_display.pack(fill="x", pady=(4, 0))

        # -- Separator --
        tb.Separator(f, orient="horizontal").pack(fill="x", pady=6)

        # -- File info panel (bottom, fills remaining space) --
        self._info_frame = tb.Frame(f)
        self._info_frame.pack(fill="both", expand=True)
        self._build_info_panel()

    # ==================================================================
    # Info panel (bottom area)
    # ==================================================================

    def _build_info_panel(self):
        """Build the file info area with logo, metadata, and attributes."""
        from PIL import Image, ImageTk

        f = self._info_frame

        # Top row: file info (left) + logo (right)
        top_row = tb.Frame(f)
        top_row.pack(fill="x", pady=(0, 4))

        # File info text (left side)
        self._file_info_label = tb.Label(
            top_row, text="No file loaded", font=("", 8),
            foreground="gray", anchor="w", justify="left",
        )
        self._file_info_label.pack(side="left", fill="x", expand=True)

        # Logo (right side, proper aspect ratio)
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        try:
            img = Image.open(logo_path)
            # Scale to 48px height, maintaining aspect ratio
            target_h = 48
            aspect = img.width / img.height
            target_w = int(target_h * aspect)
            img = img.resize((target_w, target_h), Image.LANCZOS)
            self._logo_photo = ImageTk.PhotoImage(img)
            logo_label = tb.Label(top_row, image=self._logo_photo)
            logo_label.pack(side="right", padx=(8, 0))
        except Exception:
            self._logo_photo = None

        # Attributes / dimensions display (scrollable text area)
        self._info_text = tk.Text(
            f, height=5, wrap="none", font=("Consolas", 8),
            relief="flat", state="disabled",
            background=self.root.cget("background"),
        )
        self._info_text.pack(fill="both", expand=True, pady=(0, 2))

        # Horizontal scroll for long attribute values
        xscroll = tb.Scrollbar(f, orient="horizontal", command=self._info_text.xview)
        xscroll.pack(fill="x")
        self._info_text.config(xscrollcommand=xscroll.set)

    def _update_info_panel(self):
        """Populate the info panel with current file metadata."""
        if self.dataset is None:
            self._file_info_label.config(text="No file loaded")
            self._info_text.config(state="normal")
            self._info_text.delete("1.0", "end")
            self._info_text.config(state="disabled")
            return

        ds = self.dataset
        dims = ds.get_all_dimensions()
        num_vars = len(ds.all_variable_names)

        # File summary line
        file_line = (
            f"{ds.filename}\n"
            f"{len(dims)} dims | {num_vars} vars | "
            f"Time: {ds.num_times} | Depth: {ds.num_depths}"
        )
        self._file_info_label.config(text=file_line, foreground="")

        # Build detailed text
        lines = []
        lines.append("--- Dimensions ---")
        for dim_name, size in dims.items():
            role = ds.get_dim_role(dim_name)
            role_str = f"  [{role}]" if role else ""
            lines.append(f"  {dim_name:<16} {size:>6}{role_str}")

        lines.append("")
        lines.append("--- Variables ---")
        for v in ds.variables:
            lines.append(f"  {v.name:<20} {str(v.shape):<20} {v.units}")

        attrs = ds.global_attrs
        if attrs:
            lines.append("")
            lines.append("--- Global Attributes ---")
            for key, val in attrs.items():
                val_str = str(val)
                if len(val_str) > 80:
                    val_str = val_str[:77] + "..."
                lines.append(f"  {key}: {val_str}")

        self._info_text.config(state="normal")
        self._info_text.delete("1.0", "end")
        self._info_text.insert("1.0", "\n".join(lines))
        self._info_text.config(state="disabled")

    # ==================================================================
    # Config state
    # ==================================================================

    def _get_config(self):
        """Build PlotConfig from toolbar + menu state."""
        self._config_state["plot_type"] = self._type_combo.get()
        self._config_state["colormap"] = self._cmap_combo.get()
        self._config_state["reverse_cmap"] = self._rev_var.get()
        self._config_state["projection"] = self._proj_var.get()
        self._config_state["norm_type"] = self._norm_var.get()
        self._config_state["interpolation"] = self._interp_var.get()
        self._config_state["aspect"] = self._aspect_var.get()
        return PlotConfig.from_dict(self._config_state)

    def _set_cmap(self, cmap_name):
        """Set colormap from the categorized menu and sync toolbar."""
        self._cmap_combo.set(cmap_name)
        self._on_view_change()

    def _on_view_change(self):
        """Rebuild the current plot with updated view settings."""
        if self._current_var and self.slicer:
            self.plot_manager.close_all()
            self._open_spatial()

    # ==================================================================
    # File loading
    # ==================================================================

    def _open_file_dialog(self):
        filetypes = [("NetCDF files", " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS)),
                     ("All files", "*.*")]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self._load_file(path)

    def _load_file(self, filepath):
        # Show loading overlay
        overlay = self._show_loading_overlay(filepath)

        def do_load():
            try:
                if self.dataset:
                    self.dataset.close()

                self.root.after(0, lambda: self._loading_status.config(
                    text="Opening file..."))
                self.root.after(0, lambda: self._loading_bar.config(value=20))

                ds = Dataset(filepath)

                self.root.after(0, lambda: self._loading_status.config(
                    text="Classifying dimensions..."))
                self.root.after(0, lambda: self._loading_bar.config(value=40))

                self.dataset = ds
                self.slicer = Slicer(self.dataset)

                self.root.after(0, lambda: self._loading_status.config(
                    text="Loading variables..."))
                self.root.after(0, lambda: self._loading_bar.config(value=60))

                var_names = self.dataset.all_variable_names

                self.root.after(0, lambda: self._loading_status.config(
                    text="Preparing interface..."))
                self.root.after(0, lambda: self._loading_bar.config(value=80))

                def finish():
                    self.root.title(f"NC2 - {os.path.basename(filepath)}")
                    self._var_combo.config(values=var_names)
                    if var_names:
                        self._var_combo.set(var_names[0])
                        self._on_var_selected(None)
                    self._update_info_panel()
                    self._loading_bar.config(value=100)
                    self._loading_status.config(text="Done!")
                    self.root.after(200, self._hide_loading_overlay)

                self.root.after(0, finish)

            except Exception as e:
                def show_error():
                    self._hide_loading_overlay()
                    messagebox.showerror("Error", f"Failed to load file:\n{e}")
                self.root.after(0, show_error)

        threading.Thread(target=do_load, daemon=True).start()

    def _show_loading_overlay(self, filepath):
        """Show a full-window loading overlay with progress bar."""
        self._loading_overlay = tb.Frame(self.root)
        self._loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Center content vertically
        spacer = tb.Frame(self._loading_overlay)
        spacer.pack(expand=True)

        inner = tb.Frame(self._loading_overlay)
        inner.pack(expand=False)

        filename = os.path.basename(filepath)
        tb.Label(inner, text="Loading", font=("", 14, "bold")).pack(pady=(0, 4))
        tb.Label(inner, text=filename, font=("Consolas", 10),
                 foreground="gray").pack(pady=(0, 12))

        self._loading_bar = tb.Progressbar(
            inner, length=360, mode="determinate",
            bootstyle="info-striped",
        )
        self._loading_bar.pack(pady=(0, 8))

        self._loading_status = tb.Label(inner, text="Starting...", font=("", 9))
        self._loading_status.pack()

        spacer2 = tb.Frame(self._loading_overlay)
        spacer2.pack(expand=True)

        self.root.update_idletasks()
        return self._loading_overlay

    def _hide_loading_overlay(self):
        """Remove the loading overlay."""
        if hasattr(self, "_loading_overlay") and self._loading_overlay:
            self._loading_overlay.place_forget()
            self._loading_overlay.destroy()
            self._loading_overlay = None

    def _close_file(self):
        if self.dataset:
            self.plot_manager.close_all()
            if self.playback:
                self.playback.pause()
                self.playback = None
            self.dataset.close()
            self.dataset = None
            self.slicer = None
            self._current_var = None
            self._var_combo.set("")
            self._var_combo.config(values=[])
            self._var_info_label.config(text="")
            self._stats_display.clear()
            self._clear_extra_sliders()
            self._update_info_panel()
            self.root.title("NC2")

    # ==================================================================
    # Variable selection
    # ==================================================================

    def _on_var_selected(self, event):
        var_name = self._var_combo.get()
        if not var_name or self.dataset is None:
            return

        self._current_var = var_name
        info = self.dataset.get_variable_info(var_name)
        dim_map = self.dataset.get_var_dim_indices(var_name)

        self._var_info_label.config(
            text=f"{info.long_name} | {info.shape} | {info.units}"
        )

        # Time slider
        if "time" in dim_map:
            nt = self.dataset.num_times
            time_dates = self.dataset.time_dates
            coord_labels = [str(t) for t in time_dates] if time_dates is not None else None
            self._time_slider.set_range(nt, coord_labels)
            self._time_idx = 0
        else:
            self._time_slider.set_range(1)
            self._time_idx = None

        # Depth slider
        if "depth" in dim_map:
            nd = self.dataset.num_depths
            depth_vals = self.dataset.depth_values
            coord_labels = [f"{v:.1f}" for v in depth_vals] if depth_vals is not None else None
            self._depth_slider.set_range(nd, coord_labels)
            self._depth_idx = 0
        else:
            self._depth_slider.set_range(1)
            self._depth_idx = None

        # Extra dimension sliders (unassigned dims)
        self._setup_extra_sliders(var_name, dim_map)

        # Playback controller
        if "time" in dim_map:
            nt = self.dataset.num_times
            if self.playback:
                self.playback.pause()
            self.playback = PlaybackController(self.root, nt, self._on_playback_frame)
            self._setup_playback_bar()
        else:
            if self.playback:
                self.playback.pause()
                self.playback = None

        self._update_stats()
        self._auto_plot()

    def _setup_extra_sliders(self, var_name, dim_map):
        """Create sliders for dimensions not assigned to time/depth/lat/lon."""
        self._clear_extra_sliders()
        self._extra_indices = {}

        var = self.dataset.get_variable(var_name)
        assigned = set(dim_map.keys())
        # Get dim names that aren't recognized
        for i, dim_name in enumerate(var.dimensions):
            role = None
            if dim_name == self.dataset.time_dim:
                role = "time"
            elif dim_name == self.dataset.depth_dim:
                role = "depth"
            elif dim_name == self.dataset.lat_dim:
                role = "lat"
            elif dim_name == self.dataset.lon_dim:
                role = "lon"

            if role is None:
                # Unassigned dimension -- create a slider
                size = var.shape[i]
                coord = self.dataset.get_coord(dim_name)
                coord_labels = None
                if coord is not None and len(coord) == size:
                    coord_labels = [f"{v}" for v in coord]

                self._extra_indices[dim_name] = 0

                def make_cb(dn):
                    return lambda idx: self._on_extra_dim_change(dn, idx)

                slider = DimensionSlider(
                    self._extra_sliders_frame, dim_name, size,
                    coord_values=coord_labels, on_change=make_cb(dim_name),
                )
                slider.pack(fill="x")
                self._extra_sliders[dim_name] = slider

    def _clear_extra_sliders(self):
        for slider in self._extra_sliders.values():
            slider.destroy()
        self._extra_sliders.clear()

    def _on_extra_dim_change(self, dim_name, idx):
        self._extra_indices[dim_name] = idx
        self._refresh_open_plots()
        self._update_stats()

    def _auto_plot(self):
        if not self._current_var or self.slicer is None:
            return
        self.plot_manager.close_all()
        self._open_spatial()

    def _setup_playback_bar(self):
        if self._playback_bar:
            self._playback_bar.destroy()
        if self.playback:
            self._playback_bar = PlaybackBar(self._playback_frame, self.playback)
            self._playback_bar.pack(fill="x")

    # ==================================================================
    # Dimension navigation
    # ==================================================================

    def _on_time_change(self, idx):
        self._time_idx = idx
        self._refresh_open_plots()
        self._update_stats()

    def _on_depth_change(self, idx):
        self._depth_idx = idx
        self._refresh_open_plots()
        self._update_stats()

    def _on_playback_frame(self, frame_idx):
        self._time_idx = frame_idx
        self._time_slider.index = frame_idx
        self._refresh_open_plots()

    # ==================================================================
    # Plot actions
    # ==================================================================

    def _get_time_label(self):
        if self._time_idx is None:
            return None
        if self.dataset and self.dataset.time_dates is not None:
            try:
                return str(self.dataset.time_dates[self._time_idx])
            except (IndexError, TypeError):
                pass
        return f"t={self._time_idx}"

    def _open_spatial(self):
        if not self._current_var or self.slicer is None:
            return

        config = self._get_config()
        var_name = self._current_var
        is_geo = self.dataset.has_geo_coords(var_name)

        data, lat, lon = self.slicer.get_spatial_slice(
            var_name, time_idx=self._time_idx, depth_idx=self._depth_idx,
            extra_indices=self._extra_indices,
        )
        if data is None or lat is None or lon is None:
            messagebox.showwarning("Warning", "Cannot create spatial plot for this variable.")
            return

        var_info = self.dataset.get_variable_info(var_name)
        plot_id = self.plot_manager.next_id()
        time_label = self._get_time_label()

        def on_click(lat_idx, lon_idx):
            self._extract_timeseries_at(lat_idx, lon_idx)

        window = SpatialPlot(
            data, lat, lon, config, var_info,
            plot_id=plot_id, is_geo=is_geo, click_callback=on_click,
            time_label=time_label, playback=self.playback,
        )
        self.plot_manager.register(window)

    def _open_section_dialog(self):
        if not self._current_var or self.slicer is None:
            return
        dim_map = self.dataset.get_var_dim_indices(self._current_var)
        if "depth" not in dim_map:
            messagebox.showinfo("Info", "Variable has no depth dimension.")
            return
        from .widgets import SectionDialog
        SectionDialog(self.root, self.dataset, callback=self._do_open_section)

    def _do_open_section(self, section_type, position_idx):
        config = self._get_config()
        var_name = self._current_var
        data, horiz_coord, depth_coord = self.slicer.get_vertical_section(
            var_name, self._time_idx, section_type, position_idx
        )
        if data is None or horiz_coord is None or depth_coord is None:
            return
        if section_type == "lon":
            pos_val = float(self.dataset.lat[position_idx]) if self.dataset.lat is not None else position_idx
        else:
            pos_val = float(self.dataset.lon[position_idx]) if self.dataset.lon is not None else position_idx
        var_info = self.dataset.get_variable_info(var_name)
        window = SectionPlot(data, horiz_coord, depth_coord, config, var_info,
                             section_type, pos_val, plot_id=self.plot_manager.next_id())
        self.plot_manager.register(window)

    def _open_transect_dialog(self):
        if not self._current_var or self.slicer is None:
            return
        from .widgets import SectionDialog
        SectionDialog(self.root, self.dataset, callback=self._do_open_transect)

    def _do_open_transect(self, section_type, position_idx):
        config = self._get_config()
        var_name = self._current_var
        data, coord = self.slicer.get_horizontal_section(
            var_name, self._time_idx, self._depth_idx, section_type, position_idx
        )
        if data is None or coord is None:
            return
        if section_type == "lat":
            pos_val = float(self.dataset.lat[position_idx]) if self.dataset.lat is not None else position_idx
        else:
            pos_val = float(self.dataset.lon[position_idx]) if self.dataset.lon is not None else position_idx
        depth_value = "surface"
        if self._depth_idx is not None and self.dataset.depth_values is not None:
            depth_value = f"{self.dataset.depth_values[self._depth_idx]:.1f}"
        var_info = self.dataset.get_variable_info(var_name)
        window = TransectPlot(data, coord, config, var_info, section_type,
                              pos_val, depth_value, plot_id=self.plot_manager.next_id())
        self.plot_manager.register(window)

    def _open_timeseries(self):
        if not self._current_var or self.slicer is None:
            return
        dim_map = self.dataset.get_var_dim_indices(self._current_var)
        if "time" not in dim_map:
            messagebox.showinfo("Info", "Variable has no time dimension.")
            return
        lat_idx = len(self.dataset.lat) // 2 if self.dataset.lat is not None else 0
        lon_idx = len(self.dataset.lon) // 2 if self.dataset.lon is not None else 0
        self._extract_timeseries_at(lat_idx, lon_idx)

    def _extract_timeseries_at(self, lat_idx, lon_idx):
        var_name = self._current_var
        config = self._get_config()
        data, time_coord = self.slicer.get_timeseries(
            var_name, lat_idx, lon_idx, depth_idx=self._depth_idx,
            extra_indices=self._extra_indices,
        )
        lat_val = float(self.dataset.lat[lat_idx]) if self.dataset.lat is not None else lat_idx
        lon_val = float(self.dataset.lon[lon_idx]) if self.dataset.lon is not None else lon_idx
        depth_val = None
        if self._depth_idx is not None and self.dataset.depth_values is not None:
            depth_val = float(self.dataset.depth_values[self._depth_idx])
        var_info = self.dataset.get_variable_info(var_name)
        window = TimeseriesPlot(data, time_coord, config, var_info,
                                lat_val, lon_val, depth_value=depth_val,
                                plot_id=self.plot_manager.next_id())
        self.plot_manager.register(window)

    def _open_depth_profile(self):
        if not self._current_var or self.slicer is None:
            return
        dim_map = self.dataset.get_var_dim_indices(self._current_var)
        if "depth" not in dim_map:
            messagebox.showinfo("Info", "Variable has no depth dimension.")
            return
        config = self._get_config()
        lat_idx = len(self.dataset.lat) // 2 if self.dataset.lat is not None else 0
        lon_idx = len(self.dataset.lon) // 2 if self.dataset.lon is not None else 0
        data, depth_coord = self.slicer.get_depth_profile(
            self._current_var, self._time_idx, lat_idx, lon_idx,
            extra_indices=self._extra_indices,
        )
        lat_val = float(self.dataset.lat[lat_idx]) if self.dataset.lat is not None else lat_idx
        lon_val = float(self.dataset.lon[lon_idx]) if self.dataset.lon is not None else lon_idx
        var_info = self.dataset.get_variable_info(self._current_var)
        window = DepthProfilePlot(data, depth_coord, config, var_info,
                                  lat_val, lon_val, time_label=self._get_time_label(),
                                  plot_id=self.plot_manager.next_id())
        self.plot_manager.register(window)

    # ==================================================================
    # View dialogs
    # ==================================================================

    def _show_color_limits_dialog(self):
        from .widgets import ColorLimitsDialog
        ColorLimitsDialog(self.root, self._config_state, callback=self._on_dialog_apply)

    def _show_map_features_dialog(self):
        from .widgets import MapFeaturesDialog
        MapFeaturesDialog(self.root, self._config_state, callback=self._on_dialog_apply)

    def _show_labels_dialog(self):
        from .widgets import LabelsDialog
        LabelsDialog(self.root, self._config_state, callback=self._on_dialog_apply)

    def _show_colorbar_dialog(self):
        from .widgets import ColorbarDialog
        ColorbarDialog(self.root, self._config_state, callback=self._on_dialog_apply)

    def _show_contour_dialog(self):
        from .widgets import ContourDialog
        ContourDialog(self.root, self._config_state, callback=self._on_dialog_apply)

    def _show_quiver_dialog(self):
        from .widgets import QuiverDialog
        QuiverDialog(self.root, self._config_state, callback=self._on_dialog_apply)

    def _show_streamplot_dialog(self):
        from .widgets import StreamplotDialog
        StreamplotDialog(self.root, self._config_state, callback=self._on_dialog_apply)

    def _show_alpha_dialog(self):
        from .widgets import AlphaDialog
        AlphaDialog(self.root, self._config_state, callback=self._on_dialog_apply)

    def _show_norm_dialog(self):
        from .widgets import NormDialog
        NormDialog(self.root, self._config_state, callback=self._on_dialog_apply)

    def _show_dim_dialog(self):
        if not self.dataset:
            messagebox.showinfo("Info", "No file loaded.")
            return
        from .widgets import DimensionAssignDialog
        DimensionAssignDialog(self.root, self.dataset, callback=self._on_dim_reassign)

    def _on_dim_reassign(self):
        """Called after user reassigns dimension roles."""
        # Re-select the current variable to refresh sliders and plot
        if self._current_var:
            self._on_var_selected(None)

    def _on_dialog_apply(self, updated_state):
        self._config_state.update(updated_state)
        if self._current_var and self.slicer:
            self.plot_manager.close_all()
            self._open_spatial()

    # ==================================================================
    # Export
    # ==================================================================

    def _export_gif_dialog(self):
        if not self._current_var or self.slicer is None:
            return
        if self.dataset.num_times == 0:
            messagebox.showinfo("Info", "No time dimension for GIF export.")
            return

        dialog = tb.Toplevel(self.root)
        dialog.title("Export GIF")
        dialog.minsize(300, 260)
        dialog.resizable(True, True)

        tb.Label(dialog, text="FPS:").pack(anchor="w", padx=10, pady=(10, 0))
        fps_var = tk.StringVar(value="10")
        tb.Entry(dialog, textvariable=fps_var, width=8).pack(anchor="w", padx=10)

        tb.Label(dialog, text="Frame start:").pack(anchor="w", padx=10, pady=(6, 0))
        start_var = tk.StringVar(value="0")
        tb.Entry(dialog, textvariable=start_var, width=8).pack(anchor="w", padx=10)

        tb.Label(dialog, text="Frame end (blank=all):").pack(anchor="w", padx=10, pady=(6, 0))
        end_var = tk.StringVar(value="")
        tb.Entry(dialog, textvariable=end_var, width=8).pack(anchor="w", padx=10)

        loop_var = tk.BooleanVar(value=True)
        tb.Checkbutton(dialog, text="Loop", variable=loop_var).pack(anchor="w", padx=10, pady=6)

        progress_label = tb.Label(dialog, text="", font=("", 8))
        progress_label.pack(anchor="w", padx=10)

        def do_export():
            path = filedialog.asksaveasfilename(
                defaultextension=".gif", filetypes=[("GIF files", "*.gif")],
                initialfile=f"{self._current_var}.gif")
            if not path:
                return
            fps = int(fps_var.get() or "10")
            start = int(start_var.get() or "0")
            end_str = end_var.get().strip()
            end = int(end_str) if end_str else None
            config = self._get_config()

            def progress(current, total):
                progress_label.config(text=f"Rendering {current}/{total}...")
                dialog.update_idletasks()

            def run():
                try:
                    export_gif(self.slicer, self._current_var, config, path,
                               fps=fps, frame_start=start, frame_end=end,
                               loop=loop_var.get(), progress_callback=progress)
                    self.root.after(0, lambda: messagebox.showinfo("Done", f"GIF saved:\n{path}"))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                finally:
                    self.root.after(0, dialog.destroy)

            threading.Thread(target=run, daemon=True).start()

        tb.Button(dialog, text="Export", command=do_export, bootstyle="success").pack(pady=8)

    def _save_image(self):
        if not self._current_var or self.slicer is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("SVG", "*.svg"), ("PDF", "*.pdf")],
            initialfile=f"{self._current_var}.png")
        if not path:
            return
        config = self._get_config()
        try:
            export_frame(self.slicer, self._current_var, config, path,
                         time_idx=self._time_idx, depth_idx=self._depth_idx)
            messagebox.showinfo("Done", f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _batch_export(self):
        if not self._current_var or self.slicer is None:
            return
        if self.dataset.num_times == 0:
            messagebox.showinfo("Info", "No time dimension for batch export.")
            return
        from .export import export_batch
        out_dir = filedialog.askdirectory(title="Select output directory")
        if not out_dir:
            return
        config = self._get_config()
        try:
            paths = export_batch(self.slicer, self._current_var, config, out_dir)
            messagebox.showinfo("Done", f"Exported {len(paths)} frames to:\n{out_dir}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ==================================================================
    # Plot refresh
    # ==================================================================

    def _refresh_open_plots(self):
        if not self._current_var or self.slicer is None:
            return
        var_name = self._current_var
        time_idx = self._time_idx
        depth_idx = self._depth_idx
        time_label = self._get_time_label() or ""

        def update_fn(window):
            if window.window_type == "spatial":
                data, _, _ = self.slicer.get_spatial_slice(
                    var_name, time_idx, depth_idx,
                    extra_indices=self._extra_indices,
                )
                window.update_data(data, title_suffix=time_label)

        self.plot_manager.update_all(update_fn)

    def _update_stats(self):
        if not self._current_var or self.slicer is None:
            self._stats_display.clear()
            return
        try:
            data, _, _ = self.slicer.get_spatial_slice(
                self._current_var, self._time_idx, self._depth_idx,
                extra_indices=self._extra_indices,
            )
            stats = self.slicer.compute_stats(data)
            self._stats_display.update_stats(stats)
        except Exception:
            self._stats_display.clear()

    def _close_all_plots(self):
        self.plot_manager.close_all()

    # ==================================================================
    # Help
    # ==================================================================

    def _show_about(self):
        messagebox.showinfo("About NC2",
                            "NC2 v2.0.0\n\n"
                            "Fast, versatile NetCDF viewer\n"
                            "for scientists.\n\n"
                            "github.com/rhettadam/NC2")

    def _show_shortcuts(self):
        messagebox.showinfo("Keyboard Shortcuts",
                            "Ctrl+O  Open file\n"
                            "Ctrl+S  Save image\n"
                            "Ctrl+Q  Quit\n\n"
                            "Click on a spatial plot to\n"
                            "extract a timeseries at that point.")

    # ==================================================================
    # Cleanup
    # ==================================================================

    def _on_quit(self):
        if self.playback:
            self.playback.pause()
        self.plot_manager.close_all()
        if self.dataset:
            self.dataset.close()
        self.root.destroy()
