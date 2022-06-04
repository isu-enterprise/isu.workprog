from common import *
from rdflib import Literal, Namespace, Graph, URIRef
from kg import *
import os.path
import types
from pybars import Compiler

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(format='%(levelname)s:%(module)s:%(message)s',
                    level=logging.DEBUG)

TEMPLATE_NAME = "wp-template.tex"
TARGET_DIR = os.path.abspath("./target")


def safenext(g):
    try:
        return next(g)
    except StopIteration:
        return None


def wrap(uri):
    return Entity(uri)


def uri(ent):
    if isinstance(ent, Context):
        return ent.uri
    else:
        return ent


COMPILER = Compiler()

TEMPLATE = COMPILER.compile(open(TEMPLATE_NAME, "r").read())

G = Graph()
NS = {}


def initgraph(filename):
    global G, NS
    G.parse(filename)
    binds(G)
    G += STANDARDS_KG
    G += DEPARTMENTS_KG
    G += DISCIPLINES_KG
    G += REFERENCES_KG
    G += LABELS_KG
    for ns, uri in G.namespaces():
        NS[ns] = Namespace(uri)
    return G


class Context():

    def __init__(self, uri=None, typeof=None):
        if isinstance(uri, types.GeneratorType):
            uri = next(uri)
        self.uri = uri
        self.typeof = typeof

    def __str__(self):
        return str(self.uri)

    def get(self, index):
        if ":" in index:
            pref, ns, pred = index.split(":")
            # print(pref, ns, pred)
            nspred = NS[ns][pred]
            if '^' in pref:
                # print("subj?", nspred, self)
                o = G.subjects(nspred, self.uri)
            else:
                # print(self, nspred, "obj?")
                o = G.objects(self.uri, nspred)
            if o is not None:
                try:
                    return Context(o)
                except StopIteration:
                    return "{} {}".format(self, index)
            else:
                return None
        else:
            raise IndexError("no rdf")

    def generate(self):

        for curriculum in self.rdfinsts(self.typeof):
            self.curriculum = Context(curriculum)
            self.institute = self.get("^:idd:hasCurriculum")
            self.institute.label = self.rdflabel(self.institute)
            self.university = self.institute.get("^:idd:department")
            self.university.label = self.rdflabel(self.university)
            self.basechair = Context(G.objects(curriculum, IDD.chair))
            self.basechair.label = self.rdflabel(self.basechair)
            self.enrolledIn = int(next(G.objects(curriculum, IDD.enrolledIn)))
            self.director = Context(G.objects(curriculum, IDD.director))
            self.director.label = self.rdflabel(self.director)
            self.level = Context(G.objects(curriculum, IDD.level))
            self.level.label = self.rdflabel(self.level)

            for discentry in G.objects(curriculum, IDD.hasDiscipline):
                self.discentry = Context(discentry)
                self.rdftypecheck(discentry, IDD["Discipline"])
                self.discentry.code = self.rdfdcid(self.discentry)
                self.discentry.chair = Context(G.objects(discentry, IDD.chair))
                self.discentry.chair.label = self.rdflabel(
                    self.discentry.chair.uri)
                assert self.discentry.chair.label is not None

                self.discipline = Context(G.objects(discentry, IDD.discipline))
                self.discipline.label = self.rdflabel(self.discipline)
                self.specialty = Context(G.objects(curriculum, IDD.specialty))
                self.specialty.label = self.rdflabel(self.specialty)
                self.specialty.code = next(G.objects(self.specialty.uri, DCID))
                self.mural = Context(G.objects(curriculum, IDD.studyForm))

                self.mural.label = self.rdflabel(self.mural)

                self.profile = Context(G.objects(curriculum, IDD.profile))
                self.profile.label = self.rdflabel(self.profile)

                self.setdefaults()  # Must be the last one

                yield self

    def gendir(self):
        for _ in self.generate():
            dir = os.path.join(
                TARGET_DIR,
                asdirname(self.university.label),
                asdirname(self.institute.label),
                asdirname(self.discentry.chair.label),
                asdirname(self.specialty.code) + "-" +
                asdirname(self.specialty.label),
                # asdirname(
                #     str(self.discentry.code) + "-" +
                #     str(self.discipline.label)),
                asdirname(self.profile.label),
                asdirname(self.enrolledIn),
                asdirname(self.mural.label),
            )
            safecwd(dir)
            self.genwp()

    def genwp(self):
        filename = asdirname(self.discentry.code) + "-" + asdirname(
            self.discipline.label) + ".tex"
        content = TEMPLATE({
            "context": self,
            "curr": self.curriculum,
            "disc": self.discentry
        })
        logger.info("Writing into '{}'".format(filename))
        o = open(filename, "w")
        o.write(content)
        o.close()

    def rdfdcid(self, subj):
        subj = uri(subj)
        return safenext(G.objects(subj, DCID))

    def rdflabel(self, subj):
        subj = uri(subj)
        return safenext(G.objects(subj, RDFS.label))

    def rdfinst(self, class_):
        return safenext(self.rdfinsts(class_))

    def rdfinsts(self, class_):
        return G.subjects(RDF.type, class_)

    def rdftypecheck(self, subj, type_):
        subj = uri(subj)
        if (subj, RDF.type, type_) not in G:
            raise AssertionError("{} is not of type {}".format(subj, type_))

    def objects(self, pred):
        return G.objects(self.uri, pred)

    def subjects(self, pred):
        return G.subjects(pred, self.uri)

    # def __getitem__(self, index):
    #     return self

    def setdefaults(self):
        self.city = "Иркутск"
        self.institute.abbrev = "ИМИТ"
        self.university.abbrev = "ИГУ"
        self.institute.position = "Директор"


if __name__ == "__main__":
    import sys
    preparegraphs()
    if len(sys.argv) < 2:
        filename = "01.03.02-22-1234_1к_06.plx.xls.ttl"
    else:
        filename = sys.argv[1]

    initgraph(filename)
    C = Context(typeof=IDD["Curriculum"])
    C.gendir()
