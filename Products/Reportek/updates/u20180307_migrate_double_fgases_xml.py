# -*- coding: utf-8 -*-
# Migrate fgases_xml
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20180307_migrate_double_fgases_xml; u20180307_migrate_double_fgases_xml.update(app)

from decimal import Decimal
from Products.Reportek.blob import add_OfsBlobFile
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.updates import MigrationBase
import logging
import lxml.etree
import requests
import transaction

logger = logging.getLogger(__name__)
VERSION = 13
APPLIES_TO = [
    DEPLOYMENT_BDR,
]

ALL_XML_LIST = [
    '/fgases/fr/19159/envwnw3cq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/13810/envwo1psw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fi/24431/envwpef6q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/22455/envwpwvig/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/25646/envwpfcpa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/25646/envwpfdvg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/23849/envwpfekw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/14286/envwpa8dq/2017_Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/15907/envwpfhsq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gr/20153/envwpfgag/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ro/23847/envwovuza/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/24598/envwpa5jw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/23851/envwpfrfa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/22139/envwpfsnw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/20242/envwpnylq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/lv/12491/envwoqd8q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/13548/envwpplqq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/fgas30031/envwppkw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/22903/envwpptyg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/27192/envwppytg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/26976/envwppu1w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/29764/envwp5ctw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/26434/envwpvpg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/28013/envwpuwq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/14535/envwo6bsw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/14645/envwpwk9q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/24790/envwo0niw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/9976/envwo1qdq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/22698/envwo0qra/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/26591/envwo04ng/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/9637/envwm7yvq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/9637/envwo1ncq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/si/25598/envwo06aq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/16412/envwpk03w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/16412/envwpkzlq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/23621/envwplrtg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/lt/15508/envwo6hg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/14271/envwpkdpq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/14272/envwpmeoa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cz/14663/envwo5xka/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/19446/envwo0buw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/27009/envwo2dxq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/26050/envwo6vsq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/si/25598/envwo66ga/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gr/15847/envwo61ya/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/hu/10021/envwpfzma/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/fgas21750/envwpgboa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/20272/envwpg24q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/15507/envwowk9g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/13717/envwo2dia/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/29956/envwo7ota/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/28022/envwo1qza/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/28598/envwo6vsg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/13233/envwovrtq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/27857/envwof6q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/26616/envwo0ha/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/11167/envwo0pbg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/27040/envwo1gdw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/22774/envwplo5q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/19209/envwo6gna/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/22851/envwpywpa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cz/18748/envwpzkbq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/19165/envwp0bng/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/19755/envwp0dea/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/19764/envwp0j1a/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/14377/envwp0rrq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pt/28472/envwpk0da/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/14145/envwo_va/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/21012/envwp1kxg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/22851/envwpzxgg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/27584/envwp5exq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/27537/envwp5geg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/27540/envwp5hmw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/14457/envwo0tdq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/13250/envwp5aga/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/mt/18989/envwp5vpq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gr/29070/envwp6pig/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/23746/envwp5pw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/hu/26262/envwp6jtw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/25816/envwp6t0g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/9838/envwp6cg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/fgas20758/envwpa0tw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ee/10064/envwpp3bg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/27866/envwo7jig/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/fgas24874/envwpkpna/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/dk/24404/envwpwyw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/14408/envwpw9w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/18434/envwovrgg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/15507/envworv8g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/si/25598/envwo04jq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/26091/envwzvqhw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/25031/envwpunsa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ro/30599/envwo5zvq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fi/fgas23537/envwpqdeq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/20653/envwo1zcg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/19413/envwpqtmw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/27840/envwo5mba/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/27837/envwo3chq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/27847/envwo_9qg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/27861/envwoj3w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/10061/envwo04qg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ie/9747/envwo0_eg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/23222/envwo0dqw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cz/fgas21434/envwo_3mq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/14047/envwo1ytw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/18434/envwowhqg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/30044/envwmmbtg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ro/25457/envwpa6rq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/fgas24987/envwo7mwg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/hu/23485/envwngj2a/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/lt/16277/envwplihq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/26050/envwo6zzg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/13491/envwppiza/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/13922/envwppqnq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/24070/envwppi9w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/21070/envwo0bag/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/16418/envwpwzmq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/16408/envwpwhdg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/lt/29578/envwpaweg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/hu/fgas20935/envwpajxq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fi/23686/envwp5rxg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/hr/14175/envwp52kq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/19666/envwo0dnw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/26434/envwpustg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/13433/envwpu4zg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/27630/envwpvd2q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/23558/envwpvcmg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/26329/envwpqlzq/Fluorinated_gases__F-Gases__reporting__2.xml',
    '/fgases/be/22455/envwpumlw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/16412/envwpkvjw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ro/23454/envwpayra/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/9658/envwp_83q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/hu/25566/envwpuaig/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/29855/envwpceq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/fgas23889/envwplbq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/10016/envwo1ya/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/25610/envwpt7g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/29592/envwoybdq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/27866/envwo1nzg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ie/30466/envwp99gq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ie/31173/envwp_b9a/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/20758/envwp_zeq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/22136/envwp5qta/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/24320/envwmcv8q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/23777/envwp_4pg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/19854/envwp1yca/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ro/20227/envwpi8w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/20431/envwo1ihq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/fgas30043/envwpkbtg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/16414/envwpwnvw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/16416/envwpwsxw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/15949/envwpaesg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/13986/envwo0hww/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ee/fgas30012/envwpupgq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/lt/fgas24118/envwpp0ta/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/9637/envwpuvca/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/26330/envwo1xtq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/9714/envwpfh8w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/13891/envwo1u_q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/9713/envwpfscg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/27400/envwpfs7w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/23852/envwpf_gq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/24097/envwpf7pw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cz/fgas22797/envwpgikg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/20698/envwpgoya/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/20309/envwpgm7w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/22337/envwo5nwq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/27100/envwpyrfq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/fgas30066/envwo598w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/23557/envwpz7jg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fi/14254/envwpznew/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/18476/envwpuc5q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/9773/envwpknw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/16363/envwpkng/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/fgas30029/envwo6ixg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/lt/fgas23453/envwo0swg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pt/26395/envwplsow/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/9810/envwpgvcq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/9842/envwp1l3w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/26792/envwp5lnq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/24324/envwpqh4w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/9838/envwpqt8q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ee/9831/envwpqdjq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ee/9830/envwpqemq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/14378/envwpuzdq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/18476/envwpuu1q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/20120/envwpueig/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/9713/envwpfkmg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/9719/envwpfsig/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/27240/envwpp9lw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/27582/envwp5c9a/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/27535/envwp5g1w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/27576/envwp5kxa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/24155/envwp1zxw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ro/23454/envwplf5g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/29565/envwhrpuq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/16191/envwp6m8q/2017 Report Novetrade International.xml',
    '/fgases/si/25598/envwo7idw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/27866/envwo1ozq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/lt/fgas20734/envwoqvlg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/21292/envwo09nw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/26091/envwo00xq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/9714/envwpfvdq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ro/30599/envwovq1w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/16284/envwpwvqw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/lt/29578/envwpaoqw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/dk/25513/envwo0rxw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/23012/envwpamrw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/mt/23068/envwpa5iq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/19176/envwpz0ma/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/18138/envwpztoa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/18138/envwpev8w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/26320/envwpawfq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/17809/envwpfvta/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/24846/envwpu2rq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gr/25270/envwpqysa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/23011/envwpavcw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/14050/envwo1k2g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/27009/envwo16ng/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/sk/28539/envwo2m9g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/27009/envwo2swg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/25614/envwo5tsa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/14469/envwo0jva/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/14354/envwo2fdq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/27009/envwo6wsg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/25491/envwo6_jw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/14335/envwo58nq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gr/15847/envwo7hbq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/dk/14229/envwpapzg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/18232/envwpujdg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/29333/envwpgipq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/25145/envwpgr4a/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/25145/envwpgu_q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/20678/envwpgy2q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/20702/envwpggiq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/26807/envwpghha/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/26807/envwpgwpw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/18330/envwpg1qg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ie/30467/envwp_hqg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cz/17528/envwo0bww/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/16272/envwp_k_g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/14463/envwo0vsa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/29222/envwo0mzg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/23900/envwpps5q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/27009/envwo65nq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/9976/envwo622g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/20761/envwpqwxa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/26329/envwordg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/26329/envwordg/Fluorinated_gases__F-Gases__reporting__2.xml',
    '/fgases/de/14462/envwpqxcq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/14469/envwo0k5g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fi/13693/envwl2kew/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/23023/envwo1ddw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/28420/envwpp1ua/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/16207/envwoysuw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/26091/envwo04bw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/24846/envwpqj7g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/dk/13696/envwpujpg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/19073/envwo0jwq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/19073/envwo1ueg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/19073/envwo0pyg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/19073/envwo1wlq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/hu/19451/envwpgpra/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/25614/envwo5v1q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/lt/30082/envwo0h8w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/lt/11926/envwoqm9a/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/23121/envwo0koq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/14354/envwo2c_q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/25124/envwo1zxq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ie/30486/envwp_g3w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/18193/envworjeg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/9767/envwp_v6g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/10076/envwp_7xw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ro/19229/envwp6gug/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/fgas21802/envwp7p8q/2017 REPORT ODISEY 71.xml',
    '/fgases/se/24043/envwpamng/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/30610/envwnmgug/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/9661/envwpvtw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/9749/envwpbfa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/16247/envwphjg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pt/13110/envwpwlw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/9935/envwpzqq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/fgas30010/envwp6xg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/14618/envwpzwow/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/fgas24107/envwpz9wa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/23010/envwpaxlw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/27842/envwo5q7a/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/25491/envwo6g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/21471/envwozwww/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/27855/envwoeiw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ie/20575/envwooqw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/27427/envwopyg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/22687/envwo2bug/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/si/25598/envwomow/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/26591/envwo1idg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/lt/24768/envwo7tkg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/15308/envwo6puw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/24499/envwo73xq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/27833/envwo26ya/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fi/28366/envwo_4bq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/14445/envwo1uza/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/27850/envwoclw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/9711/envwo03da/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/26758/envwo0_7a/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/26243/envwotgw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/9637/envwo1oyq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/21292/envwo1dra/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/21824/envwo0qsw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/14253/envwovy0a/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/27533/envwp5iwa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/27587/envwp5jug/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/fgas23170/envwp5zwg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/dk/20053/envwp5dhq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/14572/envwp5fug/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/18234/envwp6j4q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/hr/20132/envwp6eaq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/20286/envwpqiqg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ee/fgas30041/envwpufjw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ro/30599/envwovoba/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/9712/envwpfltg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/22287/envwpfcrg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/9719/envwpft7a/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/si/25598/envwo1oaa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ie/30642/envwp97ea/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ee/13916/envwpoyha/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/bg/25231/envwpe5gg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/9672/envwp_zcg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/29017/envwp58la/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/22903/envwpprig/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ee/fgas30047/envwpqlkq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/15946/envwpqqhg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cz/14663/envwo6ovg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/15308/envwo0b9w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/26050/envwoqtfg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/29720/envwo6sow/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/9976/envwo6zkg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/29720/envwo60_q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/27009/envwo616w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/22900/envwo69vw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/24603/envwo20gg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/14335/envwo7f2q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/29720/envwo6u5a/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/14136/envwpvswg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/fgas21604/envwpqaww/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/26384/envwpqgiw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/20286/envwpqnug/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/24357/envwo0qjw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ro/22659/envwpo98g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ro/30599/envwppkuq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/24412/envwo0rxa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/13491/envwppmgq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/14056/envwppkuw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/25814/envwppo5q/Fluorinated_gases__F-Gases__reporting__2017',
    '/fgases/it/20615/envwppxtg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fi/27049/envwpyldg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/19591/envwnm96a/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/hu/27753/envwpzvea/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/16008/envwpzxnq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fi/18668/envwpuitg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/25814/envwpkuva/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/fgas21089/envwo7nzq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/9637/envwodcg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/23948/envwo4yvq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/9799/envwpe0ia/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/9839/envwpe5ba/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/10022/envwpe7mg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ro/9899/envwpegow/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/19166/envwo7jba/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/23912/envwo2vca/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/25940/envwo51gq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/16412/envwpltxq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/mt/25743/envwplu3w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cz/30984/envwppw1g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fi/15428/envwpzzxg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/19757/envwp0eig/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pt/fgas23304/envwpbktw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/24360/envwp0leq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/24385/envwfx3fq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/25440/envwpa75q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/23580/envwo1d2w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/23338/envwpd4vw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/13491/envwppncw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/hu/21952/envwo19cg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/16174/envwppppq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/27192/envwppiwa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/27009/envwo2pca/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cy/22687/envwo1jw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pt/20311/envwoaola/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fi/13954/envwo0t7q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/fr/20309/envwpgugg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/20644/envwpg2ua/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/26050/envwnxpdg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/26329/envwk80dw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/at/26329/envwk80dw/Fluorinated_gases__F-Gases__reporting__2.xml',
    '/fgases/lt/15508/envwo4tw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/19547/envwov97g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/20631/envwplang/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/23261/envwpvp5g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/16412/envwplklw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/cz/23717/envwo15hg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/23621/envwlxu1w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/23621/envwlxu1w/Fluorinated_gases__F-Gases__reporting__2.xml',
    '/fgases/gb/23621/envwpllg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/23621/envwpllg/Fluorinated_gases__F-Gases__reporting__2.xml',
    '/fgases/gb/23621/envwpln3g/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/13328/envwpleiw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pt/26266/envwplm2w/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/23836/envwo2xwg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/it/14384/envwpvd8q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/13407/envwoqia/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/20538/envwpfxfg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/20700/envwpgmvq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/pl/20721/envwpgrtw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/26096/envwpggcq/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/18131/envwpgzsw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/es/18327/envwpg0xg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/be/9678/envwo1dpw/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/ee/22979/envwpfh3a/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/de/14607/envwpgo9q/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/se/22709/envwpadug/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/hr/19760/envwp0fka/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/hr/9577/envwp0gwa/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/nl/25371/envwpjka/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/si/13981/envwo3wg/Fluorinated_gases__F-Gases__reporting__1.xml',
    '/fgases/gb/23242/envwppxia/Fluorinated_gases__F-Gases__reporting__1.xml',
]


