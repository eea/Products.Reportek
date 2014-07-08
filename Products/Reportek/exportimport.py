from anz.casclient import AnzCASClient
from OFS.interfaces import IApplication
from anz.casclient.interfaces import IAnzCASClient

from zope.component import adapts
from zope.component import queryMultiAdapter

from Products.GenericSetup.interfaces import ISetupEnviron
from Products.GenericSetup.utils import ObjectManagerHelpers
from Products.GenericSetup.utils import PropertyManagerHelpers
from Products.GenericSetup.utils import XMLAdapterBase
from Products.GenericSetup.interfaces import IBody

from Products.PluggableAuthService.interfaces.authservice import IPluggableAuthService


class AclUsers(XMLAdapterBase, ObjectManagerHelpers, PropertyManagerHelpers):
    adapts(IPluggableAuthService, ISetupEnviron)

    def _exportNode(self):
        raise NotImplementedError

    def _importNode(self, node):
        """ parse the xml file for 'anz' type
        """
        for child in node.childNodes:
            if child.nodeName == 'object':
                node_id = child.getAttribute('id').encode('utf-8')
                node_name = child.getAttribute('name').encode('utf-8')
                node_type = child.getAttribute('type').encode('utf-8')
                if node_type != "anz":
                    continue

                if node_id not in self.context.objectIds():
                    obj = AnzCASClient(node_id, node_name)
                    self.context._setObject(node_id, obj)
                obj = self.context[node_id]

                importer = queryMultiAdapter((obj, self.environ), IBody)
                importer.node = child

    node = property(_exportNode, _importNode)


class ECASServerXMLAdapter(XMLAdapterBase, ObjectManagerHelpers,
                           PropertyManagerHelpers):
    """ Export/import ECASServerXMLAdapter plugins
    """
    adapts(IAnzCASClient, ISetupEnviron)
    name = "ecas.xml"

    _LOGGER_ID = 'ecasmultiplugins'

    def _exportNode(self):
        """ Export the object as a DOM node.
        """
        raise NotImplementedError

    def _importNode(self, node):
        """ Import the object from the DOM node.
        """
        interfaces_to_activate = []
        acl_users = self.context.getParentNode()
        plugins = acl_users['plugins']

        for child in node.childNodes:
            if child.nodeName == 'property':
                name = child.getAttribute('name')
                if name is None:
                    continue
                value = self._getNodeText(child)
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                setattr(self.context, name, value)
            elif child.nodeName == 'interface':
                name = child.getAttribute('name')

                value = self._getNodeText(child)
                if value.lower() == "true":
                    try:
                        """Verify if 'name' is a valid interface name and added
                        """
                        plugins._getInterfaceFromName(name)
                        interfaces_to_activate.append(name)
                    except KeyError:
                        self._logger.info("Can't activate interface {0}"
                                          "".format(name))
        if interfaces_to_activate:
            self.context.manage_activateInterfaces(interfaces_to_activate)

    node = property(_exportNode, _importNode)

    def _exportBody(self):
        """ Export the object as a file body.
        """
        raise NotImplementedError

    body = property(_exportBody, XMLAdapterBase._importBody)


def getRoot(context):
    """
    Return the root of the site.
    """
    root = None
    pas = context.getSite()
    """Goes up to the parent node until its provides IApplication
    Maximum steps 10.
    """
    for _ in range(10, 0, -1):
        root = pas.getParentNode()
        if IApplication.providedBy(root):
            break

    return root


def setupECASServer(context):
    root = getRoot(context)
    if root is None:
        raise ValueError("Error can't optain the root")

    acl_users = root['acl_users']
    body = context.readDataFile('ecas.xml')
    importer = queryMultiAdapter((acl_users, context), IBody,
                                 name="reportek_aclusers")
    importer.body = body


def setupReportekUtilities(context):
    root = getRoot(context)
    if root is None:
        raise ValueError("Error can't optain the root")

    body = context.readDataFile('reportekutilies.xml')
    importer = queryMultiAdapter((root, context), IBody)
    importer.body = body

def exportLDAPUserFolder(context):
    raise NotImplementedError
