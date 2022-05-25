import re
from xlrd import open_workbook
from pprint import pprint
from rdflib import (Graph, BNode, Namespace, RDF, RDFS, Literal, DCTERMS, FOAF)
from collections import OrderedDict
from common import (WPDB, WPDD, DBR, IDB, IDD, SCH, CNT, genuuid, DCID, ISU,
                    DCTERMS, IMIT, MURAL, EXMURAL, BACHOLOIR, ACBACH, APPLBACH,
                    MASTER, NUMBERRE, COMPETENCERE, REQDESCRRE, COURCODERE,
                    BULLETS, found, anywords, allwords, splitnumber,
                    normspaces, startswithnumber, listitem, binds, SPECCODERE,
                    DEPARTMENTS, YEARDISTRE, YEARRE, PROFCODERE)
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(format='%(levelname)s:%(module)s:%(message)s',
                    level=logging.DEBUG)

C = genuuid(IDB)
G = Graph()

COURSES = OrderedDict()
COMPS = OrderedDict()
UNIV = None
INST = None


def conv(filename):
    wb = open_workbook(filename)
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
                G.add((C, IDD.hasDiscipline, d))
                G.add((d, DCID, Literal(code, lang="ru")))
                G.add((d, IDD.discipline, dd))
                G.add((dd, RDF.type, IDD["Discipline"]))
                G.add((dd, RDFS.label, Literal(title, lang="ru")))
            G.add((d, IDD.hasCompetence, pcomp[1]))
            pcomp[0].append((d, dd))


def lines(sheet, normspaces=False, cells=False):
    for row in range(sheet.nrows):
        ss = [str(sheet.cell_value(row, col)) for col in range(sheet.ncols)]
        s = " ".join(ss).strip()
        if normspaces:
            s = " ".join(s.split())
        if cells:
            yield s, ss
        else:
            yield s


