"""
Geographic helpers for cartopy map plots.

Handles both common longitude conventions ([0, 360] and [-180, 180]) without
requiring the file to use one or the other. Cartopy's set_extent + pcolormesh
can collapse the viewport to a thin strip when given near-global lon bounds
(especially [0, 360] with margins past 360, or [-180, 180] on some versions);
we detect that case and use set_global() instead.
"""

import numpy as np


# Longitude span at or above this is treated as global (ERSST is ~358°).
_GLOBAL_LON_SPAN = 300.0


def _get_cartopy():
    import cartopy.crs as ccrs
    return ccrs


def lon_lat_bounds(lon, lat):
    """Return (lon_min, lon_max, lat_min, lat_max) as floats."""
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    return (
        float(np.nanmin(lon)),
        float(np.nanmax(lon)),
        float(np.nanmin(lat)),
        float(np.nanmax(lat)),
    )


def is_global_longitude(lon):
    """True if longitude values span nearly the full globe."""
    lon = np.asarray(lon, dtype=float)
    return float(np.nanmax(lon) - np.nanmin(lon)) >= _GLOBAL_LON_SPAN


def ensure_increasing_y(data, lat, lon=None):
    """
    If 1D Y/lat coordinates decrease with index, flip data (and lat)
    so maps/images are oriented south→north (ncview invert_physical).

    For 2D lat, flips rows when the column-mean latitude decreases.
    Returns (data, lat, lon) — lon unchanged unless 2D and rows flipped.
    """
    data = np.ma.array(data)
    lat = np.asarray(lat)
    lon_out = lon

    if lat.ndim == 1 and lat.size > 1:
        if float(lat[0]) > float(lat[-1]):
            lat = lat[::-1].copy()
            data = data[::-1, ...]
    elif lat.ndim == 2 and lat.shape[0] > 1:
        col_mean = np.nanmean(lat, axis=1)
        if float(col_mean[0]) > float(col_mean[-1]):
            lat = lat[::-1, :].copy()
            data = data[::-1, ...]
            if lon is not None:
                lon_arr = np.asarray(lon)
                if lon_arr.ndim == 2:
                    lon_out = lon_arr[::-1, :].copy()

    return data, lat, lon_out


def apply_geo_extent(ax, lon, lat, extent=None):
    """
    Apply map extent after data has been drawn.

    Must be called *after* pcolormesh/contourf/etc. Cartopy may reset xlim
    when plotting transformed data; setting extent afterward keeps both
    [0, 360] and [-180, 180] grids displaying correctly.

    Args:
        ax: cartopy GeoAxes
        lon, lat: coordinate arrays used for the plot
        extent: optional explicit (west, east, south, north) in PlateCarree
                degrees; when None, inferred from lon/lat
    """
    ccrs = _get_cartopy()

    if extent is not None:
        ax.set_extent(list(extent), crs=ccrs.PlateCarree())
        return

    lon_min, lon_max, lat_min, lat_max = lon_lat_bounds(lon, lat)
    lon_span = lon_max - lon_min
    lat_span = lat_max - lat_min

    if lon_span >= _GLOBAL_LON_SPAN:
        # Avoid set_extent collapse for global 0–360 or ±180 grids.
        ax.set_global()
        if lat_span < 160.0:
            pad = max(lat_span * 0.02, 1.0)
            south = max(lat_min - pad, -90.0)
            north = min(lat_max + pad, 90.0)
            try:
                ax.set_extent([-180.0, 180.0, south, north], crs=ccrs.PlateCarree())
            except (ValueError, TypeError):
                pass
        return

    pad_lon = max(lon_span * 0.02, 0.5)
    pad_lat = max(lat_span * 0.02, 0.5)
    west = lon_min - pad_lon
    east = lon_max + pad_lon
    south = max(lat_min - pad_lat, -90.0)
    north = min(lat_max + pad_lat, 90.0)

    # Regional data stored in [0, 360]: convert a contiguous box to [-180, 180]
    # so PlateCarree set_extent does not wrap oddly when east > 180.
    if lon_min >= 0.0 and lon_max <= 360.0 and lon_max > 180.0:
        west_c = west - 360.0 if west > 180.0 else west
        east_c = east - 360.0 if east > 180.0 else east
        if west_c < east_c:
            west, east = west_c, east_c

    ax.set_extent([west, east, south, north], crs=ccrs.PlateCarree())
