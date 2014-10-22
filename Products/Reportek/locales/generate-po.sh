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
        page_name=`echo $zip | sed -e's:\([0-9]\+\) \(.\+\)\.zip:\1_\2:'`
        #echo Creating $page_name
        mkdir out.xlf/$page_name
        cd out.xlf/$page_name
        unzip "../../$zip"
        if [ $? -gt 1 ]; then exit 1; fi
        cd -
    done

    cd out.xlf

    for page_dir in *; do
        page_no=`echo $page_dir | sed -e's/\([0-9]\+\)_.*/\1/'`
        cd "$page_dir"
        for zip in *.ZIP; do
            #WEB-2013-01200-00-12-CS-TRA-00.ZIP
            #WEB-2013-01200-00-12-00-EN-HR-00.ZIP
            lang=`echo $zip | sed -e's/WEB[-0-9]\+\([A-Z]\{2,2\}\)-TRA-[0-9]\+\.ZIP/\1/I'`
            if [ -z "$lang" ]; then
                lang=`echo $zip | sed -e's/WEB[-0-9]\+-EN-\([A-Z]\{2,2\}\)-[0-9]\+\.ZIP/\1/I'`
            fi
            caseLang=$lang
            lang=`echo $lang | tr 'A-Z' 'a-z'`
            zip_no=`echo $zip | sed -e's/WEB-[0-9]\+-[0-9]\+-[0-9]\+-\([0-9]\{2,2\}\)-.*\.ZIP/\1/I'`
            if [ -f ../../updates/WEB-2013*-${page_no}*-${caseLang}-*.[Zz][Ii][Pp] ]; then
                echo " ++ Found update ++"
                rm WEB-2013*-${page_no}*-${caseLang}-*.[Zz][Ii][Pp]
                cp ../../updates/WEB-2013*-${page_no}*-${caseLang}-*.[Zz][Ii][Pp] .
                zip=$(basename `ls ../../updates/WEB-2013*-${page_no}*-${caseLang}-*.[Zz][Ii][Pp]`)
            fi
            cartesian_id="${page_dir}_${lang}"
            echo " * $cartesian_id *"
            case "$cartesian_id" in
                #collection_index_hr ) ;&
                #documents_sk ) ;&
                #draft_envelope_page_sk ) ;&
                #envelope_overview_sk ) ;&
                #help_index_es ) ;&
                #help_index_sk ) ;&
                #registration_sk ) ;&
                #security.html_sk )
                #    echo " +++++++++++ SKIP ${cartesian_id} +++++++++++"
                #    ;;

                #collection_index_el ) ;&
                #collection_index_pt ) ;&
                #collection_index_sk ) ;&
                #dataconfidentiality_pt ) ;&
                #dataconfidentiality_sk ) ;&
                #documents_el ) ;&
                #documents_pt ) ;&
                #draft_envelope_page_el ) ;&
                #draft_envelope_page_pt ) ;&
                #envelope_overview_pt ) ;&
                #feedbacks_ga ) ;&
                #help_index_el ) ;&
                #privacystatement_el ) ;&
                #privacystatement_sk ) ;&
                #registration_el ) ;&
                #registration_hr ) ;&
                #security.html_el )
                #    echo " +++++++++++ KNOWN ALL_DIRS ${cartesian_id} +++++++++++"
                #    ;;&
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

#sed -i -e's/\<encoding="utf-8"?/encoding="windows-1255"?/' out.xlf/14_documents/et/LC_MESSAGES/default.xlf
#sed -i -e's/\<encoding="utf-8"?/encoding="windows-1255"?/' out.xlf/18_help_index/et/LC_MESSAGES/default.xlf
sed -i -e's/\<encoding="utf-8"?/encoding="ISO-8859-15"?/' out.xlf/14_documents/et/LC_MESSAGES/default.xlf
sed -i -e's/\<encoding="utf-8"?/encoding="ISO-8859-15"?/' out.xlf/18_help_index/et/LC_MESSAGES/default.xlf
sed -i -e's/\<encoding="utf-8"?/encoding="ISO-8859-15"?/' out.xlf/21_security.html/et/LC_MESSAGES/default.xlf

if [ ! -d out.po ]; then
    mkdir out.po
    xliff2po out.xlf out.po
    # do trmerge
fi
