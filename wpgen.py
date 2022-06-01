from common import *
from rdflib import Literal, Namespace, Graph
from kg import *
import os.path
import types

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


class CurriculumGraph():

    def __init__(self, filename, template=TEMPLATE_NAME):
        self.graph = Graph()
        self.graph.parse(filename)
        binds(self.graph)
        self.graph += STANDARDS_KG
        self.graph += DEPARTMENTS_KG
        self.graph += DISCIPLINES_KG
        self.graph += REFERENCES_KG

    def generate(self):

        for curriculum in self.rdfinsts(IDD["Curriculum"]):
            self.curriculum = Entity(curriculum)
            self.institute = Entity(
                self.graph.subjects(IDD.hasCurriculum, curriculum))
            self.institute.name = self.rdflabel(self.institute)
            self.university = Entity(
                self.graph.subjects(IDD.department, self.institute.uri))
            self.university.name = self.rdflabel(self.university)
            self.basechair = Entity(self.graph.objects(curriculum, IDD.chair))
            self.basechair.name = self.rdflabel(self.basechair)
            self.enrolledIn = int(
                next(self.graph.objects(curriculum, IDD.enrolledIn)))
            for discentry in self.graph.objects(curriculum, IDD.hasDiscipline):
                self.discentry = Entity(discentry)
                self.rdftypecheck(discentry, IDD["Discipline"])
                self.discentry.code = self.rdfdcid(self.discentry)
                self.discentry.chair = Entity(
                    self.graph.objects(discentry, IDD.chair))
                self.discentry.chair.name = self.rdflabel(
                    self.discentry.chair.uri)
                assert self.discentry.chair.name is not None

                self.discipline = Entity(
                    self.graph.objects(discentry, IDD.discipline))
                self.discipline.name = self.rdflabel(self.discipline)
                self.specialty = Entity(
                    self.graph.objects(curriculum, IDD.specialty))
                self.specialty.name = self.rdflabel(self.specialty)
                self.specialty.code = next(
                    self.graph.objects(self.specialty.uri, DCID))
                self.mural = Entity(
                    self.graph.objects(curriculum, IDD.studyForm))
                print(self.mural)
                self.mural.name = self.rdflabel(self.mural)

                self.profile = Entity(
                    self.graph.objects(curriculum, IDD.profile))
                self.profile.name = self.rdflabel(self.profile)

                yield self

    def gendir(self):
        for _ in self.generate():
            dir = os.path.join(
                TARGET_DIR,
                asdirname(self.university.name),
                asdirname(self.institute.name),
                asdirname(self.discentry.chair.name),
                asdirname(self.specialty.code) + "-" +
                asdirname(self.specialty.name),
                asdirname(
                    str(self.discentry.code) + "-" +
                    str(self.discipline.name)),
                asdirname(self.profile.name),
                asdirname(self.enrolledIn),
                asdirname(self.mural.name),
            )
            print(dir)
            safecwd(dir)

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


if __name__ == "__main__":
    import sys
    preparegraphs()
    if len(sys.argv) < 2:
        filename = "01.03.02-22-1234_1к_06.plx.xls.ttl"
    else:
        filename = sys.argv[1]

    G = CurriculumGraph(filename)
    G.gendir()
