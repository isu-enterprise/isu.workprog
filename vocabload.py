import re
from xlrd import open_workbook
from pprint import pprint
from rdflib import (Graph, BNode, Namespace, RDF, RDFS, Literal, DCTERMS, FOAF,
                    URIRef)
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
from collections import OrderedDict
from common import (WPDB, WPDD, DBR, IDB, IDD, SCH, CNT, genuuid, DCID, ISU,
                    DCTERMS, IMIT, IMIT_NAME, MURAL, EXMURAL, BACHOLOIR,
                    ACBACH, APPLBACH, MASTER, NUMBERRE, COMPETENCERE,
                    REQDESCRRE, COURCODERE, BULLETS, found, anywords, allwords,
                    splitnumber, normspaces, startswithnumber, listitem, binds,
                    SPECCODERE, DEPARTMENTS, YEARDISTRE, YEARRE, PROFCODERE,
                    EXAMS, CREDIT, CREDITWN, TASK, refinename)

from kg import (DEPARTMENTS_KG, REFERENCES_KG, DISCIPLINES_KG, update,
                preparegraphs, loadallkgs, saveallkgs, STANDARDS_KG, getfrom)

import urllib.error

import logging

"""Loads a graph on server Virtuoso, Address is in VG_URL"""


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(format='%(levelname)s:%(module)s:%(message)s',
                    level=logging.DEBUG)

VG_URL = "http://root.isclan.ru:8890/sparql"

# The following command should be executed with server ISQL interface
# grant SPARQL_UPDATE to "SPARQL"


def connect():
    vg = Graph(store="SPARQLUpdateStore")
    vg.open(VG_URL)
    return vg


def upload(g, replace=False):
    vg = connect()
    if not replace:
        vg.store.add_graph(g)
    else:
        try:
            vg.store.add_graph(g)
        except urllib.error.HTTPError as e:
            logger.info(
                "Exception while trying to create graph {}: {}, delete it.".
                format(g.identifier, e))
            vg.store.remove_graph(g)
            upload(g, replace=False)
            return
    for s, p, o in g:
        vg.store.add((s, p, o), context=g)
    vg.commit()


def uploadall(replace=False):
    loadallkgs()
    for g in [DEPARTMENTS_KG, REFERENCES_KG, DISCIPLINES_KG, STANDARDS_KG]:
        upload(g, replace=replace)


def debugcontentshow(g):

    def _(x):
        if isinstance(x, URIRef):
            return '<{}>'.format(x)
        else:
            return '"{}"'.format(x)

    if g is None:
        g = connect()
    for s, p, o in g:
        print(_(s), _(p), _(o), ' .')


def debugdump():
    vg = connect()
    vg.serialize(destination="dump.ttl", format="turtle")


def graphlist():
    vg = connect()
    for c in vg.store.contexts():
        print(c)


if __name__ == "__main__":
    import sys
    uploadall(replace=True)
    # debugdump()
    # debugcontentshow(DEPARTMENTS_KG)
    # graphlist()
    # at least one time it executed successfully !
