from setuptools import setup, find_packages


setup(
    name="pybuildtools",
    version="0.2.2",
    description=("Library implementing common processes and logging for buildsystems"),
    author="Rob Nelson",
    author_email="nexisentertainment@gmail.com",
    packages=find_packages(exclude=['testcopyright', '*-fixed', 'qc', 'build']),
    install_requires=[
        "psutil",
        "lxml",
        "twisted",
        "pyyaml",
        "jinja2",
        "toml",
        "requests>=2.0",
        'six',
        'colorama',
        'tqdm'
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
        "Programming Language :: Python :: 3.6",
    ],
)
