"""
Data extraction engine. Pulls 2D slices, cross-sections, timeseries,
and depth profiles from the dataset, routing through the cache layer.
"""

import numpy as np

from .cache import SliceCache
from .plots.geo import ensure_increasing_y


class Slicer:
    """
    Extracts data slices from a Dataset instance. All results are numpy
    masked arrays paired with their coordinate vectors. Cached transparently.
    """

    def __init__(self, dataset):
        self.ds = dataset
        self.cache = SliceCache()

    # ------------------------------------------------------------------
    # Spatial slice: 2D field at a given time and depth
    # ------------------------------------------------------------------

    def get_spatial_slice(self, var_name, time_idx=None, depth_idx=None,
                          extra_indices=None):
        """
        Extract a 2D (y x x) slice for the given variable.

        Returns:
            data: 2D numpy masked array oriented (y, x)
            lat: 1D or 2D Y/latitude coordinate
            lon: 1D or 2D X/longitude coordinate
        """
        extra_key = tuple(sorted((extra_indices or {}).items()))
        key = (var_name, "spatial", time_idx, depth_idx, extra_key)
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        var = self.ds.get_variable(var_name)
        dim_map = self.ds.infer_var_axes(var_name)
        data = self._extract_2d(var, dim_map, time_idx, depth_idx, extra_indices)

        lat, lon = self.ds.get_spatial_coords(var_name)
        if lat is None or lon is None:
            # Absolute fallback: index grids matching data shape
            ny, nx = data.shape[:2]
            lat = np.arange(ny)
            lon = np.arange(nx)

        # 2D CF coords: slice to match data if they share leading dims
        lat, lon = self._align_2d_coords(lat, lon, data.shape)

        data, lat, lon = ensure_increasing_y(data, lat, lon)

        result = (data, lat, lon)
        self.cache.put(key, result)
        return result

    def _align_2d_coords(self, lat, lon, data_shape):
        """Ensure 2D lat/lon match the 2D data shape; pass 1D through."""
        lat = np.asarray(lat)
        lon = np.asarray(lon)
        ny, nx = data_shape[0], data_shape[1]

        if lat.ndim == 2 and lon.ndim == 2:
            if lat.shape == (ny, nx) and lon.shape == (ny, nx):
                return lat, lon
            # Try transpose if axes were swapped relative to data
            if lat.shape == (nx, ny) and lon.shape == (nx, ny):
                return lat.T, lon.T
            # If larger (e.g. includes time), take last 2 dims matching
            if lat.ndim == 2 and lat.shape[-2:] == (ny, nx):
                return lat, lon

        if lat.ndim == 1 and lon.ndim == 1:
            # Length mismatch after orientation: rebuild indices
            if lat.size != ny:
                lat = np.arange(ny)
            if lon.size != nx:
                lon = np.arange(nx)

        return lat, lon

    # ------------------------------------------------------------------
    # 1D line series (entire variable along its only free axis)
    # ------------------------------------------------------------------

    def get_1d_series(self, var_name, extra_indices=None):
        """
        Extract a 1D series for plotting line data.

        Returns:
            data: 1D masked array
            coord: 1D coordinate (or indices)
            coord_name: dimension name for the X axis
        """
        var = self.ds.get_variable(var_name)
        dim_map = self.ds.infer_var_axes(var_name)
        group = self.ds._var_group(var_name) if var_name in self.ds._var_index else self.ds._ds

        idx = [slice(None)] * var.ndim
        free_axis = None

        for i, dim_name in enumerate(var.dimensions):
            role = None
            for r, ax in dim_map.items():
                if ax == i:
                    role = r
                    break

            if role in ("time", "depth", "lat", "lon") and var.shape[i] > 1 and free_axis is None:
                # Keep the longest / first multi-valued axis free for 1D plot
                if free_axis is None:
                    free_axis = i
                    continue

            if var.shape[i] == 1:
                idx[i] = 0
            elif extra_indices and dim_name in extra_indices:
                idx[i] = extra_indices[dim_name]
            elif free_axis is None and var.shape[i] > 1:
                free_axis = i
            elif i != free_axis:
                idx[i] = 0

        if free_axis is None:
            free_axis = 0
            idx[0] = slice(None)

        data = np.ma.array(var[tuple(idx)]).squeeze()
        if data.ndim > 1:
            data = data.reshape(-1)

        coord_name = var.dimensions[free_axis]
        coord = self.ds.get_coord(coord_name, group=group)
        if coord is None or np.size(coord) != data.size:
            coord = np.arange(data.size)

        return data, np.asarray(coord), coord_name

    # ------------------------------------------------------------------
    # Vertical section: depth vs lat (at fixed lon) or depth vs lon (at fixed lat)
    # ------------------------------------------------------------------

    def get_vertical_section(self, var_name, time_idx, section_type, position_idx):
        """
        Extract a vertical cross-section.

        Args:
            section_type: 'lon' for a longitude-depth section (fixed lat, shows lon vs depth)
                          'lat' for a latitude-depth section (fixed lon, shows lat vs depth)
            position_idx: index along the fixed dimension

        Returns:
            data: 2D array (depth x horizontal)
            horiz_coord: 1D coordinate array for the horizontal axis
            depth_coord: 1D depth coordinate array
        """
        key = (var_name, "vsection", section_type, time_idx, position_idx)
        cached = self.cache.get(key)
        if cached is not None:
            lat, lon = self.ds.get_spatial_coords(var_name)
            if section_type == "lon":
                return cached, lon if lon is not None else self.ds.lon, self.ds.depth_values
            return cached, lat if lat is not None else self.ds.lat, self.ds.depth_values

        var = self.ds.get_variable(var_name)
        dim_map = self.ds.infer_var_axes(var_name)
        lat, lon = self.ds.get_spatial_coords(var_name)

        idx = [slice(None)] * var.ndim
        if "time" in dim_map:
            idx[dim_map["time"]] = time_idx if time_idx is not None else 0

        if section_type == "lon":
            if "lat" in dim_map:
                idx[dim_map["lat"]] = position_idx
            horiz_coord = lon if lon is not None else self.ds.lon
            if horiz_coord is not None and np.ndim(horiz_coord) > 1:
                horiz_coord = np.asarray(horiz_coord)[position_idx, :]
        else:
            if "lon" in dim_map:
                idx[dim_map["lon"]] = position_idx
            horiz_coord = lat if lat is not None else self.ds.lat
            if horiz_coord is not None and np.ndim(horiz_coord) > 1:
                horiz_coord = np.asarray(horiz_coord)[:, position_idx]

        data = np.ma.array(var[tuple(idx)])

        if data.ndim > 2:
            data = data.squeeze()
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        if "depth" in dim_map and "lat" in dim_map and "lon" in dim_map:
            depth_axis = self._remaining_axis(dim_map, section_type, time_idx)
            if depth_axis == 1:
                data = data.T

        self.cache.put(key, data)
        return data, horiz_coord, self.ds.depth_values

    # ------------------------------------------------------------------
    # Horizontal section: transect along lat or lon at a fixed depth
    # ------------------------------------------------------------------

    def get_horizontal_section(self, var_name, time_idx, depth_idx,
                               section_type, position_idx):
        """
        Extract a horizontal transect (1D line) at a fixed depth.

        Args:
            section_type: 'lat' for a transect along a latitude line (varying lon)
                          'lon' for a transect along a longitude line (varying lat)
            position_idx: index of the fixed lat or lon

        Returns:
            data: 1D array of values along the transect
            coord: 1D coordinate array for the varying axis
        """
        key = (var_name, "hsection", section_type, time_idx, depth_idx, position_idx)
        cached = self.cache.get(key)
        lat, lon = self.ds.get_spatial_coords(var_name)
        if cached is not None:
            coord = lon if section_type == "lat" else lat
            if coord is not None and np.ndim(coord) > 1:
                coord = np.asarray(coord)[position_idx, :] if section_type == "lat" else np.asarray(coord)[:, position_idx]
            return cached, coord

        var = self.ds.get_variable(var_name)
        dim_map = self.ds.infer_var_axes(var_name)

        idx = [slice(None)] * var.ndim
        if "time" in dim_map:
            idx[dim_map["time"]] = time_idx if time_idx is not None else 0
        if "depth" in dim_map:
            idx[dim_map["depth"]] = depth_idx if depth_idx is not None else 0

        if section_type == "lat":
            if "lat" in dim_map:
                idx[dim_map["lat"]] = position_idx
            coord = lon
            if coord is not None and np.ndim(coord) > 1:
                coord = np.asarray(coord)[position_idx, :]
        else:
            if "lon" in dim_map:
                idx[dim_map["lon"]] = position_idx
            coord = lat
            if coord is not None and np.ndim(coord) > 1:
                coord = np.asarray(coord)[:, position_idx]

        data = np.ma.array(var[tuple(idx)]).flatten()

        self.cache.put(key, data)
        return data, coord

    # ------------------------------------------------------------------
    # Timeseries: value at a point over all time steps
    # ------------------------------------------------------------------

    def get_timeseries(self, var_name, lat_idx, lon_idx, depth_idx=None,
                        extra_indices=None):
        """
        Extract the full timeseries at a single spatial point.

        Returns:
            data: 1D array of values over time
            time_coord: time coordinate array (datetime or numeric)
        """
        extra_key = tuple(sorted((extra_indices or {}).items()))
        key = (var_name, "timeseries", lat_idx, lon_idx, depth_idx, extra_key)
        cached = self.cache.get(key)
        if cached is not None:
            return cached, self.ds.time_dates

        var = self.ds.get_variable(var_name)
        dim_map = self.ds.infer_var_axes(var_name)

        idx = [slice(None)] * var.ndim
        if "lat" in dim_map:
            idx[dim_map["lat"]] = lat_idx
        if "lon" in dim_map:
            idx[dim_map["lon"]] = lon_idx
        if "depth" in dim_map:
            idx[dim_map["depth"]] = depth_idx if depth_idx is not None else 0

        used = set(dim_map.values())
        for i, dim_name in enumerate(var.dimensions):
            if i in used:
                continue
            if idx[i] != slice(None):
                continue
            if extra_indices and dim_name in extra_indices:
                idx[i] = extra_indices[dim_name]
            else:
                idx[i] = 0

        data = np.ma.array(var[tuple(idx)]).flatten()

        self.cache.put(key, data)
        return data, self.ds.time_dates

    # ------------------------------------------------------------------
    # Depth profile: value at a point over all depths
    # ------------------------------------------------------------------

    def get_depth_profile(self, var_name, time_idx, lat_idx, lon_idx,
                           extra_indices=None):
        """
        Extract a depth profile at a single spatial point and time.

        Returns:
            data: 1D array of values over depth
            depth_coord: depth coordinate array
        """
        extra_key = tuple(sorted((extra_indices or {}).items()))
        key = (var_name, "profile", time_idx, lat_idx, lon_idx, extra_key)
        cached = self.cache.get(key)
        if cached is not None:
            return cached, self.ds.depth_values

        var = self.ds.get_variable(var_name)
        dim_map = self.ds.infer_var_axes(var_name)

        idx = [slice(None)] * var.ndim
        if "time" in dim_map:
            idx[dim_map["time"]] = time_idx if time_idx is not None else 0
        if "lat" in dim_map:
            idx[dim_map["lat"]] = lat_idx
        if "lon" in dim_map:
            idx[dim_map["lon"]] = lon_idx

        used = set(dim_map.values())
        for i, dim_name in enumerate(var.dimensions):
            if i in used:
                continue
            if idx[i] != slice(None):
                continue
            if extra_indices and dim_name in extra_indices:
                idx[i] = extra_indices[dim_name]
            else:
                idx[i] = 0

        data = np.ma.array(var[tuple(idx)]).flatten()

        self.cache.put(key, data)
        return data, self.ds.depth_values

    # ------------------------------------------------------------------
    # Raw slice (for non-standard dimensionality)
    # ------------------------------------------------------------------

    def get_raw_slice(self, var_name, index_dict):
        """
        Generic slice access. index_dict maps dimension names to indices
        or slice objects. Dimensions not in the dict get slice(None).

        Returns the raw numpy array.
        """
        var = self.ds.get_variable(var_name)
        idx = [slice(None)] * var.ndim
        for dim_name, val in index_dict.items():
            if dim_name in var.dimensions:
                axis = list(var.dimensions).index(dim_name)
                idx[axis] = val
        return np.ma.array(var[tuple(idx)])

    # ------------------------------------------------------------------
    # Statistics for a 2D slice
    # ------------------------------------------------------------------

    def compute_stats(self, data):
        """
        Compute summary statistics on a masked array.
        Returns a dict with keys: mean, std, min, max, median, valid_count.
        """
        compressed = data.compressed() if hasattr(data, "compressed") else data.ravel()

        if compressed.size == 0:
            return {
                "mean": np.nan, "std": np.nan, "min": np.nan,
                "max": np.nan, "median": np.nan, "valid_count": 0,
            }

        return {
            "mean": float(np.mean(compressed)),
            "std": float(np.std(compressed)),
            "min": float(np.min(compressed)),
            "max": float(np.max(compressed)),
            "median": float(np.median(compressed)),
            "valid_count": int(compressed.size),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_2d(self, var, dim_map, time_idx, depth_idx, extra_indices=None):
        """Extract a 2D spatial slice oriented as (y/lat, x/lon)."""
        idx = [slice(None)] * var.ndim
        spatial = {dim_map[r] for r in ("lat", "lon") if r in dim_map}

        for i, dim_name in enumerate(var.dimensions):
            if i in spatial:
                continue
            if "time" in dim_map and i == dim_map["time"]:
                idx[i] = time_idx if time_idx is not None else 0
            elif "depth" in dim_map and i == dim_map["depth"]:
                idx[i] = depth_idx if depth_idx is not None else 0
            elif extra_indices and dim_name in extra_indices:
                idx[i] = extra_indices[dim_name]
            else:
                idx[i] = 0

        data = np.ma.array(var[tuple(idx)]).squeeze()

        if data.ndim < 2:
            data = data.reshape(1, -1)
            return data

        while data.ndim > 2:
            data = data[0]

        # If lon precedes lat in the original dim order, squeezed data is
        # (lon, lat) and must be transposed to (lat, lon) for pcolormesh.
        if "lat" in dim_map and "lon" in dim_map:
            if dim_map["lon"] < dim_map["lat"] and data.ndim == 2:
                data = data.T

        return data

    def _remaining_axis(self, dim_map, section_type, time_idx):
        """
        After fixing time and one spatial dim, figure out which axis
        index corresponds to depth in the reduced array.
        """
        axes_used = []
        if "time" in dim_map and time_idx is not None:
            axes_used.append(dim_map["time"])
        if section_type == "lon" and "lat" in dim_map:
            axes_used.append(dim_map["lat"])
        elif section_type == "lat" and "lon" in dim_map:
            axes_used.append(dim_map["lon"])

        depth_axis = dim_map.get("depth", 0)
        offset = sum(1 for a in axes_used if a < depth_axis)
        return depth_axis - offset
