import requests as rq
from rdflib import (Namespace, URIRef, Literal, BNode, FOAF, DC, DCTERMS,
                    Graph, RDF, RDFS, XSD)

from common import (WPDB, WPDD, DBR, IDB, IDD, SCH, CNT, genuuid, DCID, IDD, IDB,
                    DCTERMS, IMIT, MURAL, EXMURAL, BACHOLOIR, ACBACH, APPLBACH,
                    MASTER, NUMBERRE, COMPETENCERE, REQDESCRRE, BULLETS, found,
                    alltext, anywords, allwords, splitnumber, startswithnumber,
                    listitem, binds)

from kg import (DEPARTMENTS_KG, REFERENCES_KG, DISCIPLINES_KG, update, preparegraphs,
                loadallkgs, saveallkgs, STANDARDS_KG, getfrom)

ENDPOINT = 'http://py.isu.ru:8000/hs/jsonpost/courses_in_faculty/'
USER = "3c9467d8-b710-11e6-943c-005056100702"
IMIT = 'c526d6c7-9a78-11e6-9438-005056100702'
INIT_NAME = 'Институт математики и информационных технологий'
SEMEVEN = 0
SEMODD = 1
SEMAUTUMN = SEMODD
SEMSPRING = SEMEVEN
HEADERS = {'Content-Type': 'application/json'}


def query(user, faculty=IMIT, profile=None, year=None, term=None):
    """Returns a JSON-parsed data structure.
    Parameters are
    `user` is the GUID of user,
    `faculty` is name of a faculty/institute,
    `profile` is the identifier of a profile/specialty
              (not used now),
    `year` is the year of study start
              (not used in requests),
    `term` is the semester mark (SEMAUTUMN, SEMSPRING)
    """
    if term is None:
        raise ValueError('term is undefined')
    resp = rq.request(method='POST',
                      url=ENDPOINT,
                      headers=HEADERS,
                      json={
                          "guid": user,
                          "facultet": faculty,
                          "flag_semestr": term
                     })
    if resp.ok:
        return resp.json()
    else:
        print('Return code:', resp.status_code)
        raise RuntimeError('request failed ({})'.format(resp.status_code))


MAPPRED = {
    'ВидКонтроля': IDD['controlType'],
    'Дисциплина': IDD['discipline'],
    'Лабораторные': IDD['laboratoryWorksAmount'],
    'Лекции': IDD['lectionAmount'],
    'ПериодКонтроля': IDD['controlPeriod'],
    'Практические': IDD['practiceAmount'],
    'Профиль': IDD['profile'],
    'ТипЗаписи': IDD['codeType'],
    'УчебныйПлан': IDD['studyPlan'],
    'УчебныйПланСпециальность': IDD['specialty'],
    'УчебныйПланУровеньПодготовки': IDD['level'],
    'УчебныйПланФормаОбучения': IDD['studyForm'],
}

MAPCLASS = {
    'ВидыКонтроля': IDD['ControlType'],
    'Дисциплины': IDD['Discipline'],
    'ПериодыКонтроля': IDD['ControlPeriod'],
    'ТипЗаписиУчебногоПлана': IDD['DisciplineCodeType'],
    'Специализации': IDD['Specialization'],
    'УчебныйПлан': IDD['Cirriculum'],
    'Специальности': IDD['Speciality'],
    'УровеньПодготовки': IDD['StudyLevel'],
    'ФормаОбучения': IDD['StudyForm'],
}

DT = {int: {'datatype': XSD.integer}, str: {'lang': u'ru'}}

TERM = {
    0: IDD['Even'],
    1: IDD['Odd'],
}

CONUNDEF = {
    'catalog': 'ВидыКонтроля',
    'name': 'Неопределено',
    'type': 'CatalogRef',
    'uid': '6ee6cd49-56a2-4008-ab10-d94dbcb56b22'
}


