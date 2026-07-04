"""
Plot window manager. Tracks all open plot windows, handles creation,
batch updates during playback, and cleanup on close.
"""

import matplotlib.pyplot as plt


class PlotWindow:
    """
    Base container for a managed plot window. Subclasses (SpatialPlot,
    SectionPlot, SeriesPlot) implement the actual rendering.
    """

    def __init__(self, fig, plot_id, window_type):
        self.fig = fig
        self.plot_id = plot_id
        self.window_type = window_type
        self.closed = False

        # Hook into the window close event
        fig.canvas.mpl_connect("close_event", self._on_close)

    def _on_close(self, event):
        self.closed = True

    def update_data(self, data, **kwargs):
        """Override in subclasses to update plot data in-place."""
        raise NotImplementedError

    def refresh(self):
        """Redraw the figure without recreating it."""
        if not self.closed:
            self.fig.canvas.draw_idle()

    def destroy(self):
        """Close the matplotlib figure."""
        if not self.closed:
            try:
                plt.close(self.fig)
            except (TypeError, ValueError):
                pass
            self.closed = True


class PlotManager:
    """
    Registry of all open plot windows. Provides factory methods for
    creating new windows and batch operations for playback.
    """

    def __init__(self):
        self._windows = {}  # plot_id -> PlotWindow
        self._next_id = 1

    @property
    def open_windows(self):
        """List of currently open (non-closed) windows."""
        self._prune_closed()
        return list(self._windows.values())

    @property
    def count(self):
        """Number of open windows."""
        self._prune_closed()
        return len(self._windows)

    def register(self, window):
        """
        Add a PlotWindow to the registry. Assigns an ID if not already set.
        Returns the assigned plot_id.
        """
        if window.plot_id is None:
            window.plot_id = self._next_id
            self._next_id += 1
        self._windows[window.plot_id] = window
        return window.plot_id

    def get(self, plot_id):
        """Retrieve a window by ID, or None if closed/missing."""
        window = self._windows.get(plot_id)
        if window is not None and window.closed:
            del self._windows[plot_id]
            return None
        return window

    def next_id(self):
        """Allocate and return the next available plot ID."""
        pid = self._next_id
        self._next_id += 1
        return pid

    def update_all(self, update_fn):
        """
        Call update_fn(window) on every open window. Used during playback
        to push new frame data to all plots simultaneously.
        """
        self._prune_closed()
        for window in list(self._windows.values()):
            if not window.closed:
                try:
                    update_fn(window)
                except Exception:
                    # Don't let one bad window break playback for others
                    pass

    def close_all(self):
        """Close and deregister every open window."""
        for window in list(self._windows.values()):
            window.destroy()
        self._windows.clear()

    def _prune_closed(self):
        """Remove windows that were closed by the user."""
        dead = [pid for pid, w in self._windows.items() if w.closed]
        for pid in dead:
            del self._windows[pid]
