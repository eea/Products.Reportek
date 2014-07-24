#!/usr/bin/env bash
# You need translate-toolkit for this script to work
# pip install translate-toolkit, or place it in buildout

# create topic dirs
# unzip
# create ln dirs
# unzip xlf
# xliff2po
# i18ndude trmerge


if [ ! -d out.xlf ]; then
    mkdir out.xlf

    for zip in *.zip; do
        page_name=`echo $zip | sed -e's:[0-9]\+ \(.\+\)\.zip:\1:'`
        echo Creating $page_name
        mkdir out.xlf/$page_name
        cd out.xlf/$page_name
        unzip "../../$zip"
        if [ $? -gt 1 ]; then exit 1; fi
        cd -
    done

    cd out.xlf

    for page_dir in *; do
        cd "$page_dir"
        for zip in *.ZIP; do
            lang=`echo $zip | sed -e's/WEB[-0-9]\+\([A-Z]\{2,2\}\)-TRA-[0-9]\+.ZIP/\1/'`
            lang=`echo $lang | tr 'A-Z' 'a-z'`
            cartesian_id="${page_dir}_${lang}"
            echo " * $cartesian_id *"
            case "$cartesian_id" in
                collection_index_hr ) ;&
                documents_sk ) ;&
                draft_envelope_page_sk ) ;&
                envelope_overview_sk ) ;&
                help_index_es ) ;&
                help_index_sk ) ;&
                registration_sk ) ;&
                security.html_sk )
                    echo " +++++++++++ SKIP ${cartesian_id} +++++++++++"
                    ;;

                collection_index_el ) ;&
                collection_index_pt ) ;&
                collection_index_sk ) ;&
                dataconfidentiality_pt ) ;&
                dataconfidentiality_sk ) ;&
                documents_el ) ;&
                documents_pt ) ;&
                draft_envelope_page_el ) ;&
                draft_envelope_page_pt ) ;&
                envelope_overview_pt ) ;&
                feedbacks_ga ) ;&
                help_index_el ) ;&
                privacystatement_el ) ;&
                privacystatement_sk ) ;&
                registration_el ) ;&
                registration_hr ) ;&
                security.html_el )
                    echo " +++++++++++ KNOWN ALL_DIRS ${cartesian_id} +++++++++++"
                    ;;&
                * )
                    echo " +++++++++++ DEFAULT ${cartesian_id} +++++++++++"
                    mkdir tmp
                    cd tmp
                    unzip "../$zip"
                    if [ $? -gt 1 ]; then exit 1; fi
                    if [ -d $lang ]; then
                        mv $lang ..
                    else
                        mkdir -p ../$lang/LC_MESSAGES
                        mv *.xlf ../$lang/LC_MESSAGES
                    fi
                    cd ..
                    #if [ ! -d $lang/LC_MESSAGES ]; then
                    #    mkdir -p $lang/LC_MESSAGES
                    #    mv $lang/*.xlf $lang/LC_MESSAGES
                    #fi
                    rm -r tmp
                    ;;
            esac
        done
        rm *.ZIP
        cd ..
    done

    cd ..
fi

if [ ! -d out.po ]; then
    mkdir out.po
    xliff2po out.xlf out.po
    # do trmerge
fi