def log_msg(msg):
    logger.info(msg)
    print msg


def back_it_up(app, xml):
    if not app.unrestrictedTraverse('/backed_up_double_gases_xml', None):
        app.manage_addFolder('backed_up_double_gases_xml')
    bck_folder = app.unrestrictedTraverse('/backed_up_double_gases_xml')
    xml_filename = xml.split('/')[-1]
    env_path = xml.split(xml_filename)[0]
    env = app.unrestrictedTraverse(env_path)
    folder_name = '_'.join([env.company_id, env_path.split('/')[-2]])
    try:
        bck_folder.manage_addFolder(folder_name)
    except Exception:
        pass
    c_folder = bck_folder.unrestrictedTraverse(folder_name)
    xml_doc = app.unrestrictedTraverse(xml)
    f = getattr(xml_doc, 'data_file')
    fc = f.open()
    c_folder.manage_addFile(xml_filename, file=fc.read())
    fc.close()


def has_backup(app, xml):
    xml_filename = xml.split('/')[-1]
    env_path = xml.split(xml_filename)[0]
    env = app.unrestrictedTraverse(env_path)
    folder_name = '_'.join([env.company_id, env_path.split('/')[-2]])
    bck_xml_file = '/'.join(['/backed_up_double_gases_xml', folder_name, xml_filename])

    if app.unrestrictedTraverse(bck_xml_file, None):
        return True
    return False


