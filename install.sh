#!/bin/bash

set -e
#set -x
FINDLINKS='http://eggrepo.eea.europa.eu/simple'
INDEX='http://pypi.python.org/simple'

SETUPTOOLS=`curl -s https://raw.github.com/eea/eea.plonebuildout.core/master/buildout-configs/versions.cfg | grep "setuptools\s*\=\s*" | sed 's/ *$//g' | sed 's/=$//g' | sed 's/\s*=\s*/==/g'`
ZCBUILDOUT=`curl -s https://raw.github.com/eea/eea.plonebuildout.core/master/buildout-configs/versions.cfg | grep "zc\.buildout\s*=\s*" | sed 's/\s*=\s*/==/g'`

if [ -z "$SETUPTOOLS" ]; then
  SETUPTOOLS="setuptools"
fi

if [ -z "$ZCBUILDOUT" ]; then
  ZCBUILDOUT="zc.buildout"
fi

if [ -z "$PYTHON" ]; then
  PYTHON="/usr/bin/env python2.6"
fi

# Make sure python is 2.6 or later
PYTHON_OK=`$PYTHON -c 'import sys
print (sys.version_info >= (2, 6) and "1" or "0")'`

if [ "$PYTHON_OK" = '0' ]; then
    echo "Python 2.6 or later is required"
    echo "EXAMPLE: PYTHON=/path/to/python-2.6 ./install.sh"
    exit 0
fi

echo "Using Python: "
echo `$PYTHON --version`

if [ -s "bin/activate" -a -s "bin/easy_install" ]; then
  echo "Updating setuptools: ./bin/easy_install -i $INDEX -f $FINDLINKS -U $SETUPTOOLS"
  ./bin/easy_install -i $INDEX -f $FINDLINKS -U $SETUPTOOLS

  echo "Updating zc.buildout: ./bin/easy_install -i $INDEX -f $FINDLINKS -U $ZCBUILDOUT"
  ./bin/easy_install -i $INDEX -f $FINDLINKS -U $ZCBUILDOUT

  echo ""
  echo "============================================================="
  echo "Buildout is already installed."
  echo "Please remove bin/activate if you want to re-run this script."
  echo "============================================================="
  echo ""

  exit 0
fi

echo "Installing virtualenv"
# NOTE: virtualenv now doesn't download anything by default, so we need to provide setuptools
curl -o "setuptools-0.9.8.tar.gz" -k "https://pypi.python.org/packages/source/s/setuptools/setuptools-0.9.8.tar.gz#md5=243076241781935f7fcad370195a4291"
curl -o "/tmp/virtualenv.py" -kL "https://raw.github.com/pypa/virtualenv/1.10.1/virtualenv.py"

echo "Running: $PYTHON /tmp/virtualenv.py --clear ."
$PYTHON "/tmp/virtualenv.py" --clear .
rm /tmp/virtualenv.py*

echo "Updating setuptools: ./bin/easy_install -i $INDEX -f FINDLINKS -U $SETUPTOOLS"
./bin/easy_install -i $INDEX -f $FINDLINKS -U $SETUPTOOLS

echo "Installing zc.buildout: $ ./bin/easy_install -i $INDEX -f $FINDLINKS -U $ZCBUILDOUT"
./bin/easy_install -i $INDEX -f $FINDLINKS -U $ZCBUILDOUT

echo "Disabling the SSL CERTIFICATION for git"
git config --global http.sslVerify false

# Copy templates from .core master
TMP_CHECKOUT="/tmp/eea.plonebuildout.core"
git clone https://github.com/eea/eea.plonebuildout.core.git $TMP_CHECKOUT
mkdir -p ./buildout-configs/templates
cp -r -n $TMP_CHECKOUT/buildout-configs/templates ./buildout-configs/
rm -rf $TMP_CHECKOUT

echo ""
echo "==========================================================="
echo "All set. Now you can run ./bin/buildout or ./bin/develop rb"
echo "==========================================================="
echo ""
