# -*- coding: utf-8 -*-
# Migrate fgases_xml
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import\
#    u20180307_migrate_double_fgases_xml
#  >>> u20180307_migrate_double_fgases_xml.update(app)

from decimal import Decimal
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.updates import MigrationBase
import logging
import lxml.etree
import transaction

logger = logging.getLogger(__name__)
VERSION = 14
APPLIES_TO = [
    DEPLOYMENT_BDR,
]

ALL_XML_LIST = [
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
    bck_xml_file = '/'.join(['/backed_up_double_gases_xml',
                             folder_name, xml_filename])

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
        try:
            xml_file = app.unrestrictedTraverse(xml)
        except Exception:
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
                log_msg("Removed unreported gases for F8_S12 in: {}".format(
                    xml))
                root = fixed_xml
        if fixed_xml is not None:
            save_xml(xml_file, fixed_xml)
        transaction.commit()
    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=True):
    if not migrate_fgases_xml(app):
        return

    log_msg('FGases XMLS migration complete')
    return True
