"""
Plot configuration dataclass. Holds every user-adjustable plot parameter
in a single structure that gets passed around the system.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Tuple

from ..constants import DEFAULTS


@dataclass
class PlotConfig:
    """
    Complete specification of how a plot should look. Passed to plot
    constructors and used to detect when a structural rebuild is needed
    vs. a simple data swap.
    """

    # Plot type and color
    plot_type: str = DEFAULTS["plot_type"]
    colormap: str = DEFAULTS["colormap"]
    reverse_cmap: bool = DEFAULTS["reverse_cmap"]
    vmin: Optional[float] = DEFAULTS["vmin"]
    vmax: Optional[float] = DEFAULTS["vmax"]
    symmetric: bool = DEFAULTS["symmetric"]

    # Normalization
    norm_type: str = DEFAULTS["norm_type"]
    norm_vmin: Optional[float] = DEFAULTS["norm_vmin"]
    norm_vmax: Optional[float] = DEFAULTS["norm_vmax"]
    norm_linthresh: float = DEFAULTS["norm_linthresh"]
    norm_gamma: float = DEFAULTS["norm_gamma"]

    # Transparency
    alpha: float = DEFAULTS["alpha"]

    # Map projection and features
    projection: str = DEFAULTS["projection"]
    extent: Optional[Tuple[float, float, float, float]] = DEFAULTS["extent"]
    gridlines: bool = DEFAULTS["gridlines"]
    gridline_alpha: float = DEFAULTS["gridline_alpha"]
    coastlines: bool = DEFAULTS["coastlines"]
    land: bool = DEFAULTS["land"]
    ocean: bool = DEFAULTS["ocean"]
    borders: bool = DEFAULTS["borders"]
    rivers: bool = DEFAULTS["rivers"]

    # Colorbar
    colorbar_orientation: str = DEFAULTS["colorbar_orientation"]
    colorbar_shrink: float = DEFAULTS["colorbar_shrink"]
    colorbar_label: str = DEFAULTS["colorbar_label"]
    colorbar_extend: str = DEFAULTS["colorbar_extend"]

    # Labels
    title: str = DEFAULTS["title"]
    xlabel: str = DEFAULTS["xlabel"]
    ylabel: str = DEFAULTS["ylabel"]

    # Contour parameters
    contour_levels: int = DEFAULTS["contour_levels"]
    contour_linewidths: float = DEFAULTS["contour_linewidths"]
    contour_linestyles: str = DEFAULTS["contour_linestyles"]

    # Quiver parameters
    quiver_scale: float = DEFAULTS["quiver_scale"]
    quiver_step: int = DEFAULTS["quiver_step"]
    quiver_pivot: str = DEFAULTS["quiver_pivot"]
    quiver_headwidth: float = DEFAULTS["quiver_headwidth"]
    quiver_headlength: float = DEFAULTS["quiver_headlength"]

    # Streamplot parameters
    streamplot_density: float = DEFAULTS["streamplot_density"]
    streamplot_linewidth: float = DEFAULTS["streamplot_linewidth"]
    streamplot_arrowsize: float = DEFAULTS["streamplot_arrowsize"]

    # Imshow parameters
    interpolation: str = DEFAULTS["interpolation"]
    aspect: str = DEFAULTS["aspect"]

    # Export
    dpi: int = DEFAULTS["dpi"]

    def to_dict(self):
        return asdict(self)

    def structural_fields(self):
        """
        Fields that require a full plot rebuild when changed.
        """
        return (
            self.plot_type,
            self.projection,
            self.extent,
            self.gridlines,
            self.coastlines,
            self.land,
            self.ocean,
            self.borders,
            self.rivers,
            self.colorbar_orientation,
            self.norm_type,
            self.aspect,
        )

    def needs_rebuild(self, other):
        if other is None:
            return True
        return self.structural_fields() != other.structural_fields()

    @classmethod
    def from_dict(cls, d):
        """Create a PlotConfig from a dictionary, ignoring unknown keys."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)
