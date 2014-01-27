from setuptools import setup, find_packages

setup(
    name='Products.Reportek',
    version='3.6.1',
    author='Eau de Web',
    author_email='office@eaudeweb.ro',
    url='http://naaya.eaudeweb.ro',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'lxml',
        'path.py',
        'requests==1.2.3',
    ],
)
