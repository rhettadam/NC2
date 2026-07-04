"""
Export engine for GIF animation, static images, and batch frame export.
All rendering happens offscreen via matplotlib's Agg backend to avoid
interfering with the interactive GUI.
"""

import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import imageio.v2 as imageio

from .constants import get_projections, DEFAULT_PROJECTION
from .plots.config import PlotConfig


def _get_cartopy():
    """Lazy import of cartopy modules."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    return ccrs, cfeature


def export_gif(slicer, var_name, config, output_path,
               fps=10, frame_start=0, frame_end=None,
               loop=True, progress_callback=None):
    """
    Render an animated GIF of a variable over its time dimension.

    Args:
        slicer: Slicer instance
        var_name: variable name to animate
        config: PlotConfig controlling appearance
        output_path: full path for the output .gif file
        fps: frames per second
        frame_start: first frame index (inclusive)
        frame_end: last frame index (exclusive), None for all
        loop: whether the GIF loops
        progress_callback: optional fn(current_frame, total_frames) for progress updates

    Returns:
        The output_path on success.
    """
    ds = slicer.ds
    num_times = ds.num_times
    if num_times == 0:
        raise ValueError("Variable has no time dimension for animation.")

    if frame_end is None:
        frame_end = num_times
    frame_end = min(frame_end, num_times)
    total = frame_end - frame_start

    # Use non-interactive backend for rendering
    orig_backend = matplotlib.get_backend()
    matplotlib.use("Agg")

    frames = []
    try:
        for i, t_idx in enumerate(range(frame_start, frame_end)):
            data, lat, lon = slicer.get_spatial_slice(var_name, time_idx=t_idx)
            frame_buf = _render_frame(data, lat, lon, config, ds, var_name, t_idx)
            frames.append(frame_buf)

            if progress_callback:
                progress_callback(i + 1, total)

        # Assemble GIF
        loop_count = 0 if loop else 1
        imageio.mimsave(output_path, frames, fps=fps, loop=loop_count)

    finally:
        matplotlib.use(orig_backend)

    return output_path


def export_frame(slicer, var_name, config, output_path,
                 time_idx=None, depth_idx=None, dpi=None):
    """
    Export a single frame as a static image (PNG, SVG, PDF, etc.).
    The format is inferred from the file extension.

    Args:
        slicer: Slicer instance
        var_name: variable name
        config: PlotConfig
        output_path: file path (extension determines format)
        time_idx: time index (or None)
        depth_idx: depth index (or None)
        dpi: override DPI (uses config.dpi if None)

    Returns:
        The output_path on success.
    """
    data, lat, lon = slicer.get_spatial_slice(var_name, time_idx=time_idx, depth_idx=depth_idx)
    ds = slicer.ds
    is_geo = ds.has_geo_coords(var_name)

    fig = _create_figure(data, lat, lon, config, ds, var_name, time_idx, is_geo)
    fig.savefig(output_path, dpi=dpi or config.dpi, bbox_inches="tight")
    plt.close(fig)

    return output_path


def export_batch(slicer, var_name, config, output_dir,
                 frame_start=0, frame_end=None, fmt="png",
                 dpi=None, progress_callback=None):
    """
    Export every frame as an individual image file.

    Args:
        slicer: Slicer instance
        var_name: variable name
        config: PlotConfig
        output_dir: directory to write frames into
        frame_start: first frame index
        frame_end: last frame index (exclusive)
        fmt: image format extension (png, svg, pdf, jpg)
        dpi: override DPI
        progress_callback: optional fn(current, total)

    Returns:
        List of output file paths.
    """
    ds = slicer.ds
    num_times = ds.num_times
    if frame_end is None:
        frame_end = num_times
    frame_end = min(frame_end, num_times)
    total = frame_end - frame_start

    os.makedirs(output_dir, exist_ok=True)
    paths = []

    for i, t_idx in enumerate(range(frame_start, frame_end)):
        filename = f"{var_name}_frame_{t_idx:04d}.{fmt}"
        path = os.path.join(output_dir, filename)
        export_frame(slicer, var_name, config, path,
                     time_idx=t_idx, dpi=dpi)
        paths.append(path)

        if progress_callback:
            progress_callback(i + 1, total)

    return paths


# ---------------------------------------------------------------------------
# Internal rendering helpers
# ---------------------------------------------------------------------------

def _render_frame(data, lat, lon, config, ds, var_name, time_idx):
    """Render a single frame to an RGBA numpy array for GIF assembly."""
    is_geo = ds.has_geo_coords(var_name)
    fig = _create_figure(data, lat, lon, config, ds, var_name, time_idx, is_geo)

    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())
    # Convert RGBA to RGB (imageio GIF doesn't use alpha)
    frame = buf[:, :, :3].copy()
    plt.close(fig)

    return frame


def _create_figure(data, lat, lon, config, ds, var_name, time_idx, is_geo):
    """Create a matplotlib figure for a single spatial frame."""
    fig = plt.figure(figsize=(10, 7), dpi=config.dpi)

    if is_geo:
        ccrs, cfeature = _get_cartopy()
        proj_name = config.projection or DEFAULT_PROJECTION
        projs = get_projections()
        proj_factory = projs.get(proj_name, projs[DEFAULT_PROJECTION])
        proj = proj_factory()
        ax = fig.add_subplot(111, projection=proj)

        if config.extent:
            ax.set_extent(config.extent, crs=ccrs.PlateCarree())
        else:
            lon_min, lon_max = float(lon.min()), float(lon.max())
            lat_min, lat_max = float(lat.min()), float(lat.max())
            margin_lon = (lon_max - lon_min) * 0.02
            margin_lat = (lat_max - lat_min) * 0.02
            ax.set_extent([
                lon_min - margin_lon, lon_max + margin_lon,
                lat_min - margin_lat, lat_max + margin_lat,
            ], crs=ccrs.PlateCarree())

        if config.coastlines:
            ax.coastlines(linewidth=0.5)
        if config.land:
            ax.add_feature(cfeature.LAND, facecolor="lightgray", alpha=0.5)
        if config.ocean:
            ax.add_feature(cfeature.OCEAN, facecolor="lightblue", alpha=0.3)
        if config.borders:
            ax.add_feature(cfeature.BORDERS, linewidth=0.3)
        if config.rivers:
            ax.add_feature(cfeature.RIVERS, linewidth=0.3, edgecolor="blue")
        if config.gridlines:
            gl = ax.gridlines(draw_labels=True, alpha=config.gridline_alpha)
            gl.top_labels = False
            gl.right_labels = False
    else:
        ax = fig.add_subplot(111)

    # Color settings
    cmap = config.colormap
    if config.reverse_cmap:
        cmap = cmap + "_r"

    if config.symmetric:
        abs_max = float(np.nanmax(np.abs(data)))
        vmin, vmax = -abs_max, abs_max
    else:
        vmin = config.vmin if config.vmin is not None else float(np.nanmin(data))
        vmax = config.vmax if config.vmax is not None else float(np.nanmax(data))

    # Plot
    transform = None
    if is_geo:
        ccrs, _ = _get_cartopy()
        transform = ccrs.PlateCarree()
    kwargs = {"cmap": cmap, "vmin": vmin, "vmax": vmax, "shading": "auto",
              "alpha": config.alpha}
    if transform:
        kwargs["transform"] = transform

    mappable = ax.pcolormesh(lon, lat, data, **kwargs)

    fig.colorbar(
        mappable, ax=ax,
        orientation=config.colorbar_orientation,
        shrink=config.colorbar_shrink,
        extend=config.colorbar_extend,
        label=config.colorbar_label or ds.get_variable_info(var_name).units,
    )

    # Title with time info
    var_info = ds.get_variable_info(var_name)
    title = config.title or var_info.long_name
    if time_idx is not None and ds.time_dates is not None:
        try:
            time_label = str(ds.time_dates[time_idx])
        except (IndexError, TypeError):
            time_label = f"t={time_idx}"
        title = f"{title} - {time_label}"
    ax.set_title(title, fontsize=11)

    fig.tight_layout()
    return fig
