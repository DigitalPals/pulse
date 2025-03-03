from setuptools import setup, find_packages
import os

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

# Read version from VERSION file
version = "0.1.0"  # Default fallback version
version_file = os.path.join(os.path.dirname(__file__), "..", "VERSION")
if os.path.exists(version_file):
    with open(version_file, "r") as f:
        version = f.read().strip()

setup(
    name="cybex-pulse",
    version=version,
    author="Cybex Team",
    author_email="info@example.com",
    description="Home Network Monitoring Application",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/cybex-pulse",
    packages=find_packages(include=['cybex_pulse', 'cybex_pulse.*']),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "cybex-pulse=cybex_pulse.__main__:main",
        ],
    },
)