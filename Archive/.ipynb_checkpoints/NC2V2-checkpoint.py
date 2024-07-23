import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import cartopy.crs as ccrs
import imageio

import netCDF4 as nc
import numpy as np
import os
import sys

class NC2:
    def __init__(self, root, file_path=None):
        self.root = root
        self.root.title("NC2 v1.3 Rhett R. Adam Jun 28 2024")
        
        self.file_path = file_path
        self.dataset = None
        self.variable_names = []
        self.depth_levels = []
        self.current_figure = None
        
        self.create_widgets()
        
        if self.file_path:
            self.load_netcdf_file()

    def create_widgets(self):
        
        style = ttk.Style()
        style.theme_use()
        #print(style.theme_names())
        style.theme_use('clam')
        
        style.configure('TButton',width = 20, relief='flat')
        style.map('TButton', foreground=[('active','white')], background=[('active', 'light sea green'), ('!active', 'light sea green')])
        
        style.map('Toolbutton', foreground=[('disabled', 'white'),('selected', 'black'),('!selected', 'white')], background=[('selected', 'SeaGreen1'),('!selected', 'grey16')])
        
        style.configure('TFrame', background='grey16')
        #style.map('TFrame')
        
        
        
        style.configure('TLabel', background='grey16', foreground='white')
        
        
        style.configure('TCombobox',fieldbackground='grey16',background='grey16',foreground='white')
        style.map('TCombobox',fieldbackground=[('readonly', 'grey16')],background=[('readonly', 'grey16')],foreground=[('readonly', 'white')],arrowcolor=[('readonly', 'white')], bordercolor=[('readonly', 'grey')],lightcolor=[('readonly','grey')], relief=[('readonly','flat')])
        
        
        style.configure('TEntry', fieldbackground='grey16',background='grey16',foreground='white', bordercolor='grey', lightcolor='grey', relief='flat')
        

        
        
        # Left control frame
        control_frame_left = ttk.Frame(self.root, padding='0.2i', style='TFrame')
        control_frame_left.pack(side=tk.LEFT, fill=tk.Y)
        
        self.select_file_button = ttk.Button(control_frame_left, text="Select NetCDF File",  command=self.select_file, style='success.TButton')
        self.select_file_button.pack(pady=10)
        
        self.variable_dropdown_label = ttk.Label(control_frame_left, text="Select Variable:", style='success.TLabel')
        self.variable_dropdown_label.pack(pady=5)
        
        self.variable_dropdown = ttk.Combobox(control_frame_left, state="readonly", width=25)
        self.variable_dropdown.pack(pady=5)
        
        self.time_step_checkbox_var = tk.BooleanVar()
        self.time_step_checkbox = ttk.Checkbutton(control_frame_left, text="Select Time Step", variable=self.time_step_checkbox_var, command=self.toggle_time_step_dropdown, style='success.Toolbutton')
        self.time_step_checkbox.pack(pady=5)
        
        self.time_step_dropdown = ttk.Combobox(control_frame_left, state="readonly", width=25)
        self.time_step_dropdown.pack(pady=5)
        self.time_step_dropdown.configure(state='disabled')

        self.depth_dropdown_label = ttk.Label(control_frame_left, text="Select Depth Level:")
        self.depth_dropdown_label.pack(pady=5)
        
        self.depth_dropdown = ttk.Combobox(control_frame_left, state="readonly", width=25)
        self.depth_dropdown.pack(pady=5)
        
        self.plot_all_checkbox_var = tk.BooleanVar()
        self.plot_all_checkbox = ttk.Checkbutton(control_frame_left, text="Plot All Time Steps", variable=self.plot_all_checkbox_var, style='success.Toolbutton')
        self.plot_all_checkbox.pack(pady=5)
        
        self.gif_checkbox_var = tk.BooleanVar()
        self.gif_checkbox = ttk.Checkbutton(control_frame_left, text="Save as GIF", variable=self.gif_checkbox_var, style='success.Toolbutton')
        self.gif_checkbox.pack(pady=5)
        
        self.gif_directory_label = ttk.Label(control_frame_left, text="GIF Directory:")
        self.gif_directory_label.pack(pady=5)
        self.gif_directory_entry = ttk.Entry(control_frame_left, width=30)
        self.gif_directory_entry.pack(pady=5)
        
        self.delete_images_var = tk.BooleanVar()
        self.delete_images_checkbox = ttk.Checkbutton(control_frame_left, text="Delete Images after GIF", variable=self.delete_images_var, style='success.Toolbutton')
        self.delete_images_checkbox.pack(pady=5)
        
        self.plot_button = ttk.Button(control_frame_left, text="Plot Variable", command=self.plot_variable)
        self.plot_button.pack(side=tk.BOTTOM, pady=10)

        # Right control frame
        control_frame_right = ttk.Frame(self.root, padding='0.35i', style='info.TFrame')
        control_frame_right.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.plot_type_label = ttk.Label(control_frame_right, text="Select Plot Type:")
        self.plot_type_label.pack(pady=5)
        
        self.plot_type_dropdown = ttk.Combobox(control_frame_right, state="readonly", width=20)
        self.plot_type_dropdown['values'] = ['pcolormesh', 'contour', 'scatter']
        self.plot_type_dropdown.set('pcolormesh')
        self.plot_type_dropdown.pack(pady=5)
        
        self.colormap_dropdown_label = ttk.Label(control_frame_right, text="Select Colormap:")
        self.colormap_dropdown_label.pack(pady=5)
        
        self.colormap_dropdown = ttk.Combobox(control_frame_right, state="readonly", width=20)
        self.colormap_dropdown.pack(pady=5)
        
        self.vmax_label = ttk.Label(control_frame_right, text="v-max:", foreground='lime')
        self.vmax_label.pack(pady=5)
        self.vmax_entry = ttk.Entry(control_frame_right, width=15)
        self.vmax_entry.pack(pady=5)
        
        self.vmin_label = ttk.Label(control_frame_right, text="v-min:", foreground='firebrick1')
        self.vmin_label.pack(pady=5)
        self.vmin_entry = ttk.Entry(control_frame_right, width=15)
        self.vmin_entry.pack(pady=5)
        
        self.xlabel_label = ttk.Label(control_frame_right, text="X-axis Label:")
        self.xlabel_label.pack(pady=5)
        self.xlabel_entry = ttk.Entry(control_frame_right, width=25)
        self.xlabel_entry.pack(pady=5)
        
        self.ylabel_label = ttk.Label(control_frame_right, text="Y-axis Label:")
        self.ylabel_label.pack(pady=5)
        self.ylabel_entry = ttk.Entry(control_frame_right, width=25)
        self.ylabel_entry.pack(pady=5)
        
        self.title_label = ttk.Label(control_frame_right, text="Plot Title:")
        self.title_label.pack(pady=5)
        self.title_entry = ttk.Entry(control_frame_right, width=25)
        self.title_entry.pack(pady=5)
        
        self.load_colormaps()

        # Variable data display frame
        self.data_display_frame = ttk.Frame(self.root,style='TFrame')
        self.data_display_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.data_display_text = tk.Text(self.data_display_frame, bg='grey',height=10, wrap=tk.WORD)
        self.data_display_text.pack(fill=tk.BOTH, expand=True)

        # Frame for the plot
        self.plot_frame = ttk.Frame(self.root, style='info.TFrame')
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def load_colormaps(self):
        colormap_names = sorted(m for m in plt.colormaps() if not m.endswith("_r"))
        self.colormap_dropdown['values'] = colormap_names
        self.colormap_dropdown.set('viridis') 
    
    def select_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("NetCDF files", "*.nc*")])
        if self.file_path:
            self.load_netcdf_file()
    
    def load_netcdf_file(self):
        try:
            self.dataset = nc.Dataset(self.file_path)
            self.variable_names = list(self.dataset.variables.keys())
            self.variable_dropdown['values'] = self.variable_names
            
            # Load time steps
            time_var = self.dataset.variables.get('time')
            if time_var is not None:
                self.time_steps = len(time_var)
                self.time_step_dropdown['values'] = list(range(self.time_steps))
                self.time_step_dropdown.set(0)
                
            # Load depth levels
            depth_var = self.dataset.variables.get('depth') or self.dataset.variables.get('z')
            if depth_var is not None:
                self.depth_levels = len(depth_var)
                self.depth_dropdown['values'] = list(range(self.depth_levels))
                self.depth_dropdown.set(0)

            # Display all variable information
            self.display_all_variable_info()
        except Exception as e:
            print(f"Error loading NetCDF file: {e}")
    
    def display_all_variable_info(self):
        self.data_display_text.delete("1.0", tk.END)
        for var_name, variable in self.dataset.variables.items():
            self.data_display_text.insert(tk.END, f"{var_name}: {repr(variable)}\n\n")

    def toggle_time_step_dropdown(self):
        if self.time_step_checkbox_var.get():
            self.time_step_dropdown.configure(state='readonly')
        else:
            self.time_step_dropdown.configure(state='disabled')
    
    def plot_variable(self):
        selected_variable = self.variable_dropdown.get()
        selected_colormap = self.colormap_dropdown.get()
        plot_type = self.plot_type_dropdown.get()

        try:
            vmin = float(self.vmin_entry.get())
        except ValueError:
            vmin = None
        try:
            vmax = float(self.vmax_entry.get())
        except ValueError:
            vmax = None

        xlabel = self.xlabel_entry.get()
        ylabel = self.ylabel_entry.get()
        title = self.title_entry.get()

        if self.plot_all_checkbox_var.get():
            time_steps = range(self.time_steps)
        else:
            if self.time_step_checkbox_var.get():
                selected_time_step = int(self.time_step_dropdown.get())  # Assuming it’s a number
            else:
                selected_time_step = 0
            time_steps = [selected_time_step]

        if selected_variable and self.dataset:
            for widget in self.plot_frame.winfo_children():
                widget.destroy()

            if self.gif_checkbox_var.get():
                gif_dir = self.gif_directory_entry.get()
                if not os.path.exists(gif_dir):
                    os.makedirs(gif_dir)

            variable_data = self.dataset.variables[selected_variable]
            variable_dims = variable_data.dimensions

            if len(variable_dims) == 3:  # [time, lat, lon]
                lats = self.dataset.variables['lat'][:] 
                lons = self.dataset.variables['lon'][:] 
                for t in time_steps:
                    try:
                        data = variable_data[t, :, :]  # Extract data for time step

                        fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})
                        ax.coastlines(linewidth=.5)

                        if plot_type == 'pcolormesh':
                            pcm = ax.pcolormesh(lons, lats, data, cmap=selected_colormap, vmin=vmin, vmax=vmax)
                        elif plot_type == 'contour':
                            pcm = ax.contour(lons, lats, data, cmap=selected_colormap, vmin=vmin, vmax=vmax)
                        elif plot_type == 'scatter':
                            pcm = ax.scatter(lons, lats, c=data, cmap=selected_colormap, vmin=vmin, vmax=vmax)

                        plt.colorbar(pcm, ax=ax, shrink=0.7)  # Adjust shrink as needed
                        ax.set_xlabel('')
                        ax.set_ylabel('')
                        gl = ax.gridlines(draw_labels=True, alpha=0)
                        gl.top_labels = False
                        gl.right_labels = False
                        if xlabel:
                            gl.bottom_labels = True
                            ax.text(0.5, -0.2, xlabel, va='bottom', ha='center',rotation='horizontal', rotation_mode='anchor',transform=ax.transAxes, fontsize=11)
                        if ylabel:
                            gl.left_labels = True
                            ax.text(-0.12, 0.5, ylabel, va='bottom', ha='center',rotation='vertical', rotation_mode='anchor',transform=ax.transAxes, fontsize=11)

                        if title:
                            ax.set_title(f'{title} (Time Step {t})')
                        else:
                            ax.set_title(f'{selected_variable} at time step {t}')

                        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
                        canvas.draw()
                        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

                        # Save figure button
                        save_button = ttk.Button(self.plot_frame, text="Save Figure", command=lambda fig=fig: self.save_figure(fig))
                        save_button.pack(side=tk.BOTTOM, pady=10)

                        if self.gif_checkbox_var.get():
                            fig.savefig(os.path.join(gif_dir, f'frame_{t:03d}.png'))

                        plt.close(fig)

                    except Exception as e:
                        print(f"Error plotting variable at time step {t}: {e}")

            elif len(variable_dims) == 4:  # [time, depth, lat, lon]
                lats = self.dataset.variables['lat'][:]
                lons = self.dataset.variables['lon'][:]
                selected_depth = int(self.depth_dropdown.get())

                for t in time_steps:
                    try:
                        data = variable_data[t, selected_depth, :, :]  # Extract data for time step and depth

                        fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})
                        ax.coastlines(linewidth=.5)

                        if plot_type == 'pcolormesh':
                            pcm = ax.pcolormesh(lons, lats, data, cmap=selected_colormap, vmin=vmin, vmax=vmax)
                        elif plot_type == 'contour':
                            pcm = ax.contour(lons, lats, data, cmap=selected_colormap, vmin=vmin, vmax=vmax)
                        elif plot_type == 'scatter':
                            pcm = ax.scatter(lons, lats, c=data, cmap=selected_colormap, vmin=vmin, vmax=vmax)

                        plt.colorbar(pcm, ax=ax, shrink=0.9)  # Adjust shrink as needed
                        ax.set_xlabel('')
                        ax.set_ylabel('')
                        gl = ax.gridlines(draw_labels=True, alpha=0)
                        gl.top_labels = False
                        gl.right_labels = False
                        if xlabel:
                            gl.bottom_labels = True
                            ax.text(0.5, -0.2, xlabel, va='bottom', ha='center',rotation='horizontal', rotation_mode='anchor',transform=ax.transAxes, fontsize=12)
                        if ylabel:
                            gl.left_labels = True
                            ax.text(-0.12, 0.5, ylabel, va='bottom', ha='center',rotation='vertical', rotation_mode='anchor',transform=ax.transAxes, fontsize=12)

                        depth_title = f' (Depth {selected_depth})' if self.depth_dropdown.get() else ''
                        if title:
                            ax.set_title(f'{title} (Time Step {t}){depth_title}')
                        else:
                            ax.set_title(f'{selected_variable} at time step {t}{depth_title}')

                        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
                        canvas.draw()
                        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

                        # Save figure button
                        save_button = ttk.Button(self.plot_frame, text="Save Figure", command=lambda fig=fig: self.save_figure(fig))
                        save_button.pack(side=tk.BOTTOM, pady=10)

                        if self.gif_checkbox_var.get():
                            fig.savefig(os.path.join(gif_dir, f'frame_{t:03d}.png'))

                        plt.close(fig)

                    except Exception as e:
                        print(f"Error plotting variable at time step {t}: {e}")

            if self.gif_checkbox_var.get():
                gif_path = os.path.join(gif_dir, 'animation.gif')
                with imageio.get_writer(gif_path, mode='I', duration=0.5) as writer:
                    for t in time_steps:
                        filename = os.path.join(gif_dir, f'frame_{t:03d}.png')
                        if os.path.exists(filename):
                            image = imageio.imread(filename)
                            writer.append_data(image)

                if self.delete_images_var.get():
                    for t in time_steps:
                        filename = os.path.join(gif_dir, f'frame_{t:03d}.png')
                        if os.path.exists(filename):
                            os.remove(filename)
                print(f"GIF saved at {gif_path}")

    def save_figure(self, fig):
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if file_path:
            fig.savefig(file_path)
            print(f"Figure saved at {file_path}")

if __name__ == "__main__":
    root = tk.Tk()
    
    root.configure()  

    # Check if a file path is provided as an argument
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = NC2(root, file_path)
    root.mainloop()