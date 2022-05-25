import re
from xlrd import open_workbook
from pprint import pprint
from rdflib import (Graph, BNode, Namespace, RDF, RDFS, Literal, DCTERMS, FOAF)
from collections import OrderedDict
from common import (WPDB, WPDD, DBR, IDB, IDD, SCH, CNT, genuuid, DCID,
                    DCTERMS, IMIT, MURAL, EXMURAL, BACHOLOIR, ACBACH, APPLBACH,
                    MASTER, NUMBERRE, COMPETENCERE, REQDESCRRE, COURCODERE,
                    BULLETS, found, anywords, allwords, splitnumber,
                    startswithnumber, listitem, binds)
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(format='%(levelname)s:%(module)s:%(message)s',
                    level=logging.DEBUG)

C = genuuid(IDB)
G = Graph()

COURSES = OrderedDict()
COMPS = OrderedDict()


def conv(filename):
    wb = open_workbook(filename)
    G.add((IMIT, RDF.type, DBR.Faculty))
    binds(G)
    for sheet in wb.sheets():
        print(sheet.name)
        procsheet(sheet)
    G.serialize(destination=filename + ".ttl", format="turtle")


def proccomp2(sheet):
    pass


def proccomp1(sheet):
    pcomp = None
    for row in range(sheet.nrows):
        code = None
        title = None
        ctype = None
        for col in range(sheet.ncols):
            t = str(sheet.cell_value(row, col).strip())
            if t == "":
                continue
            m = re.search(COMPETENCERE, t)
            q = re.search(COURCODERE, t)
            if m is not None and code is None:
                code = m.group(0)
                ctype = "comp"
                continue
            elif q is not None and code is None:
                code = q.group(0)
                if code != t:
                    logger.debug("Regex '{}'!='{}'".format(code, t))
                ctype = "cour"
                continue
            elif title is None:
                title = t
        if ctype == "comp":
            c = genuuid(IDB)
            pcomp = ([], c)
            COMPS[code] = (c, pcomp[0])
            G.add((c, RDF.type, IDD["Compenence"]))
            G.add((c, RDFS.label, Literal(title, lang="ru")))
            G.add((c, DCID, Literal(code, lang="ru")))

        elif ctype == "cour":
            if code in COURSES:
                d, dd = COURSES[code]
            else:
                d = BNode()
                dd = genuuid(IDB)
                COURSES[code] = (d, dd)
                G.add((IMIT, IDD.hasDiscipline, d))
                G.add((d, DCID, Literal(code, lang="ru")))
                G.add((d, IDD.discipline, dd))
                G.add((dd, RDF.type, IDD["Discipline"]))
                G.add((dd, RDFS.label, Literal(title, lang="ru")))
            G.add((d, IDD.hasCompetence, pcomp[1]))
            pcomp[0].append((d, dd))


def proctitle(sheet):
    pass


def procplan(sheet):
    pass


def procsheet(sheet):
    sname = sheet.name.strip().lower()
    if allwords(sname, "компетенции(2)"):
        proccomp2(sheet)
    elif allwords(sname, "компетенции"):
        proccomp1(sheet)
    elif allwords(sname, "титул"):
        proctitle(sheet)
    elif allwords(sname, "план"):
        procplan(sheet)
    else:
        logger.warn("Did not process sheet '{}'".format(sname))


if __name__ == "__main__":
    conv("01.03.02-22-1234_1к_06.plx.xls")
