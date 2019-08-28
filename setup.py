from setuptools import setup, find_packages

setup(
    name='Products.Reportek',
    version='3.8.4',
    author='Eau de Web',
    author_email='office@eaudeweb.ro',
    url='https://github.com/eea/Products.Reportek',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'Products.PluggableAuthService',
        'Zope2',
        'collective.monkeypatcher',
        'lxml',
        'path.py',
        'plone.memoize',
        'requests',
        'xlwt',
        'zipstream',
        'xmltodict==0.11.0',
        'eea.rabbitmq.client',
        'contextlib2'
    ],
    entry_points="""
          # -*- Entry points: -*-
          [console_scripts]
          zip_cache_cleanup = Products.Reportek.RepUtils:cleanup_zip_cache
          automatic_qa = Products.Reportek.scripts.automatic_qa:main
          auto_fallin = Products.Reportek.scripts.auto_fallin:main
          auto_cleanup = Products.Reportek.scripts.auto_cleanup:main
          """,
)
