from setuptools import setup, find_packages

with open("README.md", "r") as readme_file:
    readme = readme_file.read()

# requirements = []

setup(
    name="query_formatter",
    version="0.0.1",
    author="Nikita Kokarev",
    author_email="kokarevnickita@gmail.com",
    description="Easy way to format sql templates",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/NickKokarev/query-formatter/",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ]
)
