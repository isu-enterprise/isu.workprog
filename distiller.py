from rdflib import URIRef, Namespace, Graph, Literal, BNode
from common import *
from lxml.html import etree
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(format='%(levelname)s:%(module)s:%(message)s',
                    level=logging.DEBUG)

def distill(uri, html, idgen=BNode):
    tree = etree.HTML(html)
    g = Graph()
    binds(g)
    nsm = g.namespaces()
    NS = {ns: ur for ns, ur in nsm}
    # print(NS["wpdd"])

    def ext(definition):

        if isinstance(definition, (URIRef, BNode, Literal)):
            return definition

        definition = definition.strip()
        a = definition.split(":", maxsplit=1)

        if definition.startswith("http://") or \
             definition.startswith("https://") or \
             definition.startswith("file:/"):
            return URIRef(definition)
        elif len(a) > 1:
            pr, rest = a
            ns = NS.get(pr, None)
            if ns is None:
                logger.error("Unknown namespace '{}'".format(pr))
                ns = pr + ":"
            return URIRef(ns + rest)
        else:
            return g.absolutize(definition)

    def gen(subj, pred, obj):
        g.add((ext(subj), ext(pred), ext(obj)))
        # print("<{} {} {}>".format(subj, pred, obj))
        # print("<{} {} {}>".format(ext(subj), ext(pred), ext(obj)))

    def node(element, subj):
        # <subj, pred, obj>
        pred = []
        rev = []
        obj = None
        types = []
        kwargs = {}
        attrs = element.attrib

        if isinstance(element, etree._Comment):
            return

        # print(element, element.attrib)

        if "lang" in attrs:
            kwargs["lang"] = attrs["lang"]
        if "datatype" in attrs:
            kwargs["datatype"] = attrs["datatype"]

        if "property" in attrs:
            pred = attrs["property"].strip().split()
        elif "rev" in attrs:
            rev = attrs["rev"].strip().split()

        if "typeof" in attrs:
            types = attrs["typeof"].strip().split()

        if "about" in attrs:
            obj = ext(attrs["about"])
        elif "resource" in attrs:
            obj = ext(attrs["resource"])
        elif "href" in attrs:
            obj = URIRef(attrs["href"])
        elif types and obj is None:
            obj = idgen()
        elif "content" in attrs:
            obj = Literal(attrs["content"], **kwargs)
        elif element.text is not None:
            obj = Literal(element.text, **kwargs)
        if obj is not None and (pred or rev):
            for t in types:
                gen(obj, RDF.type, t)
            for p in pred:
                gen(subj, p, obj)
            for p in rev:
                gen(obj, p, subj)

        if ((pred or rev) and types) or "about" in attrs:
            subj = obj

        for e in element.iterchildren():
            node(e, subj)

    subj = URIRef(uri)
    node(tree, subj)

    return g


TEST = """<div property="wpdd:itemList" typeof="wpdd:ItemList wpdd:QuestionList" class="item-list">
          <ol id="listeditor-Question">
            <li class="edit-itemlist" rev="schema:member" typeof="wpdd:ListItem wpdd:Question">
              <div property="rdfs:label" lang="ru" class="edit-list-label" contenteditable="true">Ответ</div>
            </li>
          <li class="edit-itemlist" rev="schema:member" typeof="wpdd:ListItem wpdd:Question">
              <div property="rdfs:label" lang="ru" class="edit-list-label" contenteditable="true">2Ответ</div>
            </li><li class="edit-itemlist" rev="schema:member" typeof="wpdd:ListItem wpdd:Question">
              <div property="rdfs:label" lang="ru" class="edit-list-label" contenteditable="true">Ответ3</div>
            </li><li class="edit-itemlist" rev="schema:member" typeof="wpdd:ListItem wpdd:Question">
              <div property="rdfs:label" lang="ru" class="edit-list-label" contenteditable="true">Ответ5</div>
            </li><li class="edit-itemlist" rev="schema:member" typeof="wpdd:ListItem wpdd:Question">
              <div property="rdfs:label" lang="ru" class="edit-list-label" contenteditable="true">Ответ4</div>
            </li><li class="edit-itemlist" rev="schema:member" typeof="wpdd:ListItem wpdd:Question">
              <div property="rdfs:label" lang="ru" class="edit-list-label" contenteditable="true">Ответ4</div>
            </li></ol>
          <!-- Кнопки -->
        </div>"""

WPURI = WPDD["123434587195871958734"]

if __name__ == "__main__":
    g = distill(WPURI, TEST, idgen=lambda: genuuid(WPDB))
    g.serialize(destination="distil.ttl", encoding="utf8", format="turtle")