def proctitle(sheet):
    global UNIV, INST
    profcode = None
    tasktype = None
    for line, cells in lines(sheet, cells=True):
        lt = line.lower()

        specm = re.search(SPECCODERE, lt)
        #   федеральное государственное бюджетное образовательное
        # учреждение высшего образования "Иркутский государственный университет"
        if profcode is not None:
            profcodem = re.search(PROFCODERE, str(cells[profcode].strip()))
            if profcodem is not None:
                code = profcodem.group(1)
                title = cells[profcode+1].strip()
                uri = genuuid(IDB)
                G.add((C, IDD.professionActivity, uri))
                G.add((uri, RDF.type, IDD["ProfessionActivity"]))
                G.add((uri, RDFS.label, Literal(title, lang="ru")))
                G.add((uri, DCID, Literal(code)))
                continue
            else:
                profcodem = None
        if tasktype is not None:
            basic = cells[tasktype-1].strip()
            task = cells[tasktype].strip()
            if basic in "+-" and task != "":
                uri = BNode()
                G.add((C, IDD.taskType, uri))
                G.add((uri, RDF.type, IDD["TaskType"]))
                G.add((uri, RDFS.label, Literal(task, lang="ru")))
                G.add((uri, IDD.basic, Literal(basic=="+")))
                continue
            else:
                tasktype = None


        # print(specm)
        if allwords(lt, "федеральн государствен бюджетн") or allwords(
                lt, "фгбоуво"):
            try:
                uni = line.split('"', maxsplit=2)[1]
                unil = ''.join(uni.split()).lower()
                if unil in DEPARTMENTS:
                    UNIV = DEPARTMENTS[unil]
                else:
                    UNIV = genuuid(IDB)
                G.add((UNIV, RDF.type, IDD["University"]))
                G.add((UNIV, RDFS.label, Literal(uni, lang="ru")))
            except TypeError:
                logger.warning(
                    "Cannot figure out university from '{}' ".format(line))
                continue
            inst = line.split("\n")[1].strip()
            iinst = ''.join(inst.split()).lower()
            if iinst in DEPARTMENTS:
                INST = DEPARTMENTS[iinst]
            else:
                INST = genuuid(IDB)
            if UNIV is not None:
                G.add((UNIV, SCH.department, INST))
            G.add((INST, RDF.type, IDD["Faculty"]))
            if iinst.startswith("институт"):
                G.add((INST, RDF.type, IDD["Institute"]))
            G.add((INST, RDFS.label, Literal(inst, lang="ru")))
            G.add((INST, IDD.hasСurriculum, C))
            G.add((C, RDF.type, IDD["Сurriculum"]))
        elif allwords(lt, "профиль"):
            _, title = line.split(":", maxsplit=1)
            title = normspaces(title)
            if title != "":
                prof = genuuid(IDB)
                G.add((prof, RDF.type, IDD["Specialization"]))
                G.add((prof, RDF.type, IDD["Profile"]))
                G.add((prof, RDFS.label, Literal(title, lang="ru")))
                G.add((C, IDD.profile, prof))
            else:
                logger.error("Profile is not recognized in '{}'".format(line))
        elif allwords(lt, "кафедра"):
            _, title = line.split(":", maxsplit=1)
            title = normspaces(title)
            if title != "":
                chair = genuuid(IDB)
                G.add((chair, RDF.type, IDD["Chair"]))
                G.add((chair, RDFS.label, Literal(title, lang="ru")))
                G.add((C, IDD.chair, chair))
                G.add((INST, SCH.department, chair))
            else:
                logger.error("Chair is not recognized in '{}'".format(line))
        # elif факультет: ... имит ...
        elif allwords(lt, "квалификац"):
            _, text = line.split(": ")
            qualif, text = text.split(maxsplit=1)
            tl = text.lower()
            qualif = qualif.strip().lower()
            if qualif.startswith("бакалавр"):
                lev = BACHOLOIR
                if found(tl, "академ"):
                    lev = ACBACH
                elif found(tl, "прикладн"):
                    lev = ACBACH
                G.add((C, IDD.level, lev))
            if qualif.startswith("магистрат"):
                G.add((C, IDD.level, MASTER))
            if found(tl, "год"):
                m = re.search(YEARRE, tl)
                if m is None:
                    logger.warning(
                        "Cannot find starting year in '{}'".format(tl))
                else:
                    b, e = m.span()
                    year = int(tl[b:e])
                    G.add((C, IDD.enrolledIn, Literal(year)))
        elif allwords(lt, "учебн год"):
            m = re.search(YEARDISTRE, lt)
            if m is None:
                logger.warning("Cannot find study lasting in '{}'".format(tl))
            else:
                b, e = m.span(1)
                year1 = int(lt[b:e])
                b, e = m.span(1)
                year2 = int(lt[b:e])
                G.add((C, IDD.studyYears, Literal("{}-{}".format(year1,year2))))
        elif allwords(lt, "форм обучен"):
            _, text = lt.split(":")
            form, text = text.split(maxsplit=1)
            form = form.strip()
            mur = None
            if found(form, "заочн"):
                mur = EXMURAL
            elif found(form, "очн"):
                mur = MURAL
            if mur is not None:
                G.add((C, IDD.studyForm, mur))
            fgos = line.split("(ФГОС)", maxsplit=1)[-1]
            fgos = fgos.strip()
            G.add((C, IDD.studyStandard, Literal(fgos, lang="ru")))
        elif allwords(lt, "срок получен образован"):
            _, text = lt.split(":", maxsplit=1)
            m = re.search(r"\d{1,2}", text)
            if m is not None:
                b, e = m.span()
                dur = int(text[b:e])
                G.add((C, IDB.studyDration, Literal(dur)))
        elif allwords(lt, "код област профессиональн деятельност"):
            for i, c in enumerate(cells):
                c = str(c).strip().lower()
                if allwords(c, "код"):
                    profcode = i
                    break
        elif allwords(lt, "основн тип задач профессиональн деятельност"):
            profcode = None
            for i, c in enumerate(cells):
                c = str(c).strip().lower()
                if allwords(c, "тип задач профессиональн деятельност"):
                    tasktype = i
                    break
        elif allwords(lt, "директор"):
            tasktype = None
            _, text, _ = line.split("/")
            head = text.strip()
            uri = genuuid(IDB)
            G.add((C, IDB.director, uri))
            G.add((uri, RDF.type, FOAF["Person"]))
            G.add((uri, RDFS.label, Literal(head, lang="ru")))
        elif specm is not None:
            parts = re.split(SPECCODERE, line, maxsplit=1)
            if len(parts) > 3:
                code, title = parts[1:3]
                title = normspaces(title)
                if title != "":
                    spec = genuuid(IDB)
                    G.add((C, IDD.specialty, spec))
                    G.add((spec, RDFS.label, Literal(title, lang="ru")))
                    G.add((spec, DCID, Literal(code)))
                    G.add((spec, RDF.type, IDD["Speciality"]))
        else:
            logger.info("Skipping:'{}'".format(line))


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
        logger.warning("Did not process sheet '{}'".format(sname))


if __name__ == "__main__":
    conv("01.03.02-22-1234_1к_06.plx.xls")
