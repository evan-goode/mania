# Always prefer setuptools over distutils
from setuptools import setup, find_packages

setup(
    name='mania',
    version='1.0.0',
    description='A command-line tool for downloading music from GPM',
    url='https://github.com/evan-goode/mania',
    author='Evan Goode',
    author_email='mail@evangoo.de',
    license='The Unlicense',
    py_modules=["mania"],
    install_requires=['gmusicapi',
                      'ruamel.yaml',
                      'inquirer',
                      'eyeD3',
                      'progress',
                      'cursor'],
    entry_points={'console_scripts': ['mania=mania:main']},
)
