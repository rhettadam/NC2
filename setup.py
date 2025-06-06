from setuptools import setup, find_packages

setup(
    name='nc2',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    package_data={'nc2': ['Logo3.png']},
    install_requires=[
        'numpy>=1.26.4',
        'matplotlib>=3.8.0',
        'netCDF4>=1.6.2',
        'cartopy>=0.23.0',
        'ttkbootstrap>=1.10.1',
        'Pillow>=10.2.0',
        'imageio>=2.33.1'
    ],
    entry_points={
        'console_scripts': [
            'nc2 = nc2.nc2:main',
        ],
    },
    author='Rhett R. Adam',
    author_email='rhettadambusiness@gmail.com',
    description='NC² NetCDF viewer',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/rhettadam/NC2',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)