"""
Data extraction engine. Pulls 2D slices, cross-sections, timeseries,
and depth profiles from the dataset, routing through the cache layer.
"""

import numpy as np

from .cache import SliceCache


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
        Extract a 2D (lat x lon) slice for the given variable.

        Args:
            extra_indices: optional dict of dim_name -> index for unassigned
                           dimensions. These get fixed at the given index.

        Returns:
            data: 2D numpy masked array
            lat: 1D latitude coordinate
            lon: 1D longitude coordinate
        """
        extra_key = tuple(sorted((extra_indices or {}).items()))
        key = (var_name, "spatial", time_idx, depth_idx, extra_key)
        cached = self.cache.get(key)
        if cached is not None:
            return cached, self.ds.lat, self.ds.lon

        var = self.ds.get_variable(var_name)
        dim_map = self.ds.get_var_dim_indices(var_name)
        data = self._extract_2d(var, dim_map, time_idx, depth_idx, extra_indices)

        self.cache.put(key, data)
        return data, self.ds.lat, self.ds.lon

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
            if section_type == "lon":
                return cached, self.ds.lon, self.ds.depth_values
            else:
                return cached, self.ds.lat, self.ds.depth_values

        var = self.ds.get_variable(var_name)
        dim_map = self.ds.get_var_dim_indices(var_name)

        # Build index tuple
        idx = [slice(None)] * var.ndim
        if "time" in dim_map:
            idx[dim_map["time"]] = time_idx if time_idx is not None else 0

        if section_type == "lon":
            # Fix latitude, get lon vs depth
            if "lat" in dim_map:
                idx[dim_map["lat"]] = position_idx
            horiz_coord = self.ds.lon
        else:
            # Fix longitude, get lat vs depth
            if "lon" in dim_map:
                idx[dim_map["lon"]] = position_idx
            horiz_coord = self.ds.lat

        data = np.ma.array(var[tuple(idx)])

        # Ensure result is 2D: (depth, horizontal)
        if data.ndim > 2:
            data = data.squeeze()
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        # Orient so axis 0 is depth and axis 1 is horizontal
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
        if cached is not None:
            coord = self.ds.lon if section_type == "lat" else self.ds.lat
            return cached, coord

        var = self.ds.get_variable(var_name)
        dim_map = self.ds.get_var_dim_indices(var_name)

        idx = [slice(None)] * var.ndim
        if "time" in dim_map:
            idx[dim_map["time"]] = time_idx if time_idx is not None else 0
        if "depth" in dim_map:
            idx[dim_map["depth"]] = depth_idx if depth_idx is not None else 0

        if section_type == "lat":
            # Fix lat, vary lon
            if "lat" in dim_map:
                idx[dim_map["lat"]] = position_idx
            coord = self.ds.lon
        else:
            # Fix lon, vary lat
            if "lon" in dim_map:
                idx[dim_map["lon"]] = position_idx
            coord = self.ds.lat

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
        dim_map = self.ds.get_var_dim_indices(var_name)

        idx = [slice(None)] * var.ndim
        if "lat" in dim_map:
            idx[dim_map["lat"]] = lat_idx
        if "lon" in dim_map:
            idx[dim_map["lon"]] = lon_idx
        if "depth" in dim_map:
            idx[dim_map["depth"]] = depth_idx if depth_idx is not None else 0

        # Fix any extra unassigned dimensions
        assigned = {self.ds.time_dim, self.ds.depth_dim, self.ds.lat_dim, self.ds.lon_dim}
        for i, dim_name in enumerate(var.dimensions):
            if dim_name not in assigned and idx[i] == slice(None):
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
        dim_map = self.ds.get_var_dim_indices(var_name)

        idx = [slice(None)] * var.ndim
        if "time" in dim_map:
            idx[dim_map["time"]] = time_idx if time_idx is not None else 0
        if "lat" in dim_map:
            idx[dim_map["lat"]] = lat_idx
        if "lon" in dim_map:
            idx[dim_map["lon"]] = lon_idx

        # Fix any extra unassigned dimensions
        assigned = {self.ds.time_dim, self.ds.depth_dim, self.ds.lat_dim, self.ds.lon_dim}
        for i, dim_name in enumerate(var.dimensions):
            if dim_name not in assigned and idx[i] == slice(None):
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
                axis = var.dimensions.index(dim_name)
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
        """Extract a 2D spatial slice from an N-dimensional variable."""
        idx = [slice(None)] * var.ndim

        if "time" in dim_map:
            idx[dim_map["time"]] = time_idx if time_idx is not None else 0
        if "depth" in dim_map:
            idx[dim_map["depth"]] = depth_idx if depth_idx is not None else 0

        # Fix any extra (unassigned) dimensions at their current slider value
        if extra_indices:
            assigned = {self.ds.time_dim, self.ds.depth_dim, self.ds.lat_dim, self.ds.lon_dim}
            for i, dim_name in enumerate(var.dimensions):
                if dim_name not in assigned and dim_name in extra_indices:
                    idx[i] = extra_indices[dim_name]

        data = np.ma.array(var[tuple(idx)])

        # Squeeze out any remaining singleton dimensions
        data = data.squeeze()

        # Handle the case where squeezing reduces below 2D
        if data.ndim < 2:
            data = data.reshape(1, -1)

        return data

    def _remaining_axis(self, dim_map, section_type, time_idx):
        """
        After fixing time and one spatial dim, figure out which axis
        index corresponds to depth in the reduced array.
        """
        # Count how many dimensions precede depth that were sliced out
        axes_used = []
        if "time" in dim_map and time_idx is not None:
            axes_used.append(dim_map["time"])
        if section_type == "lon" and "lat" in dim_map:
            axes_used.append(dim_map["lat"])
        elif section_type == "lat" and "lon" in dim_map:
            axes_used.append(dim_map["lon"])

        depth_axis = dim_map.get("depth", 0)
        # How many sliced axes are before depth?
        offset = sum(1 for a in axes_used if a < depth_axis)
        return depth_axis - offset
