
ZopeTestCase is part of Zope since version 2.8.

To be able to run the unittests you must install the products Reportek
and Reportek_dependencies on a Zope system. Then goto the tests directory
of Reportek and do

./runtest runalltests.py

The runtest is a script that detects from zopectl what Python interpreter
you use and the software home. You can also use it to run individual test
scripts, as in ./runtest testCollection.py

For versions of Zope lower than 2.8, you can get ZopeTestCase from
http://zope.org/Members/shh/ZopeTestCase

For information on how to use it and write new tests, go to
http://www.zope.org/Members/shh/ZopeTestCaseWiki
