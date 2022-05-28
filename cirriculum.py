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
                    DEPARTMENTS, YEARDISTRE, YEARRE, PROFCODERE, EXAMS, CREDIT,
                    CREDITWN, TASK)

from kg import (DEPARTMENTS_KG, REFERENCES_KG, DISCIPLINES_KG, update,
                preparegraphs, loadallkgs, saveallkgs, STANDARDS_KG, getfrom)

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(format='%(levelname)s:%(module)s:%(message)s',
                    level=logging.DEBUG)

C = genuuid(IDB)
G = Graph()

COURSES = OrderedDict()
COMPS = OrderedDict()
CHAIRS = OrderedDict()
UNIV = None
INST = None
FIELDS = None


def getchair(code, getter):
    if code not in CHAIRS:
        name = getter()
        chair = getfrom(DEPARTMENTS_KG, name, IDB, IDD["Chair"])
        DEPARTMENTS_KG.add((INST, IDD.hasChair, chair))
        G.add((chair, SCH.sku, Literal(code)))
        CHAIRS[code] = chair
    else:
        chair = CHAIRS[code]
    return chair


def conv(filename):
    wb = open_workbook(filename)
    binds(G)
    sheets = list(wb.sheets())

    # At first process list of courses and their competencies

    comp = [s for s in sheets if s.name == "Компетенции"]
    rest = [s for s in sheets if s.name != "Компетенции"]
    sheets = comp + rest

    for sheet in sheets:
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
            c = getfrom(DISCIPLINES_KG, title, IDB, IDD["Compenence"])
            pcomp = ([], c)
            COMPS[code] = (c, pcomp[0])
            G.add((c, DCID, Literal(code, lang="ru")))

        elif ctype == "cour":
            if code in COURSES:
                d, dd = COURSES[code]
            else:
                d = BNode()
                dd = getfrom(DISCIPLINES_KG, title, IDB, IDD["Discipline"])
                COURSES[code] = (d, dd)
                G.add((C, IDD.hasDiscipline, d))
                G.add((d, RDF.type, IDD["Discipline"]))
                G.add((d, DCID, Literal(code, lang="ru")))
                G.add((d, IDD.discipline, dd))
            G.add((d, IDD.hasCompetence, pcomp[1]))
            pcomp[0].append((d, dd))


def lines(sheet, normspaces=False, cells=False, rowno=False):
    for row in range(sheet.nrows):
        ss = [str(sheet.cell_value(row, col)) for col in range(sheet.ncols)]
        s = " ".join(ss).strip()
        if normspaces:
            s = " ".join(s.split())
        rc = [s]

        if cells:
            rc.append(ss)
        if rowno:
            rc.append(row)
        yield rc[0] if len(rc) == 1 else rc


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
                title = cells[profcode + 1].strip()
                uri = getfrom(STANDARDS_KG,
                              title,
                              IDB,
                              IDD["ProfessionActivity"],
                              provision=lambda subj: STANDARDS_KG.add(
                                  (subj, DCID, Literal(code))))
                G.add((C, IDD.professionActivity, uri))
                continue
            else:
                profcodem = None
        if tasktype is not None:
            basic = cells[tasktype - 1].strip()
            task = cells[tasktype].strip()
            if basic in "+-" and task != "":
                uri = BNode()
                G.add((C, IDD.taskType, uri))
                G.add((uri, RDF.type, IDD["TaskType"]))
                G.add((uri, RDFS.label, Literal(task, lang="ru")))
                G.add((uri, IDD.basic, Literal(basic == "+")))
                continue
            else:
                tasktype = None

        # print(specm)
        if allwords(lt, "федеральн государствен образовательн") or anywords(
                lt, "фгбоуво фгоуво"):
            try:
                uni = line.split('"', maxsplit=2)[1].strip()
                UNIV = getfrom(DEPARTMENTS_KG, uni, IDB, IDD["University"])
            except (TypeError, IndexError):
                logger.warning(
                    "Cannot figure out university from '{}' ".format(line))
                UNIV = getfrom(DEPARTMENTS_KG,
                               "Unknown university",
                               IDB,
                               IDD["University"],
                               lang="en")
            try:
                inst = line.split("\n")[1].strip()
            except IndexError:
                inst = "Unknown institute"

            iinst = ''.join(inst.split()).lower()

            def _prov(subj):
                if UNIV is not None:
                    DEPARTMENTS_KG.add((UNIV, SCH.department, subj))
                if iinst.startswith("институт"):
                    DEPARTMENTS_KG.add((subj, RDF.type, IDD["Institute"]))

            if iinst in DEPARTMENTS:
                INST = DEPARTMENTS[iinst]
            else:
                INST = getfrom(DEPARTMENTS_KG,
                               inst,
                               IDB,
                               IDD["Faculty"],
                               provision=_prov)

            G.add((INST, IDD.hasСurriculum, C))
            G.add((C, RDF.type, IDD["Сurriculum"]))
        elif allwords(lt, "профиль"):
            _, title = line.split(":", maxsplit=1)
            title = normspaces(title)
            if title != "":
                prof = getfrom(STANDARDS_KG, title, IDB,
                               (IDD["Specialization"], IDD["Profile"]))
                G.add((C, IDD.profile, prof))
            else:
                logger.error("Profile is not recognized in '{}'".format(line))
        elif allwords(lt, "кафедра"):
            _, title = line.split(":", maxsplit=1)
            title = normspaces(title)
            if title != "":
                chair = getfrom(
                    DEPARTMENTS_KG, title, IDB, IDD["Chair"],
                    lambda subj: DEPARTMENTS_KG.add(
                        (INST, SCH.department, subj)))
                G.add((C, IDD.chair, chair))
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
                G.add((C, IDD.studyYears, Literal("{}-{}".format(year1,
                                                                 year2))))
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
                G.add((C, IDD.studyDration, Literal(dur)))
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

            def _prov(subj):
                DEPARTMENTS_KG.add((INST, IDD.director, subj))
                DEPARTMENTS_KG.add((subj, FOAF.name, Literal(head, lang="ru")))

            uri = getfrom(DEPARTMENTS_KG, head, IDB, FOAF["Person"], _prov)
            G.add((C, IDD.director, uri))
        elif specm is not None:
            parts = re.split(SPECCODERE, line, maxsplit=1)
            if len(parts) > 3:
                code, title = parts[1:3]
                title = normspaces(title)
                if title != "":
                    spec = getfrom(
                        STANDARDS_KG, title, IDB, IDD["Speciality"],
                        lambda subj: G.add((subj, DCID, Literal(code))))
                    G.add((C, IDD.specialty, spec))
        else:
            pass
            logger.debug("Skipping:'{}'".format(line))


