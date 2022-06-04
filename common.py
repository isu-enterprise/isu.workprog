import re
from rdflib import (Graph, BNode, Namespace, RDF, RDFS, Literal, DCTERMS, FOAF)
from uuid import uuid1
#from itertools import pairwise
from collections import OrderedDict
import os

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
    g.bind('cnt', CNT)


WPDB = Namespace("http://irnok.net/ontologies/database/isu/workprog#")
WPDD = Namespace("http://irnok.net/ontologies/isu/workprog#")
DBR = Namespace("http://dbpedia.org/resource/")
IDB = Namespace("http://irnok.net/ontologies/database/isu/studplan#")
IDD = Namespace("http://irnok.net/ontologies/isu/studplan#")
SCH = Namespace("https://schema.org/")
CNT = Namespace("http://www.w3.org/2011/content#")

DCID = DCTERMS.identifier

IMIT = IDB['c526d6c7-9a78-11e6-9438-005056100702']  # Taken from 1C
IMIT_NAME = 'Институт математики и информационных технологий'
ISU = IDB['6ed6df0a-dbed-11ec-b49e-704d7b84fd9f']  # Generated
ISU_NAME = "Иркутский государственный университет"
MURAL = IDB['e4f4e44d-5a0b-11e6-942f-005056100702']
EXMURAL = IDB['e4f4e44c-5a0b-11e6-942f-005056100702']
BACHOLOIR = IDB['f2d33750-5a0b-11e6-942f-005056100702']
ACBACH = IDB['f2d3374f-5a0b-11e6-942f-005056100702']
APPLBACH = IDB['f2d33754-5a0b-11e6-942f-005056100702']
MASTER = IDB["f2d33752-5a0b-11e6-942f-005056100702"]
EXAMS = IDB["2270a05e-7010-11e6-9432-005056100702"]
CREDIT = IDB['2270a057-7010-116-9432-005056100702']  # Зачет?
CREDITWN = IDB['64f1e5c8-dd4d-11ec-9333-704d7b84fd9f']
TASK = IDB['a8de13b0-dd4d-11ec-9333-704d7b84fd9f']

NUMBERRE = re.compile(
    r'^(((Тема|Раздел)\s+)?((\d{1,2}|[IVXLCDM]{1,4}|[ivxlcdm]{1,4})\.?\)?)+|[а-яА-я]\))\s+'
)
COMPETENCERE = re.compile(r"([А-ЯA-Z]{1,3}[-–]+\d+)")
REQDESCRRE = re.compile(r"(знать|уметь|владеть)")
COURCODERE = re.compile(
    r"([А-Яа-яA-Za-z]{0,4}\d{0,3}(\([А-Яа-яA-Za-z]{1,2}\))?\.)+[А-Яа-яA-Za-z]{0,4}\d{0,3}(\([А-Яа-яA-Za-z]{1,2}\))?"
)
SPECCODERE = re.compile(r"(\d{2,2}\.\d{2,2}\.\d{2,2})")
PROFCODERE = re.compile(r"(\d{2,3}(\.\d{3,3})?)")
YEARRE = re.compile(r"\d{4,4}")
YEARDISTRE = re.compile(r"(\d{4,4})[-–]+(\d{4,4})")

BULLETS = [
    "-", "*", "#", "–", '•', '‣', '⁃', '⁌', '⁍', '◘', '◦', '⦾', '⦿', '฀'
]
DEPARTMENTS = {
    "институтматематикииинформационныхтехнологий":
    (IMIT, IMIT_NAME, (IDD["Faculty"], IDD["Institute"])),
    "иркутскийгосударственныйуниверситет":
    (ISU, ISU_NAME, (IDD["University"], ))
}


def found(s, substr):
    return s.find(substr) != -1


def normspaces(s):
    return " ".join(s.split()).strip()


def alltext(node, normalize=False):
    s = node.xpath("string()").strip()
    if normalize:
        return normspaces(s)
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


def refinename(name):
    name = name.strip().rstrip(".").strip()
    while found(name, '  '):
        name = name.replace("  "," ")
    return name

def asdirname(name):
    name = str(name)
    if len(name)>200: # Really - 255 or 256
        name=refinename(name[:200])
    return name.replace(" ","-").replace("(",'_').replace(")","_")

def safecwd(dir):
    try:
        os.chdir(dir)
    except FileNotFoundError:
        os.makedirs(dir)
        os.chdir(dir)
