import re
from rdflib import (Graph, BNode, Namespace, RDF, RDFS, Literal, DCTERMS, FOAF)
from uuid import uuid1
from itertools import pairwise
from collections import OrderedDict


def genuuid(namespace=None):
    uuid = str(uuid1())
    if namespace:
        return namespace[uuid]
    else:
        return uuid


def binds(g):
    g.bind('wpdb', WPDB)
    g.bind('wpdd', WPDD)
    g.bind('idb', IDB)
    g.bind('idd', IDD)
    g.bind('dbr', DBR)
    g.bind('schema', SCH)


WPDB = Namespace("http://irnok.net/ontologies/database/isu/workprog#")
WPDD = Namespace("http://irnok.net/ontologies/isu/workprog#")
DBR = Namespace("http://dbpedia.org/resource/")
IDB = Namespace("http://irnok.net/ontologies/database/isu/studplan#")
IDD = Namespace("http://irnok.net/ontologies/isu/studplan#")
SCH = Namespace("https://schema.org/")
CNT = Namespace("http://www.w3.org/2011/content#")

DCID = DCTERMS.identifier

IMIT = IDB['c526d6c7-9a78-11e6-9438-005056100702']
MURAL = IDB['e4f4e44d-5a0b-11e6-942f-005056100702']
EXMURAL = IDB['e4f4e44c-5a0b-11e6-942f-005056100702']
BACHOLOIR = IDB['f2d33750-5a0b-11e6-942f-005056100702']
ACBACH = IDB['f2d3374f-5a0b-11e6-942f-005056100702']
APPLBACH = IDB['f2d33754-5a0b-11e6-942f-005056100702']
MASTER = IDB["f2d33752-5a0b-11e6-942f-005056100702"]

NUMBERRE = re.compile(
    r'^(((Тема|Раздел)\s+)?((\d{1,2}|[IVXLCDM]{1,4}|[ivxlcdm]{1,4})\.?\)?)+|[а-яА-я]\))\s+'
)
COMPETENCERE = re.compile(r"([А-ЯA-Z]{1,3}[-–]+\d+)")
REQDESCRRE = re.compile(r"(знать|уметь|владеть)")
COURCODERE = re.compile(r"([А-Яа-яA-Za-z]{0,4}\d{0,3}(\([А-Яа-яA-Za-z]{1,2}\))?\.)+[А-Яа-яA-Za-z]{0,4}\d{0,3}(\([А-Яа-яA-Za-z]{1,2}\))?")
# COURCODERE = re.compile(r"^([А-Яа-яA-Za-z]\d{0,3})")

BULLETS = ["-", "*", "#", "–", '•', '‣', '⁃', '⁌', '⁍', '◘', '◦', '⦾', '⦿']


def found(s, substr):
    return s.find(substr) != -1


def alltext(node, normspaces=False):
    s = node.xpath("string()").strip()
    if normspaces:
        s = " ".join(s.split())
    return s


def startswithnumber(s):
    m = re.search(NUMBERRE, s.lstrip())
    if m is None:
        return False
    return m.span()[0] == 0


def splitnumber(s):
    s = s.strip()
    m = re.search(NUMBERRE, s)
    if m is None:
        return None, None
    b, e = m.span()
    if b > 0:
        return None, None
    num = s[b:e].strip()
    num = num.rstrip(".")
    num = num.rstrip(")")
    num = num.rstrip(".")
    title = s[e:].strip()
    return num, title


def allwords(s, *set):
    if len(set) == 1:
        set = set[0]
        set = set.split()
    s = s.strip()
    for w in set:
        if not found(s, w):
            return False
    return True


def listitem(text):
    if text[0] in BULLETS:
        return text[0], text[1:].strip()
    num, title = splitnumber(text)
    return num, title


def anywords(s, *set):
    if len(set) == 1:
        set = set[0]
        set = set.split()
    s = s.strip()
    for w in set:
        if found(s, w):
            return True
    return False