def has_gas_clone(root):
    """Return True if F8_S12 has gas clones"""
    gas_ids = root.xpath("//F8_S12//Gas//GasCode//text()")
    if len(gas_ids) != len(set(gas_ids)):
        return True


def remove_cloned_gases(root):
    gases = root.xpath("//F8_S12//Gas")
    uniques = []
    for gas in gases:
        gas_code = gas.find("GasCode").text
        if gas_code not in uniques:
            uniques.append(gas_code)
        else:
            if gas.xpath("Totals//tr_12B//text()"):
                log_msg("We have a set value for 12B in a cloned gas")
            gas.getparent().remove(gas)

    return root


def has_unreported_gases(root):
    """Return True if F8_S12 has a GasCode that is not in ReportedGases"""
    if root.xpath("//Activities//Eq-I-RACHP-HFC//text()") == 'true':
        gases = root.xpath("//F8_S12//Gas")
        gas_list = root.xpath('//ReportedGases')
        if len(gases) != len(gas_list):
            return True


def remove_unreported_gases(root):
    gases = root.xpath("//F8_S12//Gas")
    reported_gas_ids = root.xpath("//ReportedGases//GasId//text()")
    for gas in gases:
        if gas.find("GasCode").text not in reported_gas_ids:
            if gas.xpath("Totals//tr_12B//text()"):
                log_msg("We have a set value for 12B in an unreported gas")
            gas.getparent().remove(gas)
    return root


