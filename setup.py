from setuptools import setup, find_packages

setup(
    name="mania",
    version="3.0.1",
    description="A command-line tool for downloading music from TIDAL",
    url="https://github.com/evan-goode/mania",
    author="Evan Goode",
    author_email="mail@evangoo.de",
    license="The Unlicense",
    packages=find_packages(),
    install_requires=[
        "bidict",
        "mutagen",
        "questionary",
        "requests",
        "ruamel.yaml>=0.15",
        "tqdm",
    ],
    entry_points={"console_scripts": ["mania=mania.main:execute"]},
)
