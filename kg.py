import os.path as op
from rdflib import Graph, RDF, RDFS, Literal, FOAF, URIRef
from common import *
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
STANDARDS_KGFN = op.join(
    KG_DIR, "standards.rdf")  # Standards, namely, professions, FES , etc.

# SER_FORMAT = "pretty-xml"
SER_FORMATS = ("pretty-xml", "turtle")

KGS = {}

DEPARTMENTS_KG = None
DISCIPLINES_KG = None
REFERENCES_KG = None
STANDARDS_KG = None
LABELS_KG = None


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
    global LABELS_KG
    loadkg(DEPARTMENTS_KGFN)
    loadkg(DISCIPLINES_KGFN)
    loadkg(REFERENCES_KGFN)
    loadkg(STANDARDS_KGFN)
    isu = getfrom(DEPARTMENTS_KG, ISU_NAME, IDB, IDD["University"], uri=ISU)
    imit = getfrom(DEPARTMENTS_KG,
                   IMIT_NAME,
                   IDB, (IDD["Faculty"], IDD["Institute"]),
                   uri=IMIT,
                   provision=lambda obj: DEPARTMENTS_KG.add(
                       (isu, IDD["department"], obj)))
    LABELS_KG = Graph()
    binds(LABELS_KG)
    LABELS_KG.add((MURAL, RDFS.label, Literal("очная", lang="ru")))
    LABELS_KG.add((EXMURAL, RDFS.label, Literal("заочная", lang="ru")))
    LABELS_KG.add((BACHOLOIR, RDFS.label, Literal("бакалавр", lang="ru")))
    LABELS_KG.add((ACBACH, RDFS.label, Literal("академический бакалавриат", lang="ru")))
    LABELS_KG.add((APPLBACH, RDFS.label, Literal("прикладной бакалавриат", lang="ru")))
    LABELS_KG.add((MASTER, RDFS.label, Literal("магистр", lang="ru")))
    LABELS_KG.add((EXAMS, RDFS.label, Literal("экзамен", lang="ru")))
    LABELS_KG.add((CREDIT, RDFS.label, Literal("зачет", lang="ru")))
    LABELS_KG.add((CREDITWN, RDFS.label, Literal("зачет с оценкой", lang="ru")))
    LABELS_KG.add((TASK, RDFS.label, Literal("контрольная работа", lang="ru")))


EXT = {"pretty-xml": "rdf", "turtle": "ttl"}


def savekg(g, filename=None, format=SER_FORMATS):
    if filename is None:
        filename = KGS[g]
    g.serialize(destination=filename,
                encoding="utf-8",
                format=format[0] if isinstance(format,
                                               (tuple, list)) else format)
    for f in SER_FORMATS:
        g.serialize(destination=filename + "." + EXT[f],
                    encoding="utf-8",
                    format=f)


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


def getfrom(graph, label, NS, typeuri, provision=None, lang="ru", uri=None):
    """Provides (returns) a labeled entity in `graph`.
    `label` is the label of the entity,
    `NS` is a namespace, where entity's identifier is,
    `typeuri` is an rdflib URIRef for type of the entity,
    `provision` is a callable accepting one argument (the entity),
        it runs if new entity is created.
    `lang` is language tag for the label Literal, defaults to "ru".
    """

    # d = KGDICTS[graph]
    # if label in d:
    #     return d[label]
    tu = typeuri[0] if isinstance(typeuri, (tuple, list)) else typeuri
    lit = Literal(label, lang=lang)
    for subj in graph.subjects(RDFS.label, lit):
        if (subj, RDF.type, tu) in graph:
            # logger.debug("FOUND: {}->({} {} {})".format(lit, subj, "a", tu))
            return subj

    if uri is None:
        uri = genuuid(NS)
    elif isinstance(uri, URIRef):
        pass
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

    # update(d, uri, label)
    return uri


loadallkgs()


def preparegraphs():
    return
