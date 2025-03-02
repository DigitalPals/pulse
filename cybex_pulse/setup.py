from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="cybex-pulse",
    version="0.1.0",
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