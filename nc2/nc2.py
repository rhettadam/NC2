from tkinter import *
from tkinter import filedialog, ttk
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import cartopy.feature as cfeature
import cartopy.crs as ccrs

import imageio.v2 as imageio
from PIL import Image, ImageTk
import time

import sys
import os
import argparse
import importlib.resources
import netCDF4 as nc
import numpy as np

class NC2:
    def __init__(self, root, file_path=None):
        self.root = root
        self.root.title("NC²")
        
        self.file_path = file_path
        self.dataset = None
        self.variable_names = []
        self.depth_levels = []
        self.current_figure = None
        self.forward_pressed = False
        self.backward_pressed = False
        
        # Initialize dimension tracking
        self.time = None
        self.time_key = None
        self.time_units = None
        self.time_steps = 0
        self.time_index_map = {}
        
        self.depth = None
        self.depth_key = None
        self.depth_units = None
        self.depth_levels = 0
        self.depth_index_map = {}
        
        self.lat = None
        self.lon = None
        self.lat_key = None
        self.lon_key = None
        
        # Initialize coordinate and dimension tracking
        self.coord_vars = {}
        self.dim_vars = {}
        self.dim_info = {}
        
        logo_path = importlib.resources.files('nc2').joinpath('Logo3.png')
        self.logo = ImageTk.PhotoImage(file=str(logo_path))
        
        self.create_widgets()
        
        if self.file_path:
            self.load_netcdf_file()
            
