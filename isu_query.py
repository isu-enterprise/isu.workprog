import requests as rq
from rdflib import (Namespace, URIRef,
                    Literal, BNode, FOAF,
                    DC, DCTERMS, Graph,
                    RDF, RDFS, XSD
                    )


ENDPOINT = 'http://py.isu.ru:8000/hs/jsonpost/courses_in_faculty/'
USER = "3c9467d8-b710-11e6-943c-005056100702"
IMIT = 'c526d6c7-9a78-11e6-9438-005056100702'
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


IDB = Namespace("http://irnok.net/ontologies/database/isu/studplan#")
IDD = Namespace("http://irnok.net/ontologies/isu/studplan#")
DBR = Namespace("https://dbpedia.org/page/")

MAP = {
    'ВидКонтроля': IDD['controlType'],
    'Дисциплина': IDD['discipline'],
    'Лабораторные': IDD['laboratoryWorksAmount'],
    'Лекции': IDD['lectionAmount'],
    'ПериодКонтроля': IDD['controlPeriod'],
    'Практические': IDD['practiceAmount'],
    'Профиль': IDD['profile'],
    'ТипЗаписи': IDD['recordType'],
    'УчебныйПлан': IDD['studyPlan'],
    'УчебныйПланСпециальность': IDD['specialty'],
    'УчебныйПланУровеньПодготовки': IDD['level'],
    'УчебныйПланФормаОбучения': IDD['studyForm']
}

DT = {
    int: {'datatype': XSD.integer},
    str: {'lang': u'ru'}
}

TERM = {
    0: IDD['Even'],
    1: IDD['Odd'],
}

CONUNDEF = {'catalog': 'ВидыКонтроля',
            'name': 'Неопределено',
            'type': 'CatalogRef',
            'uid': '6ee6cd49-56a2-4008-ab10-d94dbcb56b22'}


def tograph(query, graph=None, catalogs=None):
    j = query
    if (j['error_status']):
        raise RuntimeError('wrong return status')
    j = j['hs_json']
    i = j['Input']
    o = j['Output']
    dj = o['Data']      # list of courses
    term = i['flag_semestr']
    term = TERM[term]
    faculty = IDB[i['facultet']]

    if catalogs is None:
        catalogs = {}   # Various catalogs

    def _cat(node):
        t = type(node)
        if t in [int, str]:
            kwargs1 = DT[t]
            if node == "Неопределено":
                return _cat(CONUNDEF)
            return Literal(node, **kwargs1)
        if node['type'] in ['CatalogRef', 'DocumentRef']:
            cat = catalogs.setdefault(node['catalog'], {})
            uid = node['uid']
            cat[uid] = node['name']
            return URIRef(uid)

    if graph is None:
        g = Graph()
        g.bind('idb', IDB)
        g.bind('idd', IDD)
        g.bind('dbr', DBR)
        g.add((TERM[0], RDFS.label, Literal('четный', lang=u'ru')))
        g.add((TERM[1], RDFS.label, Literal('нечетный', lang=u'ru')))
        g.add((TERM[0], RDFS.label, Literal('even', lang=u'en')))
        g.add((TERM[1], RDFS.label, Literal('odd', lang=u'en')))
    else:
        g = graph

    g.add((faculty, RDF.type, DBR.Faculty))
    for cour in dj:
        dis = BNode()
        g.add((faculty, IDD['hasDiscipline'], dis))
        g.add((dis, IDD['term'], term))
        for k, node in cour.items():
            subj = _cat(node)
            g.add((dis, MAP[k], subj))
    return g


def setupcatalogs(graph, catalogs):
    g = graph
    for kc, cat in catalogs.items():
        for uid, name in cat.items():
            uid = URIRef(uid)
            g.add((uid, RDFS['label'], Literal(name, lang=u"ru")))
            g.add((uid, RDF.type, IDD[kc]))
    return g


if __name__ == '__main__':
    # from pprint import pprint
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
