from setuptools import setup

setup(
    name="matrace",
    version="0.1.0",
    package_dir={"": "."},
    packages=['matrace'],
    install_requires=[
        "miss_hit_core",
        "torch",
        "numpy"
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "torchdiffeq",
        ],
    },
)