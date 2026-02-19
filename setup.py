from setuptools import setup, find_packages

setup(
    name="matrace",
    version="0.1.0",
    package_dir={"": "."},
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.10",
    install_requires=[
        "miss_hit_core",
        "torch",
        "numpy",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "torchdiffeq",
        ],
    },
)