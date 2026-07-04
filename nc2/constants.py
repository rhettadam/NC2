"""
Centralized constants for NC2: projection mappings, coordinate detection
heuristics, colormap categories, and default configuration values.
"""


# ---------------------------------------------------------------------------
# Projection registry
# Maps user-facing names to cartopy CRS constructors.
# Loaded lazily to avoid import-time dependency on cartopy for modules that
# only need non-geo constants (cache, playback, etc.).
# ---------------------------------------------------------------------------

_PROJECTIONS = None
DEFAULT_PROJECTION = "PlateCarree"


def get_projections():
    """Return the projection name -> constructor dict, importing cartopy on first call."""
    global _PROJECTIONS
    if _PROJECTIONS is None:
        import cartopy.crs as ccrs
        _PROJECTIONS = {
            "PlateCarree": ccrs.PlateCarree,
            "Mercator": ccrs.Mercator,
            "Mollweide": ccrs.Mollweide,
            "Robinson": ccrs.Robinson,
            "Orthographic": ccrs.Orthographic,
            "LambertConformal": ccrs.LambertConformal,
            "LambertAzimuthalEqualArea": ccrs.LambertAzimuthalEqualArea,
            "AlbersEqualArea": ccrs.AlbersEqualArea,
            "TransverseMercator": ccrs.TransverseMercator,
            "AzimuthalEquidistant": ccrs.AzimuthalEquidistant,
            "Stereographic": ccrs.Stereographic,
            "NorthPolarStereo": ccrs.NorthPolarStereo,
            "SouthPolarStereo": ccrs.SouthPolarStereo,
            "Geostationary": ccrs.Geostationary,
            "Sinusoidal": ccrs.Sinusoidal,
            "InterruptedGoodeHomolosine": ccrs.InterruptedGoodeHomolosine,
            "EuroPP": ccrs.EuroPP,
            "RotatedPole": lambda: ccrs.RotatedPole(pole_longitude=180.0, pole_latitude=36.0),
        }
    return _PROJECTIONS


# Name list for the GUI dropdown (does not trigger cartopy import)
PROJECTION_NAMES = [
    "PlateCarree", "Mercator", "Mollweide", "Robinson", "Orthographic",
    "LambertConformal", "LambertAzimuthalEqualArea", "AlbersEqualArea",
    "TransverseMercator", "AzimuthalEquidistant", "Stereographic",
    "NorthPolarStereo", "SouthPolarStereo", "Geostationary", "Sinusoidal",
    "InterruptedGoodeHomolosine", "EuroPP", "RotatedPole",
]


# ---------------------------------------------------------------------------
# Coordinate detection heuristics
# Used to classify NetCDF dimensions/variables as time, depth, lat, or lon.
# ---------------------------------------------------------------------------

# Dimension/variable names that indicate latitude
LAT_NAMES = {
    "lat", "latitude", "lats", "latitudes",
    "nav_lat", "y", "yt_ocean", "yu_ocean",
    "nlat", "geolat", "lat_rho", "lat_u", "lat_v",
}

# Dimension/variable names that indicate longitude
LON_NAMES = {
    "lon", "longitude", "lons", "longitudes",
    "nav_lon", "x", "xt_ocean", "xu_ocean",
    "nlon", "geolon", "lon_rho", "lon_u", "lon_v",
}

# Dimension/variable names that indicate time
TIME_NAMES = {
    "time", "t", "times", "date", "dates",
    "ocean_time", "Time", "TIME",
}

# Dimension/variable names that indicate depth/level
DEPTH_NAMES = {
    "depth", "depths", "z", "level", "lev", "levels",
    "deptht", "depthu", "depthv", "depthw",
    "st_ocean", "sw_ocean", "z_t", "z_w",
    "sigma", "s_rho", "s_w", "eta",
    "pressure", "plev", "isobaric",
}

# Units substrings that identify time variables
TIME_UNITS_PATTERNS = (
    "since",       # "days since ...", "seconds since ...", etc.
    "day",
    "hour",
    "minute",
    "second",
)

# Units that identify depth/pressure variables
DEPTH_UNITS = {"m", "meters", "metre", "metres", "km", "dbar", "pa", "hpa", "mb"}

# Standard name attributes that identify coordinate types
STANDARD_NAMES = {
    "lat": {"latitude"},
    "lon": {"longitude"},
    "time": {"time"},
    "depth": {"depth", "altitude", "height", "air_pressure", "sea_water_pressure"},
}

