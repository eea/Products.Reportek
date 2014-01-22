#!/usr/bin/env bash
cd $(dirname $0)
domain=default
i18ndude_name=i18ndude
i18ndude_path=/var/local/cdr_all/bdr/bin/

[ -n "$1" ] && i18ndude_path="$1"

$i18ndude_path/$i18ndude_name rebuild-pot --pot $domain.pot --create $domain ../../../
$i18ndude_path/$i18ndude_name sync --pot $domain.pot */LC_MESSAGES/$domain.po

