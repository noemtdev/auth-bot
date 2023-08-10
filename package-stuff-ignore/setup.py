from setuptools import setup, find_packages

VERSION = '1.0'
DESCRIPTION = 'A package that allows you to import a module to backup your members!'

# Setting up
setup(
    name="noms-auth",
    version=VERSION,
    author="asov",
    author_email="<noemtdev@gmail.com>",
    description=DESCRIPTION,
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=['aiohttp'],
    keywords=['python', 'discord', 'backup', 'members'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
        "Programming Language :: Python :: 3",
    ],
    package_data={'noms-auth': ['noms-auth/*']}
)