def save_xml(old_xml, new_xml):
    new_xml = lxml.etree.tostring(new_xml)
    old_xml.manage_file_upload(file=new_xml,
                               content_type='text/xml',
                               preserve_mtime=True)


def migrate_fgases_xml(app):
    for xml in ALL_XML_LIST:
        xml_filename = xml.split('/')[-1]
        env_path = xml.split(xml_filename)[0]
        env = app.unrestrictedTraverse(env_path)
        try:
            xml_file = app.unrestrictedTraverse(xml)
        except Exception as e:
            log_msg('Unable to get xml file: {}'.format(xml))
            continue
        fixed_xml = None
        # back_it_up(app, xml)
        f = getattr(xml_file, 'data_file').open()
        root = lxml.etree.fromstring(f.read())
        f.close()
        if has_gas_clone(root):
            log_msg("Cloned gases found for: {}".format(xml))
            if not has_backup(app, xml):
                back_it_up(app, xml)
            fixed_xml = remove_cloned_gases(root)
            if fixed_xml is not None:
                log_msg("Removed cloned gases for F8_S12 in: {}".format(xml))
                root = fixed_xml
        if has_unreported_gases(root):
            if not has_backup(app, xml):
                back_it_up(app, xml)
            fixed_xml = remove_unreported_gases(root)
            if fixed_xml is not None:
                log_msg("Removed unreported gases for F8_S12 in: {}".format(xml))
                root = fixed_xml
        if fixed_xml is not None:
            save_xml(xml_file, fixed_xml)
        transaction.commit()
    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    if not migrate_fgases_xml(app):
        return

    log_msg('FGases XMLS migration complete')
    return True
