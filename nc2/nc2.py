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
import tkinter.messagebox as messagebox

class NC2:
    def __init__(self, root, file_path=None):
        self.root = root
        self.root.title("NC²")
        
        # Set window icon
        icon_path = importlib.resources.files('nc2').joinpath('Logo3.png')
        icon_image = Image.open(str(icon_path))
        # Convert to icon format (ICO for Windows)
        icon_photo = ImageTk.PhotoImage(icon_image)
        self.root.iconphoto(True, icon_photo)
        
        self.file_path = file_path
        self.dataset = None
        self.variable_names = []
        self.depth_levels = []
        self.current_figure = None
        self.forward_pressed = False
        self.backward_pressed = False
        
        # Add playback control variables
        self.is_playing = False
        self.play_speed = 500  # milliseconds between frames
        self.play_direction = 1  # 1 for forward, -1 for reverse
        self.after_id = None  # To store the after() callback ID
        
        # Add plot state tracking
        self.current_plot = None
        self.current_canvas = None
        self.current_ax = None
        self.current_cbar = None
        
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
        
        # Add vertical slice tracking
        self.slice_type = tk.StringVar(value="lon_depth")  # Default to longitude-depth slice
        self.slice_position = 0  # Default slice position
        self.slice_slider = None
        self.slice_value_label = None
        
        logo_path = importlib.resources.files('nc2').joinpath('Logo3.png')
        self.logo = ImageTk.PhotoImage(file=str(logo_path))
        
        self.create_widgets()
        
        if self.file_path:
            self.load_netcdf_file()
            
