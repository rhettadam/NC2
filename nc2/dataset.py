"""
NetCDF dataset wrapper with lazy loading, automatic dimension classification,
and metadata extraction. This is the single point of contact with the file.
"""

import os
import numpy as np
import netCDF4 as nc

from .constants import (
    LAT_NAMES, LON_NAMES, TIME_NAMES, DEPTH_NAMES,
    TIME_UNITS_PATTERNS, DEPTH_UNITS, STANDARD_NAMES, AXIS_ATTRS,
    SUPPORTED_EXTENSIONS,
)


class VariableInfo:
    """Lightweight metadata container for a single NetCDF variable."""

    __slots__ = ("name", "shape", "dimensions", "units", "long_name", "dtype")

    def __init__(self, name, shape, dimensions, units, long_name, dtype):
        self.name = name
        self.shape = shape
        self.dimensions = dimensions
        self.units = units
        self.long_name = long_name
        self.dtype = dtype

    def __repr__(self):
        return f"<Var '{self.name}' {self.shape} [{self.units}]>"


class Dataset:
    """
    Wraps a netCDF4.Dataset and provides:
      - Automatic classification of dimensions (time, depth, lat, lon)
      - Lazy coordinate array loading (loaded once on first access)
      - Variable metadata without loading data
      - Direct slice access via variable references
    """

    def __init__(self, filepath):
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        ext = os.path.splitext(filepath)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file extension '{ext}'. "
                f"Supported: {SUPPORTED_EXTENSIONS}"
            )

        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self._ds = nc.Dataset(filepath, mode="r")

        # Dimension classification results
        self.time_dim = None
        self.depth_dim = None
        self.lat_dim = None
        self.lon_dim = None

        # Coordinate arrays (loaded lazily)
        self._coords = {}

        # Run classification
        self._classify_dimensions()

    def close(self):
        """Close the underlying netCDF4 dataset."""
        if self._ds is not None:
            self._ds.close()
            self._ds = None

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------
    # Dimension classification
    # ------------------------------------------------------------------

    def _classify_dimensions(self):
        """
        Identify which dimensions correspond to time, depth, lat, and lon.
        Uses a priority system: axis attribute > standard_name > name matching > units.
        """
        for dim_name, dim in self._ds.dimensions.items():
            var = self._ds.variables.get(dim_name)
            role = self._identify_role(dim_name, var)

            if role == "time" and self.time_dim is None:
                self.time_dim = dim_name
            elif role == "depth" and self.depth_dim is None:
                self.depth_dim = dim_name
            elif role == "lat" and self.lat_dim is None:
                self.lat_dim = dim_name
            elif role == "lon" and self.lon_dim is None:
                self.lon_dim = dim_name

        # Second pass: check variables that are not dimensions (2D coords, etc.)
        # but only fill in gaps
        for var_name, var in self._ds.variables.items():
            if var_name in self._ds.dimensions:
                continue
            role = self._identify_role(var_name, var)
            if role == "lat" and self.lat_dim is None and var.ndim == 1:
                self.lat_dim = var_name
            elif role == "lon" and self.lon_dim is None and var.ndim == 1:
                self.lon_dim = var_name

    def _identify_role(self, name, var):
        """
        Determine if a dimension/variable is time, depth, lat, or lon.
        Returns one of: 'time', 'depth', 'lat', 'lon', or None.
        """
        # Check axis attribute first (strongest signal per CF conventions)
        if var is not None:
            axis = getattr(var, "axis", "").upper()
            if axis == AXIS_ATTRS["time"]:
                return "time"
            if axis == AXIS_ATTRS["depth"]:
                return "depth"
            if axis == AXIS_ATTRS["lat"]:
                return "lat"
            if axis == AXIS_ATTRS["lon"]:
                return "lon"

            # Check standard_name attribute
            std_name = getattr(var, "standard_name", "").lower()
            for role, names in STANDARD_NAMES.items():
                if std_name in names:
                    return role

            # Check units for time
            units = getattr(var, "units", "").lower()
            if any(pattern in units for pattern in TIME_UNITS_PATTERNS):
                return "time"

            # Check units for depth
            if units in DEPTH_UNITS:
                return "depth"

        # Fall back to name matching
        name_lower = name.lower()
        if name_lower in TIME_NAMES:
            return "time"
        if name_lower in DEPTH_NAMES:
            return "depth"
        if name_lower in LAT_NAMES:
            return "lat"
        if name_lower in LON_NAMES:
            return "lon"

        return None

    # ------------------------------------------------------------------
    # Coordinate access (lazy-loaded, cached)
    # ------------------------------------------------------------------

    def get_coord(self, dim_name):
        """
        Get the coordinate array for a classified dimension.
        Loads from file on first access, then caches in memory.
        """
        if dim_name is None:
            return None

        if dim_name not in self._coords:
            var = self._ds.variables.get(dim_name)
            if var is not None:
                self._coords[dim_name] = var[:]
            else:
                # No coordinate variable, return indices
                size = len(self._ds.dimensions[dim_name])
                self._coords[dim_name] = np.arange(size)

        return self._coords[dim_name]

    @property
    def lat(self):
        """Latitude coordinate array."""
        return self.get_coord(self.lat_dim)

    @property
    def lon(self):
        """Longitude coordinate array."""
        return self.get_coord(self.lon_dim)

    @property
    def time_values(self):
        """Raw time coordinate array (numeric)."""
        return self.get_coord(self.time_dim)

    @property
    def depth_values(self):
        """Depth/level coordinate array."""
        return self.get_coord(self.depth_dim)

    @property
    def time_dates(self):
        """Time coordinate converted to datetime objects."""
        if self.time_dim is None:
            return None

        var = self._ds.variables.get(self.time_dim)
        if var is None:
            return None

        units = getattr(var, "units", None)
        calendar = getattr(var, "calendar", "standard")

        if units is None:
            return self.time_values

        try:
            return nc.num2date(var[:], units=units, calendar=calendar)
        except Exception:
            return self.time_values

    @property
    def num_times(self):
        """Number of time steps, or 0 if no time dimension."""
        if self.time_dim is None:
            return 0
        return len(self._ds.dimensions[self.time_dim])

    @property
    def num_depths(self):
        """Number of depth levels, or 0 if no depth dimension."""
        if self.depth_dim is None:
            return 0
        return len(self._ds.dimensions[self.depth_dim])

    # ------------------------------------------------------------------
    # Variable metadata
    # ------------------------------------------------------------------

    @property
    def variables(self):
        """
        List of VariableInfo for all data variables (excludes pure coordinates).
        A variable is considered 'data' if it has 2+ dimensions or is not
        identified as a coordinate.
        """
        coord_names = {self.time_dim, self.depth_dim, self.lat_dim, self.lon_dim}
        result = []
        for name, var in self._ds.variables.items():
            if name in coord_names:
                continue
            # Skip 0-dimensional scalars and bounds variables
            if var.ndim == 0:
                continue
            info = VariableInfo(
                name=name,
                shape=var.shape,
                dimensions=var.dimensions,
                units=getattr(var, "units", ""),
                long_name=getattr(var, "long_name", name),
                dtype=var.dtype,
            )
            result.append(info)
        return result

    @property
    def all_variable_names(self):
        """Names of all data variables."""
        return [v.name for v in self.variables]

    def get_variable(self, name):
        """Get the raw netCDF4 variable reference (no data loaded)."""
        return self._ds.variables[name]

    def get_variable_info(self, name):
        """Get VariableInfo for a specific variable."""
        var = self._ds.variables[name]
        return VariableInfo(
            name=name,
            shape=var.shape,
            dimensions=var.dimensions,
            units=getattr(var, "units", ""),
            long_name=getattr(var, "long_name", name),
            dtype=var.dtype,
        )

    # ------------------------------------------------------------------
    # Manual dimension role override
    # ------------------------------------------------------------------

    def set_dim_role(self, dim_name, role):
        """
        Manually assign a dimension to a role. Pass role=None to mark
        as unassigned. Clears the old assignment for that role and
        invalidates cached coordinates.
        """
        # Clear any existing dimension that holds this role
        if role == "time":
            self.time_dim = dim_name
        elif role == "depth":
            self.depth_dim = dim_name
        elif role == "lat":
            self.lat_dim = dim_name
        elif role == "lon":
            self.lon_dim = dim_name
        elif role is None:
            # Unassign: if this dim was previously assigned, clear that slot
            if self.time_dim == dim_name:
                self.time_dim = None
            elif self.depth_dim == dim_name:
                self.depth_dim = None
            elif self.lat_dim == dim_name:
                self.lat_dim = None
            elif self.lon_dim == dim_name:
                self.lon_dim = None

        # Invalidate coordinate cache for this dimension
        self._coords.pop(dim_name, None)

    def get_dim_role(self, dim_name):
        """Return the current role string for a dimension, or None."""
        if dim_name == self.time_dim:
            return "time"
        if dim_name == self.depth_dim:
            return "depth"
        if dim_name == self.lat_dim:
            return "lat"
        if dim_name == self.lon_dim:
            return "lon"
        return None

    def get_all_dimensions(self):
        """Return ordered dict of all dimensions: name -> size."""
        return {name: len(dim) for name, dim in self._ds.dimensions.items()}

    def unassigned_dims(self, var_name):
        """
        Return list of (dim_name, dim_size) for dimensions of a variable
        that are not assigned to time/depth/lat/lon.
        """
        var = self._ds.variables[var_name]
        assigned = {self.time_dim, self.depth_dim, self.lat_dim, self.lon_dim}
        result = []
        for dim_name in var.dimensions:
            if dim_name not in assigned:
                size = len(self._ds.dimensions[dim_name])
                result.append((dim_name, size))
        return result

    # ------------------------------------------------------------------
    # Dimension role lookup for a specific variable
    # ------------------------------------------------------------------

    def get_var_dim_indices(self, var_name):
        """
        For a variable, return a dict mapping role -> axis index.
        Example: {'time': 0, 'depth': 1, 'lat': 2, 'lon': 3}
        Only includes dimensions that are classified.
        """
        var = self._ds.variables[var_name]
        dims = var.dimensions
        result = {}
        for i, d in enumerate(dims):
            if d == self.time_dim:
                result["time"] = i
            elif d == self.depth_dim:
                result["depth"] = i
            elif d == self.lat_dim:
                result["lat"] = i
            elif d == self.lon_dim:
                result["lon"] = i
        return result

    def has_geo_coords(self, var_name):
        """Check if a variable has both lat and lon dimensions."""
        var = self._ds.variables[var_name]
        dims = set(var.dimensions)
        return (
            self.lat_dim is not None
            and self.lon_dim is not None
            and self.lat_dim in dims
            and self.lon_dim in dims
        )

    # ------------------------------------------------------------------
    # Global attributes
    # ------------------------------------------------------------------

    @property
    def global_attrs(self):
        """Dictionary of global file attributes."""
        return {attr: self._ds.getncattr(attr) for attr in self._ds.ncattrs()}

    @property
    def dimensions_info(self):
        """Dict of dimension_name -> size."""
        return {name: len(dim) for name, dim in self._ds.dimensions.items()}
