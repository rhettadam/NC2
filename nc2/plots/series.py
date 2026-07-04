"""
Timeseries and depth profile plot windows. Line plots for extracting
temporal evolution or vertical structure at a specific point.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from .manager import PlotWindow
from .config import PlotConfig


class TimeseriesPlot(PlotWindow):
    """
    Line plot of a variable's value over time at a fixed spatial point.
    Supports overlaying multiple series (different points or variables).
    """

    def __init__(self, data, time_coord, config, var_info,
                 lat_value, lon_value, depth_value=None, plot_id=None):
        """
        Args:
            data: 1D array of values over time
            time_coord: 1D array of time values (datetime or numeric)
            config: PlotConfig
            var_info: VariableInfo
            lat_value: latitude of the extracted point
            lon_value: longitude of the extracted point
            depth_value: depth level (if applicable)
            plot_id: assigned by manager
        """
        self.config = config
        self.var_info = var_info
        self.lat_value = lat_value
        self.lon_value = lon_value
        self.depth_value = depth_value
        self.time_coord = time_coord

        self._lines = []
        self._ax = None
        self._uses_dates = False

        fig = self._build_figure(data)
        super().__init__(fig, plot_id, "timeseries")
        plt.show(block=False)

    def _build_figure(self, data):
        """Construct the timeseries line plot."""
        fig = plt.figure(figsize=(7, 4), dpi=100)
        fig.set_tight_layout(True)
        self.fig = fig  # must be set before _apply_formatting uses it
        ax = fig.add_subplot(111)
        self._ax = ax

        # Determine if time axis is datetime
        self._uses_dates = self._check_datetime(self.time_coord)

        x = self.time_coord
        if self._uses_dates:
            x = mdates.date2num(self.time_coord)

        line, = ax.plot(x, data, linewidth=1.2, color="steelblue",
                        label=self._make_label())
        self._lines.append(line)

        self._apply_formatting(ax)
        return fig

    def _apply_formatting(self, ax):
        """Labels, grid, date formatting."""
        depth_str = f", z={self.depth_value}" if self.depth_value is not None else ""
        title = (
            self.config.title
            or f"{self.var_info.long_name} at ({self.lat_value:.2f}, {self.lon_value:.2f}{depth_str})"
        )
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(self.config.xlabel or "Time")
        ax.set_ylabel(
            self.config.ylabel or f"{self.var_info.long_name} ({self.var_info.units})"
        )
        ax.grid(True, alpha=0.3)

        if self._uses_dates:
            ax.xaxis.set_major_formatter(mdates.AutoDateFormatter(mdates.AutoDateLocator()))
            self.fig.autofmt_xdate()

        if len(self._lines) > 1:
            ax.legend(fontsize=9)

    def _make_label(self):
        """Generate a legend label for this series."""
        return f"({self.lat_value:.1f}, {self.lon_value:.1f})"

    def add_series(self, data, time_coord, lat_value, lon_value, label=None):
        """Overlay an additional timeseries on the same axes."""
        if self.closed:
            return

        x = time_coord
        if self._uses_dates:
            x = mdates.date2num(time_coord)

        lbl = label or f"({lat_value:.1f}, {lon_value:.1f})"
        line, = self._ax.plot(x, data, linewidth=1.2, label=lbl)
        self._lines.append(line)
        self._ax.legend(fontsize=9)
        self.fig.canvas.draw_idle()

    def update_data(self, data, **kwargs):
        """Update the primary line data."""
        if self.closed or not self._lines:
            return
        self._lines[0].set_ydata(data)
        self._ax.relim()
        self._ax.autoscale_view(scaley=True, scalex=False)
        self.fig.canvas.draw_idle()

    @staticmethod
    def _check_datetime(arr):
        """Check if the coordinate array contains datetime-like objects."""
        if arr is None or len(arr) == 0:
            return False
        sample = arr[0]
        return hasattr(sample, "year") or hasattr(sample, "timestamp")


class DepthProfilePlot(PlotWindow):
    """
    Line plot of a variable's value over depth at a fixed point and time.
    Depth axis is inverted (increasing downward, plotted on y-axis).
    """

    def __init__(self, data, depth_coord, config, var_info,
                 lat_value, lon_value, time_label=None, plot_id=None):
        """
        Args:
            data: 1D array of values over depth
            depth_coord: 1D depth coordinate array
            config: PlotConfig
            var_info: VariableInfo
            lat_value: latitude of the extracted point
            lon_value: longitude of the extracted point
            time_label: string label for the time step
            plot_id: assigned by manager
        """
        self.config = config
        self.var_info = var_info
        self.lat_value = lat_value
        self.lon_value = lon_value
        self.time_label = time_label
        self.depth_coord = depth_coord

        self._lines = []
        self._ax = None

        fig = self._build_figure(data)
        super().__init__(fig, plot_id, "profile")
        plt.show(block=False)

    def _build_figure(self, data):
        """Construct the depth profile plot (depth on y-axis, value on x)."""
        fig = plt.figure(figsize=(5, 5.5), dpi=100)
        fig.set_tight_layout(True)
        self.fig = fig  # must be set before any method uses it
        ax = fig.add_subplot(111)
        self._ax = ax

        line, = ax.plot(data, self.depth_coord, linewidth=1.2, color="steelblue",
                        label=self._make_label())
        self._lines.append(line)

        # Depth increases downward
        ax.invert_yaxis()
        self._apply_formatting(ax)

        return fig

    def _apply_formatting(self, ax):
        """Labels and grid."""
        time_str = f", t={self.time_label}" if self.time_label else ""
        title = (
            self.config.title
            or f"{self.var_info.long_name} at ({self.lat_value:.2f}, {self.lon_value:.2f}{time_str})"
        )
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(
            self.config.xlabel or f"{self.var_info.long_name} ({self.var_info.units})"
        )
        ax.set_ylabel(self.config.ylabel or "Depth")
        ax.grid(True, alpha=0.3)

        if len(self._lines) > 1:
            ax.legend(fontsize=9)

    def _make_label(self):
        """Legend label for this profile."""
        return f"({self.lat_value:.1f}, {self.lon_value:.1f})"

    def add_profile(self, data, depth_coord, lat_value, lon_value, label=None):
        """Overlay an additional depth profile on the same axes."""
        if self.closed:
            return

        lbl = label or f"({lat_value:.1f}, {lon_value:.1f})"
        line, = self._ax.plot(data, depth_coord, linewidth=1.2, label=lbl)
        self._lines.append(line)
        self._ax.legend(fontsize=9)
        self.fig.canvas.draw_idle()

    def update_data(self, data, **kwargs):
        """Update the primary profile data."""
        if self.closed or not self._lines:
            return
        self._lines[0].set_xdata(data)
        self._ax.relim()
        self._ax.autoscale_view(scalex=True, scaley=False)
        self.fig.canvas.draw_idle()
