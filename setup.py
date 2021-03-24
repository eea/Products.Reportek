import os
from os.path import join

from setuptools import find_packages, setup

NAME = 'Products.Reportek'
PATH = NAME.split('.') + ['version.txt']
VERSION = open(join(*PATH)).read().strip()
setup(name=NAME,
      version=VERSION,
      description="Products Reportek",
      long_description_content_type="text/x-rst",
      long_description=(
          open("README.rst").read() + "\n" +
          open(os.path.join("docs", "changelog.rst")).read()
      ),
      author='European Environment Agency: DIS1 P-Team',
      author_email='eea-edw-c-team-alerts@googlegroups.com',
      url='https://github.com/eea/Products.Reportek',
      packages=find_packages(),
      include_package_data=True,
      license='MPL',
      zip_safe=False,
      install_requires=[
          'Products.PluggableAuthService',
          'Zope2',
          'collective.monkeypatcher',
          'lxml',
          'path.py',
          'plone.caching',
          'plone.cachepurging',
          'plone.memoize',
          'requests',
          'xlwt',
          'clamd',
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
