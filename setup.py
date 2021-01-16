from setuptools import setup, find_packages

README = ''
with open('README.md', 'r') as f:
    README=f.read()
setup(
    name="pybuildtools",
    version="0.4.0",
    description="Library implementing common processes and logging for buildsystems",
    long_description=README,
    long_description_content_type='text/markdown',
    author="Rob Nelson",
    author_email="nexisentertainment@gmail.com",
    packages=find_packages(exclude=['testcopyright', '*-fixed', 'qc', 'build', '*.bat', '*.sh', '*.jinja', 'vnm.*', '.pre-commit-config.yaml', '.check-identity']),
    python_requires='>=3.8',
    install_requires=[
        'colorama',
        'jinja2',
        'lxml',
        'psutil',
        'pygit2',
        'requests',
        'ruamel.yaml',
        'six',
        'toml',
        'tqdm',
        'twisted',
    ],
    extras_require={
        "development": [
            "mypy"
        ],
    },
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.6",
    ],
)
