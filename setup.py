import pathlib

from setuptools import setup, find_packages

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / 'README.md').read_text()

setup(
    name='weaverlet',
    version='0.2.0',
    author='Alberto Garcia-Robledo',
    author_email="alberto.garob@gmail.com",
    packages=find_packages(),
    include_package_data=True,
    license='MIT',
    description='weaverlet',
    long_description=README,
    long_description_content_type="text/markdown",
    url="",
    install_requires=[        
        'Flask==2.0.2',
        'werkzeug==2.0.0',
        'dash==2.0.0',
        'dash_extensions==0.0.65',                
        'jupyter-dash==0.4.2'        
    ]
)
