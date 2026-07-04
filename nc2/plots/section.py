"""
Cross-section plot windows. Handles both vertical sections (depth vs
lat/lon) and horizontal transects (value along a line at fixed depth).
"""

import numpy as np
import matplotlib.pyplot as plt

from .manager import PlotWindow
from .config import PlotConfig


class SectionPlot(PlotWindow):
    """
    Vertical cross-section: shows a 2D slice of depth vs. latitude
    or depth vs. longitude. Depth axis is inverted (increasing downward).
    Supports in-place data updates for playback.
    """

    def __init__(self, data, horiz_coord, depth_coord, config, var_info,
                 section_type, position_value, plot_id=None):
        """
        Args:
            data: 2D array (depth x horizontal)
            horiz_coord: 1D coordinate for horizontal axis
            depth_coord: 1D coordinate for vertical axis
            config: PlotConfig
            var_info: VariableInfo
            section_type: 'lon' or 'lat' (which axis is the horizontal)
            position_value: the fixed coordinate value for the title
            plot_id: assigned by manager
        """
        self.config = config
        self.var_info = var_info
        self.section_type = section_type
        self.position_value = position_value
        self.horiz_coord = horiz_coord
        self.depth_coord = depth_coord

        self._mappable = None
        self._colorbar = None
        self._ax = None

        fig = self._build_figure(data)
        super().__init__(fig, plot_id, "section")
        plt.show(block=False)

    def _build_figure(self, data):
        """Construct the section plot from scratch."""
        fig = plt.figure(figsize=(7, 4.5), dpi=100)
        fig.set_tight_layout(True)
        self.fig = fig  # must be set before _render_data uses it
        ax = fig.add_subplot(111)
        self._ax = ax

        self._render_data(ax, data)
        self._apply_labels(ax)

        # Depth increases downward
        ax.invert_yaxis()

        return fig

    def _render_data(self, ax, data):
        """Draw section data and store mappable reference."""
        cmap = self.config.colormap
        if self.config.reverse_cmap:
            cmap = cmap + "_r"

        vmin, vmax = self._compute_clim(data)
        plot_type = self.config.plot_type

        if plot_type in ("pcolormesh", "imshow"):
            self._mappable = ax.pcolormesh(
                self.horiz_coord, self.depth_coord, data,
                cmap=cmap, vmin=vmin, vmax=vmax, shading="auto",
            )
        elif plot_type == "contourf":
            self._mappable = ax.contourf(
                self.horiz_coord, self.depth_coord, data,
                levels=self.config.contour_levels, cmap=cmap,
                vmin=vmin, vmax=vmax,
            )
        elif plot_type == "contour":
            self._mappable = ax.contour(
                self.horiz_coord, self.depth_coord, data,
                levels=self.config.contour_levels, cmap=cmap,
                vmin=vmin, vmax=vmax,
            )
        else:
            # Default to pcolormesh for section views
            self._mappable = ax.pcolormesh(
                self.horiz_coord, self.depth_coord, data,
                cmap=cmap, vmin=vmin, vmax=vmax, shading="auto",
            )

        if self._mappable is not None:
            self._colorbar = self.fig.colorbar(
                self._mappable, ax=ax,
                orientation=self.config.colorbar_orientation,
                shrink=self.config.colorbar_shrink,
                label=self.config.colorbar_label or self.var_info.units,
            )

    def _apply_labels(self, ax):
        """Set title and axis labels for the section."""
        if self.section_type == "lon":
            horiz_label = "Longitude"
            fixed_label = "Lat"
        else:
            horiz_label = "Latitude"
            fixed_label = "Lon"

        title = (
            self.config.title
            or f"{self.var_info.long_name} -- {fixed_label} = {self.position_value:.2f}"
        )
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(self.config.xlabel or horiz_label)
        ax.set_ylabel(self.config.ylabel or "Depth")

    def _compute_clim(self, data):
        """Determine color limits from config or data, handling masked arrays."""
        # Use compressed() to get only valid values from masked arrays
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
    # In-place update
    # ------------------------------------------------------------------

    def update_data(self, data, **kwargs):
        """Swap section data without full rebuild (pcolormesh only)."""
        if self.closed:
            return

        plot_type = self.config.plot_type

        if plot_type in ("pcolormesh", "imshow") and self._mappable is not None:
            self._mappable.set_array(data.ravel())
            if self.config.vmin is None or self.config.vmax is None:
                vmin, vmax = self._compute_clim(data)
                self._mappable.set_clim(vmin, vmax)
            if "title_suffix" in kwargs:
                title = self.config.title or self.var_info.long_name
                self._ax.set_title(f"{title} - {kwargs['title_suffix']}", fontsize=11)
            self.fig.canvas.draw_idle()
        else:
            # Contour types require full redraw
            self._ax.clear()
            self._render_data(self._ax, data)
            self._apply_labels(self._ax)
            self._ax.invert_yaxis()
            if "title_suffix" in kwargs:
                title = self.config.title or self.var_info.long_name
                self._ax.set_title(f"{title} - {kwargs['title_suffix']}", fontsize=11)
            self.fig.canvas.draw_idle()


class TransectPlot(PlotWindow):
    """
    Horizontal transect: a 1D line plot showing values along a latitude
    or longitude line at a fixed depth. Useful for seeing gradients
    along a single axis.
    """

    def __init__(self, data, coord, config, var_info,
                 section_type, position_value, depth_value, plot_id=None):
        """
        Args:
            data: 1D array of values along the transect
            coord: 1D coordinate array for the x-axis
            config: PlotConfig
            var_info: VariableInfo
            section_type: 'lat' (along lat line) or 'lon' (along lon line)
            position_value: the fixed lat or lon value
            depth_value: the depth level value
            plot_id: assigned by manager
        """
        self.config = config
        self.var_info = var_info
        self.section_type = section_type
        self.position_value = position_value
        self.depth_value = depth_value
        self.coord = coord

        self._line = None
        self._ax = None

        fig = self._build_figure(data)
        super().__init__(fig, plot_id, "transect")
        plt.show(block=False)

    def _build_figure(self, data):
        """Construct the transect line plot."""
        fig = plt.figure(figsize=(7, 4), dpi=100)
        fig.set_tight_layout(True)
        self.fig = fig  # must be set before any method uses it
        ax = fig.add_subplot(111)
        self._ax = ax

        self._line, = ax.plot(self.coord, data, linewidth=1.2, color="steelblue")
        self._apply_labels(ax)

        return fig

    def _apply_labels(self, ax):
        """Set title and axis labels for the transect."""
        if self.section_type == "lat":
            xlabel = "Longitude"
            fixed_label = f"Lat = {self.position_value:.2f}"
        else:
            xlabel = "Latitude"
            fixed_label = f"Lon = {self.position_value:.2f}"

        title = (
            self.config.title
            or f"{self.var_info.long_name} -- {fixed_label}, Depth = {self.depth_value}"
        )
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(self.config.xlabel or xlabel)
        ax.set_ylabel(self.config.ylabel or f"{self.var_info.long_name} ({self.var_info.units})")
        ax.grid(True, alpha=0.3)

    def update_data(self, data, **kwargs):
        """Update the transect line data in-place."""
        if self.closed or self._line is None:
            return
        self._line.set_ydata(data)
        self._ax.relim()
        self._ax.autoscale_view(scaley=True, scalex=False)
        if "title_suffix" in kwargs:
            title = self.config.title or self.var_info.long_name
            self._ax.set_title(f"{title} - {kwargs['title_suffix']}", fontsize=11)
        self.fig.canvas.draw_idle()
