"""
NetCDF dataset wrapper with lazy loading, automatic dimension classification,
NetCDF-4 group walking, CF 2D coordinates, and ncview-style axis fallbacks.
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
      - Recursive NetCDF-4 group discovery (qualified var names)
      - Automatic classification of dimensions (time, depth, lat, lon)
      - Position-based Y/X/T fallback when names are missing
      - CF ``coordinates`` 2D lat/lon (curvilinear) support
      - Lazy coordinate array loading with index fallback
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

        # Dimension classification results (global / root-preferred names)
        self.time_dim = None
        self.depth_dim = None
        self.lat_dim = None
        self.lon_dim = None

        # Coordinate arrays (loaded lazily): key = (group_path, dim_name)
        self._coords = {}

        # Group / variable index: qualified_name -> (group, local_name)
        self._var_index = {}
        # dim_key -> (group, local_name, dim_obj); dim_key is qualified or local
        self._dim_index = {}
        # Variables referenced by a ``bounds`` attribute (skip as displayable)
        self._bounds_targets = set()
        # Cached CF 2D lat/lon per data variable
        self._cf_2d_cache = {}
        # Group path list for info panel
        self.group_paths = []

        self._index_groups()
        self._collect_bounds_targets()
        self._classify_dimensions()

    def close(self):
        """Close the underlying netCDF4 dataset."""
        ds = getattr(self, "_ds", None)
        if ds is not None:
            try:
                ds.close()
            except Exception:
                pass
            self._ds = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------
    # Group indexing
    # ------------------------------------------------------------------

    def _index_groups(self):
        """Recursively register variables and dimensions from all groups."""
        self._var_index.clear()
        self._dim_index.clear()
        self.group_paths = []
        self._walk_group(self._ds, "")

    def _walk_group(self, group, path):
        if path:
            self.group_paths.append(path)

        for dim_name, dim in group.dimensions.items():
            qname = f"{path}/{dim_name}" if path else dim_name
            self._dim_index[qname] = (group, dim_name, dim)
            # Prefer first registration for unqualified short name
            if dim_name not in self._dim_index:
                self._dim_index[dim_name] = (group, dim_name, dim)

        for var_name in group.variables:
            qname = f"{path}/{var_name}" if path else var_name
            self._var_index[qname] = (group, var_name)

        for gname, subgroup in group.groups.items():
            subpath = f"{path}/{gname}" if path else gname
            self._walk_group(subgroup, subpath)

    def _collect_bounds_targets(self):
        """Collect names of variables that are CF bounds auxiliaries."""
        self._bounds_targets = set()
        for qname, (group, local) in self._var_index.items():
            var = group.variables[local]
            bounds = getattr(var, "bounds", None)
            if bounds:
                self._bounds_targets.add(str(bounds))
                if group.path not in (None, "/", ""):
                    # Also qualify relative to this group when possible
                    gpath = group.path.strip("/")
                    if gpath:
                        self._bounds_targets.add(f"{gpath}/{bounds}")

    def _var_group(self, qname):
        group, _ = self._var_index[qname]
        return group

    def _find_var_in_group_or_parents(self, group, name):
        """Resolve a variable name walking from group up to root."""
        g = group
        while g is not None:
            if name in g.variables:
                return g.variables[name]
            g = g.parent if hasattr(g, "parent") else None
        # Absolute qualified lookup
        if name in self._var_index:
            grp, local = self._var_index[name]
            return grp.variables[local]
        return None

    def _dim_size(self, dim_name, group=None):
        """Size of a dimension, searching group then global index."""
        if group is not None and dim_name in group.dimensions:
            return len(group.dimensions[dim_name])
        entry = self._dim_index.get(dim_name)
        if entry is not None:
            return len(entry[2])
        if dim_name in self._ds.dimensions:
            return len(self._ds.dimensions[dim_name])
        raise KeyError(f"Dimension not found: {dim_name}")

    # ------------------------------------------------------------------
    # Dimension classification
    # ------------------------------------------------------------------

    def _classify_dimensions(self):
        """
        Identify which dimensions correspond to time, depth, lat, and lon.
        Uses axis attribute > standard_name > units > name matching.
        """
        # Prefer root dimensions first for global role slots
        for dim_name, dim in self._ds.dimensions.items():
            var = self._ds.variables.get(dim_name)
            role = self._identify_role(dim_name, var)
            self._assign_role(role, dim_name)

        # Then all indexed dims (including groups) to fill gaps
        for qname, (group, local, _dim) in list(self._dim_index.items()):
            if "/" not in qname and qname in self._ds.dimensions:
                continue  # already handled root
            var = group.variables.get(local)
            role = self._identify_role(local, var)
            # Only assign global slots from short names when empty
            if "/" not in qname:
                self._assign_role(role, qname)

        # 1D non-dimension coordinate variables
        for qname, (group, local) in self._var_index.items():
            if local in group.dimensions:
                continue
            var = group.variables[local]
            if var.ndim != 1:
                continue
            role = self._identify_role(local, var)
            if role == "lat" and self.lat_dim is None:
                self.lat_dim = local
            elif role == "lon" and self.lon_dim is None:
                self.lon_dim = local

    def _assign_role(self, role, dim_name):
        if role == "time" and self.time_dim is None:
            self.time_dim = dim_name
        elif role == "depth" and self.depth_dim is None:
            self.depth_dim = dim_name
        elif role == "lat" and self.lat_dim is None:
            self.lat_dim = dim_name
        elif role == "lon" and self.lon_dim is None:
            self.lon_dim = dim_name

    def _identify_role(self, name, var):
        """
        Determine if a dimension/variable is time, depth, lat, or lon.
        Returns one of: 'time', 'depth', 'lat', 'lon', or None.
        """
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

            std_name = getattr(var, "standard_name", "").lower()
            for role, names in STANDARD_NAMES.items():
                if std_name in names:
                    return role

            units = getattr(var, "units", "").lower()
            if any(pattern in units for pattern in TIME_UNITS_PATTERNS):
                return "time"

            if units in DEPTH_UNITS:
                return "depth"

            # Lat/lon units: accept both [-180,180] and [0,360]
            if "degree" in units and var.ndim >= 1 and var.size > 0:
                name_l = name.lower()
                looks_lat = (
                    name_l.startswith("lat")
                    or "north" in units
                    or "south" in units
                )
                looks_lon = (
                    name_l.startswith("lon")
                    or "east" in units
                    or "west" in units
                )
                if looks_lat or looks_lon:
                    try:
                        v0 = float(np.asarray(var).flat[0])
                        v1 = float(np.asarray(var).flat[-1])
                        vmin, vmax = (v0, v1) if v0 <= v1 else (v1, v0)
                    except Exception:
                        vmin = vmax = None
                    if vmin is not None:
                        if looks_lat and vmax < 90.01 and vmin > -90.01:
                            return "lat"
                        if looks_lon and vmax < 360.01 and vmin > -180.01:
                            return "lon"

        name_lower = name.lower().split("/")[-1]
        if name_lower in TIME_NAMES:
            return "time"
        if name_lower in DEPTH_NAMES:
            return "depth"
        if name_lower in LAT_NAMES:
            return "lat"
        if name_lower in LON_NAMES:
            return "lon"

        return None

    def _role_for_dim(self, dim_name, group):
        """Resolve role for a dimension in a group context."""
        local = dim_name.split("/")[-1]
        # Match global classification by basename
        if local == self.time_dim or dim_name == self.time_dim:
            return "time"
        if local == self.depth_dim or dim_name == self.depth_dim:
            return "depth"
        if local == self.lat_dim or dim_name == self.lat_dim:
            return "lat"
        if local == self.lon_dim or dim_name == self.lon_dim:
            return "lon"

        var = None
        if group is not None and local in group.variables:
            var = group.variables[local]
        else:
            var = self._find_var_in_group_or_parents(group or self._ds, local)
        return self._identify_role(local, var)

    # ------------------------------------------------------------------
    # Coordinate access (lazy-loaded, cached)
    # ------------------------------------------------------------------

    def get_coord(self, dim_name, group=None):
        """
        Get the coordinate array for a dimension.
        Loads from file on first access; falls back to indices.
        """
        if dim_name is None:
            return None

        local = dim_name.split("/")[-1]
        gpath = ""
        if group is not None:
            gpath = (group.path or "").strip("/")
        cache_key = (gpath, local)

        if cache_key not in self._coords:
            var = None
            if group is not None:
                var = self._find_var_in_group_or_parents(group, local)
            if var is None:
                var = self._ds.variables.get(local)
            if var is not None and var.ndim == 1:
                self._coords[cache_key] = np.asarray(var[:])
            else:
                size = self._dim_size(local, group=group)
                self._coords[cache_key] = np.arange(size)

        return self._coords[cache_key]

    @property
    def lat(self):
        """Latitude coordinate array (1D global classification)."""
        return self.get_coord(self.lat_dim)

    @property
    def lon(self):
        """Longitude coordinate array (1D global classification)."""
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

        var = self._find_var_in_group_or_parents(self._ds, self.time_dim)
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
        try:
            return self._dim_size(self.time_dim)
        except KeyError:
            return 0

    @property
    def num_depths(self):
        """Number of depth levels, or 0 if no depth dimension."""
        if self.depth_dim is None:
            return 0
        try:
            return self._dim_size(self.depth_dim)
        except KeyError:
            return 0

    # ------------------------------------------------------------------
    # Displayable variables (ncview-style filter)
    # ------------------------------------------------------------------

    def _is_displayable(self, qname, group, local, var):
        """Ncview-like rules for which variables appear in the UI."""
        if local in group.dimensions:
            return False
        if var.ndim == 0:
            return False
        if var.size <= 1:
            return False
        if local.endswith("_bnds") or local.endswith("_bounds"):
            return False
        if local in self._bounds_targets or qname in self._bounds_targets:
            return False

        # At least one scannable dimension (first dim always, or size > 1)
        if not any(i == 0 or s > 1 for i, s in enumerate(var.shape)):
            return False
        return True

    @property
    def variables(self):
        """List of VariableInfo for displayable data variables."""
        result = []
        for qname, (group, local) in sorted(self._var_index.items()):
            var = group.variables[local]
            if not self._is_displayable(qname, group, local, var):
                continue
            info = VariableInfo(
                name=qname,
                shape=var.shape,
                dimensions=var.dimensions,
                units=getattr(var, "units", ""),
                long_name=getattr(var, "long_name", local),
                dtype=var.dtype,
            )
            result.append(info)
        return result

    @property
    def all_variable_names(self):
        """Names of all displayable data variables (qualified)."""
        return [v.name for v in self.variables]

    def get_variable(self, name):
        """Get the raw netCDF4 variable reference (no data loaded)."""
        if name not in self._var_index:
            # Fallback: root-only name
            return self._ds.variables[name]
        group, local = self._var_index[name]
        return group.variables[local]

    def get_variable_info(self, name):
        """Get VariableInfo for a specific variable."""
        var = self.get_variable(name)
        local = name.split("/")[-1]
        return VariableInfo(
            name=name,
            shape=var.shape,
            dimensions=var.dimensions,
            units=getattr(var, "units", ""),
            long_name=getattr(var, "long_name", local),
            dtype=var.dtype,
        )

    # ------------------------------------------------------------------
    # Axis inference (roles + ncview position fallback)
    # ------------------------------------------------------------------

    def infer_var_axes(self, var_name):
        """
        Map roles -> axis index for a variable.

        Uses classified CF/name roles when present on the var's dims.
        Falls back to ncview-style position rules:
          - last dim = lon/X, second-to-last = lat/Y
          - first scannable unused dim = time when >= 3 dims
        """
        var = self.get_variable(var_name)
        dims = list(var.dimensions)
        group = self._var_group(var_name) if var_name in self._var_index else self._ds
        result = {}

        for i, d in enumerate(dims):
            role = self._role_for_dim(d, group)
            if role and role not in result:
                result[role] = i

        n = len(dims)
        used = set(result.values())

        if "lon" not in result and "lat" not in result and n >= 2:
            result["lat"] = n - 2
            result["lon"] = n - 1
            used = set(result.values())
        else:
            if "lon" not in result and n >= 1:
                # Prefer last unused axis
                for i in range(n - 1, -1, -1):
                    if i not in used:
                        result["lon"] = i
                        used.add(i)
                        break
            if "lat" not in result and n >= 2:
                for i in range(n - 1, -1, -1):
                    if i not in used:
                        result["lat"] = i
                        used.add(i)
                        break

        if "time" not in result and n >= 3:
            for i, _d in enumerate(dims):
                size = var.shape[i]
                if i not in used and (i == 0 or size > 1):
                    result["time"] = i
                    break

        return result

    def get_var_dim_indices(self, var_name):
        """Role -> axis index (includes position fallback)."""
        return self.infer_var_axes(var_name)

    # ------------------------------------------------------------------
    # CF 2D coordinates / geographic detection
    # ------------------------------------------------------------------

    def get_cf_2d_lat_lon(self, var_name):
        """
        Return (lat2d, lon2d) from CF ``coordinates`` if present, else (None, None).
        Arrays are cached per variable.
        """
        if var_name in self._cf_2d_cache:
            return self._cf_2d_cache[var_name]

        var = self.get_variable(var_name)
        coords_attr = getattr(var, "coordinates", None)
        lat2d = lon2d = None

        if coords_attr:
            group = self._var_group(var_name) if var_name in self._var_index else self._ds
            for tok in str(coords_attr).split():
                cvar = self._find_var_in_group_or_parents(group, tok)
                if cvar is None or cvar.ndim != 2:
                    continue
                role = self._identify_role(tok, cvar)
                if role == "lat" and lat2d is None:
                    lat2d = np.asarray(cvar[:])
                elif role == "lon" and lon2d is None:
                    lon2d = np.asarray(cvar[:])

        self._cf_2d_cache[var_name] = (lat2d, lon2d)
        return lat2d, lon2d

    def get_spatial_coords(self, var_name):
        """
        Return (lat, lon) for plotting — 1D or 2D arrays.
        Falls back to index vectors for the inferred Y/X dims.
        """
        lat2d, lon2d = self.get_cf_2d_lat_lon(var_name)
        if lat2d is not None and lon2d is not None:
            return lat2d, lon2d

        axes = self.infer_var_axes(var_name)
        var = self.get_variable(var_name)
        group = self._var_group(var_name) if var_name in self._var_index else self._ds
        lat = lon = None
        if "lat" in axes:
            lat = self.get_coord(var.dimensions[axes["lat"]], group=group)
        if "lon" in axes:
            lon = self.get_coord(var.dimensions[axes["lon"]], group=group)
        return lat, lon

    def _coords_look_geographic(self, lat, lon):
        """Heuristic: values look like lat/lon in degrees."""
        if lat is None or lon is None:
            return False
        try:
            lat_min = float(np.nanmin(lat))
            lat_max = float(np.nanmax(lat))
            lon_min = float(np.nanmin(lon))
            lon_max = float(np.nanmax(lon))
        except Exception:
            return False
        if not (lat_max <= 90.01 and lat_min >= -90.01):
            return False
        if not (lon_max <= 360.01 and lon_min >= -180.01):
            return False
        # Degenerate index-like 0..n-1 over tiny ranges still OK if within geo box
        return True

    def has_geo_coords(self, var_name):
        """
        True if this variable can be plotted on a geographic map.
        Supports classic 1D lat/lon dims and CF 2D auxiliary coordinates.
        Position-fallback Y/X axes alone are not treated as geographic unless
        the coordinate variables have degree units.
        """
        lat2d, lon2d = self.get_cf_2d_lat_lon(var_name)
        if lat2d is not None and lon2d is not None:
            return self._coords_look_geographic(lat2d, lon2d)

        axes = self.infer_var_axes(var_name)
        if "lat" not in axes or "lon" not in axes:
            return False

        var = self.get_variable(var_name)
        group = self._var_group(var_name) if var_name in self._var_index else self._ds
        lat_dim = var.dimensions[axes["lat"]]
        lon_dim = var.dimensions[axes["lon"]]
        lat_role = self._role_for_dim(lat_dim, group)
        lon_role = self._role_for_dim(lon_dim, group)
        lat, lon = self.get_spatial_coords(var_name)
        if lat is None or lon is None:
            return False

        if lat_role == "lat" and lon_role == "lon":
            return self._coords_look_geographic(lat, lon)

        # Position-inferred axes: only geo if coords declare degree units
        lat_var = self._find_var_in_group_or_parents(group, lat_dim)
        lon_var = self._find_var_in_group_or_parents(group, lon_dim)
        lat_units = getattr(lat_var, "units", "").lower() if lat_var else ""
        lon_units = getattr(lon_var, "units", "").lower() if lon_var else ""
        if "degree" in lat_units and "degree" in lon_units:
            return self._coords_look_geographic(lat, lon)

        return False

    def var_ndim(self, var_name):
        """Number of dimensions of a variable."""
        return self.get_variable(var_name).ndim

    def spatial_axis_names(self, var_name):
        """Return (y_dim_name, x_dim_name) for inferred spatial axes."""
        axes = self.infer_var_axes(var_name)
        var = self.get_variable(var_name)
        y = var.dimensions[axes["lat"]] if "lat" in axes else None
        x = var.dimensions[axes["lon"]] if "lon" in axes else None
        return y, x

    # ------------------------------------------------------------------
    # Manual dimension role override
    # ------------------------------------------------------------------

    def set_dim_role(self, dim_name, role):
        """
        Manually assign a dimension to a role. Pass role=None to mark
        as unassigned. Clears the old assignment for that role and
        invalidates cached coordinates.
        """
        if role == "time":
            self.time_dim = dim_name
        elif role == "depth":
            self.depth_dim = dim_name
        elif role == "lat":
            self.lat_dim = dim_name
        elif role == "lon":
            self.lon_dim = dim_name
        elif role is None:
            if self.time_dim == dim_name:
                self.time_dim = None
            elif self.depth_dim == dim_name:
                self.depth_dim = None
            elif self.lat_dim == dim_name:
                self.lat_dim = None
            elif self.lon_dim == dim_name:
                self.lon_dim = None

        # Invalidate related caches
        keys = [k for k in self._coords if k[1] == dim_name or k[1] == dim_name.split("/")[-1]]
        for k in keys:
            self._coords.pop(k, None)
        self._cf_2d_cache.clear()

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
        result = {}
        seen = set()
        for _qname, (group, local, dim) in sorted(self._dim_index.items()):
            key = (id(group), local)
            if key in seen:
                continue
            seen.add(key)
            gpath = (getattr(group, "path", None) or "").strip("/")
            name = f"{gpath}/{local}" if gpath else local
            result[name] = len(dim)
        return result

    def unassigned_dims(self, var_name):
        """
        Return list of (dim_name, dim_size) for dimensions of a variable
        that are not assigned to time/depth/lat/lon via inference.
        """
        var = self.get_variable(var_name)
        axes = self.infer_var_axes(var_name)
        used_indices = set(axes.values())
        group = self._var_group(var_name) if var_name in self._var_index else self._ds
        result = []
        for i, dim_name in enumerate(var.dimensions):
            if i not in used_indices:
                size = self._dim_size(dim_name, group=group)
                result.append((dim_name, size))
        return result

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
        return self.get_all_dimensions()
