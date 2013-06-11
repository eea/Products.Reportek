from setuptools import setup, find_packages

setup(
    name='Products.Reportek',
    version='3.1-dev',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'lxml',
        'path.py',
        'requests==1.2.3',
    ],
)
