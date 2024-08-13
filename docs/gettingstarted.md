---
layout: default
title: Getting Started
permalink: /getting-started/
---
# Getting Started

<p style="font-size: 20px;">
To install NC², run the following command:
</p>

```sh
pip install nc2
```

<p style="font-size: 20px;">
After installation, you can run NC² from the command line as follows:
</p>

```sh
nc2 path/to/your/file.nc
```

<p style="font-size: 20px;">
You can also run NC² without a preloaded file:
</p>

```sh
nc2
```

### Using NC²

## Select NetCDF File
<p style="font-size: 20px;">
To select a file using your operating system's file explorer, use the 'Select NetCDF File' button.
</p>
![file_select](https://github.com/user-attachments/assets/b1a84564-2a65-4fb4-9374-432efd37c201)

## Select Variable
<p style="font-size: 20px;">
Use the "Select Variable" dropdown to choose which variable in your NetCDF file you want to visualize.
</p>
![Screenshot from 2024-08-05 03-41-17](https://github.com/user-attachments/assets/04e430d1-701f-4f83-a962-1607fbae4c06)

## Select Time Step
<p style="font-size: 20px;">
For three dimensional data, use the "Select Time Step" dropdown to select the specific time step for the variable you are viewing.
</p>
![Screenshot from 2024-08-05 03-41-28](https://github.com/user-attachments/assets/66d364f0-a6c2-4d5e-97ea-86645fa87bf9)

## Select Depth Level
<p style="font-size: 20px;">
For four dimensional data, use the "Select Depth Level" dropdown to choose the depth level you want to visualize.
</p>
![Screenshot from 2024-08-05 03-41-45](https://github.com/user-attachments/assets/d6e0caf5-c390-49b8-b17e-99b3d3002adc)

## Plot Types and Colormaps
- **Select Plot Type:** Choose the type of plot (e.g., pcolormesh, contour).
- **Dynamic Plot Option Settings:** Pcolormesh is the standard plot type. When selecting a different plot type, the settings will update dynamically:

  ![Screenshot from 2024-08-13 02-04-30](https://github.com/user-attachments/assets/2b7e403e-1c5d-4481-8e43-2c3c3f9d09af)
  ![Screenshot from 2024-08-13 02-05-11](https://github.com/user-attachments/assets/56488348-9c9e-4b8f-b81e-64c727122c59)
  ![Screenshot from 2024-08-13 02-05-39](https://github.com/user-attachments/assets/5b05c306-b2fc-498a-b6a8-b066b62e76f9)
  ![Screenshot from 2024-08-13 02-05-51](https://github.com/user-attachments/assets/6ec2c7a3-ae73-4a1c-b317-1e2e51836f5b)

- **Select Colormap:** Choose the colormap for your plot.
- **Reverse Colormap:** Toggle to reverse the colormap.
- **Colorbar Orientation:** Choose the orientation of the colorbar (right, left, top, bottom).
- **Colorbar Shrink:** float, default: 1.0 (Fraction by which to multiply the size of the colorbar).

  ![Screenshot from 2024-08-13 13-15-54](https://github.com/user-attachments/assets/3ec7a9c5-fa81-4ecb-b41f-f9309dc2aac0)

## Adjust Plot Parameters
- **V-Max and V-Min:** float, optional (Define the data range that the colormap covers). 
- **Extents:** Define the geographical extents of the plot as 'xmin, xmax, ymin, ymax.'
- **Projections**: Specify the projection for the plot (e.g., PlateCarree).
- **Gridlines and Alpha:** Toggle gridlines and adjust transparency.
- **Ocean/Land Toggle:** Ocean/land Cfeature masking.

  ![Screenshot from 2024-08-13 13-29-14](https://github.com/user-attachments/assets/ef868f26-e5eb-4e86-9e68-4c83b240ad4b)

## Time Plot and Depth Plot
**Show Time Plot:** Click to visualize a time series of your selected variable at a specific depth

![Screenshot from 2024-08-13 13-35-48](https://github.com/user-attachments/assets/12f8d3ab-48a0-4a82-a384-12bd9b32830a)

![Screenshot from 2024-08-13 13-34-37](https://github.com/user-attachments/assets/ac1cfe6d-594d-4178-8a67-fa305cc75ac9)

**Show Depth Plot:** Click to visualize a depth series of your selected variable at a specific time step.

![Screenshot from 2024-08-13 13-40-03](https://github.com/user-attachments/assets/db77ac66-38d5-47f2-8cee-3fcad28a39be)

![Screenshot from 2024-08-13 13-39-17](https://github.com/user-attachments/assets/82eb8f32-ae1e-4761-bc1c-315e43b39aef)

## Vertical Section Plots
**Input a longitude coordinate and press the slice button to produce a vertical section at a meridian line**

![Screenshot from 2024-08-13 14-19-46](https://github.com/user-attachments/assets/1ad88a34-89d6-4b4e-a7c1-c751b0f1a7b2)

![Screenshot from 2024-08-13 14-21-01](https://github.com/user-attachments/assets/00ab2678-4740-42b9-bbc2-a01b0bec6521)

**Input a latitude coordinate and press the slice button to produce a vertical section at a parallel line**

![Screenshot from 2024-08-13 14-21-32](https://github.com/user-attachments/assets/fe1457ca-b3a2-4c9b-b3ed-8bf04f7b956f)

![Screenshot from 2024-08-13 14-22-35](https://github.com/user-attachments/assets/75597e13-542c-4157-bfde-a4a180d77e15)

## GIF Generation
- **FPS:** Specify the FPS (Frames Per Second) of the GIF file
- **Range:** Specify the indice that the GIF generation should stop at
- **Loop:** Produce a looping GIF file
- **Delete/Save Images:** Delete or save images after GIF generation

  ![gif](https://github.com/user-attachments/assets/d071b27f-0efc-4d3b-b01b-76e6d0b5eb77)

**The "Make GIF" Checkbutton must be selected to generate a GIF. When it is selected, the user cannot select a specific timestep as well.**
**The "Save GIF" Button opens up a file explorer where you must select a directory for the GIF to be generated.**
**Press the "Plot Variable" Button to generate the GIF.**

## GIF Playback
- **Play:** Play the GIF at standard speed (10 FPS)
- **Pause:** Pause the GIF
- **Reverse:** Reverse the GIF at standard speed
- **Stop:** Restart the GIF playback and reset speed
- **Slow (<<):** Slow down by increments of 2 FPS
- **Speed (>>):** Speed up by increments of 2 FPS

  ![Screenshot from 2024-08-13 14-08-52](https://github.com/user-attachments/assets/7f566f36-c7cf-4edd-bc97-f272724933eb)

## Navigation Toolbar
- **Home, Forward and Back buttons:** Forward/Back are used to navigate back and forth between previously defined views. Home always takes you to the default view of your data. 
- **Pan/Zoom:** Press the left mouse button and hold it to pan the figure, dragging it to a new position. Press the right mouse button to zoom, dragging it to a new position.
- **Zoom to Rectangle:** Define a rectangular region by dragging the mouse while holding the button to a new location. When using the left mouse button, the axes view limits will be zoomed to the defined region.
- **Configure Subplots:** Use this tool to configure the appearance of the subplot (stretch/compress the left, right, top, or bottom side of the subplot.
- **Save Figure:** Click this button to launch a file save dialog. You can save files with the following extensions: png, ps, eps, svg and pdf.
- **Forward (>>) Button:** Advance the time step selection by one.
- **Back (<<) Button:** Reverse the time step selection by one.

![toolbar](https://github.com/user-attachments/assets/1e6a4a8f-5ed4-4f2a-aef4-34320985e6e3)

## Metadata and Statistics
- **View detailed metadata about the loaded NetCDF file**

![Screenshot from 2024-08-13 15-00-57](https://github.com/user-attachments/assets/96e3a13b-4aba-4436-83be-2d20e3a21f7d)

- **View basic statistics of your selected variable at a specific time and/or depth**

![Screenshot from 2024-08-13 15-01-19](https://github.com/user-attachments/assets/5c93c803-1a1f-4ec9-92d0-8ef888fe30ff)

- **View lon, lat, I and J indices, and the data value where the mouse is currently hovering**

![Screenshot from 2024-08-13 15-02-56](https://github.com/user-attachments/assets/138f4dc9-b637-4ed0-9e54-575530406fe0)

## Additional Features
- **Show in Window:** Toggle to display the plot in a separate window.

![Screenshot from 2024-08-13 14-31-29](https://github.com/user-attachments/assets/d823d23c-356f-4a03-8d3a-ecfe1ed6f199)

![Screenshot from 2024-08-13 14-33-04](https://github.com/user-attachments/assets/5a7b6e1a-688d-4060-86a9-a4e31d9677bf)

- **Labels:** Add labels for X-axis and Y-axis.
- **Plot Title:** Set a title for your plot.
- **Themes:** Select a theme for NC² from a a dropdown of light and dark options. 

![Screenshot from 2024-08-13 14-34-15](https://github.com/user-attachments/assets/591741c1-9a52-4918-9d27-45ebc8b144bc)

# Contact Me

<p style="font-size: 20px;">
For any inquiries, suggestions, or feedback, feel free to reach out:
</p>

```sh
Email: rhettadambusiness@gmail.com

Rhett R. Adam

VU Undergrad EES
```