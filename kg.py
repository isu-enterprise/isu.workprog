import os.path as op
from rdflib import Graph, RDF, RDFS, Literal, FOAF
from common import binds, genuuid, IDD
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(format='%(levelname)s:%(module)s:%(message)s',
                    level=logging.DEBUG)


KG_DIR = op.abspath("../kg")
# Universities, institutions, chairs, and other departments (subdivisions)
DEPARTMENTS_KGFN = op.join(KG_DIR, "departments.rdf")
DISCIPLINES_KGFN = op.join(KG_DIR,
                           "disciplines.rdf")  # Disciplines' descriptions
REFERENCES_KGFN = op.join(KG_DIR, "rferences.rdf")  # Literature, URL's, etc.
STANDARDS_KGFN = op.join(KG_DIR, "standards.rdf")  # Standards, namely, professions, FES , etc.

SER_FORMAT = "pretty-xml"

KGS = {}

DEPARTMENTS_KG = None
DISCIPLINES_KG = None
REFERENCES_KG = None
STANDARDS_KG = None


def loadkg(filename):
    global KGS, DEPARTMENTS_KG, DISCIPLINES_KG, REFERENCES_KG
    global STANDARDS_KG
    g = Graph()
    try:
        g.parse(filename)
    except FileNotFoundError:
        logger.warning("KG does not exist '{}'".format(filename))
    KGS[filename] = g
    KGS[g] = filename

    if filename == DISCIPLINES_KGFN:
        DISCIPLINES_KG = g
    elif filename == DEPARTMENTS_KGFN:
        DEPARTMENTS_KG = g
    elif filename == REFERENCES_KGFN:
        REFERENCES_KG = g
    elif filename == STANDARDS_KGFN:
        STANDARDS_KG = g
    binds(g)
    return g


def loadallkgs():
    loadkg(DEPARTMENTS_KGFN)
    loadkg(DISCIPLINES_KGFN)
    loadkg(REFERENCES_KGFN)
    loadkg(STANDARDS_KGFN)


def savekg(g, filename=None, format=SER_FORMAT):
    if filename is None:
        filename = KGS[g]
    g.serialize(destination=filename, encoding="utf-8", format=SER_FORMAT)


def saveallkgs():
    for v in KGS.values():
        if isinstance(v, Graph):
            savekg(v)


select_uri_label = """
SELECT ?uri ?label
WHERE
{
    ?uri a ?class .
    ?uri rdfs:label ?label .
}
"""


def update(d, uri, label):
    d[uri] = label
    d[label] = uri


KGDICTS = {}


def labeluri(graph, type_uri):
    """Make a dictionary, mapping rdfs:label to
    resource uri"""

    assert graph is not None

    d = {}
    if not isinstance(type_uri, (tuple, list)):
        type_uri = [type_uri]

    for t in type_uri:
        for uri, label in graph.query(select_uri_label, initBindings={"class":t}):
            update(d, label, uri)

    KGDICTS[graph] = d
    return d


def getfrom(graph, label, NS, typeuri, provision=None, lang="ru", uri=None):
    """Provides (returns) a labeled entity in `graph`.
    `label` is the label of the entity,
    `NS` is a namespace, where entity's identifier is,
    `typeuri` is an rdflib URIRef for type of the entity,
    `provision` is a callable accepting one argument (the entity),
        it runs if new entity is created.
    `lang` is language tag for the label Literal, defaults to "ru".
    """

    d = KGDICTS[graph]
    if label in d:
        return d[label]
    if uri is None:
        uri = genuuid(NS)
    elif isinstance(uri, str):
        uri = NS[uri]

    if isinstance(typeuri, (tuple, list)):
        for t in typeuri:
            graph.add((uri, RDF.type, t))
    else:
        graph.add((uri, RDF.type, typeuri))
    graph.add((uri, RDFS.label, Literal(label, lang=lang)))
    if callable(provision):
        provision(uri)
    update(d, uri, label)
    return uri


urilabel = labeluri

loadallkgs()

def preparegraphs():
    global DEPS, DISCS, STANS
    # loadallkgs()
    urilabel(DEPARTMENTS_KG, type_uri=(
        IDD["University"],
        IDD["Faculty"],
        IDD["Institute"],
        IDD["Chair"],
        FOAF["Person"]
    ))
    urilabel(DISCIPLINES_KG, type_uri=(
        IDD["Compenence"],
        IDD["Discipline"],
    ))
    urilabel(STANDARDS_KG, type_uri=(
        IDD["ProfessionActivity"],
        IDD["ControlType"],
        IDD["StudyForm"],
        IDD["StudyLevel"],
        IDD["Speciality"],
        IDD["Specialization"],
    ))
