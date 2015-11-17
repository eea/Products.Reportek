#!/usr/bin/env bash
# You need translate-toolkit for this script to work
# pip install translate-toolkit, or place it in buildout

if [ -z "$1" ]; then
    echo -e "Provide the full path to i18ndude as first argument.\n(and run in the directory where the translations zip is stored in)"
    exit 1
fi

i18ndude_path=$1

if [ ! -d out.xlf ]; then
    echo "Extracting xlf from zips"
    mkdir out.xlf

    # create topic dirs and unzip
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
                #    echo " +++ SKIP ${cartesian_id} +++"
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
                #    echo " +++ KNOWN ALL_DIRS ${cartesian_id} +++"
                #    ;;&
                * )
                    echo " +++ DEFAULT ${cartesian_id} +++"
                    mkdir tmp
                    cd tmp
                    unzip "../$zip"
                    if [ $? -gt 1 ]; then exit 1; fi
                    # create language dirs
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
else
    echo "out.xlf dir present. Skipping xlf extraction from zip"
fi

echo "Correcting declared encoding"
#sed -i -e's/\<encoding="utf-8"?/encoding="windows-1255"?/' out.xlf/14_documents/et/LC_MESSAGES/default.xlf
#sed -i -e's/\<encoding="utf-8"?/encoding="windows-1255"?/' out.xlf/18_help_index/et/LC_MESSAGES/default.xlf
sed -i -e's/\<encoding="utf-8"?/encoding="ISO-8859-15"?/' out.xlf/14_documents/et/LC_MESSAGES/default.xlf
sed -i -e's/\<encoding="utf-8"?/encoding="ISO-8859-15"?/' out.xlf/18_help_index/et/LC_MESSAGES/default.xlf
sed -i -e's/\<encoding="utf-8"?/encoding="ISO-8859-15"?/' out.xlf/21_security.html/et/LC_MESSAGES/default.xlf

# xliff2po
if [ ! -d out.po ]; then
    echo "Converting from xlf to po"
    mkdir out.po
    xliff2po out.xlf out.po
else
    echo "out.po dir present. Skipping Converting from xlf to po"
fi

# remove the fuzzy marker - i18ndude trmerge will ignore all the messages that are fuzzy
if [ ! -d out.nofuzzy.po ]; then
    echo "Clearing all fuzzy flags"
    cp -r out.po out.nofuzzy.po
    find out.nofuzzy.po -name '*.po' -type f -exec sed -i -e's/#, fuzzy//' {} \;
else
    echo " out.nofuzzy.po dir present. Skipping Clearing all fuzzy flags"
fi

# i18ndude trmerge
if [ ! -d out.merged.po ]; then
    echo "Merging all page specific po into one per language"
    mkdir out.merged.po
    merged_dir=`pwd`/out.merged.po
    for page_dir in out.nofuzzy.po/*; do
        cd $page_dir
        for lang_dir in *; do
            current_output_lang_dir=$merged_dir/$lang_dir/LC_MESSAGES
            if [ ! -d $current_output_lang_dir ]; then
                mkdir -p $current_output_lang_dir
                cp $lang_dir/LC_MESSAGES/default.po $current_output_lang_dir/
            else
                $i18ndude_path trmerge $current_output_lang_dir/default.po $lang_dir/LC_MESSAGES/default.po > /tmp/default.po && mv /tmp/default.po $current_output_lang_dir/default.po
            fi
        done
        cd -
    done
else
    echo "out.merged.po dir present. Skipping Merging all page specific po into one per language"
fi