# ********** Widgets ********** #

    def create_widgets(self):
        control_frame_left = tk.Frame(self.root, padx=10, pady=10)
        control_frame_left.pack(side=tk.LEFT, fill=tk.Y)
        
        width, height = self.logo.width(), self.logo.height()
        self.logo_label = Label(control_frame_left, width=width, height=height, image = self.logo)
        self.logo_label.pack(pady=5)
        
        self.select_file_button = tb.Button(control_frame_left, text="Select NetCDF File", command=self.select_file, bootstyle='info')
        self.select_file_button.pack(pady=10)
        
        self.variable_dropdown_label = tb.Label(control_frame_left, text="Select Variable:", font=("Helvetica", 12))
        self.variable_dropdown_label.pack(pady=5)
        
        self.variable_dropdown = tb.Combobox(control_frame_left, state="readonly", bootstyle='primary')
        self.variable_dropdown.pack(pady=5)
        self.variable_dropdown.bind("<<ComboboxSelected>>", self.on_variable_selected)
        
        self.time_dropdown_label = tb.Label(control_frame_left, text="Select Time Step:", font=("Helvetica", 12))
        self.time_dropdown_label.pack(pady=5)
        
        self.time_dropdown = tb.Combobox(control_frame_left, state="readonly", bootstyle='primary')
        self.time_dropdown.pack(pady=5)
        self.time_dropdown.configure(state='disabled')
        self.time_dropdown.bind("<<ComboboxSelected>>", self.calculate_time)

        self.depth_dropdown_label = tb.Label(control_frame_left, text="Select Depth Level:", font=("Helvetica", 12))
        self.depth_dropdown_label.pack(pady=5)
        
        self.depth_dropdown = tb.Combobox(control_frame_left, state="readonly", bootstyle='primary')
        self.depth_dropdown.pack(pady=5)
        self.depth_dropdown.configure(state='disabled')
        self.depth_dropdown.bind("<<ComboboxSelected>>", self.calculate_depth)

        self.depth_time_label = tb.Label(control_frame_left, text='', bootstyle='warning')
        self.depth_time_label.pack(pady=10)
        
        self.statistics_label = tb.Label(control_frame_left, text='', bootstyle='info')
        self.statistics_label.pack(pady=5)
        
        self.hover_label = tb.Label(control_frame_left, text='', font=("Helvetica", 12),bootstyle='warning')
        self.hover_label.pack(pady=10)
        
        self.gif_checkbox_var = tk.BooleanVar()
        self.gif_checkbox = tb.Checkbutton(control_frame_left, text="Make GIF", variable=self.gif_checkbox_var, bootstyle='danger, round-toggle', command=self.toggle_gif_checkbox)
        self.gif_checkbox.pack(pady=5)
        
        gif_fpstime = tb.Frame(control_frame_left)
        gif_fpstime.pack(pady=3)
        
        self.gif_FPS_entry_var = tk.StringVar()
        self.gif_FPS_entry_var.set("FPS")
        self.gif_FPS_entry = tb.Entry(gif_fpstime, width=6, textvariable=self.gif_FPS_entry_var, bootstyle='warning')
        self.gif_FPS_entry.pack(side=tk.LEFT, padx=6, pady=5)
        
        self.time_steps_entry_var = tk.StringVar()
        self.time_steps_entry_var.set('Range')
        self.time_steps_entry = tb.Entry(gif_fpstime, width=6, textvariable=self.time_steps_entry_var, bootstyle='warning')
        self.time_steps_entry.pack(side=tk.LEFT, padx=6, pady=5)
        
        gif_deloop = tb.Frame(control_frame_left)
        gif_deloop.pack(pady=1)
        
        self.delete_images_var = tk.BooleanVar()
        self.delete_images_checkbox = tb.Checkbutton(gif_deloop, text="Delete Images", variable=self.delete_images_var, bootstyle='danger, round-toggle')
        self.delete_images_checkbox.pack(side=tk.LEFT, padx=3, pady=5)
        
        self.gif_loop_var = tk.BooleanVar()
        self.gif_loop = tb.Checkbutton(gif_deloop, text="Loop", variable=self.gif_loop_var, bootstyle='danger, round-toggle')
        self.gif_loop.pack(side=tk.LEFT, padx=2, pady=5)
     
        self.gif_directory = tb.Button(control_frame_left, text='Save GIF', command=self.select_gif_directory, bootstyle='warning')
        self.gif_directory.pack(pady=5)

        self.plot_button = tb.Button(control_frame_left, text="Plot Variable", command=self.plot_variable, bootstyle='info')
        self.plot_button.pack(side=tk.BOTTOM, pady=10)
        
        self.window_plot_var = tk.BooleanVar()
        self.window_plot = tb.Checkbutton(control_frame_left, text='Show In Window', variable=self.window_plot_var, bootstyle='danger, round-toggle')
        self.window_plot.pack(side=tk.BOTTOM, pady=5)

        control_frame_right = tk.Frame(self.root, bg='grey16', padx=10, pady=10)
        control_frame_right.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.plot_type_label = tb.Label(control_frame_right, text="Select Plot Type:", font=("Helvetica", 12))
        self.plot_type_label.pack(pady=5)
        
        self.plot_type_dropdown = tb.Combobox(control_frame_right, state="readonly", bootstyle='success')
        self.plot_type_dropdown['values'] = ['pcolormesh', 'contour', 'contourf', 'imshow', 'quiver', 'streamplot']
        self.plot_type_dropdown.set('pcolormesh')
        self.plot_type_dropdown.pack(pady=5)
        
        self.levels_entry_var = tk.StringVar()
        self.levels_entry = tb.Entry(control_frame_right, textvariable=self.levels_entry_var, bootstyle='secondary')
        
        self.steps_var = tk.StringVar()
        self.steps_entry = tb.Entry(control_frame_right, textvariable=self.steps_var, bootstyle='secondary')
        
        self.scale_var = tk.StringVar()
        self.scale_entry = tb.Entry(control_frame_right, textvariable=self.scale_var, bootstyle='secondary')
        
        self.density_var = tk.StringVar()
        self.density_entry = tb.Entry(control_frame_right, textvariable=self.density_var, bootstyle='secondary')
        
        self.linewidth_var = tk.StringVar()
        self.linewidth_entry = tb.Entry(control_frame_right, textvariable=self.linewidth_var, bootstyle='secondary')
        
        self.plot_type_dropdown.bind("<<ComboboxSelected>>", self.on_plot_select)
        
        self.colormap_dropdown_label = tb.Label(control_frame_right, text="Select Colormap:", font=("Helvetica", 12))
        self.colormap_dropdown_label.pack(pady=5)
        
        self.colormap_dropdown = tb.Combobox(control_frame_right, state="readonly", bootstyle='success')
        self.colormap_dropdown.pack(pady=5)
        
        self.load_colormaps()
        
        self.reverse_colormap_var = tk.BooleanVar()
        self.reverse_colormap = tb.Checkbutton(control_frame_right, text='Reverse', variable=self.reverse_colormap_var, bootstyle='danger, round-toggle')
        self.reverse_colormap.pack(pady=5)

        self.colorbar_orientation_label = tb.Label(control_frame_right, text="Colorbar Orientation:", font=("Helvetica", 12))
        self.colorbar_orientation_label.pack(pady=5)
        self.colorbar_orientation_dropdown = tb.Combobox(control_frame_right, state="readonly", bootstyle='secondary')
        self.colorbar_orientation_dropdown['values'] = ['vertical', 'horizontal']
        self.colorbar_orientation_dropdown.set('vertical')
        self.colorbar_orientation_dropdown.pack(pady=5)
        
        self.cbar_shrink_entry_var = tk.StringVar()
        self.cbar_shrink_entry_var.set("Shrink (0-1)")
        self.cbar_shrink_entry = tb.Entry(control_frame_right, textvariable=self.cbar_shrink_entry_var, bootstyle='secondary')
        self.cbar_shrink_entry.pack(pady=5)
        
        self.vmax_label_entry_var = tk.StringVar()
        self.vmax_label_entry_var.set('V-Max')
        self.vmax_entry = tb.Entry(control_frame_right, textvariable = self.vmax_label_entry_var, bootstyle='success')
        self.vmax_entry.pack(pady=5)
        
        self.vmin_label_entry_var = tk.StringVar()
        self.vmin_label_entry_var.set("V-Min")
        self.vmin_entry = tb.Entry(control_frame_right, textvariable=self.vmin_label_entry_var, bootstyle='danger')
        self.vmin_entry.pack(pady=5)
        
        self.extent_label_var = tk.StringVar()
        self.extent_label_var.set("Extents [x0, x1, y0, y1]")
        self.extent_entry = tb.Entry(control_frame_right, textvariable=self.extent_label_var, bootstyle='secondary')
        self.extent_entry.pack(pady=5)
        
        central_longitude = 0
        central_latitude = 0
        
        self.projections = {
            'PlateCarree': ccrs.PlateCarree(central_longitude = central_longitude),
            'Mercator': ccrs.Mercator(central_longitude = central_longitude),
            'Orthographic': ccrs.Orthographic(central_longitude = central_longitude),
            'LambertConformal': ccrs.LambertConformal(central_longitude = central_longitude),
            'Mollweide': ccrs.Mollweide(central_longitude = central_longitude),
            'Robinson': ccrs.Robinson(central_longitude = central_longitude),
            'TransverseMercator': ccrs.TransverseMercator(central_longitude = central_longitude),
            'AlbersEqualArea': ccrs.AlbersEqualArea(central_longitude = central_longitude),
            'AzimuthalEquidistant': ccrs.AzimuthalEquidistant(central_longitude = central_longitude),
            'Geostationary': ccrs.Geostationary(central_longitude = central_longitude),
            'InterruptedGoodeHomolosine': ccrs.InterruptedGoodeHomolosine(central_longitude = central_longitude),
            'LambertAzimuthalEqualArea': ccrs.LambertAzimuthalEqualArea(central_longitude = central_longitude),
            'NorthPolarStereo': ccrs.NorthPolarStereo(central_longitude = central_longitude),
            'SouthPolarStereo': ccrs.SouthPolarStereo(central_longitude = central_longitude),
            'Stereographic': ccrs.Stereographic(central_longitude = central_longitude),
            'Sinusoidal': ccrs.Sinusoidal(central_longitude = central_longitude),
            'EuroPP': ccrs.EuroPP(),
            'OSGB': ccrs.OSGB(),
            'RotatedPole': ccrs.RotatedPole()
            }
        
        self.projection_dropdown_label = tb.Label(control_frame_right, text="Projection:", font=("Helvetica", 12))
        self.projection_dropdown = tb.Combobox(control_frame_right, values=list(self.projections.keys()))
        self.projection_dropdown.set('PlateCarree')
        self.projection_dropdown.pack(pady=5)
        
        gridlines_frame = tb.Frame(control_frame_right)
        gridlines_frame.pack(pady=5)
        
        self.gridlines_var = tk.BooleanVar()
        self.gridlines = tb.Checkbutton(gridlines_frame, text='Gridlines', variable=self.gridlines_var, bootstyle='danger, round-toggle')
        self.gridlines.pack(side = tk.LEFT, pady=5, padx=2)
        
        self.alpha_entry_var = tk.StringVar()
        self.alpha_entry_var.set('Alpha')
        self.alpha_entry = tb.Entry(gridlines_frame, textvariable=self.alpha_entry_var, bootstyle='secondary', width=5)
        self.alpha_entry.pack(side = tk.LEFT, pady=5, padx=2)
        
        checkboxes_frame = tb.Frame(control_frame_right)
        checkboxes_frame.pack(pady=5)
        
        self.ocean_checkbox_var = tk.BooleanVar()
        self.ocean_checkbox = tb.Checkbutton(checkboxes_frame, text='Ocean', variable=self.ocean_checkbox_var, bootstyle='danger, round-toggle')
        self.ocean_checkbox.pack(side=tk.LEFT, pady=5, padx=2)
        
        self.land_checkbox_var = tk.BooleanVar()
        self.land_checkbox = tb.Checkbutton(checkboxes_frame, text='Land', variable=self.land_checkbox_var, bootstyle='danger, round-toggle')
        self.land_checkbox.pack(side=tk.LEFT, pady=5, padx=2)
        
        self.xlabel_label = tb.Label(control_frame_right, text="X-axis Label:", font=("Helvetica", 12))
        self.xlabel_label.pack(pady=5)
        self.xlabel_entry = tb.Entry(control_frame_right, bootstyle='secondary')
        self.xlabel_entry.pack(pady=5)
        
        self.ylabel_label = tb.Label(control_frame_right, text="Y-axis Label:", font=("Helvetica", 12))
        self.ylabel_label.pack(pady=5)
        self.ylabel_entry = tb.Entry(control_frame_right, bootstyle='secondary')
        self.ylabel_entry.pack(pady=5)
        
        self.title_label = Label(control_frame_right, text="Plot Title:", font=("Helvetica", 12))
        self.title_label.pack(pady=5)
        self.title_entry = tb.Entry(control_frame_right, bootstyle='secondary')
        self.title_entry.pack(pady=5)
        
        self.theme_dropdown = tb.Menubutton(control_frame_right, text="Theme", bootstyle='secondary', direction='below')
        self.theme_menu = tb.Menu(self.theme_dropdown, tearoff=0)
        
        self.light_theme_menu = tb.Menu(self.theme_menu, tearoff=0)
        self.dark_theme_menu = tb.Menu(self.theme_menu, tearoff=0)

        for theme in ['cosmo', 'flatly', 'minty', 'morph', 'simplex']:
            self.light_theme_menu.add_command(label=theme, command=lambda t=theme: self.change_theme(t))
        
        for theme in ['solar', 'superhero', 'darkly', 'cyborg', 'vapor']:
            self.dark_theme_menu.add_command(label=theme, command=lambda t=theme: self.change_theme(t))
        
        self.theme_menu.add_cascade(label="Light Themes", menu=self.light_theme_menu)
        self.theme_menu.add_cascade(label="Dark Themes", menu=self.dark_theme_menu)

        self.theme_dropdown.config(menu=self.theme_menu)
        self.theme_dropdown.pack(pady=5)

        self.data_display_frame = tk.Frame(self.root, bg='grey14', padx=10, pady=5)
        self.data_display_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.data_display_text = tk.Text(self.data_display_frame, bg='grey12', fg='lime', height=10, wrap=tk.WORD, font=("Helvetica", 10))
        self.data_display_text.pack(fill=tk.BOTH, expand=True)

        self.plot_frame = tk.Frame(self.root, bg='grey12', padx=10, pady=10)
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
# ********** Logic ********** #
    
    def load_colormaps(self):
        colormap_names = sorted(m for m in plt.colormaps() if not m.endswith("_r"))
        self.colormap_dropdown['values'] = colormap_names
        self.colormap_dropdown.set('jet') 
    
    def select_file(self):
        filetypes = [
            ("NetCDF files", "*.nc"),
            ("NetCDF files", "*.nc4"),
            ("NetCDF files", "*.cdf"),
            ("NetCDF files", "*.netcdf"),
            ("All files", "*.*")
        ]
        self.file_path = filedialog.askopenfilename(
            title="Select NetCDF File",
            filetypes=filetypes,
            initialdir=os.path.expanduser("~")
        )
        if self.file_path:
            try:
                # Try to open the file to verify it's a valid NetCDF file
                with nc.Dataset(self.file_path, 'r') as test_dataset:
                    pass
                self.load_netcdf_file()
            except Exception as e:
                self.data_display_text.delete("1.0", tk.END)
                self.data_display_text.insert(tk.END, f"Error: Selected file is not a valid NetCDF file.\n{str(e)}")
                self.file_path = None
    
    def load_netcdf_file(self):
        try:
            self.dataset = nc.Dataset(self.file_path)
            
            # Get all variables and their dimensions
            self.variable_names = list(self.dataset.variables.keys())
            
            # Initialize coordinate and dimension tracking
            self.coord_vars = {}
            self.dim_vars = {}
            self.dim_info = {}
            
            # First pass: identify all dimensions and their sizes
            for dim_name, dim in self.dataset.dimensions.items():
                self.dim_vars[dim_name] = dim
                self.dim_info[dim_name] = {
                    'size': len(dim),
                    'is_unlimited': dim.isunlimited(),
                    'coord_var': None,
                    'type': None
                }
            
            # Second pass: identify coordinate variables and their types
            for var_name, var in self.dataset.variables.items():
                # Check if this is a coordinate variable (matches its dimension name)
                if var_name in self.dataset.dimensions:
                    self.coord_vars[var_name] = var
                    self.dim_info[var_name]['coord_var'] = var
                    
                    # Try to determine dimension type
                    if hasattr(var, 'units'):
                        units = var.units.lower()
                        if any(unit in units for unit in ['time', 'date', 'since']):
                            self.dim_info[var_name]['type'] = 'time'
                        elif any(unit in units for unit in ['degree', 'radian']):
                            if 'lon' in var_name.lower() or 'x' in var_name.lower():
                                self.dim_info[var_name]['type'] = 'longitude'
                            elif 'lat' in var_name.lower() or 'y' in var_name.lower():
                                self.dim_info[var_name]['type'] = 'latitude'
                        elif any(unit in units for unit in ['meter', 'depth', 'height']):
                            self.dim_info[var_name]['type'] = 'vertical'
                    # If no units, try to determine type from standard_name
                    elif hasattr(var, 'standard_name'):
                        std_name = var.standard_name.lower()
                        if 'time' in std_name:
                            self.dim_info[var_name]['type'] = 'time'
                        elif 'longitude' in std_name:
                            self.dim_info[var_name]['type'] = 'longitude'
                        elif 'latitude' in std_name:
                            self.dim_info[var_name]['type'] = 'latitude'
                        elif 'depth' in std_name:
                            self.dim_info[var_name]['type'] = 'vertical'
            
            # Identify primary dimensions based on common patterns
            self.time = None
            self.time_key = None
            self.depth = None
            self.depth_key = None
            self.lat = None
            self.lon = None
            self.lat_key = None
            self.lon_key = None
            
            # Find time dimension
            for dim_name, info in self.dim_info.items():
                if info['type'] == 'time':
                    self.time = self.coord_vars[dim_name]
                    self.time_key = dim_name
                    break
            
            # Find vertical dimension
            for dim_name, info in self.dim_info.items():
                if info['type'] == 'vertical' or dim_name.lower() == 'depth':
                    self.depth = self.coord_vars[dim_name]
                    self.depth_key = dim_name
                    break
            
            # Find spatial dimensions
            for dim_name, info in self.dim_info.items():
                if info['type'] == 'latitude':
                    self.lat = self.coord_vars[dim_name][:]
                    self.lat_key = dim_name
                elif info['type'] == 'longitude':
                    self.lon = self.coord_vars[dim_name][:]
                    self.lon_key = dim_name
            
            # Handle time dimension
            if self.time is not None:
                try:
                    self.time_units = self.time.units if hasattr(self.time, 'units') else 'unknown'
                    self.time_steps = len(self.time)
                    time_values = [nc.num2date(self.time[t], units=self.time_units) for t in range(self.time_steps)]
                    self.time_index_map = {str(time_values[i]): i for i in range(self.time_steps)}
                    self.time_dropdown['values'] = list(self.time_index_map.keys())
                    self.time_dropdown.set(list(self.time_index_map.keys())[0])
                    self.time_dropdown.configure(state='readonly')
                except Exception as e:
                    print(f"Warning: Could not process time values: {e}")
                    self.time_dropdown.configure(state='disabled')
            else:
                self.time_dropdown.configure(state='disabled')
            
            # Handle depth dimension
            if self.depth is not None:
                try:
                    self.depth_units = self.depth.units if hasattr(self.depth, 'units') else 'unknown'
                    self.depth_levels = len(self.depth)
                    depth_values = self.depth[:]  # Get actual depth values
                    self.depth_index_map = {f"{depth_values[i]:.2f} {self.depth_units}": i for i in range(self.depth_levels)}
                    self.depth_dropdown['values'] = list(self.depth_index_map.keys())
                    self.depth_dropdown.set(list(self.depth_index_map.keys())[0])
                    self.depth_dropdown.configure(state='readonly')
                except Exception as e:
                    print(f"Warning: Could not process depth values: {e}")
                    self.depth_dropdown.configure(state='disabled')
            else:
                self.depth_dropdown.configure(state='disabled')
            
            # Filter out coordinate variables from the variable list
            coord_vars = {self.time_key, self.depth_key, self.lat_key, self.lon_key}
            self.variable_names = [i for i in self.dataset.variables.keys() if i not in coord_vars]
            self.variable_dropdown['values'] = self.variable_names
            
            # Display file information
            self.data_display_text.delete("1.0", tk.END)
            self.data_display_text.insert(tk.END, "=== File Information ===\n")
            self.data_display_text.insert(tk.END, f"File: {os.path.basename(self.file_path)}\n")
            self.data_display_text.insert(tk.END, f"Format: {self.dataset.file_format}\n\n")
            
            self.data_display_text.insert(tk.END, "=== Dimensions ===\n")
            for dim_name, info in self.dim_info.items():
                dim_type = info['type'] if info['type'] else 'unknown'
                self.data_display_text.insert(tk.END, 
                    f"{dim_name}: {info['size']} {'(unlimited)' if info['is_unlimited'] else ''} (type: {dim_type})\n")
            
            self.data_display_text.insert(tk.END, "\n=== Variables ===\n")
            for var_name, variable in self.dataset.variables.items():
                self.data_display_text.insert(tk.END, f"\n{var_name}:\n")
                self.data_display_text.insert(tk.END, f"  Shape: {variable.shape}\n")
                self.data_display_text.insert(tk.END, f"  Dimensions: {variable.dimensions}\n")
                if hasattr(variable, 'units'):
                    self.data_display_text.insert(tk.END, f"  Units: {variable.units}\n")
                if hasattr(variable, 'long_name'):
                    self.data_display_text.insert(tk.END, f"  Long name: {variable.long_name}\n")
                if hasattr(variable, 'standard_name'):
                    self.data_display_text.insert(tk.END, f"  Standard name: {variable.standard_name}\n")
                if hasattr(variable, 'missing_value'):
                    self.data_display_text.insert(tk.END, f"  Missing value: {variable.missing_value}\n")
                if hasattr(variable, '_FillValue'):
                    self.data_display_text.insert(tk.END, f"  Fill value: {variable._FillValue}\n")
            
        except Exception as e:
            print(f"Error loading NetCDF file: {e}")
            self.data_display_text.delete("1.0", tk.END)
            self.data_display_text.insert(tk.END, f"Error loading file: {str(e)}")
            
    def on_variable_selected(self, event):
        selected_variable = self.variable_dropdown.get()
        variable_data = self.dataset.variables[selected_variable]
        
        strip = selected_variable.replace('_',' ').title()
        
        self.plot_button.config(text=f"Plot {strip}")
        
        
        dims = variable_data.dimensions

        if self.depth_key in dims:
            self.depth_dropdown.configure(state='readonly')
            self.depth_dropdown.set(list(self.depth_index_map.keys())[0])
            self.calculate_depth()
        else:
            self.depth_dropdown.configure(state='disabled')
        if self.time_key in dims:
            self.time_dropdown.configure(state='readonly')
            self.time_dropdown.set(list(self.time_index_map.keys())[0])
            self.calculate_time()
        else:
            self.time_dropdown.configure(state='disabled')

    def calculate_time(self, event=None):
        try:
            # Check if time dimension exists
            if not hasattr(self, 'time') or self.time is None:
                self.depth_time_label.config(text="No time dimension found")
                return
                
            # Check if time dropdown has a selection
            if not self.time_dropdown.get():
                self.depth_time_label.config(text="No time step selected")
                return
                
            # Get the selected time and its index
            selected_time = self.time_dropdown.get()
            if selected_time not in self.time_index_map:
                self.depth_time_label.config(text="Invalid time selection")
                return
                
            time_index = self.time_index_map[selected_time]
            
            # Convert time value
            try:
                global time_value
                time_value = nc.num2date(self.time[time_index], units=self.time_units)
            except Exception as e:
                self.depth_time_label.config(text=f"Error converting time: {str(e)}")
                return
            
            # Update label based on whether depth is available
            try:
                if hasattr(self, 'depth') and self.depth is not None and self.depth_dropdown.get():
                    selected_depth = self.depth_dropdown.get()
                    if selected_depth in self.depth_index_map:
                        depth_index = self.depth_index_map[selected_depth]
                        depth_value = self.depth[depth_index]
                        self.depth_time_label.config(text=f"{time_value} ({depth_value} {self.depth_units})")
                    else:
                        self.depth_time_label.config(text=f"{time_value}")
                else:
                    self.depth_time_label.config(text=f"{time_value}")
            except Exception as e:
                self.depth_time_label.config(text=f"{time_value} (Error with depth: {str(e)})")
                
            # Update statistics and plot
            try:
                self.show_statistics()
                self.plot_variable()
            except Exception as e:
                self.depth_time_label.config(text=f"{time_value} (Error updating display: {str(e)})")
            
        except Exception as e:
            error_msg = str(e)
            if "time_index_map" in error_msg:
                self.depth_time_label.config(text="Time index map not initialized")
            elif "time_units" in error_msg:
                self.depth_time_label.config(text="Time units not found")
            else:
                self.depth_time_label.config(text=f"Error calculating time: {error_msg}")

    def calculate_depth(self, event=None):
        try:
            if not hasattr(self, 'depth') or self.depth is None:
                self.depth_time_label.config(text="No depth dimension found")
                return
                
            selected_depth = self.depth_dropdown.get()
            depth_index = self.depth_index_map[selected_depth]
            global depth_value
            depth_value = self.depth[depth_index]
            
            # Update label based on whether time is available
            if hasattr(self, 'time') and self.time is not None:
                selected_time = self.time_dropdown.get()
                time_index = self.time_index_map[selected_time]
                time_value = nc.num2date(self.time[time_index], units=self.time_units)
                self.depth_time_label.config(text=f"{time_value} ({depth_value} {self.depth_units})")
            else:
                self.depth_time_label.config(text=f"Depth: {depth_value} {self.depth_units}")
                
            self.show_statistics()
            self.plot_variable()
            
        except Exception as e:
            self.depth_time_label.config(text=f"Error calculating depth: {e}")
            
    def show_statistics(self):
        try:
            if not hasattr(self, 'dataset') or self.dataset is None:
                self.statistics_label.config(text="No dataset loaded")
                return
                
            selected_variable = self.variable_dropdown.get()
            if not selected_variable:
                self.statistics_label.config(text="No variable selected")
                return
                
            if selected_variable not in self.dataset.variables:
                self.statistics_label.config(text=f"Variable {selected_variable} not found in dataset")
                return
                
            variable_data = self.dataset.variables[selected_variable]
            variable_dims = variable_data.dimensions
            data = None
            
            try:
                # Handle different dimension structures
                if len(variable_dims) == 1:
                    data = variable_data[:]
                elif len(variable_dims) == 2:
                    data = variable_data[:, :]
                elif len(variable_dims) == 3:
                    if hasattr(self, 'time') and self.time is not None:
                        selected_time_step = self.time_dropdown.get()
                        if not selected_time_step or selected_time_step not in self.time_index_map:
                            self.statistics_label.config(text="Invalid time selection")
                            return
                        time_index = self.time_index_map[selected_time_step]
                        data = variable_data[time_index, :, :]
                    else:
                        data = variable_data[:, :, :]
                elif len(variable_dims) == 4:
                    if hasattr(self, 'time') and self.time is not None and hasattr(self, 'depth') and self.depth is not None:
                        selected_time_step = self.time_dropdown.get()
                        selected_depth = self.depth_dropdown.get()
                        if not selected_time_step or selected_time_step not in self.time_index_map:
                            self.statistics_label.config(text="Invalid time selection")
                            return
                        if not selected_depth or selected_depth not in self.depth_index_map:
                            self.statistics_label.config(text="Invalid depth selection")
                            return
                        time_index = self.time_index_map[selected_time_step]
                        depth_index = self.depth_index_map[selected_depth]
                        data = variable_data[time_index, depth_index, :, :]
                    else:
                        data = variable_data[:, :, :, :]
                else:
                    self.statistics_label.config(text=f"Unsupported dimension structure: {variable_dims}")
                    return

                if data is None:
                    self.statistics_label.config(text="Unable to extract data")
                    return

                if np.ma.isMaskedArray(data):
                    data = data.compressed()
                    if len(data) == 0:
                        self.statistics_label.config(text="No valid data points")
                        return
                    
                mean = np.round(float(np.mean(data)), 4)
                median = np.round(float(np.median(data)), 4)
                std_dev = np.round(float(np.std(data)), 4)
                min_val = np.round(float(np.min(data)), 4)
                max_val = np.round(float(np.max(data)), 4)
                
                anomalies = data > mean + 2 * std_dev
                anomaly_count = np.sum(anomalies)
                
                stats_message = f"Mean: {mean}\nMedian: {median}\nStandard Deviation: {std_dev}\nDetected {anomaly_count} anomalies.\nMin: {min_val}\nMax: {max_val}"
                self.statistics_label.config(text=f"{stats_message}")
                
            except Exception as e:
                self.statistics_label.config(text=f"Error processing data: {str(e)}")
                
        except Exception as e:
            self.statistics_label.config(text=f"Error calculating statistics: {str(e)}")
        
    def toggle_gif_checkbox(self):
        if self.gif_checkbox_var.get():
            self.time_dropdown.configure(state='disabled')
        else:
            self.time_dropdown.configure(state='readonly')
            
    def select_gif_directory(self):
            self.gif_dir = filedialog.askdirectory()
            if self.gif_dir:
                self.gif_directory.config(text=f"{self.gif_dir}")   
                
    def on_plot_select(self, event):
        plot = self.plot_type_dropdown.get()
        if plot in ['contour', 'contourf']:
            self.levels_entry_var.set("Levels")
            self.levels_entry.pack(after=self.plot_type_dropdown, pady=5) 
        else:
            self.levels_entry.pack_forget()
        if plot == 'quiver':
            self.steps_var.set('Steps')
            self.steps_entry.pack(after=self.plot_type_dropdown, pady=5)
            self.scale_var.set('Scale')
            self.scale_entry.pack(after=self.plot_type_dropdown, pady=5)
        else:
            self.steps_entry.pack_forget()
            self.scale_entry.pack_forget()
        if plot == 'streamplot':
            self.density_var.set('Density') 
            self.density_entry.pack(after=self.plot_type_dropdown, pady=5)
            self.linewidth_var.set('Linewidth')
            self.linewidth_entry.pack(after=self.plot_type_dropdown, pady=5)
        else:
            self.density_entry.pack_forget()
            self.linewidth_entry.pack_forget()
       
    def update_hover_info(self, event):
        if event.inaxes:
            lon = event.xdata
            lat = event.ydata
            selected_variable = self.variable_dropdown.get()
        
        # Find the closest index
            lon_idx = np.argmin(np.abs(self.lon - lon))
            lat_idx = np.argmin(np.abs(self.lat - lat))

        # Extract the data value
            if self.depth_key in self.dataset.variables[selected_variable].dimensions:
                depth_index = self.depth_index_map[self.depth_dropdown.get()]
                time_index = self.time_index_map[self.time_dropdown.get()]
                data_value = self.dataset.variables[selected_variable][time_index, depth_index, lat_idx, lon_idx]
            else:
                time_index = self.time_index_map[self.time_dropdown.get()]
                data_value = self.dataset.variables[selected_variable][time_index, lat_idx, lon_idx]
                
            if np.ma.is_masked(data_value):
                value_str = "Masked"
            else:
                value_str = f"{data_value:.2f}"
            
            strip = selected_variable.replace('_',' ').title()
            hover_info = f"Lon: {lon:.2f}, Lat: {lat:.2f}\ni: {lon_idx} j: {lat_idx}\n{strip}: {value_str}"
            self.hover_label.config(text=hover_info)
            
    def forward(self):
        self.forward_pressed = True
        self.plot_variable()
        
    def backward(self):
        self.backward_pressed = True
        self.plot_variable()

    def plot_variable(self):
        try:
            if not hasattr(self, 'dataset') or self.dataset is None:
                self.data_display_text.insert(tk.END, "\nError: No dataset loaded\n")
                return
                
            selected_variable = self.variable_dropdown.get()
            if not selected_variable:
                self.data_display_text.insert(tk.END, "\nError: No variable selected\n")
                return
                
            if selected_variable not in self.dataset.variables:
                self.data_display_text.insert(tk.END, f"\nError: Variable {selected_variable} not found in dataset\n")
                return
                
            # Clear previous plot
            for widget in self.plot_frame.winfo_children():
                widget.destroy()
                
            # Get plot parameters
            try:
                selected_colormap = self.colormap_dropdown.get()
                if self.reverse_colormap_var.get():
                    selected_colormap = selected_colormap + '_r'

                plot_type = self.plot_type_dropdown.get()
                colorbar_orientation = self.colorbar_orientation_dropdown.get()
                selected_projection = self.projection_dropdown.get()
                
                # Parse numeric parameters
                try:
                    vmin = float(self.vmin_entry.get()) if self.vmin_entry.get() else None
                except ValueError:
                    vmin = None
                    
                try:
                    vmax = float(self.vmax_entry.get()) if self.vmax_entry.get() else None
                except ValueError:
                    vmax = None
                    
                try:
                    levels = int(self.levels_entry.get()) if self.levels_entry.get() else None
                except ValueError:
                    levels = None
                    
                try:
                    step = int(self.steps_entry.get()) if self.steps_entry.get() else 5
                except ValueError:
                    step = 5
                    
                try:
                    scale = float(self.scale_entry.get()) if self.scale_entry.get() else None
                except ValueError:
                    scale = None
                    
                try:
                    density = float(self.density_entry.get()) if self.density_entry.get() else 1
                except ValueError:
                    density = 1
                    
                try:
                    linewidth = float(self.linewidth_entry.get()) if self.linewidth_entry.get() else None
                except ValueError:
                    linewidth = None
                    
                try:
                    shrink = float(self.cbar_shrink_entry.get()) if self.cbar_shrink_entry.get() else 1
                except ValueError:
                    shrink = 1
                    
                try:
                    Range = int(self.time_steps_entry.get()) if self.time_steps_entry.get() else None
                except ValueError:
                    Range = None
                    
                # Parse extent if provided
                manual_extent = None
                if self.extent_entry.get():
                    try:
                        x_min, x_max, y_min, y_max = map(float, self.extent_entry.get().split(','))
                        manual_extent = [x_min, x_max, y_min, y_max]
                    except ValueError:
                        self.data_display_text.insert(tk.END, "\nWarning: Invalid extent format. Using default extent.\n")

                xlabel = self.xlabel_entry.get()
                ylabel = self.ylabel_entry.get()
                title = self.title_entry.get()
                
            except Exception as e:
                self.data_display_text.insert(tk.END, f"\nError parsing plot parameters: {str(e)}\n")
                return

            # Determine time steps to plot
            if self.gif_checkbox_var.get():
                time_steps = range(self.time_steps)
                if Range is not None:
                    time_steps = range(Range)
            else:
                current_index = self.time_dropdown.current()
                if self.forward_pressed:
                    current_index += 1
                    self.time_dropdown.current(current_index)
                elif self.backward_pressed:
                    current_index -= 1
                    self.time_dropdown.current(current_index)
                time_steps = [current_index]
                self.forward_pressed = False
                self.backward_pressed = False

            # Get variable data and attributes
            variable_data = self.dataset.variables[selected_variable]
            variable_dims = variable_data.dimensions
            var_units = getattr(variable_data, 'units', '')
            var_long_name = getattr(variable_data, 'long_name', selected_variable)
            
            # Determine if this is a geographic dataset
            is_geographic = (self.lat is not None and self.lon is not None)
            
            # Handle different dimension structures
            if len(variable_dims) == 1:  # 1D data
                # Simple line plot for 1D data
                data = variable_data[:]
                dim_name = variable_dims[0]
                dim_values = self.coord_vars[dim_name][:] if dim_name in self.coord_vars else np.arange(len(data))
                
                fig, ax = plt.subplots()
                ax.plot(dim_values, data)
                ax.set_xlabel(dim_name)
                ax.set_ylabel(var_long_name)
                if title:
                    ax.set_title(title)
                else:
                    ax.set_title(f"{var_long_name} vs {dim_name}")
                
                canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
                
            elif len(variable_dims) == 2:  # 2D data
                # Try to determine if this is a spatial slice
                if is_geographic:
                    # Assume lat/lon ordering
                    data = variable_data[:]
                    if self.lat.shape[0] == data.shape[0] and self.lon.shape[0] == data.shape[1]:
                        lon, lat = np.meshgrid(self.lon, self.lat)
                    else:
                        # Non-geographic 2D data
                        dim1 = self.coord_vars[variable_dims[0]][:] if variable_dims[0] in self.coord_vars else np.arange(data.shape[0])
                        dim2 = self.coord_vars[variable_dims[1]][:] if variable_dims[1] in self.coord_vars else np.arange(data.shape[1])
                        lon, lat = np.meshgrid(dim2, dim1)
                else:
                    # Non-geographic 2D data
                    data = variable_data[:]
                    dim1 = self.coord_vars[variable_dims[0]][:] if variable_dims[0] in self.coord_vars else np.arange(data.shape[0])
                    dim2 = self.coord_vars[variable_dims[1]][:] if variable_dims[1] in self.coord_vars else np.arange(data.shape[1])
                    lon, lat = np.meshgrid(dim2, dim1)
                
                self._plot_2d_data(data, lon, lat, var_units, var_long_name, plot_type, selected_colormap,
                                 vmin, vmax, levels, colorbar_orientation, shrink, xlabel, ylabel, title,
                                 is_geographic, selected_projection, manual_extent)
                
            elif len(variable_dims) == 3:  # 3D data (time + 2D)
                for t in time_steps:
                    try:
                        if self.gif_checkbox_var.get():
                            plt.ioff()
                            
                        if self.time is not None:
                            time_value = nc.num2date(self.time[t], units=self.time_units)
                        else:
                            time_value = f"Step {t}"
                            
                        data = variable_data[t, :, :]
                        
                        if is_geographic:
                            lon, lat = np.meshgrid(self.lon, self.lat)
                        else:
                            dim1 = self.coord_vars[variable_dims[1]][:] if variable_dims[1] in self.coord_vars else np.arange(data.shape[0])
                            dim2 = self.coord_vars[variable_dims[2]][:] if variable_dims[2] in self.coord_vars else np.arange(data.shape[1])
                            lon, lat = np.meshgrid(dim2, dim1)
                            
                        self._plot_2d_data(data, lon, lat, var_units, var_long_name, plot_type, selected_colormap,
                                         vmin, vmax, levels, colorbar_orientation, shrink, xlabel, ylabel,
                                         f"{title or var_long_name} ({time_value})", is_geographic,
                                         selected_projection, manual_extent)
                        
                    except Exception as e:
                        print(f"Error plotting variable at time step {t}: {e}")
                        
            elif len(variable_dims) == 4:  # 4D data (time + depth + 2D)
                selected_depth = self.depth_dropdown.get()
                depth_index = self.depth_index_map[selected_depth]
                
                for t in time_steps:
                    try:
                        if self.gif_checkbox_var.get():
                            plt.ioff()
                            
                        if self.time is not None:
                            time_value = nc.num2date(self.time[t], units=self.time_units)
                        else:
                            time_value = f"Step {t}"
                            
                        data = variable_data[t, depth_index, :, :]
                        
                        if is_geographic:
                            lon, lat = np.meshgrid(self.lon, self.lat)
                        else:
                            dim1 = self.coord_vars[variable_dims[2]][:] if variable_dims[2] in self.coord_vars else np.arange(data.shape[0])
                            dim2 = self.coord_vars[variable_dims[3]][:] if variable_dims[3] in self.coord_vars else np.arange(data.shape[1])
                            lon, lat = np.meshgrid(dim2, dim1)
                            
                        depth_str = f" at {selected_depth}" if selected_depth else f" at depth {depth_index}"
                        self._plot_2d_data(data, lon, lat, var_units, var_long_name, plot_type, selected_colormap,
                                         vmin, vmax, levels, colorbar_orientation, shrink, xlabel, ylabel,
                                         f"{title or var_long_name} ({time_value}){depth_str}", is_geographic,
                                         selected_projection, manual_extent)
                        
                    except Exception as e:
                        print(f"Error plotting variable at time step {t}: {e}")
                        
            else:
                # Handle other dimension structures
                print(f"Unsupported dimension structure: {variable_dims}")
                self.data_display_text.insert(tk.END, f"\nWarning: Unsupported dimension structure: {variable_dims}\n")
                
        except Exception as e:
            self.data_display_text.insert(tk.END, f"\nError in plot_variable: {str(e)}\n")
            return

    def show_gif_in_window(self, gif_path):
        gif_window = Toplevel(self.root)
        gif_window.title("GIF Preview")
        gif_window.geometry("800x520")

        gif_label = Label(gif_window)
        gif_label.pack()

        playback_control_frame = tk.Frame(gif_window)
        playback_control_frame.pack(pady=5)
        
        slow_button = tb.Button(playback_control_frame, text='<<', command=self.slow_gif, bootstyle='warning-outline')
        slow_button.pack(side=tk.LEFT, padx=5)

        play_button = tb.Button(playback_control_frame, text="Play", command=self.play_gif, bootstyle='success-outline')
        play_button.pack(side=tk.LEFT, padx=2)

        pause_button = tb.Button(playback_control_frame, text="Pause", command=self.pause_gif, bootstyle='warning-outline')
        pause_button.pack(side=tk.LEFT, padx=2)

        reverse_button = tb.Button(playback_control_frame, text="Reverse", command=self.reverse_gif, bootstyle='info-outline')
        reverse_button.pack(side=tk.LEFT,padx=2)

        stop_button = tb.Button(playback_control_frame, text="Stop", command=self.stop_gif, bootstyle='danger-outline')
        stop_button.pack(side=tk.LEFT,padx=2)
        
        speed_button = tb.Button(playback_control_frame, text='>>', command=self.speed_gif, bootstyle='warning-outline')
        speed_button.pack(side=tk.LEFT, padx=5)

        self.gif_frames = []
        self.gif_path = gif_path
        self.gif_label = gif_label
        self.gif_window = gif_window
        self.gif_playing = False
        self.gif_paused = False
        self.gif_reversed = False
        self.current_frame_index = 0
        self.playback_speed = 100

        with Image.open(gif_path) as gif:
            for frame in range(gif.n_frames):
                gif.seek(frame)
                frame_image = ImageTk.PhotoImage(gif.convert("RGBA"))
                self.gif_frames.append(frame_image)
                
        self.play_gif()
        
    def play_gif(self):
        self.gif_playing = True
        self.gif_paused = False
        self.gif_reversed = False
        self.update_gif()

    def pause_gif(self):
        self.gif_playing = False
        self.gif_paused = True

    def reverse_gif(self):
        self.gif_playing = True
        self.gif_paused = False
        self.gif_reversed = True
        self.update_gif()

    def stop_gif(self):
        self.gif_playing = False
        self.gif_paused = False
        self.gif_reversed = False
        self.current_frame_index = 0
        self.gif_label.configure(image=self.gif_frames[self.current_frame_index])
        self.playback_speed = 100
        
    def slow_gif(self):
        self.playback_speed += 25
            
    def speed_gif(self): 
        if self.playback_speed > 25:
            self.playback_speed -= 25

    def update_gif(self):
        if self.gif_playing and not self.gif_paused:
            if self.gif_reversed:
                self.current_frame_index = (self.current_frame_index - 1) % len(self.gif_frames)
            else:
                self.current_frame_index = (self.current_frame_index + 1) % len(self.gif_frames)
            self.gif_label.configure(image=self.gif_frames[self.current_frame_index])
            self.gif_window.after(self.playback_speed, self.update_gif)
            
    def change_theme(self, theme_name):
        tb.Style().theme_use(theme_name)

    def _plot_2d_data(self, data, lon, lat, var_units, var_long_name, plot_type, selected_colormap,
                     vmin, vmax, levels, colorbar_orientation, shrink, xlabel, ylabel, title,
                     is_geographic, selected_projection, manual_extent):
        """Helper method to plot 2D data with various options."""
        try:
            # Create figure and axis
            if is_geographic:
                fig = plt.figure(figsize=(10, 8))
                ax = plt.axes(projection=self.projections[selected_projection])
                
                # Set map extent
                if manual_extent:
                    ax.set_extent(manual_extent, crs=ccrs.PlateCarree())
                else:
                    ax.set_extent([lon.min(), lon.max(), lat.min(), lat.max()], crs=ccrs.PlateCarree())
                
                # Add map features
                if self.gridlines_var.get():
                    try:
                        alpha = float(self.alpha_entry.get()) if self.alpha_entry.get() else 0.5
                    except ValueError:
                        alpha = 0.5
                    ax.gridlines(draw_labels=True, alpha=alpha)
                
                if self.ocean_checkbox_var.get():
                    ax.add_feature(cfeature.OCEAN)
                if self.land_checkbox_var.get():
                    ax.add_feature(cfeature.LAND)
                
                # Plot data
                if plot_type == 'pcolormesh':
                    plot = ax.pcolormesh(lon, lat, data, transform=ccrs.PlateCarree(),
                                       cmap=selected_colormap, vmin=vmin, vmax=vmax)
                elif plot_type == 'contour':
                    plot = ax.contour(lon, lat, data, transform=ccrs.PlateCarree(),
                                    cmap=selected_colormap, levels=levels, vmin=vmin, vmax=vmax)
                elif plot_type == 'contourf':
                    plot = ax.contourf(lon, lat, data, transform=ccrs.PlateCarree(),
                                     cmap=selected_colormap, levels=levels, vmin=vmin, vmax=vmax)
                elif plot_type == 'imshow':
                    plot = ax.imshow(data, transform=ccrs.PlateCarree(), cmap=selected_colormap,
                                   vmin=vmin, vmax=vmax, extent=[lon.min(), lon.max(), lat.min(), lat.max()])
                else:
                    plot = ax.pcolormesh(lon, lat, data, transform=ccrs.PlateCarree(),
                                       cmap=selected_colormap, vmin=vmin, vmax=vmax)
                
                # Add colorbar
                cbar = plt.colorbar(plot, ax=ax, orientation=colorbar_orientation, shrink=shrink)
                cbar.set_label(f"{var_long_name} [{var_units}]")
                
                # Set labels and title
                if xlabel:
                    ax.set_xlabel(xlabel)
                if ylabel:
                    ax.set_ylabel(ylabel)
                if title:
                    ax.set_title(title)
                
            else:
                # Non-geographic plot
                fig, ax = plt.subplots(figsize=(10, 8))
                
                if plot_type == 'pcolormesh':
                    plot = ax.pcolormesh(lon, lat, data, cmap=selected_colormap, vmin=vmin, vmax=vmax)
                elif plot_type == 'contour':
                    plot = ax.contour(lon, lat, data, cmap=selected_colormap, levels=levels, vmin=vmin, vmax=vmax)
                elif plot_type == 'contourf':
                    plot = ax.contourf(lon, lat, data, cmap=selected_colormap, levels=levels, vmin=vmin, vmax=vmax)
                elif plot_type == 'imshow':
                    plot = ax.imshow(data, cmap=selected_colormap, vmin=vmin, vmax=vmax)
                else:
                    plot = ax.pcolormesh(lon, lat, data, cmap=selected_colormap, vmin=vmin, vmax=vmax)
                
                # Add colorbar
                cbar = plt.colorbar(plot, ax=ax, orientation=colorbar_orientation, shrink=shrink)
                cbar.set_label(f"{var_long_name} [{var_units}]")
                
                # Set labels and title
                if xlabel:
                    ax.set_xlabel(xlabel)
                if ylabel:
                    ax.set_ylabel(ylabel)
                if title:
                    ax.set_title(title)
            
            # Add the plot to the GUI
            canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            
            # Add navigation toolbar
            toolbar = NavigationToolbar2Tk(canvas, self.plot_frame)
            toolbar.update()
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            
            # Connect hover event
            canvas.mpl_connect('motion_notify_event', self.update_hover_info)
            
        except Exception as e:
            print(f"Error in _plot_2d_data: {e}")
            self.data_display_text.insert(tk.END, f"\nError plotting data: {str(e)}\n")
            return

def main():
    parser = argparse.ArgumentParser(description='Run NC² NetCDF viewer.')
    parser.add_argument('file', nargs='?', help='NetCDF file to open')

    args = parser.parse_args()
    file_path = os.path.abspath(args.file) if args.file else None

    root = tb.Window(themename='darkly')
    app = NC2(root, file_path)
    root.mainloop()


if __name__ == "__main__":
    main()
