#!/usr/bin/env bash
# You need translate-toolkit for this script to work
# pip install translate-toolkit, or place it in buildout

if [ -z "$1" ]; then
	echo "Provide output directory"
	exit 1
fi

out_dir=`readlink -f "$1"`
if [ ! -d $out_dir ]; then
	mkdir -p $out_dir
else
	echo "$out_dir already exits. exiting..."
	exit 1
fi
cd $(dirname $0)

po2xliff . $out_dir
#find $out_dir -type f -name '*.xlf' -exec sed -i -e"s:<file\>\(.*\)>:<file\1 target-language=\"$(echo {}|sed -e's#^.*\(..\)/LC_MESSAGES/.*$#\1#g')\">:" {} \;
for f in $out_dir/*; do
	lang=`basename $f`
	for xlf in `find $f -type f -name '*.xlf'`; do
		echo "change file ${xlf}; put lang $lang in target-language"
		sed -i -e"s:<file\>\(.*\)>:<file\1 target-language=\"${lang}\">:" ${xlf}
		sed -i -e"s:source-language=\"en-US\":source-language=\"en-GB\":" ${xlf}
	done
done

out_dir_small_name=`basename $out_dir`
cd ${out_dir}/..
tar -czf ${out_dir_small_name}.tar.gz $out_dir_small_name
cd -
