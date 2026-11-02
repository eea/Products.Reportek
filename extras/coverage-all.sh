#!/bin/bash
# Run the test suite under coverage once per deployment and merge the results
# into a single coverage.xml (CDR-only and BDR-only code both count, nothing twice).
#
#   DEPLOYMENTS="CDR BDR" extras/coverage-all.sh
#
# Per-deployment JUnit XML goes to xunit-<DEPLOYMENT>/testreports/, the
# per-deployment coverage data is kept as .coverage.<DEPLOYMENT>.
# Like the entrypoint's `coverage` mode, test failures do not change the exit
# status: Jenkins reads them from the JUnit XML.
PKG="${GIT_NAME:-Products.Reportek}"
ZOPE_HOME="${ZOPE_HOME:-/opt/zope}"
ZOPE_USER="${ZOPE_USER:-zope-www}"
cd "$ZOPE_HOME/src/$PKG" || exit 2

as_zope() {
  if [ "$(id -u)" = "0" ]; then gosu "$ZOPE_USER" "$@"; else "$@"; fi
}

rm -rf .coverage .coverage.* coverage.xml xunit-*
for dep in ${DEPLOYMENTS:-CDR BDR}; do
  echo "=== coverage run: REPORTEK_DEPLOYMENT=$dep"
  as_zope env REPORTEK_DEPLOYMENT="$dep" COVERAGE_FILE="$(pwd)/.coverage.$dep" \
    "$ZOPE_HOME/bin/coverage" run "$ZOPE_HOME/bin/zope-testrunner" \
    --test-path "$(pwd)" -v -vv -s "$PKG" --xml="$(pwd)/xunit-$dep"
done

echo "=== merging coverage data"
as_zope env COVERAGE_FILE="$(pwd)/.coverage" "$ZOPE_HOME/bin/coverage" combine --keep .coverage.*
as_zope "$ZOPE_HOME/bin/coverage" xml -i --include="*/$PKG/*"
exit 0
