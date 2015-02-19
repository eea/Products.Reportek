from setuptools import setup, find_packages

setup(
    name='Products.Reportek',
    version='3.7.2-dev13',
    author='Eau de Web',
    author_email='office@eaudeweb.ro',
    url='https://github.com/eea/Products.Reportek',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'lxml',
        'path.py',
        'requests==1.2.3',
        'plone.memoize',
        'Zope2',
    ],
)