def tograph(query, graph=None, catalogs=None):
    j = query
    if (j['error_status']):
        raise RuntimeError('wrong return status')
    j = j['hs_json']
    i = j['Input']
    o = j['Output']
    dj = o['Data']  # list of courses
    term = i['flag_semestr']
    term = TERM[term]
    faculty = IDB[i['facultet']]

    if catalogs is None:
        catalogs = {}  # Various catalogs

    def _cat(node):
        t = type(node)
        if t in [int, str]:
            kwargs1 = DT[t]
            if node == "Неопределено":
                return _cat(CONUNDEF)
            return Literal(node, **kwargs1)
        if node['type'] in ['CatalogRef', 'DocumentRef']:
            cat = catalogs.setdefault(node['catalog'], {})
            uid = IDB[node['uid']]
            cat[uid] = node['name']
            return uid

    if graph is None:
        g = Graph()
        binds(g)
        DISCIPLINES_KG.add((TERM[0], RDFS.label, Literal('четный', lang=u'ru')))
        DISCIPLINES_KG.add((TERM[1], RDFS.label, Literal('нечетный', lang=u'ru')))
        DISCIPLINES_KG.add((TERM[0], RDFS.label, Literal('even', lang=u'en')))
        DISCIPLINES_KG.add((TERM[1], RDFS.label, Literal('odd', lang=u'en')))
    else:
        g = graph

    faculty = getfrom(DEPARTMENTS_KG, INIT_NAME, IDB,
                      (DBR.Faculty, IDD.Faculty, IDD.Institute),
                      uri = faculty)
    for cour in dj:
        dis = BNode()
        g.add((dis, RDF.type, IDD['Discipline']))
        g.add((faculty, IDD['hasDiscipline'], dis))
        # g.add((dis, IDD["discipline"], )) # TODO: add discipline reference
        g.add((dis, IDD['term'], term))
        for k, node in cour.items():
            subj = _cat(node)
            g.add((dis, MAPPRED[k], subj))
    return g


MAPABBR = {
    'ПМиИ': 'Прикладная математика и информатика',
    'МОиАИС': 'Математическое обеспечение и администрирование информационных систем',
    'ФИиИТ': 'Фундаментальная информатика и информационные технологии',
}


def setupcatalogs(graph, catalogs):
    g = graph
    _ = 'УчебныйПлан'

    def _d(uid, n):
        # 02УП2021_01.03.02_ПМиИ (000009111 от 06.05.21)
        _code, _number, _1, _date = n.split(' ')
        number = _number.lstrip('(')
        date = _date.rstrip(')')
        d, m, y = date.split('.')
        if len(y) < 4:
            y = "20" + y
        date = "{}-{}-{}".format(y, m, d)
        _1, spec_code, spec_abbr = _code.split('_')
        spec_abbr = spec_abbr.strip()
        try:
            spec_name = MAPABBR[spec_abbr]
        except KeyError:
            print("No name for '{}'".format(spec_abbr))
            spec_name = None
        year = _1[-4:]
        g.add((uid, IDD['number'], Literal(number, datatype=XSD.string)))
        g.add((uid, IDD['signDate'], Literal(date, datatype=XSD.date)))
        if spec_abbr:
            g.add((uid, IDD['nameAbbreviation'], Literal(spec_abbr, lang=u"ru")))
            if spec_name:
                g.add((uid, IDD['name'], Literal(spec_name, lang=u'ru')))
        g.add((uid, IDD['specialityCode'], Literal(spec_code, datatype=XSD.string)))
        g.add((uid, IDD['enrolledIn'], Literal(year, datatype=XSD.integer)))

    for kc, cat in catalogs.items():
        for uid, name in cat.items():
            if kc == _:
                _d(uid, name)
            g.add((uid, RDFS['label'], Literal(name, lang=u"ru")))
            g.add((uid, RDF.type, MAPCLASS[kc]))
    return g


if __name__ == '__main__':
    # from pprint import pprint
    preparegraphs()
    q = query(user=USER, faculty=IMIT, term=SEMSPRING)
    catalogs = {}
    print('Processing spring')
    g = tograph(q, catalogs=catalogs)
    q = query(user=USER, faculty=IMIT, term=SEMAUTUMN)
    print('Processing autumn')
    g = tograph(q, graph=g, catalogs=catalogs)
    print('Processing catalogs')
    setupcatalogs(g, catalogs)
    g.serialize('studplan.ttl', format='turtle')
    saveallkgs()
