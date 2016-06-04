from setuptools import setup, find_packages


setup(
    name="buildtools",
    version="0.0.1",
    description=("Simple library implementing common processes and logging for buildsystems"),
    author="Rob Nelson",
    author_email="nexisentertainment@gmail.com",
    packages=find_packages(),
    install_requires=[
        "psutil",
        "lxml",
        "twisted",
        "pyyaml",
        "jinja2",
        "toml",
        "requests>=2.0",
        'six'
    ],
    tests_require=[
        "pytest",
        "mock==1.0.1",
    ],
    extras_require={
        "development": [
            "pylint",
        ],
    },
    license="MIT License",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 2.7",
    ],
)
