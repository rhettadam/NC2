from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='nc2',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    package_data={'nc2': ['Logo3.png']},
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'nc2 = nc2.nc2:main',
        ],
    },
    author='Rhett Adam',
    author_email='rhettadambusiness@gmail.com',
    description='NC² NetCDF viewer',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/rhettadam/nc2',
)
