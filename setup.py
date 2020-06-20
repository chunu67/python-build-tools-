from setuptools import setup, find_packages

README = ''
with open('README.md', 'r') as f:
    README=f.read()
setup(
    name="pybuildtools",
    version="0.3.1",
    description="Library implementing common processes and logging for buildsystems",
    long_description=README,
    long_description_content_type='text/markdown',
    author="Rob Nelson",
    author_email="nexisentertainment@gmail.com",
    packages=find_packages(exclude=['testcopyright', '*-fixed', 'qc', 'build']),
    python_requires='>=3.6',
    install_requires=[
        'colorama',
        'jinja2',
        'lxml',
        'psutil',
        'pygit2',
        'pyyaml',
        'requests',
        'six',
        'toml',
        'tqdm',
        'twisted'
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
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.6",
    ],
)
