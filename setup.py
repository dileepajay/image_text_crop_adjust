 
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="crop_adjust",
    version="0.1.0",
    author="DileepaJay",
    author_email="me.dreamwalker@gmail.com",
    description="A library for adjusting bounding boxes around dark text/objects in images",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="http://github.com/dileepajay/crop_adjust",
    packages=setuptools.find_packages(),  # automatically finds "crop_adjust" package
    install_requires=[
        "Pillow>=9.0.0",
    ],
    python_requires=">=3.7",
)
