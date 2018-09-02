from setuptools import setup, find_packages

setup(
    name='mania',
    version='2.0.0',
    description='A command-line tool for downloading music from GPM and TIDAL',
    url='https://github.com/evan-goode/mania',
    author='Evan Goode',
    author_email='mail@evangoo.de',
    license='The Unlicense',
    packages=find_packages(),
    install_requires=[
        'gmusicapi',
        'ruamel.yaml>=0.15',
        'whaaaaat',
        'progress',
        'cursor',
        'mutagen',
        'requests'
    ],
    entry_points={'console_scripts': ['mania=mania.main:execute']},
)
