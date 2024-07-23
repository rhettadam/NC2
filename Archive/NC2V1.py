import tkinter as tk
from tkinter import filedialog, ttk
import netCDF4 as nc
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from matplotlib import cm


class NetCDFViewer:
        def __init__(self, root):
            self.root = root
            self.root.title("NetCDF Viewer")
            
            self.file_path = None
            self.dataset = None
            self.variable_names = []
            
            self.create_widgets()
    
        def create_widgets(self):
            self.select_file_button = tk.Button(self.root, text="Select NetCDF File", command=self.select_file)
            self.select_file_button.pack(pady=10)
            
            self.variable_dropdown_label = tk.Label(self.root, text="Select Variable:")
            self.variable_dropdown_label.pack(pady=5)
            
            self.variable_dropdown = ttk.Combobox(self.root, state="readonly")
            self.variable_dropdown.pack(pady=5)
            
            self.colormap_dropdown_label = tk.Label(self.root, text="Select Colormap:")
            self.colormap_dropdown_label.pack(pady=5)
            
            self.colormap_dropdown = ttk.Combobox(self.root, state="readonly")
            self.colormap_dropdown.pack(pady=5)
            
            self.plot_button = tk.Button(self.root, text="Plot Variable", command=self.plot_variable)
            self.plot_button.pack(pady=10)
            
            self.load_colormaps()
    
        def load_colormaps(self):
            colormap_names = sorted(m for m in plt.colormaps() if not m.endswith("_r"))
            self.colormap_dropdown['values'] = colormap_names
            self.colormap_dropdown.set('viridis')  # Set a default colormap
    
        def select_file(self):
            self.file_path = filedialog.askopenfilename(filetypes=[("NetCDF files", "*.nc")])
            if self.file_path:
                self.load_netcdf_file()
    
        def load_netcdf_file(self):
            try:
                self.dataset = nc.Dataset(self.file_path)
                self.variable_names = list(self.dataset.variables.keys())
                self.variable_dropdown['values'] = self.variable_names
            except Exception as e:
                print(f"Error loading NetCDF file: {e}")
    
        def plot_variable(self):
            selected_variable = self.variable_dropdown.get()
            selected_colormap = self.colormap_dropdown.get()
            if selected_variable and self.dataset:
                try:
                    variable_data = self.dataset.variables[selected_variable]
                    lats = self.dataset.variables['lat'][:]
                    lons = self.dataset.variables['lon'][:]
                    data = variable_data[0, :, :]  # Assuming the first time step
                    
                    fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})
                    ax.coastlines()
                    pcm = ax.pcolormesh(lons, lats, data, cmap=selected_colormap)
                    plt.colorbar(pcm, ax=ax)
                    ax.set_title(f'{selected_variable} at time step 1')
                    plt.show()
                except Exception as e:
                    print(f"Error plotting variable: {e}")


if __name__ == "__main__":
        root = tk.Tk()
        app = NetCDFViewer(root)
        root.mainloop()