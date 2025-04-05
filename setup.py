from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="magic_folder",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A magic folder that uses local AI to sort and organize files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/magic_folder",
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
        "python-magic",
        "pytesseract",
        "Pillow",
        "pandas",
        "textract",
        "transformers",
        "openpyxl",
        "ebooklib",
        "mutagen",
    ],
    entry_points={
        "console_scripts": [
            "magic-folder=magic_folder.__main__:main",
        ],
    },
    include_package_data=True,
    package_data={
        "magic_folder": ["config/*.json"],
    },
)