from setuptools import setup, find_packages
import shutil
import os

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Copy config files to the package directory during setup
if not os.path.exists("magic_folder/config"):
    os.makedirs("magic_folder/config")
    
if os.path.exists("config/default_config.json"):
    shutil.copy("config/default_config.json", "magic_folder/config/default_config.json")

setup(
    name="magic_folder",
    version="0.1.0",
    author="Antonio Lujano",
    author_email="a00lujano@gmail.com",
    description="A magic folder that uses local AI to sort and organize files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AntonioLujanoLuna/magic_folder",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "watchdog",
        "PyPDF2",
        "python-docx",
        "python-magic-bin; platform_system=='Windows'",
        "python-magic; platform_system!='Windows'",
        "pytesseract",
        "Pillow",
        "pandas",
        "transformers",
        "sentence-transformers",
        "numpy",
        "scikit-learn",
        "openpyxl",
        "ebooklib",
        "mutagen",
        "flask",
        "apscheduler",
        "textract",
        "werkzeug",
    ],
    entry_points={
        "console_scripts": [
            "magic-folder=magic_folder.__main__:main",
        ],
    },
    include_package_data=True,
    package_data={
        "magic_folder": ["config/*.json", "web/templates/*.html", "web/static/*"],
    },
)