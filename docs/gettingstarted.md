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

### Main Features

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

- **Select Colormap:** Choose the color scheme for your plot.
- **Reverse Colormap:** Toggle to reverse the color mapping.
- **Colorbar Orientation:** Choose the orientation of the colorbar (right, left, top, bottom).
<!-- Screenshot needed: Show the plot type and colormap selection options -->

## Adjust Plot Parameters
- **V-Max and V-Min:** Set the maximum and minimum values for the color scale.
- **Extents:** Define the geographical extents (xmin, xmax, ymin, ymax).
- **Gridlines and Alpha:** Toggle gridlines and adjust transparency.
- **Ocean/Land Toggle:** Highlight ocean or land.
- **Labels:** Add labels for X-axis and Y-axis.
- **Plot Title:** Set a title for your plot.
<!-- Screenshot needed: Show the fields for V-Max, V-Min, extents, and toggles for gridlines, ocean/land -->

## Time Plot and Depth Plot
- **Show Time Plot:** Click to visualize data over time.
- **Show Depth Plot:** Click to visualize data over depth.
<!-- Screenshot needed: Show the "Show Time Plot" and "Show Depth Plot" buttons -->

## GIF Generation
- **FPS**: Specify the FPS (Frames Per Second) of the GIF file
- **Range**: Specify the indice that the GIF generation should stop at
- **Loop**: Produce a looping GIF file
- **Delete/Save Images**: Delete or save images after GIF generation

![gif](https://github.com/user-attachments/assets/d071b27f-0efc-4d3b-b01b-76e6d0b5eb77)

## Additional Features
- **Show in Window:** Toggle to display the plot in a separate window.
<!-- Screenshot needed: Highlight the additional feature buttons -->

## Viewing Data Information
<p style="font-size: 20px;">
View detailed metadata about the loaded NetCDF file and selected variable in the lower panel.
</p>
<!-- Screenshot needed: Show the metadata display area -->

