from setuptools import setup, find_packages

setup(
    name="4dnetworkmesh",
    version='3.2.3',
    packages=find_packages(),
    install_requires=[
        'numpy',
        'networkx>=3.0',
        'matplotlib>=3.5.0',
    ],
)