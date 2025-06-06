# Welcome To NC²

[![PyPI version](https://badge.fury.io/py/nc2.svg)](https://pypi.org/project/nc2/)

## What are NetCDF Files?

NetCDF (Network Common Data Form) is a set of software libraries and self-describing, machine-independent data formats that support the creation, access, and sharing of array-oriented scientific data. NetCDF files are widely used in climate science, meteorology, oceanography, and other fields to store and distribute large datasets. These files are valuable for their ability to store multi-dimensional data (such as temperature, humidity, and wind speed) efficiently, making them essential for researchers and scientists dealing with complex environmental data.

## NCview and Panoply

Programs such as NCview and Panoply have become indispensable tools for scientists working with NetCDF files.

    NCview: NCview is a simple yet powerful visual browser for NetCDF files. It allows users to quickly view the data stored in these files through various plotting options. NCview is particularly useful for scientists who need to quickly check the contents of their datasets.

    Panoply: Panoply, developed by NASA, is another powerful tool that provides more advanced features than NCview. It allows users to visualize georeferenced and other arrays from NetCDF, HDF, and GRIB datasets. Panoply offers a range of plotting options, including latitude-longitude, latitude-vertical, and time-latitude plots, making it a versatile tool for in-depth data analysis.

Both NCview and Panoply are essential for scientists who need to visualize and analyze their data quickly. However, these tools come with limitations, such as less intuitive user interfaces and a lack of customization options for publication-quality plots.

## What is NC²?

![Logo4](https://github.com/user-attachments/assets/377cbe6b-5433-42c3-94a3-8f8b73f4ee7f)


NC² is a next-generation NetCDF viewer designed to overcome the limitations of traditional tools like NCview and Panoply. Built with CartoPy and Matplotlib, NC² offers a versatile and user-friendly platform for visualizing and analyzing NetCDF data. Here’s what NC² brings to the table:

    Modern GUI: NC² features a clean and intuitive graphical user interface (GUI) that significantly reduces the learning curve for new users. 

    Familiar Tools: NC² is built with familiar scientific Python libraries, including CartoPy for cartographic projections and Matplotlib for plotting. This makes it easy for users who are already familiar with these tools to extend and customize their data visualizations.

    Publication-Quality Plots: One of the standout features of NC² is its ability to produce publication-quality plots. Users can create highly customizable plots that meet standards required for scientific publications, ensuring that their visualizations are both accurate and aesthetically pleasing.

    Versatility: NC² is designed to handle a wide range of NetCDF data types. Whether you are working with atmospheric data, oceanographic measurements, or climate model outputs, NC² provides the tools you need to visualize and analyze your data effectively.

    Easy Customization: NC² offers a variety of customization options, allowing users to tailor their plots to their specific needs. From adjusting color maps and scales to adding annotations and labels, NC² makes it easy to create detailed and informative visualizations.

    Advanced Features: In addition to basic plotting functionalities, NC² provides advanced features such as time series analysis, depth profiling, and GIF generations. These features enable users to gain deeper insights into their data and conduct more comprehensive analyses.

Explore the features and capabilities of NC², and see how it can enhance your research and data analysis workflows.

![ScreenRecording2025-06-06124348-ezgif com-video-to-gif-converter](https://github.com/user-attachments/assets/f795717d-457c-425e-a9e1-f0f37a34620c)

## Installation

To install NC², run the following command:

```sh
pip install nc2
```
After installation, you can run NC² from the command line as follows:

```sh
nc2 path/to/your/file.nc
```

## Contact Me!

rhettadambusiness@gmail.com

Rhett R. Adam 7/25/24

VU Undergrad EES

## License

NC² is distributed under the GPL-3.0 License. See the LICENSE file for details.

Copyright (c) 2024 Rhett R. Adam

