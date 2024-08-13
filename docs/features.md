---
layout: default
title: Features
permalink: /features/
---
# NC² Features

## 1. File Selection and Variable Handling
- **Select NetCDF File**: Easily choose and load NetCDF files for analysis.
- **Variable Selection**: A dropdown menu to select the specific variable of interest from the loaded NetCDF file (e.g., water_temp, salinity, etc.).

## 2. Time and Depth Control
- **Time Step Selection**: Choose the specific time step for the data visualization.
- **Depth Level Selection**: Select the depth level of interest

## 3. Data Information and Statistics
- **Data Summary**: Display basic statistics for the selected DTG and/or depth, including mean, median, standard deviation, anomalies detected, minimum, and maximum values.
- **Cursor Location Information**: Real-time display of the cursor's longitude and latitude coordinates, I and J indices, and the corresponding data value at that location.

## 4. Plot Customization
- **Plot Type Selection**: Choose different plot types such as **pcolormesh**, **contour**, **contourf**, **quiver**, **streamplot**, and **imshow**, with dynamically updated customization variables.
- **Colormap Selection**: Select from various colormaps (e.g., jet) to enhance the visualization and interpretation of data.
- **Reverse Colormap**: Option to reverse the colormap for better contrast and data representation.
- **Colorbar Orientation**: Customize the orientation of the colorbar (left, right, top, bottom) to suit the presentation needs.
- **Adjustable Value Limits**: Set custom limits for the color range (V-Max, V-Min) to focus on specific data ranges.
- **Geographical Extents**: Specify the geographical extents for the plot to zoom into particular regions of interest.
- **Projections**: Specify the projection for the plot (e.g., PlateCarree).

## 5. Further Customization
- **Gridlines Toggle**: Enable or disable gridlines on the plot for better spatial referencing and specify alpha (transparency). 
- **Masking Toggle**: Enable Cartopy Feature ocean and land masking.
- **Axis Labels**: Add labels to the X and Y axes for clear identification of the data dimensions.
- **Plot Title**: Set a custom title for the plot to provide context and clarity.

## 6. Data Visualization
- **Show in Window**: Display the selected data variable in a separate window.
- **Save as GIF**: Option to save the animation as a GIF for easy sharing and presentation.
- **GIF Options**: Options for GIF generation:
    - **FPS**: Specify the FPS (Frames Per Second) of the GIF file
    - **Range**: Specify the indice that the GIF generation should stop at
    - **Loop**: Produce a looping GIF file
    - **Delete/Save Images**: Delete or save images after GIF generation
- **Playback Controls**: Play, pause, reverse, speed up, slow down, and stop animations to analyze temporal changes in the dataset.

## 7. Interactive Analysis Tools
- **Time Series**: Generate time series and histogram plots to analyze data trends over time, and at a specific depth.
- **Depth Series**: Generate depth series and histogram plots to analyze data trends over depth, and at a specific time.
- **Vertical Section**: Create vertical section plots at latitude or longitude slices to examine vertical variations in the dataset.

## 8. User Interface and Experience
- **Modern GUI**: Intuitive and user-friendly interface designed for ease of use, reducing the learning curve for new users.
- **Theme Customization**: Toggle between light and dark modes for a comfortable viewing experience in different lighting conditions.
- **Detailed Legends and Labels**: Enhanced legends and labels for better understanding and interpretation of the plots.
- **Multiple Plotting Windows**: Capability to open multiple plotting windows simultaneously for comparative analysis.

## 9. Integration with Scientific Tools
- **Built with Cartopy and Matplotlib**: Leverages powerful Python libraries for cartographic projections and high-quality plotting, ensuring accuracy and flexibility.
- **Publication-Quality Plots**: Ability to produce highly customizable and publication-quality plots suitable for scientific presentations and publications.

## 10. Additional Features
- **Navigation Toolbar**: Plot navigation toolbar with buttons:
    - Reset original view 
    - Back to previous view 
    - Forward to next view 
    - Pan figure 
    - Zoom to rectangle 
    - Configure subplots 
    - Save figure
- **Comprehensive Documentation**: Detailed user documentation available to help users understand and utilize all features effectively.

# Contact Me

<p style="font-size: 20px;">
For any inquiries, suggestions, or feedback, feel free to reach out:
</p>

```sh
Email: rhettadambusiness@gmail.com

Rhett R. Adam

VU Undergrad EES
```
