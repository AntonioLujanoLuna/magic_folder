#!/usr/bin/env python3
"""
Installer script for Magic Folder
Checks dependencies and installs missing components
"""

import os
import sys
import platform
import subprocess
import shutil
import pkg_resources
from pathlib import Path

def print_header(message):
    """Print a formatted header message"""
    print("\n" + "=" * 60)
    print(f" {message}")
    print("=" * 60)

def print_status(message, success=True):
    """Print a status message with appropriate formatting"""
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 8):
        print_status(f"Python 3.8+ required, but {major}.{minor} detected", False)
        return False
    print_status(f"Python {major}.{minor} detected")
    return True

def check_pip():
    """Check if pip is available"""
    if shutil.which("pip") or shutil.which("pip3"):
        print_status("pip detected")
        return True
    print_status("pip not found", False)
    return False

def install_package(package):
    """Install a Python package using pip"""
    pip_cmd = "pip3" if shutil.which("pip3") else "pip"
    try:
        subprocess.check_call([pip_cmd, "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def check_package(package):
    """Check if a Python package is installed"""
    try:
        pkg_resources.get_distribution(package)
        return True
    except pkg_resources.DistributionNotFound:
        return False

def check_tesseract():
    """Check if Tesseract OCR is installed"""
    if shutil.which("tesseract"):
        print_status("Tesseract OCR detected")
        return True
    print_status("Tesseract OCR not found", False)
    return False

def suggest_tesseract_install():
    """Provide instructions for installing Tesseract OCR"""
    system = platform.system().lower()
    
    print("\nTesseract OCR is required for processing images and PDFs with OCR.")
    print("Installation instructions:")
    
    if system == "darwin":  # macOS
        print("\n  macOS (using Homebrew):")
        print("  brew install tesseract")
    elif system == "linux":
        if os.path.exists("/etc/debian_version"):  # Debian/Ubuntu
            print("\n  Ubuntu/Debian:")
            print("  sudo apt-get install tesseract-ocr")
        elif os.path.exists("/etc/fedora-release"):  # Fedora
            print("\n  Fedora:")
            print("  sudo dnf install tesseract")
        else:
            print("\n  Linux (package manager varies):")
            print("  Search for tesseract-ocr in your package manager")
    elif system == "windows":
        print("\n  Windows:")
        print("  1. Download installer from https://github.com/UB-Mannheim/tesseract/wiki")
        print("  2. Run the installer and follow instructions")
        print("  3. Add Tesseract to your PATH environment variable")
    
    print("\nAfter installing Tesseract, run this installer again.")

def install_dependencies():
    """Install required Python packages"""
    required_packages = [
        "watchdog",
        "PyPDF2",
        "python-docx",
        "python-magic",
        "pytesseract",
        "Pillow",
        "pandas",
        "textract",
        "transformers",
        "sentence-transformers",
        "numpy",
        "scikit-learn",
        "openpyxl",
        "ebooklib",
        "mutagen",
        "flask",  # For web interface
        "apscheduler",  # For reports and scheduling
    ]
    
    print_header("Installing required Python packages")
    
    failed_packages = []
    for package in required_packages:
        if check_package(package):
            print_status(f"{package} already installed")
        else:
            print(f"Installing {package}...")
            if install_package(package):
                print_status(f"{package} installed successfully")
            else:
                print_status(f"Failed to install {package}", False)
                failed_packages.append(package)
    
    return failed_packages

def install_magic_folder():
    """Install Magic Folder package"""
    print_header("Installing Magic Folder")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
        print_status("Magic Folder installed successfully")
        return True
    except subprocess.CalledProcessError:
        print_status("Failed to install Magic Folder", False)
        return False

def create_config():
    """Create default config if it doesn't exist"""
    home_dir = os.path.expanduser("~")
    magic_folder_dir = os.path.join(home_dir, "magic_folder")
    config_file = os.path.join(magic_folder_dir, "config.json")
    
    if not os.path.exists(magic_folder_dir):
        os.makedirs(magic_folder_dir)
        print_status(f"Created directory: {magic_folder_dir}")
    
    if not os.path.exists(config_file):
        # Copy the default config
        example_config = os.path.join("config", "example_config.json")
        if os.path.exists(example_config):
            shutil.copy(example_config, config_file)
            print_status(f"Created default configuration at {config_file}")
        else:
            print_status(f"Could not find example config to copy", False)

def platform_specific_checks():
    """Perform platform-specific dependency checks"""
    system = platform.system().lower()
    
    if system == "windows":
        # On Windows, check for Microsoft Visual C++ Redistributable
        # This is a common dependency for many Python packages
        print("\nNote: Some packages may require Microsoft Visual C++ Redistributable.")
        print("If you encounter errors, please download and install it from:")
        print("https://aka.ms/vs/17/release/vc_redist.x64.exe")
    
    elif system == "linux":
        # On Linux, check for common build dependencies
        print("\nNote: You may need build dependencies for some packages.")
        if os.path.exists("/etc/debian_version"):  # Debian/Ubuntu
            print("On Ubuntu/Debian, run: sudo apt-get install build-essential libpoppler-cpp-dev")
        elif os.path.exists("/etc/fedora-release"):  # Fedora
            print("On Fedora, run: sudo dnf install gcc-c++ poppler-cpp-devel")

def main():
    """Main installer function"""
    print_header("Magic Folder Installer")
    
    # Check Python version
    if not check_python_version():
        print("\nPlease upgrade to Python 3.8 or higher and run this installer again.")
        return False
    
    # Check pip availability
    if not check_pip():
        print("\nPlease install pip and run this installer again.")
        return False
    
    # Install Python dependencies
    failed_packages = install_dependencies()
    
    # Check for Tesseract OCR
    has_tesseract = check_tesseract()
    if not has_tesseract:
        suggest_tesseract_install()
    
    # Install Magic Folder package
    installed = install_magic_folder()
    
    # Create default config
    if installed:
        create_config()
    
    # Platform-specific checks
    platform_specific_checks()
    
    # Summary
    print_header("Installation Summary")
    
    if failed_packages:
        print_status(f"Some packages failed to install: {', '.join(failed_packages)}", False)
        print("You can try to install them manually using pip.")
    
    if not has_tesseract:
        print_status("Tesseract OCR not installed - OCR functionality will be limited", False)
    
    if installed and not failed_packages:
        print_status("Magic Folder installed successfully!")
        print("\nTo start using Magic Folder, run:")
        print("  magic-folder")
        print("\nFor more options, run:")
        print("  magic-folder --help")
    else:
        if failed_packages:
            print("\nTry fixing the failed dependencies and run the installer again.")
        else:
            print("\nInstallation incomplete. Please check the errors above.")
    
    return installed and not failed_packages

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 