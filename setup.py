import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyvpc",
    version="0.0.3",
    author="Arie Lev",
    author_email="levinsonarie@gmail.com",
    description="Python AWS VPC CIDR available range finder with sub networks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ArieLevs/PyVPC",
    license='Apache License 2.0',
    packages=setuptools.find_packages(),
    install_requires=[
        'argparse==1.4.0',
        'boto3==1.11.9'
    ],
    classifiers=(
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    entry_points={
        'console_scripts': [
            'pyvpc = pyvpc.pyvpc:main'
        ],
    },
)
