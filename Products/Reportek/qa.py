"""Remote QA dispatch.

Reportek used to keep QA scripts of its own in /QARepository and run them on
the Zope host: a QAScript's ``script_url`` was a command line, so anyone
allowed to add or edit one could run any command there. That was removed. All
QA now goes through the QA application (XMLCONV over XML-RPC or REST, or RabbitMQ);
Zope never runs QA code itself.

The QA application is found the way QARepository used to find it: the
application mapped to the envelope process's AutomaticQA activity, otherwise
the path in ReportekEngine's ``QA_application`` property.
"""

import logging

from Acquisition import aq_base

from Products.Reportek.constants import (
    DATAFLOW_MAPPINGS,
    ENGINE_ID,
    QAREPOSITORY_ID,
)

logger = logging.getLogger(__name__)

# Script ids of the removed local QA scripts started with this prefix.
LOCAL_SCRIPT_PREFIX = "loc_"
LOCAL_SCRIPT_REFUSED = "QA error: local QA scripts are no longer supported."


class QAResult:
    """container for QA script results"""

    def __init__(self, data=""):
        self.data = data


def _default_qa_application_path(context):
    """The retired QARepository's QA_application while it still exists, as
    that is the value that was in effect; ReportekEngine's QA_application once
    the u20261125 update has copied it over and removed QARepository."""
    root = context.getPhysicalRoot()
    legacy = getattr(aq_base(root), QAREPOSITORY_ID, None)
    path = getattr(legacy, "QA_application", "") if legacy is not None else ""
    if not path:
        engine = getattr(aq_base(root), ENGINE_ID, None)
        path = getattr(engine, "QA_application", "") if engine is not None else ""
    return path


def get_qa_application(context):
    """The QA application for ``context`` (an envelope or a document in it),
    or None if this instance has none."""
    path = _default_qa_application_path(context)
    try:
        process = context.getMySelf().getProcess()
        if "AutomaticQA" in process.listActivities():
            aqa_act = getattr(process, "AutomaticQA")
            path = aqa_act.mapped_application_details()["path"]
    except Exception:
        pass
    if not path:
        return None
    return context.unrestrictedTraverse(path, None)


def can_run_qa_on_files(context, files):
    """{file id: [QA script labels]} for the scripts that can be run manually
    on each of ``files``."""
    # imported here: RemoteApplication imports Document, which imports this
    from Products.Reportek.RemoteApplication import RemoteApplication

    result = {}
    qa_app = get_qa_application(context)
    qa_type = "xmlrpc" if isinstance(qa_app, RemoteApplication) else "REST"
    mappings = getattr(context, DATAFLOW_MAPPINGS)
    for doc in files:
        # get the valid schemas for the envelope's dataflows
        valid_schemas = mappings.getSchemasForDataflows(doc.dataflow_uris)
        # go on only if it's an XML file with a non-empty valid schema or
        # if no valid schemas are defined for those dataflows
        # NOTE due to updated dataflow_uris, valid_schemas is always None
        if doc.xml_schema_location and (
            doc.xml_schema_location in valid_schemas
            or not valid_schemas
            or qa_type == "REST"
        ):
            if qa_app:
                scripts = qa_app.listQAScripts(doc.xml_schema_location)
                # Exclude ZIP output type - refs: 136918
                result[doc.id] = [script for script in scripts if script[4] != "ZIP"]
    return result


def run_qa_script(context, file_url, script_id):
    """Run QA script ``script_id`` of the QA application on ``file_url``.

    Returns (file id, [content type, QAResult]). Only scripts of the QA
    application can run; ids of the removed local scripts are refused.
    """
    root = context.getPhysicalRoot()
    server_url = context.REQUEST.SERVER_URL
    engine = getattr(aq_base(root), ENGINE_ID, None)
    if engine is not None and getattr(engine, "qa_httpres", False):
        server_url = server_url.replace("https://", "http://")

    # make sure file_url is a real Zope file; traversed from the context, as
    # QARepository did through acquisition, so relative paths resolve the same
    file_obj = context.unrestrictedTraverse(
        file_url.replace("%s/" % server_url, ""), None
    )
    if file_obj is None:
        return "", ["", QAResult("QA error")]

    file_id = file_url.split("/")[-1]
    if script_id.startswith(LOCAL_SCRIPT_PREFIX):
        logger.warning(
            "Refused to run removed local QA script %r on %s", script_id, file_url
        )
        return file_id, ["text/plain", QAResult(LOCAL_SCRIPT_REFUSED)]

    qa_app = get_qa_application(context)
    if not qa_app:
        return file_id, ["", QAResult("QA error: no QA application")]
    try:
        return file_id, qa_app.runQAScript(file_url, script_id)
    except Exception as e:
        return file_id, ["", QAResult("QA error: {}".format(str(e)))]
