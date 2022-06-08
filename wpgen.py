from common import *
from rdflib import Literal, Namespace, Graph, URIRef
from kg import *
import os.path
import types
from pybars import Compiler
from pprint import pprint

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
CTX = {}
RCTX = {}


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


class Assignment:

    def __init__(self, context, name=None):
        self.name = name
        self.context = context

    def __str__(self):
        return self.context.renderpath() + " = " + str(self.name)

    def renderpath(self):
        return self.__str__()

    def get(self, index, default=None):
        if self.name is None:  # Definition phase
            self.name = index
            return self
        elif self.name == index:
            return self.context
        else:
            logger.error("Cannot resolve assignment '{} {}'".format(self, index))
            return None


class Context():

    def __init__(self,
                 uri=None,
                 typeof=None,
                 prev=None,
                 op=None,
                 forward=None):
        if isinstance(uri, types.GeneratorType):
            self.gen = uri
            uri = next(uri)
        self.uri = uri
        self.typeof = typeof
        self.prev = prev
        self.op = op
        self.forward = forward

    def __str__(self):
        uri = self.uri
        if isinstance(uri, types.GeneratorType):
            uri = next(uri)
        val = str(uri)
        return r"\rdf{" + self.renderpath() + "}{" + val + "}"

    def renderpath(self):
        global RCTX
        s = ""
        if self.prev is not None:
            if self.op is not None:
                if self.forward:
                    oop = r""
                else:
                    oop = r"^"
                s += self.prev.renderpath() + " " + oop + self.op
        else:
            uri = self.uri
            suri = str(uri)
            if suri in RCTX:
                uri = RCTX[suri]
            else:
                uri = repr(uri).replace("rdflib.term.", "").replace("'", "|")
            s = r"\ctx{" + uri + "}"

        return s

    def get(self, index, default=None):
        if index == "=":
            return Assignment(context=self)
        if ":" in index:
            pref, ns, pred = index.split(":")
            # print(pref, ns, pred)
            nspred = NS[ns][pred]
            pobj = True
            if '^' in pref:
                pobj = False
                o = G.subjects(nspred, self.uri)
            else:
                o = G.objects(self.uri, nspred)
            if o is not None:
                try:
                    return Context(o,
                                   prev=self,
                                   op=ns + ":" + pred,
                                   forward=pobj)
                except StopIteration:
                    print("{} {} (no results)".format(self, index))
                    return ""
            else:
                return default
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

        # Add any special helpers
    def _each(self, this, options, context):
        result = []
        if isinstance(context, Context):
            result.append(r"\begin{rdfctx}{" + context.renderpath() + "}")
        result.extend(options['fn'](context))
        if hasattr(context, "gen"):
            for thing in context.gen:
                result.extend(options['fn'](Context(thing)))
        if isinstance(context, Context):
            result.append(r"\end{rdfctx}")
        return result

    def _defcontext(self, this, options):
        # print(this, options)
        answer = ["%\n"]
        answer.append(r"\rdf{%" + "\n")
        for name, val in this.context.items():
            if val.uri is not None:
                answer.append(r"\rdfsetctx{" + name + "}{" +
                              repr(val.uri).replace("rdflib.term.", "") +
                              "}%" + "\n")
        return answer + ["}{}%\n"]

    def _with(self, this, options, context):
        result = []
        if isinstance(context, Context):
            result.append(r"\begin{rdfctx}{" + context.renderpath() + "}")
        result.append(options['fn'](context))
        if isinstance(context, Context):
            result.append(r"\end{rdfctx}")
        return result

    def _let(self, this, options, context):
        result = []
        print("CTX", type(context))

        if isinstance(context, Assignment):
            prevroot = {}
            root = options["root"]
            prevroot.update(root)
            root[context.name] = context.context
            result.append(r"\begin{rdfctx}{\rdfsetctx{" + context.name + "}{" +
                          context.context.renderpath() + "}}")
        result.append(options['fn'](context))
        if isinstance(context, Assignment):
            del root[context.name]
            root.update(prevroot)
            result.append(r"\end{rdfctx}")

        return result

    def genwp(self):
        global CTX, RCTX
        filename = asdirname(self.discentry.code) + "-" + asdirname(
            self.discipline.label) + ".tex"
        CTX = {
            "context": self,
            "curr": self.curriculum,
            "disc": self.discentry
        }
        RCTX = {str(v.uri): k for k, v in CTX.items()}
        RCTX[None] = "_"
        content = TEMPLATE(CTX,
                           helpers={
                               "rdfeach": self._each,
                               "defcontext": self._defcontext,
                               "rdflet": self._let,
                               "rdfwith": self._with,
                           })
        logger.info("Writing into '{}'".format(filename))
        o = open(filename, "w")
        o.write(content)
        o.close()
        # quit()

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