def upget(row, col, sheet):
    rc = []
    dirup = True
    r = row
    c = col
    pc = None
    while True:
        e = str(sheet.cell_value(r, c)).strip().lower()
        e = ''.join(str(e).split())
        # print("U:", dirup, r, c, e)
        if e in [""]:
            if dirup:
                if r == row:
                    return None
                else:
                    dirup = False
                    pc = c
                    continue
            else:  # dirleft
                if c > 0:
                    c -= 1
                else:
                    # if rc[-1] in ["компетенции", "наименование", "код"]:
                    #     r-=2
                    dirup = True
                    c = pc
                    r -= 1
        else:
            if e == "-":
                return rc
            rc.append(e)
            if r == 0:
                return rc
            else:
                r -= 1
                dirup = True
    return None


def idtproc(idt):

    def _(x):
        x = x.replace("семестр", "").replace("курс", "")
        try:
            x = int(x)
        except ValueError:
            pass
        return x

    if idt == []:
        return None
    idt = [_(i) for i in idt]
    if idt[0] in ["код", "наименование", "компетенции"] and len(idt) > 1:
        idt = idt[:1] + ["закрепленнаякафедра"]
    return idt


FIELDLIST = [
    (['считатьвплане'], IDD.account, lambda x: Literal(x.strip() == "+")),
    (['индекс']),
    (['наименование']),
    (['экзамен', 'формаконтроля'], IDD.controlType, EXAMS),
    (['зачет', 'формаконтроля'], IDD.controlType, CREDIT),
    (['зачетсоц.', 'формаконтроля'], IDD.controlType,
     CREDITWN),  # TODO: Add into global graph its description
    (['кр', 'формаконтроля'], IDD.controlType, TASK),  # TODO: description
    (['экспертное',
      'з.е.'], (BNode, IDD.credits, IDD["Credits"]), IDD.expert, Literal),
    (['факт', 'з.е.'], BNode, IDD.actual, Literal),
    (['часоввз.е.'], IDD.hoursInCredit, Literal),
    (['экспертное', 'итогоакад.часов'], (BNode, IDD.hours, IDD["Hours"]),
     IDD.expert, Literal),
    (['поплану', 'итогоакад.часов'], BNode, IDD.actual, Literal),
    (['конт.раб.', 'итогоакад.часов'], BNode, IDD.test, Literal),
    (['ср', 'итогоакад.часов'], BNode, IDD.independentWork, Literal),
    (['контроль', 'итогоакад.часов'], BNode, IDD.control, Literal),
    (['электчасы', 'итогоакад.часов'], BNode, IDD.elective, Literal),
    (['з.е.'], (BNode, IDD["term"], IDD["ControlPeriod"]), IDD.credits,
     Literal),
    (['итого'], BNode, IDD.total, Literal),
    (['лек'], BNode, IDD.lection, Literal),
    (['лаб'], BNode, IDD.laboratoryWorks, Literal),
    (['пр'], BNode, IDD.practice, Literal),
    (['конс'], BNode, IDD.consultation, Literal),
    (['ко'], BNode, IDD.control, Literal),
    (['ср'], BNode, IDD.independentWork, Literal),
    (['кср'], BNode, IDD.independentWorkControl, Literal),
    (['контроль'], BNode, IDD.preparation, Literal),
    # (['код', 'закрепленнаякафедра'], IDD.chair, ID_[""]),
    # (['наименование', 'закрепленнаякафедра'], ID_., ID_[""]),
    # (['компетенции', 'закрепленнаякафедра'], ID_., ID_[""])
]

