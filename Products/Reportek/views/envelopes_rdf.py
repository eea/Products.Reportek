from Products.Five import BrowserView
from Products.PythonScripts.standard import html_quote, url_quote
from Products.Reportek.catalog import searchResults
from Products.Reportek import constants


class EnvelopesRDF(BrowserView):
    def __call__(self, *args, **kwargs):
        self.request.RESPONSE.setHeader('content-type',
                                        'application/rdf+xml;charset=utf-8')
        res = []
        res_a = res.append
        query = {
            'meta_type': 'Report Envelope',
            'released': 1
        }
        engine = getattr(self.context, constants.ENGINE_ID)
        age = getattr(engine, 'rdf_export_envs_age', None)
        if age:
            query['reportingdate'] = {
                'query': self.context.ZopeTime() - age,
                'range': 'min'
            }

        res_a('<?xml version="1.0" encoding="utf-8"?>')
        res_a(
            '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"')
        res_a(' xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"')
        res_a(' xmlns="http://rod.eionet.europa.eu/schema.rdf#"')
        res_a(
            ' xmlns:cr="http://cr.eionet.europa.eu/ontologies/contreg.rdf#">')

        s_url = self.request.SERVER_URL
        res_a("""<rdf:Description rdf:about="">
    <rdfs:label>Deliveries from %s</rdfs:label>
</rdf:Description>""" % s_url)
        catalog = self.context.Catalog

        brains = searchResults(catalog, query)
        for brain in brains:
            try:
                res_a("""<cr:File rdf:about="%s%s"/>""" % (
                    s_url,
                    html_quote(url_quote(brain.getPath()))))
            except Exception:
                res_a("""<!-- deleted envelope %s -->""" % brain.id)

        res_a('</rdf:RDF>')
        return '\n'.join(res)
