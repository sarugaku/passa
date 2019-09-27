from setuptools import setup

setup(
    name="demo",
    version="0.0.1",
    license="MIT",
    py_modules="demo.py",
    description="Demo package",
    install_requires=["requests"],
    extras_require={
        "time": ["pytz"],
        "csv": ["tablib"]
    }
)