FIELDS = {}
for _ in FIELDLIST:
    k = "-".join(_[0])
    cmds = _[1:]
    FIELDS[k] = cmds


def procplan(sheet):
    ic = {}
    header = True
    codepos = None
    for line, cells, row in lines(sheet, cells=True, rowno=True):
        lt = line.lower()
        code = None
        if header:
            if allwords(lt, "индекс наименование"):
                for i, c in enumerate(cells):
                    cl = c.lower()
                    idt = upget(row, i, sheet)
                    idt = idtproc(idt)

                    # print(idt)
                    ic[i] = idt
                    if cl == "индекс":
                        print("CODEPOS:", i)
                        codepos = i
                header = False
            continue
        # not header
        il = cells[codepos].strip()
        codem = re.search(COURCODERE, il)
        disc = descr = None
        if codem is not None:
            code = codem.group(0)
            try:
                disc, descr = COURSES[code]
            except KeyError:
                logger.warning("Unknown course code '{}':'{}'".format(
                    code, line))
                continue
        elif il != "":
            logger.warning(
                "Non-empty code field did not processed '{}'.".format(line))
            continue
        else:
            continue

        # Now process the numbers
        bnode = None
        credit = None
        for col, c in enumerate(cells):

            v = c.strip()
            t = str
            try:
                v = int(v)
                t = int
            except ValueError:
                pass
            if v == "":
                continue

            ident = ic[col]

            if ident is None:
                continue

            id0 = ident[0]
            if id0 == "код":
                chair = getchair(v, lambda: cells[col + 1].strip())

                G.add((disc, IDD.chair, chair))
                break
            term = False
            # if id0 in [
            #         'з.е.', 'итого', 'лек', 'лаб', 'пр', 'конс', 'ко', 'ср',
            #         'контроль'
            # ]:
            if len(ident) > 1 and isinstance(ident[-1],
                                             int):  # term data has numbers
                idk = [id0]
                term = True
            else:
                idk = ident
            print(idk)
            idk = "-".join(idk)
            try:
                cmds = FIELDS[idk]
            except KeyError:
                cmds = None
            # print("CMDS:", idk, cmds)

            # interpreting cmds
            if cmds is None or len(cmds) < 1:
                continue

            c0 = cmds[0]
            if isinstance(c0, tuple) and c0[0] == BNode:
                bnode = BNode()
                G.add((bnode, RDF.type, c0[2]))
                G.add((disc, c0[1], bnode))
                cmds = cmds[1:]
                if term:
                    _, sem, cour, = ident
                    G.add((bnode, IDD["number"], Literal(sem)))
                    G.add((bnode, IDD.course, Literal(cour)))
            elif c0 is not BNode and bnode is not bnode:
                bnode = None
            elif c0 is BNode:
                cmds = cmds[1:]

            subj = disc
            obj = None
            pred = None

            if bnode is not None:
                subj = bnode
            try:
                pred, obj = cmds
            except ValueError:
                logging.error("Unpack: '{}' for '{}':'{}'".format(
                    cmds, idk, FIELDS[idk]))

            if callable(obj):
                obj = obj(v)
            if None in [subj, pred, obj]:
                logging.warning("Incomplete triple <{},{},{}>".format(
                    subj, pred, obj))

            if id0 == 'ко':
                if v == 10:
                    G.add((subj, IDD.type, EXAMS))
                elif v == 8:
                    if credit is None:
                        logger.error(
                            "Found hours for credit, but not credit "
                            "type in course description '{}'".format(line))
                    else:
                        G.add((subj, IDD.type, credit))
            elif id0 == 'зачетсоц.':
                credit = CREDITWN
            elif id0 == 'зачет':
                credit = CREDIT
            G.add((subj, pred, obj))


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
    import sys
    preparegraphs()
    if len(sys.argv) < 2:
        # conv("01.03.02-22-1234_1к_06.plx.xls")
        # conv("../cirriculums/02.04.02-22-12_1к.plx.xls")
        conv("../cirriculums/44.03.05-22-12345_1к.plx.xls")
    else:
        conv(sys.argv[1])
    saveallkgs()
    # conv("./09.03.01 (АСУб-22).plx.xls")
