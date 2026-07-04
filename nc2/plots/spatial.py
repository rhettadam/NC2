"""
2D spatial (map) plot window. Handles geo-aware plots with cartopy
projections and non-geo index-space plots. Supports in-place data
updates for smooth playback.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from .manager import PlotWindow
from .config import PlotConfig
from ..constants import get_projections, DEFAULT_PROJECTION


def _get_cartopy():
    """Lazy import of cartopy modules."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    return ccrs, cfeature


class SpatialPlot(PlotWindow):
    """
    A standalone matplotlib window showing a 2D spatial field.
    Supports pcolormesh, contourf, contour, imshow, quiver, and streamplot
    with optional cartopy map features and full matplotlib API surface.
    """

    def __init__(self, data, lat, lon, config, var_info, plot_id=None,
                 is_geo=True, click_callback=None, time_label=None,
                 playback=None):
        self.config = config
        self.var_info = var_info
        self.is_geo = is_geo
        self.click_callback = click_callback
        self.time_label = time_label
        self.lat = lat
        self.lon = lon
        self.playback = playback

        self._mappable = None
        self._colorbar = None
        self._ax = None
        self._pick_mode = False

        fig = self._build_figure(data)
        super().__init__(fig, plot_id, "spatial")

        self._add_toolbar_extras(fig)

        if click_callback:
            fig.canvas.mpl_connect("button_press_event", self._on_click)

        plt.show(block=False)

    # ------------------------------------------------------------------
    # Figure construction
    # ------------------------------------------------------------------

    def _build_figure(self, data):
        fig = plt.figure(figsize=(8, 5.5), dpi=100)
        fig.set_tight_layout(True)
        self.fig = fig

        if self.is_geo:
            proj = self._get_projection()
            ax = fig.add_subplot(111, projection=proj)
            self._apply_map_features(ax)
        else:
            ax = fig.add_subplot(111)

        self._ax = ax
        self._render_data(ax, data)
        self._apply_labels(ax)

        return fig

    def _get_projection(self):
        proj_name = self.config.projection or DEFAULT_PROJECTION
        projs = get_projections()
        proj_factory = projs.get(proj_name, projs[DEFAULT_PROJECTION])
        return proj_factory()

    def _apply_map_features(self, ax):
        ccrs, cfeature = _get_cartopy()

        if self.config.extent:
            ax.set_extent(self.config.extent, crs=ccrs.PlateCarree())
        else:
            lon_min, lon_max = float(self.lon.min()), float(self.lon.max())
            lat_min, lat_max = float(self.lat.min()), float(self.lat.max())
            margin_lon = (lon_max - lon_min) * 0.02
            margin_lat = (lat_max - lat_min) * 0.02
            ax.set_extent([
                lon_min - margin_lon, lon_max + margin_lon,
                lat_min - margin_lat, lat_max + margin_lat,
            ], crs=ccrs.PlateCarree())

        if self.config.coastlines:
            ax.coastlines(linewidth=0.5)
        if self.config.land:
            ax.add_feature(cfeature.LAND, facecolor="lightgray", alpha=0.5)
        if self.config.ocean:
            ax.add_feature(cfeature.OCEAN, facecolor="lightblue", alpha=0.3)
        if self.config.borders:
            ax.add_feature(cfeature.BORDERS, linewidth=0.3)
        if self.config.rivers:
            ax.add_feature(cfeature.RIVERS, linewidth=0.3, edgecolor="blue")
        if self.config.gridlines:
            gl = ax.gridlines(draw_labels=True, alpha=self.config.gridline_alpha)
            gl.top_labels = False
            gl.right_labels = False

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def _get_norm(self, vmin, vmax):
        """Build a matplotlib Normalize instance based on config.norm_type."""
        norm_type = self.config.norm_type

        # Override vmin/vmax with norm-specific bounds if set
        nmin = self.config.norm_vmin if self.config.norm_vmin is not None else vmin
        nmax = self.config.norm_vmax if self.config.norm_vmax is not None else vmax

        if norm_type == "log":
            # LogNorm requires strictly positive bounds
            nmin = max(nmin, 1e-10)
            nmax = max(nmax, nmin * 10)
            return mcolors.LogNorm(vmin=nmin, vmax=nmax)

        elif norm_type == "symlog":
            return mcolors.SymLogNorm(
                linthresh=self.config.norm_linthresh,
                vmin=nmin, vmax=nmax,
            )

        elif norm_type == "power":
            return mcolors.PowerNorm(
                gamma=self.config.norm_gamma,
                vmin=nmin, vmax=nmax,
            )

        # "linear" or unrecognized -- use standard Normalize
        return mcolors.Normalize(vmin=nmin, vmax=nmax)

    # ------------------------------------------------------------------
    # Data rendering
    # ------------------------------------------------------------------

    def _render_data(self, ax, data):
        cmap = self.config.colormap
        if self.config.reverse_cmap:
            cmap = cmap + "_r"

        vmin, vmax = self._compute_clim(data)
        norm = self._get_norm(vmin, vmax)
        alpha = self.config.alpha
        transform = None
        if self.is_geo:
            ccrs, _ = _get_cartopy()
            transform = ccrs.PlateCarree()
        plot_type = self.config.plot_type

        if plot_type == "pcolormesh":
            kwargs = {"cmap": cmap, "norm": norm, "shading": "auto", "alpha": alpha}
            if transform:
                kwargs["transform"] = transform
            self._mappable = ax.pcolormesh(self.lon, self.lat, data, **kwargs)

        elif plot_type == "contourf":
            kwargs = {
                "cmap": cmap, "levels": self.config.contour_levels,
                "norm": norm, "alpha": alpha,
            }
            if transform:
                kwargs["transform"] = transform
            self._mappable = ax.contourf(self.lon, self.lat, data, **kwargs)

        elif plot_type == "contour":
            kwargs = {
                "cmap": cmap, "levels": self.config.contour_levels,
                "norm": norm,
                "linewidths": self.config.contour_linewidths,
                "linestyles": self.config.contour_linestyles,
            }
            if transform:
                kwargs["transform"] = transform
            self._mappable = ax.contour(self.lon, self.lat, data, **kwargs)

        elif plot_type == "imshow":
            kwargs = {
                "cmap": cmap, "norm": norm, "alpha": alpha,
                "origin": "lower",
                "aspect": self.config.aspect,
                "interpolation": self.config.interpolation,
            }
            if transform:
                kwargs["transform"] = transform
                extent_vals = [float(self.lon[0]), float(self.lon[-1]),
                               float(self.lat[0]), float(self.lat[-1])]
                kwargs["extent"] = extent_vals
            self._mappable = ax.imshow(data, **kwargs)

        elif plot_type == "quiver":
            step = self.config.quiver_step
            kwargs = {
                "scale": self.config.quiver_scale,
                "pivot": self.config.quiver_pivot,
                "headwidth": self.config.quiver_headwidth,
                "headlength": self.config.quiver_headlength,
            }
            if transform:
                kwargs["transform"] = transform
            lon_sub = self.lon[::step]
            lat_sub = self.lat[::step]
            data_sub = data[::step, ::step]
            self._mappable = ax.quiver(
                lon_sub, lat_sub, data_sub, np.zeros_like(data_sub), **kwargs
            )

        elif plot_type == "streamplot":
            kwargs = {
                "cmap": cmap,
                "density": self.config.streamplot_density,
                "linewidth": self.config.streamplot_linewidth,
                "arrowsize": self.config.streamplot_arrowsize,
            }
            if transform:
                kwargs["transform"] = transform
            self._mappable = ax.streamplot(
                self.lon, self.lat, data, np.zeros_like(data), **kwargs
            )

        else:
            kwargs = {"cmap": cmap, "norm": norm, "shading": "auto", "alpha": alpha}
            if transform:
                kwargs["transform"] = transform
            self._mappable = ax.pcolormesh(self.lon, self.lat, data, **kwargs)

        # Colorbar
        if self._mappable is not None and plot_type not in ("quiver", "streamplot"):
            cbar_kwargs = {
                "ax": ax,
                "orientation": self.config.colorbar_orientation,
                "label": self.config.colorbar_label or self.var_info.units,
                "fraction": 0.046,
                "pad": 0.04,
                "extend": self.config.colorbar_extend,
                "shrink": self.config.colorbar_shrink,
            }
            self._colorbar = self.fig.colorbar(self._mappable, **cbar_kwargs)

    def _apply_labels(self, ax):
        title = self.config.title or f"{self.var_info.long_name} ({self.var_info.units})"
        if self.time_label:
            title = f"{title} - {self.time_label}"
        ax.set_title(title, fontsize=11)

        if not self.is_geo:
            ax.set_xlabel(self.config.xlabel or "Longitude")
            ax.set_ylabel(self.config.ylabel or "Latitude")

    def _compute_clim(self, data):
        valid = data.compressed() if hasattr(data, "compressed") else np.asarray(data).ravel()
        valid = valid[np.isfinite(valid)]
        if valid.size == 0:
            return 0.0, 1.0

        if self.config.symmetric:
            abs_max = float(np.max(np.abs(valid)))
            return -abs_max, abs_max

        vmin = self.config.vmin if self.config.vmin is not None else float(np.min(valid))
        vmax = self.config.vmax if self.config.vmax is not None else float(np.max(valid))
        return vmin, vmax

    # ------------------------------------------------------------------
    # In-place update for playback
    # ------------------------------------------------------------------

    def update_data(self, data, **kwargs):
        if self.closed:
            return

        plot_type = self.config.plot_type

        if plot_type in ("pcolormesh", "imshow") and self._mappable is not None:
            flat = data.ravel()
            self._mappable.set_array(flat)

            if self.config.vmin is None or self.config.vmax is None:
                vmin, vmax = self._compute_clim(data)
                self._mappable.set_clim(vmin, vmax)

            if "title_suffix" in kwargs:
                title = self.config.title or self.var_info.long_name
                self._ax.set_title(f"{title} - {kwargs['title_suffix']}", fontsize=11)

            self.fig.canvas.draw_idle()

        elif plot_type in ("contourf", "contour"):
            self._ax.clear()
            if self.is_geo:
                self._apply_map_features(self._ax)
            self._render_data(self._ax, data)
            if "title_suffix" in kwargs:
                title = self.config.title or self.var_info.long_name
                self._ax.set_title(f"{title} - {kwargs['title_suffix']}", fontsize=11)
            else:
                self._apply_labels(self._ax)
            self.fig.canvas.draw_idle()

    def rebuild(self, data, config):
        if self.closed:
            return

        self.config = config
        self.fig.clear()

        if self.is_geo:
            proj = self._get_projection()
            self._ax = self.fig.add_subplot(111, projection=proj)
            self._apply_map_features(self._ax)
        else:
            self._ax = self.fig.add_subplot(111)

        self._colorbar = None
        self._render_data(self._ax, data)
        self._apply_labels(self._ax)
        self.fig.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Toolbar extras (playback + pick)
    # ------------------------------------------------------------------

    def _add_toolbar_extras(self, fig):
        """Add custom buttons to the matplotlib navigation toolbar."""
        import tkinter as tk

        toolbar = fig.canvas.manager.toolbar
        if toolbar is None:
            return

        # Separator between built-in buttons and our extras
        sep = tk.Frame(toolbar, width=2, bd=1, relief="sunken", height=24)
        sep.pack(side="left", padx=8, pady=2, fill="y")

        btn_opts = {"padx": 3, "pady": 1}

        # Playback buttons (only if there's a playback controller)
        if self.playback is not None:
            self._tb_prev = tk.Button(toolbar, text="|<", command=self.playback.stop, **btn_opts)
            self._tb_prev.pack(side="left", padx=1)

            self._tb_back = tk.Button(toolbar, text="<", command=self.playback.step_backward, **btn_opts)
            self._tb_back.pack(side="left", padx=1)

            self._tb_play = tk.Button(toolbar, text=">", command=self._tb_toggle_play, **btn_opts)
            self._tb_play.pack(side="left", padx=1)

            self._tb_fwd = tk.Button(toolbar, text=">", command=self.playback.step_forward, **btn_opts)
            self._tb_fwd.config(text=">|")
            self._tb_fwd.pack(side="left", padx=1)

            # Another separator before pick
            sep2 = tk.Frame(toolbar, width=2, bd=1, relief="sunken", height=24)
            sep2.pack(side="left", padx=8, pady=2, fill="y")

        # Pick button (always present if click_callback exists)
        if self.click_callback:
            self._pick_btn = tk.Button(
                toolbar, text="Pick",
                relief="raised", **btn_opts,
                command=self._toggle_pick,
            )
            self._pick_btn.pack(side="left", padx=4)

    def _tb_toggle_play(self):
        if self.playback is None:
            return
        if self.playback.playing:
            self.playback.pause()
            self._tb_play.config(text=">")
        else:
            self.playback.play()
            self._tb_play.config(text="||")

    def _toggle_pick(self):
        self._pick_mode = not self._pick_mode
        if self._pick_mode:
            self._pick_btn.config(text="Pick*", relief="sunken")
        else:
            self._pick_btn.config(text="Pick", relief="raised")

    def _on_click(self, event):
        if not self._pick_mode:
            return
        if event.inaxes != self._ax or self.click_callback is None:
            return

        click_lon, click_lat = event.xdata, event.ydata
        if click_lon is None or click_lat is None:
            return

        lat_idx = int(np.argmin(np.abs(self.lat - click_lat)))
        lon_idx = int(np.argmin(np.abs(self.lon - click_lon)))
        self.click_callback(lat_idx, lon_idx)