# Axis attribute values (CF convention)
AXIS_ATTRS = {
    "lat": "Y",
    "lon": "X",
    "time": "T",
    "depth": "Z",
}


# ---------------------------------------------------------------------------
# Colormap categories (curated favorites for the View menu)
# ---------------------------------------------------------------------------

COLORMAPS = {
    "Sequential": [
        "viridis", "plasma", "inferno", "magma", "cividis",
        "Blues", "Greens", "Oranges", "Reds", "Purples",
        "YlOrRd", "YlGnBu", "BuPu", "GnBu", "OrRd",
    ],
    "Diverging": [
        "RdBu_r", "RdYlBu_r", "RdYlGn_r", "BrBG", "PiYG",
        "PRGn", "PuOr", "coolwarm", "bwr", "seismic",
    ],
    "Cyclic": [
        "twilight", "twilight_shifted", "hsv",
    ],
    "Qualitative": [
        "Set1", "Set2", "Set3", "tab10", "tab20",
        "Paired", "Accent", "Dark2", "Pastel1", "Pastel2",
    ],
}


def get_all_colormaps():
    """Get every registered matplotlib colormap at runtime."""
    import matplotlib.pyplot as plt
    return sorted(plt.colormaps())


# Flat curated list (for validation fallback)
ALL_COLORMAPS = [cm for group in COLORMAPS.values() for cm in group]

DEFAULT_COLORMAP = "viridis"


# ---------------------------------------------------------------------------
# Plot type options
# ---------------------------------------------------------------------------

PLOT_TYPES = [
    "pcolormesh",
    "contourf",
    "contour",
    "imshow",
    "quiver",
    "streamplot",
]

DEFAULT_PLOT_TYPE = "pcolormesh"


# ---------------------------------------------------------------------------
# Default plot configuration values
# ---------------------------------------------------------------------------

DEFAULTS = {
    "plot_type": "pcolormesh",
    "colormap": "viridis",
    "reverse_cmap": False,
    "vmin": None,
    "vmax": None,
    "symmetric": False,
    "projection": "PlateCarree",
    "extent": None,
    "gridlines": True,
    "gridline_alpha": 0.3,
    "coastlines": True,
    "land": False,
    "ocean": False,
    "borders": False,
    "rivers": False,
    "colorbar_orientation": "vertical",
    "colorbar_shrink": 0.8,
    "colorbar_label": "",
    "colorbar_extend": "neither",
    "title": "",
    "xlabel": "",
    "ylabel": "",
    "contour_levels": 20,
    "contour_linewidths": 1.0,
    "contour_linestyles": "solid",
    "quiver_scale": 1.0,
    "quiver_step": 3,
    "quiver_pivot": "middle",
    "quiver_headwidth": 3.0,
    "quiver_headlength": 5.0,
    "streamplot_density": 1.0,
    "streamplot_linewidth": 1.0,
    "streamplot_arrowsize": 1.0,
    "norm_type": "linear",
    "norm_vmin": None,
    "norm_vmax": None,
    "norm_linthresh": 1.0,
    "norm_gamma": 1.0,
    "alpha": 1.0,
    "interpolation": "nearest",
    "aspect": "auto",
    "dpi": 150,
}

# Normalization types available
NORM_TYPES = ["linear", "log", "symlog", "power"]

# Imshow interpolation methods
INTERPOLATIONS = [
    "nearest", "bilinear", "bicubic", "spline16", "spline36",
    "hanning", "hamming", "hermite", "kaiser", "quadric",
    "catrom", "gaussian", "bessel", "mitchell", "sinc", "lanczos",
]

# Colorbar extend options
COLORBAR_EXTENDS = ["neither", "both", "min", "max"]

# Aspect ratio options
ASPECT_RATIOS = ["auto", "equal"]


# ---------------------------------------------------------------------------
# Supported file extensions
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = (".nc", ".nc4", ".cdf", ".netcdf", ".hdf5", ".h5")


# ---------------------------------------------------------------------------
# Performance tuning
# ---------------------------------------------------------------------------

# Default slice cache size in megabytes (overridable via NC2_CACHE_MB env var)
DEFAULT_CACHE_MB = 512

# Playback speed bounds in milliseconds
PLAYBACK_MIN_INTERVAL_MS = 50
PLAYBACK_MAX_INTERVAL_MS = 2000
PLAYBACK_DEFAULT_INTERVAL_MS = 300
PLAYBACK_STEP_MS = 50