# ********** Widgets ********** #

    def create_widgets(self):
        # Set minimum window size
        self.root.minsize(1000, 768)
        
        # Create main container with grid layout
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights
        main_container.grid_columnconfigure(1, weight=1)  # Plot area expands
        main_container.grid_rowconfigure(0, weight=1)     # Main content expands
        
        # Left control panel - fixed width
        control_frame_left = tk.Frame(main_container, padx=10, pady=10, width=200)
        control_frame_left.grid(row=0, column=0, sticky='nsew')
        control_frame_left.grid_propagate(False)  # Prevent frame from shrinking
        
        width, height = self.logo.width(), self.logo.height()
        self.logo_label = Label(control_frame_left, width=width, height=height, image=self.logo)
        self.logo_label.pack(pady=5)
        
        self.select_file_button = tb.Button(control_frame_left, text="Select NetCDF File", command=self.select_file, bootstyle='info')
        self.select_file_button.pack(pady=10, fill=tk.X)
        
        self.variable_dropdown_label = tb.Label(control_frame_left, text="Select Variable:", font=("Helvetica", 12))
        self.variable_dropdown_label.pack(pady=5)
        
        self.variable_dropdown = tb.Combobox(control_frame_left, state="readonly", bootstyle='info')
        self.variable_dropdown.pack(pady=5, fill=tk.X)
        self.variable_dropdown.bind("<<ComboboxSelected>>", self.on_variable_selected)
        
        self.time_dropdown_label = tb.Label(control_frame_left, text="Time Step:", font=("Helvetica", 12))
        self.time_dropdown_label.pack(pady=5)
        
        # Create frame for time slider and its value
        time_frame = tb.Frame(control_frame_left)
        time_frame.pack(fill=tk.X, pady=5)
        
        # Add time value label above slider
        self.time_value_label = tb.Label(time_frame, text="0", bootstyle='info')
        self.time_value_label.pack(fill=tk.X, pady=(0, 5))
        
        # Replace time dropdown with slider
        self.time_slider = tb.Scale(time_frame, bootstyle='info', orient='horizontal', length=180)
        self.time_slider.pack(fill=tk.X)
        self.time_slider.configure(state='disabled')
        self.time_slider.bind("<ButtonRelease-1>", self.calculate_time)
        self.time_slider.bind("<B1-Motion>", self.update_time_label)

        self.depth_dropdown_label = tb.Label(control_frame_left, text="Depth Level:", font=("Helvetica", 12))
        self.depth_dropdown_label.pack(pady=5)
        
        # Create frame for depth slider and its value
        depth_frame = tb.Frame(control_frame_left)
        depth_frame.pack(fill=tk.X, pady=5)
        
        # Add depth value label above slider
        self.depth_value_label = tb.Label(depth_frame, text="0", bootstyle='info')
        self.depth_value_label.pack(fill=tk.X, pady=(0, 5))
        
        # Replace depth dropdown with slider
        self.depth_slider = tb.Scale(depth_frame, bootstyle='info', orient='horizontal', length=180)
        self.depth_slider.pack(fill=tk.X)
        self.depth_slider.configure(state='disabled')
        self.depth_slider.bind("<ButtonRelease-1>", self.calculate_depth)
        self.depth_slider.bind("<B1-Motion>", self.update_depth_label)

        self.depth_time_label = tb.Label(control_frame_left, text='', bootstyle='warning')
        self.depth_time_label.pack(pady=10)
        
        self.statistics_label = tb.Label(control_frame_left, text='', bootstyle='info')
        self.statistics_label.pack(pady=5)
        
        self.hover_label = tb.Label(control_frame_left, text='', font=("Helvetica", 12), bootstyle='warning')
        self.hover_label.pack(pady=10)
        
        # Create bottom button frame
        bottom_buttons = tb.Frame(control_frame_left)
        bottom_buttons.pack(side=tk.BOTTOM, pady=10, fill=tk.X)
        
        # Add Plot Variable and Create GIF buttons side by side
        self.plot_button = tb.Button(bottom_buttons, text="Plot Variable", command=self.plot_variable, bootstyle='info')
        self.plot_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        self.make_gif_button = tb.Button(bottom_buttons, text="Create GIF", command=self.show_gif_settings, bootstyle='warning')
        self.make_gif_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        # Right control panel - fixed width
        control_frame_right = tk.Frame(main_container, bg='grey16', padx=10, pady=10, width=200)
        control_frame_right.grid(row=0, column=2, sticky='nsew')
        control_frame_right.grid_propagate(False)  # Prevent frame from shrinking
        
        self.plot_type_label = tb.Label(control_frame_right, text="Select Plot Type:", font=("Helvetica", 12))
        self.plot_type_label.pack(pady=5)
        
        self.plot_type_dropdown = tb.Combobox(control_frame_right, state="readonly", bootstyle='success')
        self.plot_type_dropdown['values'] = ['pcolormesh', 'contour', 'contourf', 'imshow', 'quiver', 'streamplot']
        self.plot_type_dropdown.set('pcolormesh')
        self.plot_type_dropdown.pack(pady=5, fill=tk.X)
        self.plot_type_dropdown.bind("<<ComboboxSelected>>", lambda e: (self.on_plot_select(e), self.plot_variable()))
        
        self.levels_entry_var = tk.StringVar()
        self.levels_entry = tb.Entry(control_frame_right, textvariable=self.levels_entry_var, bootstyle='secondary')
        self.levels_entry.bind('<Return>', lambda e: self.plot_variable())
        self.levels_entry.bind('<FocusOut>', lambda e: self.plot_variable())
        
        self.steps_var = tk.StringVar()
        self.steps_entry = tb.Entry(control_frame_right, textvariable=self.steps_var, bootstyle='secondary')
        self.steps_entry.bind('<Return>', lambda e: self.plot_variable())
        self.steps_entry.bind('<FocusOut>', lambda e: self.plot_variable())
        
        self.scale_var = tk.StringVar()
        self.scale_entry = tb.Entry(control_frame_right, textvariable=self.scale_var, bootstyle='secondary')
        self.scale_entry.bind('<Return>', lambda e: self.plot_variable())
        self.scale_entry.bind('<FocusOut>', lambda e: self.plot_variable())
        
        self.density_var = tk.StringVar()
        self.density_entry = tb.Entry(control_frame_right, textvariable=self.density_var, bootstyle='secondary')
        self.density_entry.bind('<Return>', lambda e: self.plot_variable())
        self.density_entry.bind('<FocusOut>', lambda e: self.plot_variable())
        
        self.linewidth_var = tk.StringVar()
        self.linewidth_entry = tb.Entry(control_frame_right, textvariable=self.linewidth_var, bootstyle='secondary')
        self.linewidth_entry.bind('<Return>', lambda e: self.plot_variable())
        self.linewidth_entry.bind('<FocusOut>', lambda e: self.plot_variable())
        
        self.colormap_dropdown_label = tb.Label(control_frame_right, text="Select Colormap:", font=("Helvetica", 12))
        self.colormap_dropdown_label.pack(pady=5)
        
        self.colormap_dropdown = tb.Combobox(control_frame_right, state="readonly", bootstyle='success')
        self.colormap_dropdown.pack(pady=5, fill=tk.X)
        self.colormap_dropdown.bind("<<ComboboxSelected>>", lambda e: self.plot_variable())
        
        self.load_colormaps()
        
        self.reverse_colormap_var = tk.BooleanVar()
        self.reverse_colormap = tb.Checkbutton(control_frame_right, text='Reverse', variable=self.reverse_colormap_var, 
                                             bootstyle='danger, round-toggle', command=self.plot_variable)
        self.reverse_colormap.pack(pady=5)

        self.colorbar_orientation_label = tb.Label(control_frame_right, text="Colorbar Orientation:", font=("Helvetica", 12))
        self.colorbar_orientation_label.pack(pady=5)
        self.colorbar_orientation_dropdown = tb.Combobox(control_frame_right, state="readonly", bootstyle='secondary')
        self.colorbar_orientation_dropdown['values'] = ['vertical', 'horizontal']
        self.colorbar_orientation_dropdown.set('vertical')
        self.colorbar_orientation_dropdown.pack(pady=5, fill=tk.X)
        self.colorbar_orientation_dropdown.bind("<<ComboboxSelected>>", lambda e: self.plot_variable())
        
        self.cbar_shrink_entry_var = tk.StringVar()
        self.cbar_shrink_entry_var.set("Shrink (0-1)")
        self.cbar_shrink_entry = tb.Entry(control_frame_right, textvariable=self.cbar_shrink_entry_var, bootstyle='secondary')
        self.cbar_shrink_entry.pack(pady=5, fill=tk.X)
        self.cbar_shrink_entry.bind('<Return>', lambda e: self.plot_variable())
        self.cbar_shrink_entry.bind('<FocusOut>', lambda e: self.plot_variable())
        
        self.vmax_label_entry_var = tk.StringVar()
        self.vmax_label_entry_var.set('V-Max')
        self.vmax_entry = tb.Entry(control_frame_right, textvariable=self.vmax_label_entry_var, bootstyle='success')
        self.vmax_entry.pack(pady=5, fill=tk.X)
        self.vmax_entry.bind('<Return>', lambda e: self.plot_variable())
        self.vmax_entry.bind('<FocusOut>', lambda e: self.plot_variable())
        
        self.vmin_label_entry_var = tk.StringVar()
        self.vmin_label_entry_var.set("V-Min")
        self.vmin_entry = tb.Entry(control_frame_right, textvariable=self.vmin_label_entry_var, bootstyle='danger')
        self.vmin_entry.pack(pady=5, fill=tk.X)
        self.vmin_entry.bind('<Return>', lambda e: self.plot_variable())
        self.vmin_entry.bind('<FocusOut>', lambda e: self.plot_variable())
        
        self.extent_label_var = tk.StringVar()
        self.extent_label_var.set("Extents [x0, x1, y0, y1]")
        self.extent_entry = tb.Entry(control_frame_right, textvariable=self.extent_label_var, bootstyle='secondary')
        self.extent_entry.pack(pady=5, fill=tk.X)
        self.extent_entry.bind('<Return>', lambda e: self.plot_variable())
        self.extent_entry.bind('<FocusOut>', lambda e: self.plot_variable())
        
        self.xlabel_label = tb.Label(control_frame_right, text="X-axis Label:", font=("Helvetica", 12))
        self.xlabel_label.pack(pady=5)
        self.xlabel_entry = tb.Entry(control_frame_right, bootstyle='secondary')
        self.xlabel_entry.pack(pady=5, fill=tk.X)
        self.xlabel_entry.bind('<Return>', lambda e: self.plot_variable())
        self.xlabel_entry.bind('<FocusOut>', lambda e: self.plot_variable())
        
        self.ylabel_label = tb.Label(control_frame_right, text="Y-axis Label:", font=("Helvetica", 12))
        self.ylabel_label.pack(pady=5)
        self.ylabel_entry = tb.Entry(control_frame_right, bootstyle='secondary')
        self.ylabel_entry.pack(pady=5, fill=tk.X)
        self.ylabel_entry.bind('<Return>', lambda e: self.plot_variable())
        self.ylabel_entry.bind('<FocusOut>', lambda e: self.plot_variable())
        
        self.title_label = Label(control_frame_right, text="Plot Title:", font=("Helvetica", 12))
        self.title_label.pack(pady=5)
        self.title_entry = tb.Entry(control_frame_right, bootstyle='secondary')
        self.title_entry.pack(pady=5, fill=tk.X)
        self.title_entry.bind('<Return>', lambda e: self.plot_variable())
        self.title_entry.bind('<FocusOut>', lambda e: self.plot_variable())
        
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
        self.theme_dropdown.pack(pady=5, fill=tk.X)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.grid(row=0, column=1, sticky='nsew')
        
        # Create main tab
        main_tab = tk.Frame(self.notebook)
        self.notebook.add(main_tab, text='Main View')
        
        # Create vertical slice tab
        slice_tab = tk.Frame(self.notebook)
        self.notebook.add(slice_tab, text='Vertical Slices')
        
        # Central plot area with data display at bottom for main tab
        central_frame = tk.Frame(main_tab)
        central_frame.pack(fill=tk.BOTH, expand=True)
        central_frame.grid_rowconfigure(0, weight=1)  # Plot area expands
        central_frame.grid_columnconfigure(0, weight=1)  # Plot area expands horizontally

        # Plot frame for main tab
        self.plot_frame = tk.Frame(central_frame, bg='grey12', padx=10, pady=10)
        self.plot_frame.grid(row=0, column=0, sticky='nsew')

        # Data display frame at bottom for main tab
        self.data_display_frame = tk.Frame(central_frame, bg='grey14', padx=10, pady=5, height=150)
        self.data_display_frame.grid(row=1, column=0, sticky='ew')
        self.data_display_frame.grid_propagate(False)  # Keep fixed height

        self.data_display_text = tk.Text(self.data_display_frame, bg='grey12', fg='lime', height=8, wrap=tk.WORD, font=("Helvetica", 10))
        self.data_display_text.pack(fill=tk.BOTH, expand=True)

        central_longitude = 0
        central_latitude = 0
        
        self.projections = {
            'PlateCarree': ccrs.PlateCarree(central_longitude=central_longitude),
            'Mercator': ccrs.Mercator(central_longitude=central_longitude),
            'Orthographic': ccrs.Orthographic(central_longitude=central_longitude),
            'LambertConformal': ccrs.LambertConformal(central_longitude=central_longitude),
            'Mollweide': ccrs.Mollweide(central_longitude=central_longitude),
            'Robinson': ccrs.Robinson(central_longitude=central_longitude),
            'TransverseMercator': ccrs.TransverseMercator(central_longitude=central_longitude),
            'AlbersEqualArea': ccrs.AlbersEqualArea(central_longitude=central_longitude),
            'AzimuthalEquidistant': ccrs.AzimuthalEquidistant(central_longitude=central_longitude),
            'Geostationary': ccrs.Geostationary(central_longitude=central_longitude),
            'InterruptedGoodeHomolosine': ccrs.InterruptedGoodeHomolosine(central_longitude=central_longitude),
            'LambertAzimuthalEqualArea': ccrs.LambertAzimuthalEqualArea(central_longitude=central_longitude),
            'NorthPolarStereo': ccrs.NorthPolarStereo(central_longitude=central_longitude),
            'SouthPolarStereo': ccrs.SouthPolarStereo(central_longitude=central_longitude),
            'Stereographic': ccrs.Stereographic(central_longitude=central_longitude),
            'Sinusoidal': ccrs.Sinusoidal(central_longitude=central_longitude),
            'EuroPP': ccrs.EuroPP(),
            'OSGB': ccrs.OSGB(),
            'RotatedPole': ccrs.RotatedPole()
        }
        
        self.projection_dropdown_label = tb.Label(control_frame_right, text="Projection:", font=("Helvetica", 12))
        self.projection_dropdown_label.pack(pady=5)
        self.projection_dropdown = tb.Combobox(control_frame_right, values=list(self.projections.keys()), bootstyle='success')
        self.projection_dropdown.set('PlateCarree')
        self.projection_dropdown.pack(pady=5, fill=tk.X)
        self.projection_dropdown.bind("<<ComboboxSelected>>", lambda e: self.plot_variable())
        
        gridlines_frame = tb.Frame(control_frame_right)
        gridlines_frame.pack(pady=5, fill=tk.X)
        
        self.gridlines_var = tk.BooleanVar()
        self.gridlines = tb.Checkbutton(gridlines_frame, text='Gridlines', variable=self.gridlines_var, 
                                      bootstyle='danger, round-toggle', command=self.plot_variable)
        self.gridlines.pack(side=tk.LEFT, pady=5, padx=2)
        
        self.alpha_entry_var = tk.StringVar()
        self.alpha_entry_var.set('Alpha')
        self.alpha_entry = tb.Entry(gridlines_frame, textvariable=self.alpha_entry_var, bootstyle='secondary', width=5)
        self.alpha_entry.pack(side=tk.LEFT, pady=5, padx=2, expand=True)
        self.alpha_entry.bind('<Return>', lambda e: self.plot_variable())
        self.alpha_entry.bind('<FocusOut>', lambda e: self.plot_variable())
        
        checkboxes_frame = tb.Frame(control_frame_right)
        checkboxes_frame.pack(pady=5, fill=tk.X)
        
        self.ocean_checkbox_var = tk.BooleanVar()
        self.ocean_checkbox = tb.Checkbutton(checkboxes_frame, text='Ocean', variable=self.ocean_checkbox_var, 
                                           bootstyle='danger, round-toggle', command=self.plot_variable)
        self.ocean_checkbox.pack(side=tk.LEFT, pady=5, padx=2)
        
        self.land_checkbox_var = tk.BooleanVar()
        self.land_checkbox = tb.Checkbutton(checkboxes_frame, text='Land', variable=self.land_checkbox_var, 
                                          bootstyle='danger, round-toggle', command=self.plot_variable)
        self.land_checkbox.pack(side=tk.LEFT, pady=5, padx=2)

        # Add vertical slice controls to slice tab
        slice_control_frame = tk.Frame(slice_tab, padx=10, pady=10)
        slice_control_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # Create central frame for vertical slice plot and data display
        slice_central_frame = tk.Frame(slice_tab)
        slice_central_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        slice_central_frame.grid_rowconfigure(0, weight=1)  # Plot area expands
        slice_central_frame.grid_columnconfigure(0, weight=1)  # Plot area expands horizontally
        
        # Slice type selection
        slice_type_label = tb.Label(slice_control_frame, text="Slice Type:", font=("Helvetica", 12))
        slice_type_label.pack(pady=5)
        
        slice_type_frame = tb.Frame(slice_control_frame)
        slice_type_frame.pack(fill=tk.X, pady=5)
        
        lon_depth_radio = tb.Radiobutton(slice_type_frame, text="Longitude-Depth", 
                                       variable=self.slice_type, value="lon_depth",
                                       command=self.update_slice_controls, bootstyle='info-toolbutton')
        lon_depth_radio.pack(side=tk.LEFT, padx=5)
        
        lat_depth_radio = tb.Radiobutton(slice_type_frame, text="Latitude-Depth", 
                                       variable=self.slice_type, value="lat_depth",
                                       command=self.update_slice_controls, bootstyle='info-toolbutton')
        lat_depth_radio.pack(side=tk.LEFT, padx=5)
        
        # Slice position slider
        self.slice_position_label = tb.Label(slice_control_frame, text="Slice Position:", font=("Helvetica", 12))
        self.slice_position_label.pack(pady=5)
        
        self.slice_value_label = tb.Label(slice_control_frame, text="0", bootstyle='info')
        self.slice_value_label.pack(pady=5)
        
        self.slice_slider = tb.Scale(slice_control_frame, bootstyle='info', orient='horizontal', length=180)
        self.slice_slider.pack(fill=tk.X, pady=5)
        self.slice_slider.bind("<ButtonRelease-1>", self.plot_vertical_slice)
        self.slice_slider.bind("<B1-Motion>", self.update_slice_label)
        
        # Time slider for vertical slice
        self.slice_time_label = tb.Label(slice_control_frame, text="Time Step:", font=("Helvetica", 12))
        self.slice_time_label.pack(pady=5)
        
        self.slice_time_value_label = tb.Label(slice_control_frame, text="0", bootstyle='info')
        self.slice_time_value_label.pack(pady=5)
        
        self.slice_time_slider = tb.Scale(slice_control_frame, bootstyle='info', orient='horizontal', length=180)
        self.slice_time_slider.pack(fill=tk.X, pady=5)
        self.slice_time_slider.bind("<ButtonRelease-1>", self.plot_vertical_slice)
        self.slice_time_slider.bind("<B1-Motion>", self.update_slice_time_label)
        
        # Plot controls for vertical slice
        self.slice_plot_button = tb.Button(slice_control_frame, text="Plot Slice", 
                                         command=self.plot_vertical_slice, bootstyle='info')
        self.slice_plot_button.pack(pady=10, fill=tk.X)
        
        # Create plot frame for vertical slice
        self.slice_plot_frame = tk.Frame(slice_central_frame, bg='grey12', padx=10, pady=10)
        self.slice_plot_frame.grid(row=0, column=0, sticky='nsew')
        
        # Create data display frame for vertical slice
        self.slice_data_display_frame = tk.Frame(slice_central_frame, bg='grey14', padx=10, pady=5, height=150)
        self.slice_data_display_frame.grid(row=1, column=0, sticky='ew')
        self.slice_data_display_frame.grid_propagate(False)  # Keep fixed height
        
        self.slice_data_display_text = tk.Text(self.slice_data_display_frame, bg='grey12', fg='lime', 
                                             height=8, wrap=tk.WORD, font=("Helvetica", 10))
        self.slice_data_display_text.pack(fill=tk.BOTH, expand=True)

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
            # Open dataset with chunking enabled for better performance with large files
            self.dataset = nc.Dataset(self.file_path, mode='r', format='NETCDF4')
            
            # Get all variables and their dimensions - use lazy loading
            self.variable_names = list(self.dataset.variables.keys())
            
            # Initialize coordinate and dimension tracking
            self.coord_vars = {}
            self.dim_vars = {}
            self.dim_info = {}
            
            # First pass: identify all dimensions and their sizes - avoid loading data
            for dim_name, dim in self.dataset.dimensions.items():
                self.dim_vars[dim_name] = dim
                self.dim_info[dim_name] = {
                    'size': len(dim),
                    'is_unlimited': dim.isunlimited(),
                    'coord_var': None,
                    'type': None
                }
            
            # Second pass: identify coordinate variables and their types - minimize data loading
            for var_name, var in self.dataset.variables.items():
                # Check if this is a coordinate variable (matches its dimension name)
                if var_name in self.dataset.dimensions:
                    # Store variable reference without loading data
                    self.coord_vars[var_name] = var
                    self.dim_info[var_name]['coord_var'] = var
                    
                    # Try to determine dimension type without loading data
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
            
            # Identify primary dimensions based on common patterns - references only
            self.time = None
            self.time_key = None
            self.depth = None
            self.depth_key = None
            self.lat = None
            self.lon = None
            self.lat_key = None
            self.lon_key = None
            
            # Find time dimension - store reference only
            for dim_name, info in self.dim_info.items():
                if info['type'] == 'time':
                    self.time = self.coord_vars[dim_name]
                    self.time_key = dim_name
                    break
            
            # Find vertical dimension - store reference only
            for dim_name, info in self.dim_info.items():
                if info['type'] == 'vertical' or dim_name.lower() == 'depth':
                    self.depth = self.coord_vars[dim_name]
                    self.depth_key = dim_name
                    break
            
            # Find spatial dimensions - load only when needed
            for dim_name, info in self.dim_info.items():
                if info['type'] == 'latitude':
                    # Use chunking for large arrays
                    self.lat = self.coord_vars[dim_name][:]
                    self.lat_key = dim_name
                elif info['type'] == 'longitude':
                    # Use chunking for large arrays
                    self.lon = self.coord_vars[dim_name][:]
                    self.lon_key = dim_name
            
            # Handle time dimension with optimized loading
            if self.time is not None:
                try:
                    self.time_units = self.time.units if hasattr(self.time, 'units') else 'unknown'
                    self.time_steps = len(self.time)
                    
                    # Configure time slider
                    self.time_slider.configure(from_=0, to=self.time_steps-1, state='normal')
                    self.time_slider.set(0)
                    
                    # Update time value label
                    time_value = nc.num2date(self.time[0], units=self.time_units)
                    self.time_value_label.config(text=str(time_value))
                except Exception as e:
                    print(f"Warning: Could not process time values: {e}")
                    self.time_slider.configure(state='disabled')
            else:
                self.time_slider.configure(state='disabled')
            
            # Handle depth dimension with optimized loading
            if self.depth is not None:
                try:
                    self.depth_units = self.depth.units if hasattr(self.depth, 'units') else 'unknown'
                    self.depth_levels = len(self.depth)
                    
                    # Configure depth slider
                    self.depth_slider.configure(from_=0, to=self.depth_levels-1, state='normal')
                    self.depth_slider.set(0)
                    
                    # Update depth value label
                    depth_value = self.depth[0]
                    self.depth_value_label.config(text=f"{depth_value:.2f}")
                except Exception as e:
                    print(f"Warning: Could not process depth values: {e}")
                    self.depth_slider.configure(state='disabled')
            else:
                self.depth_slider.configure(state='disabled')
            
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
            
            # Display variable information with lazy loading
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
        # Reset plot state when changing variables
        self.current_plot = None
        self.current_canvas = None
        self.current_ax = None
        self.current_cbar = None
        plt.close('all')
        
        selected_variable = self.variable_dropdown.get()
        variable_data = self.dataset.variables[selected_variable]
        
        strip = selected_variable.replace('_',' ').title()
        
        self.plot_button.config(text=f"Plot {strip}")
        
        dims = variable_data.dimensions

        if self.depth_key in dims:
            self.depth_slider.configure(state='normal')
            self.depth_slider.set(0)
            self.calculate_depth()
        else:
            self.depth_slider.configure(state='disabled')
            
        if self.time_key in dims:
            self.time_slider.configure(state='normal')
            self.time_slider.set(0)
            self.calculate_time()
            
        # Create initial plot
        self.plot_variable()
        
        # Start playback automatically if there's a time dimension
        if self.time_key in dims:
            self.start_playback()

    def update_time_label(self, event=None):
        """Update the time value label during slider movement"""
        if hasattr(self, 'time') and self.time is not None:
            try:
                time_index = int(self.time_slider.get())
                time_value = nc.num2date(self.time[time_index], units=self.time_units)
                self.time_value_label.config(text=str(time_value))
            except Exception as e:
                self.time_value_label.config(text="Error")

    def update_depth_label(self, event=None):
        """Update the depth value label during slider movement"""
        if hasattr(self, 'depth') and self.depth is not None:
            try:
                depth_index = int(self.depth_slider.get())
                depth_value = self.depth[depth_index]
                self.depth_value_label.config(text=f"{depth_value:.2f}")
            except Exception as e:
                self.depth_value_label.config(text="Error")

    def calculate_time(self, event=None):
        try:
            # Check if time dimension exists
            if not hasattr(self, 'time') or self.time is None:
                self.depth_time_label.config(text="No time dimension found")
                return
                
            # Get the selected time index directly from slider
            time_index = int(self.time_slider.get())
            
            # Convert time value
            try:
                time_value = nc.num2date(self.time[time_index], units=self.time_units)
                # Update time value label
                self.time_value_label.config(text=str(time_value))
            except Exception as e:
                self.depth_time_label.config(text=f"Error converting time: {str(e)}")
                return
            
            # Update label based on whether depth is available
            try:
                if hasattr(self, 'depth') and self.depth is not None:
                    depth_index = int(self.depth_slider.get())
                    depth_value = self.depth[depth_index]
                    self.depth_time_label.config(text=f"{time_value} ({depth_value:.2f} {self.depth_units})")
                    # Update depth value label
                    self.depth_value_label.config(text=f"{depth_value:.2f}")
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
            if "time_units" in error_msg:
                self.depth_time_label.config(text="Time units not found")
            else:
                self.depth_time_label.config(text=f"Error calculating time: {error_msg}")

    def calculate_depth(self, event=None):
        try:
            if not hasattr(self, 'depth') or self.depth is None:
                self.depth_time_label.config(text="No depth dimension found")
                return
                
            # Get the selected depth index directly from slider
            depth_index = int(self.depth_slider.get())
            depth_value = self.depth[depth_index]
            # Update depth value label
            self.depth_value_label.config(text=f"{depth_value:.2f}")
            
            # Update label based on whether time is available
            if hasattr(self, 'time') and self.time is not None:
                time_index = int(self.time_slider.get())
                time_value = nc.num2date(self.time[time_index], units=self.time_units)
                self.depth_time_label.config(text=f"{time_value} ({depth_value:.2f} {self.depth_units})")
                # Update time value label
                self.time_value_label.config(text=str(time_value))
            else:
                self.depth_time_label.config(text=f"Depth: {depth_value:.2f} {self.depth_units}")
                
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
                        time_index = int(self.time_slider.get())
                        data = variable_data[time_index, :, :]
                    else:
                        data = variable_data[:, :, :]
                elif len(variable_dims) == 4:
                    if hasattr(self, 'time') and self.time is not None and hasattr(self, 'depth') and self.depth is not None:
                        time_index = int(self.time_slider.get())
                        depth_index = int(self.depth_slider.get())
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
            self.time_slider.configure(state='disabled')
        else:
            self.time_slider.configure(state='readonly')
            
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
            try:
                if self.depth_key in self.dataset.variables[selected_variable].dimensions:
                    depth_index = int(self.depth_slider.get())
                    time_index = int(self.time_slider.get())
                    data_value = self.dataset.variables[selected_variable][time_index, depth_index, lat_idx, lon_idx]
                else:
                    time_index = int(self.time_slider.get())
                    data_value = self.dataset.variables[selected_variable][time_index, lat_idx, lon_idx]
                    
                if np.ma.is_masked(data_value):
                    value_str = "Masked"
                else:
                    value_str = f"{data_value:.2f}"
                
                strip = selected_variable.replace('_',' ').title()
                hover_info = f"Lon: {lon:.2f}, Lat: {lat:.2f}\ni: {lon_idx} j: {lat_idx}\n{strip}: {value_str}"
                self.hover_label.config(text=hover_info)
            except Exception as e:
                self.hover_label.config(text="Error getting value")
            
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

            # Close any existing figures to prevent memory leaks
            plt.close('all')
                
            # Clear previous plot and controls
            for widget in self.plot_frame.winfo_children():
                widget.destroy()

            # Create frames for the layout
            plot_area = tk.Frame(self.plot_frame)
            plot_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

            bottom_controls = tb.Frame(self.plot_frame)
            bottom_controls.pack(side=tk.BOTTOM, fill=tk.X)

            toolbar_frame = tb.Frame(bottom_controls)
            toolbar_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            media_controls = tb.Frame(bottom_controls)
            media_controls.pack(side=tk.RIGHT, fill=tk.X, padx=10)

            # Add media control buttons
            stop_btn = tb.Button(media_controls, text="⏹", command=self.stop_playback, bootstyle='danger')
            stop_btn.pack(side=tk.LEFT, padx=2)

            rev_btn = tb.Button(media_controls, text="⏮", command=self.reverse_playback, bootstyle='warning')
            rev_btn.pack(side=tk.LEFT, padx=2)

            self.play_btn = tb.Button(media_controls, text="⏸" if self.is_playing else "▶", 
                                    command=self.toggle_playback, bootstyle='success')
            self.play_btn.pack(side=tk.LEFT, padx=2)

            fwd_btn = tb.Button(media_controls, text="⏭", command=self.forward_playback, bootstyle='warning')
            fwd_btn.pack(side=tk.LEFT, padx=2)

            # Add separator
            tb.Separator(media_controls, orient='vertical').pack(side=tk.LEFT, padx=5, fill='y')

            slow_down = tb.Button(media_controls, text="<<", command=self.decrease_speed, bootstyle='info')
            slow_down.pack(side=tk.LEFT, padx=2)

            self.speed_label = tb.Label(media_controls, text=f"Speed: {self.play_speed}ms")
            self.speed_label.pack(side=tk.LEFT, padx=5)

            speed_up = tb.Button(media_controls, text=">>", command=self.increase_speed, bootstyle='info')
            speed_up.pack(side=tk.LEFT, padx=2)

            # Get variable data and attributes
            variable_data = self.dataset.variables[selected_variable]
            variable_dims = variable_data.dimensions

            # Get current time step
            if self.time_key in variable_dims:
                time_index = int(self.time_slider.get())
            
            # Handle depth selection
            if self.depth_key in variable_dims:
                depth_index = int(self.depth_slider.get())
                if depth_index is None:
                    self.data_display_text.insert(tk.END, "\nError: No depth levels available\n")
                    return
            
            # Create figure
            fig = plt.figure(figsize=(10, 6), constrained_layout=True)
            
            # Handle different dimension structures
            if len(variable_dims) == 1:  # 1D data
                data = variable_data[:]
                dim_name = variable_dims[0]
                dim_values = self.coord_vars[dim_name][:] if dim_name in self.coord_vars else np.arange(len(data))
                
                ax = fig.add_subplot(111)
                ax.plot(dim_values, data)
                ax.set_xlabel(dim_name)
                ax.set_ylabel(variable_data.long_name if hasattr(variable_data, 'long_name') else selected_variable)
                if self.title_entry.get() and self.title_entry.get() != "Plot Title":
                    ax.set_title(self.title_entry.get())
                else:
                    ax.set_title(f"{variable_data.long_name if hasattr(variable_data, 'long_name') else selected_variable} vs {dim_name}")
                
            else:  # 2D, 3D, or 4D data
                if self.lat is not None and self.lon is not None:
                    ax = fig.add_subplot(111, projection=self.projections[self.projection_dropdown.get()])
                    ax.coastlines(resolution='50m', linewidth=0.5)
                    ax.add_feature(cfeature.BORDERS, linewidth=0.3)
                    
                    if self.ocean_checkbox_var.get():
                        ax.add_feature(cfeature.OCEAN, alpha=0.5)
                    if self.land_checkbox_var.get():
                        ax.add_feature(cfeature.LAND, alpha=0.5)
                        
                    # Add gridlines with proper labels
                    alpha = float(self.alpha_entry.get()) if self.alpha_entry.get() and self.alpha_entry.get() != "Alpha" and self.gridlines_var.get() else 0.0
                    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                                    linewidth=0.5, color='gray', alpha=alpha)
                    gl.top_labels = False
                    gl.right_labels = False
                    gl.xlabel_style = {'size': 8}
                    gl.ylabel_style = {'size': 8}
                else:
                    ax = fig.add_subplot(111)
                
                # Get the data slice
                if len(variable_dims) == 2:
                    data = variable_data[:, :]
                elif len(variable_dims) == 3:
                    data = variable_data[time_index, :, :]
                else:  # 4D
                    data = variable_data[time_index, depth_index, :, :]
                
                # Create meshgrid for plotting
                if self.lat is not None and self.lon is not None:
                    # Get longitude and latitude arrays
                    lon_data = self.lon
                    lat_data = self.lat
                    
                    # Handle cases where longitude is in [0, 360] range
                    if np.any(lon_data > 180):
                        lon_data = np.where(lon_data > 180, lon_data - 360, lon_data)
                        
                    lon, lat = np.meshgrid(lon_data, lat_data)
                    
                    # Set map extent based on data bounds
                    if self.extent_entry.get() and self.extent_entry.get() != "Extents [x0, x1, y0, y1]":
                        try:
                            x_min, x_max, y_min, y_max = map(float, self.extent_entry.get().split(','))
                            ax.set_extent([x_min, x_max, y_min, y_max], crs=ccrs.PlateCarree())
                        except:
                            # Calculate default extent from data
                            x_min, x_max = lon_data.min(), lon_data.max()
                            y_min, y_max = lat_data.min(), lat_data.max()
                            # Add small padding
                            x_pad = (x_max - x_min) * 0.05
                            y_pad = (y_max - y_min) * 0.05
                            ax.set_extent([x_min - x_pad, x_max + x_pad, 
                                         y_min - y_pad, y_max + y_pad], 
                                            crs=ccrs.PlateCarree())
                    else:
                        # Calculate default extent from data
                        x_min, x_max = lon_data.min(), lon_data.max()
                        y_min, y_max = lat_data.min(), lat_data.max()
                        # Add small padding
                        x_pad = (x_max - x_min) * 0.05
                        y_pad = (y_max - y_min) * 0.05
                        ax.set_extent([x_min - x_pad, x_max + x_pad, 
                                     y_min - y_pad, y_max + y_pad], 
                                    crs=ccrs.PlateCarree())
                else:
                    if len(variable_dims) == 2:
                        dim1 = self.coord_vars[variable_dims[0]][:] if variable_dims[0] in self.coord_vars else np.arange(data.shape[0])
                        dim2 = self.coord_vars[variable_dims[1]][:] if variable_dims[1] in self.coord_vars else np.arange(data.shape[1])
                    elif len(variable_dims) == 3:
                        dim1 = self.coord_vars[variable_dims[1]][:] if variable_dims[1] in self.coord_vars else np.arange(data.shape[0])
                        dim2 = self.coord_vars[variable_dims[2]][:] if variable_dims[2] in self.coord_vars else np.arange(data.shape[1])
                    else:  # 4D
                        dim1 = self.coord_vars[variable_dims[2]][:] if variable_dims[2] in self.coord_vars else np.arange(data.shape[0])
                        dim2 = self.coord_vars[variable_dims[3]][:] if variable_dims[3] in self.coord_vars else np.arange(data.shape[1])
                    lon, lat = np.meshgrid(dim2, dim1)
                
                # Get vmin/vmax values
                try:
                    vmin = float(self.vmin_entry.get()) if self.vmin_entry.get() and self.vmin_entry.get() != "V-Min" else None
                except ValueError:
                    vmin = None
                    
                try:
                    vmax = float(self.vmax_entry.get()) if self.vmax_entry.get() and self.vmax_entry.get() != "V-Max" else None
                except ValueError:
                    vmax = None
                    
                # Get levels value
                try:
                    levels = int(self.levels_entry.get()) if self.levels_entry.get() and self.levels_entry.get() != "Levels" else None
                except ValueError:
                    levels = None
                
                # Plot the data
                if self.plot_type_dropdown.get() == 'pcolormesh':
                    plot = ax.pcolormesh(lon, lat, data, 
                                       transform=ccrs.PlateCarree() if self.lat is not None and self.lon is not None else None,
                                       cmap=self.colormap_dropdown.get() + '_r' if self.reverse_colormap_var.get() else self.colormap_dropdown.get(),
                                       vmin=vmin, vmax=vmax)
                elif self.plot_type_dropdown.get() == 'contour':
                    plot = ax.contour(lon, lat, data,
                                    transform=ccrs.PlateCarree() if self.lat is not None and self.lon is not None else None,
                                    cmap=self.colormap_dropdown.get() + '_r' if self.reverse_colormap_var.get() else self.colormap_dropdown.get(),
                                    levels=levels, vmin=vmin, vmax=vmax)
                elif self.plot_type_dropdown.get() == 'contourf':
                    plot = ax.contourf(lon, lat, data,
                                     transform=ccrs.PlateCarree() if self.lat is not None and self.lon is not None else None,
                                     cmap=self.colormap_dropdown.get() + '_r' if self.reverse_colormap_var.get() else self.colormap_dropdown.get(),
                                     levels=levels, vmin=vmin, vmax=vmax)
                else:  # imshow
                    plot = ax.imshow(data, 
                                   cmap=self.colormap_dropdown.get() + '_r' if self.reverse_colormap_var.get() else self.colormap_dropdown.get(),
                                   vmin=vmin, vmax=vmax,
                                   extent=[lon.min(), lon.max(), lat.min(), lat.max()],
                                   transform=ccrs.PlateCarree() if self.lat is not None and self.lon is not None else None)
                
                # Add colorbar
                try:
                    shrink = float(self.cbar_shrink_entry.get()) if self.cbar_shrink_entry.get() and self.cbar_shrink_entry.get() != "Shrink (0-1)" else 1.0
                except ValueError:
                    shrink = 1.0
                    
                cbar = plt.colorbar(plot, ax=ax, orientation=self.colorbar_orientation_dropdown.get(), shrink=shrink)
                cbar.set_label(f"{variable_data.long_name if hasattr(variable_data, 'long_name') else selected_variable} [{variable_data.units if hasattr(variable_data, 'units') else ''}]")
                
                # Set labels and title
                if self.xlabel_entry.get() and self.xlabel_entry.get() != "X-axis Label":
                    ax.set_xlabel(self.xlabel_entry.get())
                elif not (self.lat is not None and self.lon is not None):
                    ax.set_xlabel('Longitude' if self.lon_key else variable_dims[-1])
                
                if self.ylabel_entry.get() and self.ylabel_entry.get() != "Y-axis Label":
                    ax.set_ylabel(self.ylabel_entry.get())
                elif not (self.lat is not None and self.lon is not None):
                    ax.set_ylabel('Latitude' if self.lat_key else variable_dims[-2])
                    
                if self.title_entry.get() and self.title_entry.get() != "Plot Title":
                    ax.set_title(self.title_entry.get())
                else:
                    time_str = f" at {nc.num2date(self.time[time_index], units=self.time_units)}" if self.time_key in variable_dims else ""
                    depth_str = f" at {self.depth[depth_index]:.2f} {self.depth_units}" if self.depth_key in variable_dims else ""
                    ax.set_title(f"{variable_data.long_name if hasattr(variable_data, 'long_name') else selected_variable}{time_str}{depth_str}")
            
            # Create canvas and add to GUI
            canvas = FigureCanvasTkAgg(fig, master=plot_area)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Add toolbar
            toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            toolbar.update()
            
            # Connect hover event
            canvas.mpl_connect('motion_notify_event', self.update_hover_info)
            
            # Store references
            self.current_canvas = canvas
            self.current_ax = ax
            self.current_plot = plot if len(variable_dims) > 1 else None
            self.current_cbar = cbar if len(variable_dims) > 1 else None
            
        except Exception as e:
            self.data_display_text.insert(tk.END, f"\nError in plot_variable: {str(e)}\n")
            import traceback
            traceback.print_exc()
            return

    def save_gif(self):
        """Create GIF with current settings"""
        try:
            if not hasattr(self, 'dataset') or self.dataset is None:
                self.data_display_text.insert(tk.END, "\nError: No dataset loaded\n")
                return
                
            selected_variable = self.variable_dropdown.get()
            variable_data = self.dataset.variables[selected_variable]
            
            # Get settings
            fps = int(self.gif_fps_var.get())
            range_str = self.gif_range_var.get().lower()
            
            # Determine frame range
            if range_str == 'all':
                frame_range = range(self.time_steps)
            else:
                start, end = map(int, range_str.split('-'))
                frame_range = range(start, end + 1)
            
            # Create output directory if needed
            os.makedirs(self.gif_dir, exist_ok=True)
            
            # Save current time index
            current_time = int(self.time_slider.get())
            
            # Progress info
            total_frames = len(frame_range)
            self.data_display_text.insert(tk.END, f"\nCreating GIF with {total_frames} frames...\n")
            
            frames = []
            for i in frame_range:
                self.time_slider.set(i)
                
                # Create figure
                fig = plt.figure(figsize=(10, 6), constrained_layout=True)
                
                # Plot the frame
                if self.lat is not None and self.lon is not None:
                    ax = fig.add_subplot(111, projection=ccrs.PlateCarree())
                    
                    # Add map features
                    ax.coastlines(resolution='50m', linewidth=0.5)
                    ax.add_feature(cfeature.BORDERS, linewidth=0.3)
                    
                    if self.ocean_checkbox_var.get():
                        ax.add_feature(cfeature.OCEAN, alpha=0.5)
                    if self.land_checkbox_var.get():
                        ax.add_feature(cfeature.LAND, alpha=0.5)
                    
                    # Get data for this frame
                    if self.depth_key in variable_data.dimensions:
                        depth_index = int(self.depth_slider.get())
                        data = variable_data[i, depth_index, :, :]
                    else:
                        data = variable_data[i, :, :]
                    
                    # Create plot
                    lon, lat = np.meshgrid(self.lon, self.lat)
                    
                    # Plot data using current plot type
                    if self.plot_type_dropdown.get() == 'pcolormesh':
                        plot = ax.pcolormesh(lon, lat, data, transform=ccrs.PlateCarree(),
                                           cmap=self.colormap_dropdown.get() + '_r' if self.reverse_colormap_var.get() else self.colormap_dropdown.get(),
                                           vmin=float(self.vmin_entry.get()) if self.vmin_entry.get() and self.vmin_entry.get() != "V-Min" else None,
                                           vmax=float(self.vmax_entry.get()) if self.vmax_entry.get() and self.vmax_entry.get() != "V-Max" else None)
                    elif self.plot_type_dropdown.get() == 'contour':
                        plot = ax.contour(lon, lat, data, transform=ccrs.PlateCarree(),
                                        cmap=self.colormap_dropdown.get() + '_r' if self.reverse_colormap_var.get() else self.colormap_dropdown.get(),
                                        levels=int(self.levels_entry.get()) if self.levels_entry.get() and self.levels_entry.get() != "Levels" else None,
                                        vmin=float(self.vmin_entry.get()) if self.vmin_entry.get() and self.vmin_entry.get() != "V-Min" else None,
                                        vmax=float(self.vmax_entry.get()) if self.vmax_entry.get() and self.vmax_entry.get() != "V-Max" else None)
                    elif self.plot_type_dropdown.get() == 'contourf':
                        plot = ax.contourf(lon, lat, data, transform=ccrs.PlateCarree(),
                                         cmap=self.colormap_dropdown.get() + '_r' if self.reverse_colormap_var.get() else self.colormap_dropdown.get(),
                                         levels=int(self.levels_entry.get()) if self.levels_entry.get() and self.levels_entry.get() != "Levels" else None,
                                         vmin=float(self.vmin_entry.get()) if self.vmin_entry.get() and self.vmin_entry.get() != "V-Min" else None,
                                         vmax=float(self.vmax_entry.get()) if self.vmax_entry.get() and self.vmax_entry.get() != "V-Max" else None)
                    else:  # imshow
                        plot = ax.imshow(data, transform=ccrs.PlateCarree(),
                                       cmap=self.colormap_dropdown.get() + '_r' if self.reverse_colormap_var.get() else self.colormap_dropdown.get(),
                                       vmin=float(self.vmin_entry.get()) if self.vmin_entry.get() and self.vmin_entry.get() != "V-Min" else None,
                                       vmax=float(self.vmax_entry.get()) if self.vmax_entry.get() and self.vmax_entry.get() != "V-Max" else None,
                                       extent=[lon.min(), lon.max(), lat.min(), lat.max()])
                    
                    # Set extent
                    if self.extent_entry.get() and self.extent_entry.get() != "Extents [x0, x1, y0, y1]":
                        try:
                            x_min, x_max, y_min, y_max = map(float, self.extent_entry.get().split(','))
                            ax.set_extent([x_min, x_max, y_min, y_max], crs=ccrs.PlateCarree())
                        except:
                            ax.set_extent([-98, -80, 18, 31], crs=ccrs.PlateCarree())
                    else:
                        ax.set_extent([-98, -80, 18, 31], crs=ccrs.PlateCarree())
                    
                    # Add gridlines
                    alpha = float(self.alpha_entry.get()) if self.alpha_entry.get() and self.alpha_entry.get() != "Alpha" and self.gridlines_var.get() else 0.0
                    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                                    linewidth=0.5, color='gray', alpha=alpha,
                                    xlocs=np.arange(-100, -70, 5),
                                    ylocs=np.arange(15, 35, 5))
                    gl.top_labels = False
                    gl.right_labels = False
                    gl.xlabel_style = {'size': 8}
                    gl.ylabel_style = {'size': 8}
                    
                    # Add colorbar
                    try:
                        shrink = float(self.cbar_shrink_entry.get()) if self.cbar_shrink_entry.get() and self.cbar_shrink_entry.get() != "Shrink (0-1)" else 1.0
                    except ValueError:
                        shrink = 1.0
                    cbar = plt.colorbar(plot, ax=ax, orientation=self.colorbar_orientation_dropdown.get(), shrink=shrink)
                    if hasattr(variable_data, 'units'):
                        cbar.set_label(f"{selected_variable} [{variable_data.units}]")
                    else:
                        cbar.set_label(selected_variable)
                    
                    # Add title
                    time_value = nc.num2date(self.time[i], units=self.time_units)
                    if self.title_entry.get() and self.title_entry.get() != "Plot Title":
                        ax.set_title(f"{self.title_entry.get()} ({time_value})")
                    else:
                        if self.depth_key in variable_data.dimensions:
                            depth_str = f" at {self.depth[int(self.depth_slider.get())]:.2f} {self.depth_units}"
                            ax.set_title(f"{selected_variable} ({time_value}){depth_str}")
                        else:
                            ax.set_title(f"{selected_variable} ({time_value})")
                
                # Save frame to memory
                fig.canvas.draw()
                buf = fig.canvas.buffer_rgba()
                image = np.asarray(buf)
                # Convert RGBA to RGB
                image = image[:, :, :3]
                frames.append(image)
                
                # Clean up
                plt.close(fig)
                
                # Update progress
                if i % 10 == 0:
                    self.data_display_text.insert(tk.END, f"Frame {i+1}/{total_frames}\n")
                    self.data_display_text.see(tk.END)
                    self.root.update()
            
            # Create GIF file
            gif_file = os.path.join(self.gif_dir, f'{selected_variable}_animation.gif')
            imageio.mimsave(gif_file, frames, fps=fps, loop=0 if self.gif_loop_var.get() else 1)
            
            # Restore original time index
            self.time_slider.set(current_time)
            
            # Show success message
            self.data_display_text.insert(tk.END, f"\nGIF saved successfully to:\n{gif_file}\n")
            
            # Show the GIF
            self.show_gif_in_window(gif_file)
            
        except Exception as e:
            self.data_display_text.insert(tk.END, f"\nError creating GIF: {str(e)}\n")
            import traceback
            traceback.print_exc()

    def show_gif_in_window(self, gif_path):
        gif_window = Toplevel(self.root)
        gif_window.title("GIF Preview")
        gif_window.geometry("1024x800")  # Increased window size
        
        # Create main container frame
        main_frame = tk.Frame(gif_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create frame for GIF with padding
        gif_frame = tk.Frame(main_frame)
        gif_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        gif_label = Label(gif_frame)
        gif_label.pack(fill=tk.BOTH, expand=True)

        # Create frame for playback controls with increased padding
        playback_control_frame = tk.Frame(main_frame)
        playback_control_frame.pack(fill=tk.X, pady=15)  # Increased vertical padding
        
        # Add spacer frame for centering
        tk.Frame(playback_control_frame).pack(side=tk.LEFT, expand=True)
        
        # Create buttons frame for grouped controls
        buttons_frame = tk.Frame(playback_control_frame)
        buttons_frame.pack(side=tk.LEFT)
        
        # Speed control
        slow_button = tb.Button(buttons_frame, text='<<', command=self.slow_gif, 
                              bootstyle='warning-outline', width=8)
        slow_button.pack(side=tk.LEFT, padx=5)

        # Main controls
        play_button = tb.Button(buttons_frame, text="Play", command=self.play_gif, 
                              bootstyle='success-outline', width=8)
        play_button.pack(side=tk.LEFT, padx=5)

        pause_button = tb.Button(buttons_frame, text="Pause", command=self.pause_gif, 
                               bootstyle='warning-outline', width=8)
        pause_button.pack(side=tk.LEFT, padx=5)

        reverse_button = tb.Button(buttons_frame, text="Reverse", command=self.reverse_gif, 
                                 bootstyle='info-outline', width=8)
        reverse_button.pack(side=tk.LEFT, padx=5)

        stop_button = tb.Button(buttons_frame, text="Stop", command=self.stop_gif, 
                              bootstyle='danger-outline', width=8)
        stop_button.pack(side=tk.LEFT, padx=5)
        
        # Speed up control
        speed_button = tb.Button(buttons_frame, text='>>', command=self.speed_gif, 
                               bootstyle='warning-outline', width=8)
        speed_button.pack(side=tk.LEFT, padx=5)
        
        # Add spacer frame for centering
        tk.Frame(playback_control_frame).pack(side=tk.LEFT, expand=True)
        
        # Add speed indicator label
        self.speed_indicator = tb.Label(main_frame, text="Playback Speed: 100ms", 
                                      bootstyle='info')
        self.speed_indicator.pack(pady=5)

        self.gif_frames = []
        self.gif_path = gif_path
        self.gif_label = gif_label
        self.gif_window = gif_window
        self.gif_playing = False
        self.gif_paused = False
        self.gif_reversed = False
        self.current_frame_index = 0
        self.playback_speed = 100

        # Load GIF frames
        with Image.open(gif_path) as gif:
            # Calculate size to fit window while maintaining aspect ratio
            gif_width, gif_height = gif.size
            window_width = 1000  # Slightly less than window width to account for padding
            window_height = 680  # Leave room for controls
            
            # Calculate scaling factor
            width_ratio = window_width / gif_width
            height_ratio = window_height / gif_height
            scale_factor = min(width_ratio, height_ratio)
            
            # Calculate new dimensions
            new_width = int(gif_width * scale_factor)
            new_height = int(gif_height * scale_factor)
            
            for frame in range(gif.n_frames):
                gif.seek(frame)
                # Resize frame to fit window
                frame_image = gif.convert("RGBA").resize((new_width, new_height), Image.Resampling.LANCZOS)
                frame_photo = ImageTk.PhotoImage(frame_image)
                self.gif_frames.append(frame_photo)
                
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
        self.playback_speed = min(500, self.playback_speed + 25)
        self.speed_indicator.config(text=f"Playback Speed: {self.playback_speed}ms")
            
    def speed_gif(self): 
        self.playback_speed = max(25, self.playback_speed - 25)
        self.speed_indicator.config(text=f"Playback Speed: {self.playback_speed}ms")

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

    def toggle_playback(self):
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()

    def start_playback(self):
        self.is_playing = True
        self.play_btn.configure(text="⏸")
        self.advance_frame()

    def pause_playback(self):
        self.is_playing = False
        self.play_btn.configure(text="▶")
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        plt.close('all')  # Clean up any remaining figures

    def stop_playback(self):
        self.pause_playback()
        self.time_slider.set(0)
        # Reset plot state
        self.current_plot = None
        self.current_canvas = None
        self.current_ax = None
        self.current_cbar = None
        plt.close('all')
        self.plot_variable()

    def reverse_playback(self):
        self.play_direction = -1
        if not self.is_playing:
            self.start_playback()

    def forward_playback(self):
        self.play_direction = 1
        if not self.is_playing:
            self.start_playback()

    def increase_speed(self):
        self.play_speed = max(50, self.play_speed - 50)
        self.speed_label.configure(text=f"Speed: {self.play_speed}ms")

    def decrease_speed(self):
        self.play_speed = min(2000, self.play_speed + 50)
        self.speed_label.configure(text=f"Speed: {self.play_speed}ms")

    def advance_frame(self):
        if not self.is_playing:
            return

        current_index = int(self.time_slider.get())
        next_index = current_index + self.play_direction
        
        # Handle wrapping around
        if next_index >= self.time_steps:
            next_index = 0
        elif next_index < 0:
            next_index = self.time_steps - 1
            
        # Update slider without triggering full redraw
        self.time_slider.set(next_index)
        
        # Update data without recreating the plot
        selected_variable = self.variable_dropdown.get()
        variable_data = self.dataset.variables[selected_variable]
        
        if self.depth_key in variable_data.dimensions:
            depth_index = int(self.depth_slider.get())
            data = variable_data[next_index, depth_index]
        else:
            data = variable_data[next_index]
            
        # Update plot data without redrawing everything
        if self.current_plot is not None:
            plot_type = self.plot_type_dropdown.get()
            if plot_type in ['pcolormesh', 'imshow']:
                self.current_plot.set_array(data.ravel())
            elif plot_type in ['contour', 'contourf']:
                self.current_ax.clear()
                if self.lat is not None and self.lon is not None:
                    lon, lat = np.meshgrid(self.lon, self.lat)
                    if plot_type == 'contour':
                        self.current_plot = self.current_ax.contour(lon, lat, data, 
                            transform=ccrs.PlateCarree() if self.current_ax.name == 'cartopy' else None,
                            cmap=self.colormap_dropdown.get() + '_r' if self.reverse_colormap_var.get() else self.colormap_dropdown.get(),
                            levels=int(self.levels_entry.get()) if self.levels_entry.get() else None,
                            vmin=float(self.vmin_entry.get()) if self.vmin_entry.get() else None,
                            vmax=float(self.vmax_entry.get()) if self.vmax_entry.get() else None)
                    else:
                        self.current_plot = self.current_ax.contourf(lon, lat, data,
                            transform=ccrs.PlateCarree() if self.current_ax.name == 'cartopy' else None,
                            cmap=self.colormap_dropdown.get() + '_r' if self.reverse_colormap_var.get() else self.colormap_dropdown.get(),
                            levels=int(self.levels_entry.get()) if self.levels_entry.get() else None,
                            vmin=float(self.vmin_entry.get()) if self.vmin_entry.get() else None,
                            vmax=float(self.vmax_entry.get()) if self.vmax_entry.get() else None)
            
            # Update title with current time
            time_value = nc.num2date(self.time[next_index], units=self.time_units)
            if self.depth_key in variable_data.dimensions:
                depth_value = self.depth[int(self.depth_slider.get())]
                depth_str = f" at {depth_value:.2f} {self.depth_units}"
            else:
                depth_str = ""
            self.current_ax.set_title(f"{variable_data.long_name if hasattr(variable_data, 'long_name') else selected_variable} ({time_value}){depth_str}")
            
            # Update the canvas
            self.current_canvas.draw_idle()
            
            # Update statistics and labels
            self.show_statistics()
            self.depth_time_label.config(text=f"{time_value}{depth_str}")
            self.time_value_label.config(text=str(time_value))  # Update time value label
        
        # Schedule the next frame
        self.after_id = self.root.after(self.play_speed, self.advance_frame)

    def __del__(self):
        """Cleanup when the object is destroyed"""
        plt.close('all')  # Clean up any remaining figures

    def show_gif_settings(self):
        """Show popup dialog for GIF settings"""
        # Create popup dialog
        dialog = tb.Toplevel(self.root)
        dialog.title("GIF Settings")
        dialog.geometry("300x400")
        
        # Center the dialog on the screen
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Add padding around all widgets
        frame = tb.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # FPS setting
        fps_frame = tb.Frame(frame)
        fps_frame.pack(fill=tk.X, pady=5)
        fps_label = tb.Label(fps_frame, text="FPS:", width=10)
        fps_label.pack(side=tk.LEFT)
        self.gif_fps_var = tk.StringVar(value="2")
        fps_entry = tb.Entry(fps_frame, textvariable=self.gif_fps_var, width=10)
        fps_entry.pack(side=tk.LEFT, padx=5)
        
        # Frame range setting
        range_frame = tb.Frame(frame)
        range_frame.pack(fill=tk.X, pady=5)
        range_label = tb.Label(range_frame, text="Range:", width=10)
        range_label.pack(side=tk.LEFT)
        self.gif_range_var = tk.StringVar(value="all")
        range_entry = tb.Entry(range_frame, textvariable=self.gif_range_var, width=10)
        range_entry.pack(side=tk.LEFT, padx=5)
        range_help = tb.Label(range_frame, text="(e.g., '1-50' or 'all')", font=("Helvetica", 8))
        range_help.pack(side=tk.LEFT, padx=5)
        
        # Loop setting
        loop_frame = tb.Frame(frame)
        loop_frame.pack(fill=tk.X, pady=5)
        self.gif_loop_var = tk.BooleanVar(value=True)
        loop_check = tb.Checkbutton(loop_frame, text="Loop GIF", variable=self.gif_loop_var, 
                                  bootstyle="danger-round-toggle")
        loop_check.pack(side=tk.LEFT)
        
        # Delete images setting
        delete_frame = tb.Frame(frame)
        delete_frame.pack(fill=tk.X, pady=5)
        self.delete_images_var = tk.BooleanVar(value=True)
        delete_check = tb.Checkbutton(delete_frame, text="Delete temp images", 
                                    variable=self.delete_images_var, bootstyle="danger-round-toggle")
        delete_check.pack(side=tk.LEFT)
        
        # Output directory selection
        dir_frame = tb.Frame(frame)
        dir_frame.pack(fill=tk.X, pady=10)
        self.gif_dir = None
        dir_button = tb.Button(dir_frame, text="Select Output Directory", 
                             command=lambda: self.select_gif_directory(dir_label))
        dir_button.pack(fill=tk.X)
        dir_label = tb.Label(dir_frame, text="No directory selected", wraplength=250)
        dir_label.pack(fill=tk.X, pady=5)
        
        # Create GIF button
        create_button = tb.Button(frame, text="Create GIF", 
                                command=lambda: self.create_gif_from_settings(dialog),
                                bootstyle="warning")
        create_button.pack(fill=tk.X, pady=20)
        
        # Cancel button
        cancel_button = tb.Button(frame, text="Cancel", 
                                command=dialog.destroy,
                                bootstyle="secondary")
        cancel_button.pack(fill=tk.X)

    def select_gif_directory(self, label_widget=None):
        """Select output directory for GIF"""
        self.gif_dir = filedialog.askdirectory()
        if self.gif_dir and label_widget:
            label_widget.config(text=self.gif_dir)

    def create_gif_from_settings(self, dialog):
        """Create GIF using the settings from the dialog"""
        if not self.gif_dir:
            messagebox.showerror("Error", "Please select an output directory first.")
            return
            
        try:
            fps = int(self.gif_fps_var.get())
            if fps <= 0:
                raise ValueError("FPS must be positive")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid FPS value (positive integer).")
            return
            
        # Parse range
        range_str = self.gif_range_var.get().lower()
        if range_str != 'all':
            try:
                start, end = map(int, range_str.split('-'))
                if start < 0 or end >= self.time_steps or start > end:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid range (e.g., '1-50' or 'all').")
                return
        
        # Close the settings dialog
        dialog.destroy()
        
        # Create the GIF
        self.save_gif()

    def update_slice_controls(self):
        """Update slice controls based on selected slice type"""
        if not hasattr(self, 'dataset') or self.dataset is None:
            return
            
        slice_type = self.slice_type.get()
        
        # Update slider range based on slice type
        if slice_type == "lon_depth":
            if self.lon is not None:
                self.slice_slider.configure(from_=0, to=len(self.lon)-1, state='normal')
                self.slice_position_label.config(text="Longitude Index:")
        else:  # lat_depth
            if self.lat is not None:
                self.slice_slider.configure(from_=0, to=len(self.lat)-1, state='normal')
                self.slice_position_label.config(text="Latitude Index:")
                
        # Update time slider
        if self.time is not None:
            self.slice_time_slider.configure(from_=0, to=self.time_steps-1, state='normal')
            
        self.plot_vertical_slice()
        
    def update_slice_label(self, event=None):
        """Update the slice position label during slider movement"""
        slice_type = self.slice_type.get()
        position = int(self.slice_slider.get())
        
        if slice_type == "lon_depth" and self.lon is not None:
            value = self.lon[position]
            self.slice_value_label.config(text=f"{value:.2f}°")
        elif slice_type == "lat_depth" and self.lat is not None:
            value = self.lat[position]
            self.slice_value_label.config(text=f"{value:.2f}°")
            
    def update_slice_time_label(self, event=None):
        """Update the time value label during slider movement"""
        if hasattr(self, 'time') and self.time is not None:
            try:
                time_index = int(self.slice_time_slider.get())
                time_value = nc.num2date(self.time[time_index], units=self.time_units)
                self.slice_time_value_label.config(text=str(time_value))
            except Exception as e:
                self.slice_time_value_label.config(text="Error")
                
    def plot_vertical_slice(self, event=None):
        """Plot vertical slice of the data"""
        try:
            if not hasattr(self, 'dataset') or self.dataset is None:
                self.slice_data_display_text.insert(tk.END, "\nError: No dataset loaded\n")
                return
                
            selected_variable = self.variable_dropdown.get()
            if not selected_variable:
                self.slice_data_display_text.insert(tk.END, "\nError: No variable selected\n")
                return
                
            if selected_variable not in self.dataset.variables:
                self.slice_data_display_text.insert(tk.END, f"\nError: Variable {selected_variable} not found in dataset\n")
                return
                
            # Close any existing figures
            plt.close('all')
            
            # Clear previous plot
            for widget in self.slice_plot_frame.winfo_children():
                widget.destroy()
                
            # Create figure
            fig = plt.figure(figsize=(10, 6), constrained_layout=True)
            
            # Get variable data
            variable_data = self.dataset.variables[selected_variable]
            time_index = int(self.slice_time_slider.get())
            slice_index = int(self.slice_slider.get())
            
            # Get the data slice
            if self.slice_type.get() == "lon_depth":
                if len(variable_data.dimensions) == 4:  # time, depth, lat, lon
                    data = variable_data[time_index, :, :, slice_index]
                    y_coords = self.depth
                    x_coords = self.lat
                    x_label = "Latitude"
                    y_label = f"Depth ({self.depth_units})"
                    title = f"{variable_data.long_name if hasattr(variable_data, 'long_name') else selected_variable} at Longitude {self.lon[slice_index]:.2f}°"
                else:
                    self.slice_data_display_text.insert(tk.END, "\nError: Variable does not have required dimensions\n")
                    return
            else:  # lat_depth
                if len(variable_data.dimensions) == 4:  # time, depth, lat, lon
                    data = variable_data[time_index, :, slice_index, :]
                    y_coords = self.depth
                    x_coords = self.lon
                    x_label = "Longitude"
                    y_label = f"Depth ({self.depth_units})"
                    title = f"{variable_data.long_name if hasattr(variable_data, 'long_name') else selected_variable} at Latitude {self.lat[slice_index]:.2f}°"
                else:
                    self.slice_data_display_text.insert(tk.END, "\nError: Variable does not have required dimensions\n")
                    return
                    
            # Create plot
            ax = fig.add_subplot(111)
            
            # Get vmin/vmax values
            try:
                vmin = float(self.vmin_entry.get()) if self.vmin_entry.get() and self.vmin_entry.get() != "V-Min" else None
            except ValueError:
                vmin = None
                
            try:
                vmax = float(self.vmax_entry.get()) if self.vmax_entry.get() and self.vmax_entry.get() != "V-Max" else None
            except ValueError:
                vmax = None
                
            # Get levels value
            try:
                levels = int(self.levels_entry.get()) if self.levels_entry.get() and self.levels_entry.get() != "Levels" else None
            except ValueError:
                levels = None
                
            # Plot the data
            if self.plot_type_dropdown.get() == 'pcolormesh':
                plot = ax.pcolormesh(x_coords, y_coords, data,
                                   cmap=self.colormap_dropdown.get() + '_r' if self.reverse_colormap_var.get() else self.colormap_dropdown.get(),
                                   vmin=vmin, vmax=vmax)
            elif self.plot_type_dropdown.get() == 'contour':
                plot = ax.contour(x_coords, y_coords, data,
                                cmap=self.colormap_dropdown.get() + '_r' if self.reverse_colormap_var.get() else self.colormap_dropdown.get(),
                                levels=levels, vmin=vmin, vmax=vmax)
            else:  # contourf
                plot = ax.contourf(x_coords, y_coords, data,
                                 cmap=self.colormap_dropdown.get() + '_r' if self.reverse_colormap_var.get() else self.colormap_dropdown.get(),
                                 levels=levels, vmin=vmin, vmax=vmax)
                                 
            # Add colorbar
            try:
                shrink = float(self.cbar_shrink_entry.get()) if self.cbar_shrink_entry.get() and self.cbar_shrink_entry.get() != "Shrink (0-1)" else 1.0
            except ValueError:
                shrink = 1.0
                
            cbar = plt.colorbar(plot, ax=ax, orientation=self.colorbar_orientation_dropdown.get(), shrink=shrink)
            cbar.set_label(f"{variable_data.long_name if hasattr(variable_data, 'long_name') else selected_variable} [{variable_data.units if hasattr(variable_data, 'units') else ''}]")
            
            # Set labels and title
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            
            # Add time to title
            time_value = nc.num2date(self.time[time_index], units=self.time_units)
            ax.set_title(f"{title} at {time_value}")
            
            # Invert y-axis for depth
            ax.invert_yaxis()
            
            # Create canvas and add to GUI
            canvas = FigureCanvasTkAgg(fig, master=self.slice_plot_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Add toolbar
            toolbar_frame = tk.Frame(self.slice_plot_frame)
            toolbar_frame.pack(fill=tk.X)
            toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            toolbar.update()
            
            # Store references
            self.current_canvas = canvas
            self.current_ax = ax
            self.current_plot = plot
            self.current_cbar = cbar
            
        except Exception as e:
            self.slice_data_display_text.insert(tk.END, f"\nError in plot_vertical_slice: {str(e)}\n")
            import traceback
            traceback.print_exc()
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
