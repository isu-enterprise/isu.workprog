from common import *
from rdflib import Literal, Namespace, Graph
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


class Entity():

    def __init__(self, uri):
        if isinstance(uri, types.GeneratorType):
            uri = next(uri)
        self.uri = uri

    def __str__(self):
        return str(self.uri)


def wrap(uri):
    return Entity(uri)


def uri(ent):
    if isinstance(ent, Entity):
        return ent.uri
    else:
        return ent

COMPILER = Compiler()

class CurriculumGraph():

    def __init__(self, filename, template=TEMPLATE_NAME):
        self.graph = Graph()
        self.graph.parse(filename)
        binds(self.graph)
        self.graph += STANDARDS_KG
        self.graph += DEPARTMENTS_KG
        self.graph += DISCIPLINES_KG
        self.graph += REFERENCES_KG

        self.template = COMPILER.compile(open(TEMPLATE_NAME,"r").read())

    def generate(self):

        for curriculum in self.rdfinsts(IDD["Curriculum"]):
            self.curriculum = Entity(curriculum)
            self.institute = Entity(
                self.graph.subjects(IDD.hasCurriculum, curriculum))
            self.institute.label = self.rdflabel(self.institute)
            self.university = Entity(
                self.graph.subjects(IDD.department, self.institute.uri))
            self.university.label = self.rdflabel(self.university)
            self.basechair = Entity(self.graph.objects(curriculum, IDD.chair))
            self.basechair.label = self.rdflabel(self.basechair)
            self.enrolledIn = int(
                next(self.graph.objects(curriculum, IDD.enrolledIn)))
            self.director = Entity(self.objects(curriculum, IDD.director))
            self.director.label = self.rdflabel(self.director)
            self.level = Entity(self.objects(curriculum, IDD.level))
            self.level.label = self.rdflabel(self.level)

            for discentry in self.graph.objects(curriculum, IDD.hasDiscipline):
                self.discentry = Entity(discentry)
                self.rdftypecheck(discentry, IDD["Discipline"])
                self.discentry.code = self.rdfdcid(self.discentry)
                self.discentry.chair = Entity(
                    self.graph.objects(discentry, IDD.chair))
                self.discentry.chair.label = self.rdflabel(
                    self.discentry.chair.uri)
                assert self.discentry.chair.label is not None

                self.discipline = Entity(
                    self.graph.objects(discentry, IDD.discipline))
                self.discipline.label = self.rdflabel(self.discipline)
                self.specialty = Entity(
                    self.graph.objects(curriculum, IDD.specialty))
                self.specialty.label = self.rdflabel(self.specialty)
                self.specialty.code = next(
                    self.graph.objects(self.specialty.uri, DCID))
                self.mural = Entity(
                    self.graph.objects(curriculum, IDD.studyForm))

                self.mural.label = self.rdflabel(self.mural)

                self.profile = Entity(
                    self.graph.objects(curriculum, IDD.profile))
                self.profile.label = self.rdflabel(self.profile)

                self.setdefaults() # Must be the last one

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
        content = self.template({"ctx":self, "dsc":self.discentry})
        logger.info("Writing into '{}'".format(filename))
        o = open(filename, "w")
        o.write(content)
        o.close()


    def rdfdcid(self, subj):
        subj = uri(subj)
        return safenext(self.graph.objects(subj, DCID))

    def rdflabel(self, subj):
        subj = uri(subj)
        return safenext(self.graph.objects(subj, RDFS.label))

    def rdfinst(self, class_):
        return safenext(self.rdfinsts(class_))

    def rdfinsts(self, class_):
        return self.graph.subjects(RDF.type, class_)

    def rdftypecheck(self, subj, type_):
        subj = uri(subj)
        if (subj, RDF.type, type_) not in self.graph:
            raise AssertionError("{} is not of type {}".format(subj, type_))

    def objects(self, subj, pred):
        subj = uri(subj)
        return self.graph.objects(subj, pred)

    def subjects(self, pred, obj):
        return self.graph.subjects(pred, obj)

    # def __getitem__(self, index):
    #     return self

    def setdefaults(self):
        self.city="Иркутск"
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

    G = CurriculumGraph(filename)
    G.gendir()
