from lxml import etree
import re
from pprint import pprint
from rdflib import (Graph, BNode, Namespace, RDF, RDFS, Literal, DCTERMS, FOAF)
from uuid import uuid1
from itertools import pairwise
from collections import OrderedDict
from common import (WPDB, WPDD, DBR, IDB, IDD, SCH, CNT, genuuid, DCID, IDD, IDB,
                    DCTERMS, IMIT, MURAL, EXMURAL, BACHOLOIR, ACBACH, APPLBACH,
                    MASTER, NUMBERRE, COMPETENCERE, REQDESCRRE, BULLETS, found,
                    alltext, anywords, allwords, splitnumber, startswithnumber,
                    listitem, binds)

from kg import (DEPARTMENTS_KG, REFERENCES_KG, DISCIPLINES_KG, update, preparegraphs,
                urilabel, loadallkgs, saveallkgs, STANDARDS_KG, getfrom)

G = Graph()
CDC = BNode()

WP = genuuid(WPDB)
binds(G)


class Style:

    def __init__(self, id, size, family, color="#000000"):
        self.id = id
        self.size = size
        self.family = family
        self.color = color
        self.process()

    def process(self):
        """LRIIJL+TimesNewRoman,Bold  -> font = Times, bold=True, italic=False, strake=False,
           WLDDDC+Times-Bold
        """
        # self.family
        # .split,
        #  r"([A-Z][a-z]*)"
        self.font = None
        self.bold = False
        _, rest = self.family.split("+", maxsplit=1)
        m = re.search(r'([A-Z][a-z]*)', rest)
        self.font = m.group(1)

        _, e = m.span()
        rest = rest[e:]
        # print("BEFORE BOLD:", rest)

        m = re.search(r'[Bb]old', rest)
        self.bold = m is not None
        m = re.search(r'[Ii]talic', rest)
        self.italic = m is not None
        m = re.search(r'[Ss]tre', rest)
        self.streak = m is not None

    def __str__(self):
        return "Style(id={},{},{},b={},i={},s={},{},{})".format(
            self.id, self.size, self.font, self.bold, self.italic, self.streak,
            self.color, self.family)


def printel(el):
    print("<{} {}>{}</{}>".format(el.tag, el.attrib, el.text, el.tag))


def debugsave(node, filename):
    o = open(filename, "wb")
    o.write(etree.tostring(node, encoding="utf8"))
    o.close()


def orphanite(node):
    node.getparent().remove(node)
    return node


def pairs(iterable):
    _ = (e for e in iterable)

    try:
        while True:
            a = next(_)
            b = next(_)
            yield a, b
    except StopIteration:
        pass


def can_merge(o1, o2):
    if o1.get("font") == o2.get("font"):
        return True

    # for a in ['bold', 'italic', 'strike', 'fontname', 'color']:
    for a in ['fontname', 'color']:
        if o1.get(a) != o2.get(a):
            return False

    return True


def mergesz(o1, o2, name, less=False, add=False):
    s1 = int(o1.get(name))
    s2 = int(o1.get(name))
    if add:
        s1 += s2
    elif less:
        s1 = min(s1, s2)
    else:
        s1 = max(s1, s2)
    o2.attrib[name] = str(s1)


def merge(o1, o2):
    global WP

    def mv():
        for e in o2:
            o1.append(e)

    # Merge sizes
    mergesz(o1, o2, "height")
    mergesz(o1, o2, "bottom")
    mergesz(o1, o2, "top", less=True)
    mergesz(o1, o2, "size")
    mergesz(o1, o2, "width", add=True)

    # >foo< | >bar<>< | => >foobar<><
    if o1.text is not None and len(o1) == 0:
        o1.text += o2.text if o2.text is not None else ""

    # >foo<><
    elif len(o1) != 0:
        # ...| >bar<>< |=> >foo<>bar<><
        e = o1[-1]
        if e.tail is None:
            e.tail = ""
        e.tail += o2.text if o2.text is not None else ""
        if e.tail == "":
            e.tail = None

    # o1.text is None and len(o1) == 0, i.e. o1 is empty
    mv()


def conv(filename):
    tree = etree.parse(filename)
    stylenodes = tree.xpath('//fontspec')
    styles = {}
    for style in stylenodes:
        # print(style.get('id'), style.get("family"))                                                             #<text top="157" left="493" width="4" height="13" font="0" <fontspec id="0" size="17" family="CWXMBY+Times-Bold" color="#000000"/>
        _id = style.get("id")
        attrs = style.attrib
        s = Style(**attrs)
        styles[_id] = s
    # for _id, style in styles.items():
    #     print("{}={}".format(_id, style))

    lines = tree.xpath('//text')
    for line in lines:
        _id = line.get("font")
        s = styles[_id]
        a = line.attrib
        a['bold'] = "1" if s.bold else "0"
        a['italic'] = "1" if s.italic else "0"
        a['strike'] = "1" if s.streak else "0"
        a['fontname'] = s.font
        a['size'] = s.size
        a['color'] = s.color
        a['bottom'] = str(int(a['top']) + int(a['height']))

    lines = tree.xpath('//text[@bold="1"]')

    # массив нижних линий, что-то выше 2/3 вверх, остальное вниз pt линии не принадлежит

    pages = tree.xpath("//page")

    rope = -1000
    wall = None
    node = None
    for page in pages:
        nodes = {}
        for tag in page:
            if tag.tag == "text":

                bot = int(tag.get("bottom"))
                size = int(tag.get("size"))
                ok = False
                d = bot - rope
                if d > 0:
                    ok = d < 0.33 * size
                else:
                    d = -d
                    ok = d < 0.66 * size

                if ok:
                    wall = int(tag.get("left")) + int(tag.get("width"))
                    n = nodes[node]
                else:
                    wall = None
                    rope = bot
                    node = etree.Element("div")
                    # print("Addpending", node, page);
                    n = nodes.setdefault(node, [])

                n.append(tag)
                # for child in tag:
                #    node.append(child)

            tag.getparent().remove(tag)
        for k, texts in nodes.items():

            def _(x):
                return int(x.get("left"))

            texts.sort(key=_)  # Sort by the left side position
            for t in texts:
                t.tag = "span"
                k.append(t)
        for node in nodes.keys():
            page.append(node)

    pages = tree.xpath("//page")
    for p in pages:
        p.tag = "section"
    doc = tree.xpath("//pdf2xml")
    for p in doc:
        p.tag = "body"

    # Change empty <div><span>...</span><div>, where ... is empty to <p/>
    divs = tree.xpath("//div")
    for div in divs:
        t = div.xpath('string()').strip()
        if t == "":
            for e in div[1:]:
                div.remove(e)
            span = div[0]
            span.tag = "p"
            span.text = None
            attrs = {}
            attrs.update(span.attrib)
            span.clear()
            span.attrib.update(attrs)
            div.attrib["par"] = "1"

    # Here we have sets of runs, now join them as html strings

    divs = tree.xpath("//div")

    for div in divs:
        pspan = None
        for span in div:
            if pspan is None:
                pspan = span
                continue
            if can_merge(pspan, span):
                merge(pspan, span)
                div.remove(span)
                continue
            pspan = span

    # Join <b>foo</b><b>bar</b> -> <b>foobar</b>
    divs = tree.xpath("//div/span")
    for div in divs:
        pe = None
        for e in div:
            if pe is None:
                pe = e
                continue
            if pe.tag == e.tag:
                pe.text += e.text
                e.getparent().remove(e)
                continue
            pe = p

    #Paragraph: join lines

    # Recognize paragraphs by indents: indent is the shift of "left" > "size" of font

    secs = tree.xpath("//section")
    for sec in secs:
        left = int(sec.get("width")) - int(sec.get("left"))
        for div in sec:
            if div.tag == "div":
                l = int(div[0].get("left"))
                if left > l:
                    left = l
        for div in sec:
            if div.tag == "div":
                for span in div:
                    sz = int(span.get("size"))
                    l = int(span.get("left"))
                    if l - sz >= left:
                        span.attrib["indent"] = "1"

    # Split the first page into a subtree

    titlepage = tree.xpath("//section")[0]
    titlepage.getparent().remove(titlepage)
    TITLEPAGE = titlepage
    del titlepage

    # Now we can remove sections/pages

    bodies = tree.xpath("//body")
    for body in bodies:
        ndivs = []
        for sec in body:
            for e in sec:
                ndivs.append(e)
        body.clear()
        for d in ndivs:
            body.append(d)
        del ndivs

    # # Join divs with spans staring at the same "left" value,
    # # The second span must start with a lower case letter
    # # first check if there is div with more than one span

    divs = tree.xpath("//div")
    _dc = False
    for div in divs:
        if len(div) > 1:
            _dc = True
            printel("-->", div)
            for e in div:
                printel(e)
            print
    assert not _dc, "Found non-joined spans in a div"

    # Remove DIVS at all
    divs = tree.xpath("//div")
    spans = []
    for div in divs:
        for e in div:
            spans.append(e)

    bodies = tree.xpath("//body")
    for body in bodies:
        body.clear()
        for span in spans:
            body.append(span)

    # Joinig itself # Span starting with a number stops joining
    spans = tree.xpath("/body/*")
    pspan = None
    for span in spans:
        if span.tag != "span":
            pspan = None
            continue
        if pspan is None:
            pspan = span
            continue
        if pspan.get("left") == span.get("left"):
            t = alltext(span)
            tag, name = listitem(t)
            if not tag:
                merge(pspan, span)
                span.getparent().remove(span)
                pspan.attrib["par"] = "rest"  # Sign that the join is a
                continue  # paragraph body

        pspan = None

    # Clear empty <p/> nodes
    for p in tree.xpath("//p"):
        t = p.xpath("string()").strip()
        if t == "":
            p.clear()
    # <p/><p/> -> <p/>
    pp = None
    for e in tree.xpath("/body/*"):
        if e.tag != "p":
            pp = None
            continue
        if pp is None:
            pp = e
            continue
        if pp is not None:
            e.getparent().remove(e)

    # Merge "par" = "rest" spans to a span with "ident"="1"
    spans = tree.xpath("/body/*")
    pspan = None
    for span in spans:
        if span.tag != "span":
            pspan = None
            continue

        if span.get("indent", None) == "1":
            pspan = span
            continue

        if True:  #span.get("par", None) == "rest":

            if pspan is not None:
                merge(pspan, span)
                span.getparent().remove(span)
                pspan.tag = "p"
                pspan.attrib["indent"] = "1"
                pspan = None
                continue
            else:
                span.tag = "p"
                span.attrib["indent"] = "0"
                pspan = None
                continue

        pspan = None

    # Paragraph having "bold" and text staring from number -> <hX>

    for p in tree.xpath('//p[@bold="1"]'):
        t = p.xpath("string()").strip()
        num, title = splitnumber(t)
        if num is not None:
            p.clear()
            nums = num.split('.')
            p.tag = "h" + str(len(nums))
            p.text = title
            p.attrib["section"] = num

    # split text by sections
    SECTIONS = {"_": etree.Element("section")}
    csec = SECTIONS["_"]
    for e in tree.xpath("/body/*"):
        if e.tag.startswith("h1"):
            num = e.get("section")
            csec = SECTIONS[num] = etree.Element("section")
            csec.attrib["number"] = num
            name = e.xpath("string()").strip()
            csec.attrib["title"] = name
            csec.attrib["level"] = "1"
        csec.append(e)
    # TODO: subsections... h2, etc.

    G.add((WP, RDF.type, DBR["Syllabus"]))
    # G.add((WP, RDF.type, IDD['Discipline']))
    G.add((WP, WPDD['courseDC'], CDC))

    for secnum, sec in SECTIONS.items():
        procsec(secnum, sec)

    tree = etree.Element("html", lang="ru")
    body = etree.SubElement(tree, "body")
    header = etree.SubElement(body, "header")
    proctitlepage(TITLEPAGE)
    header.append(TITLEPAGE)
    for k, v in SECTIONS.items():
        body.append(v)

    ofilename = "m-" + filename + ".html"
    o = open(ofilename, "wb")
    o.write(b"<!DOCTYPE html >\n")
    o.write(etree.tostring(tree, encoding="utf-8", pretty_print=True))
    o.close()

    G.serialize(destination=filename + ".ttl")


# INSTITUTES = {"институтматематикииинформационныхтехнологий": IMIT}


def upfirst(s):
    return s[0].upper() + s[1:]


MURALFORM = {
    "заочная": EXMURAL,
    "очная": MURAL,
}


def proctitlepage(titlepage):
    for span in titlepage.xpath('.//div/span[@bold="1"]'):
        n = span.getparent().getnext()
        if n.tag == "div":
            removed = False
            for s in n:
                if s.get("bold") == "0":
                    removed = True
                    merge(span, s)
            if removed:
                n.getparent().remove(n)

    for s in titlepage.xpath(".//span"):
        t = s.xpath('string()').strip()
        tl = t.lower()
        tn = "".join(tl.split())
        tc = upfirst(" ".join(tl.split()))
        if tl.startswith('институт'):
            inst = tn
            inst = getfrom(DEPARTMENTS_KG, tc, IDB,
                           (IDD["Faculty"], IDD["Institute"]))
            G.add((WP, WPDD.institute, inst))
        elif tl.startswith("кафедра"):
            chair = getfrom(DEPARTMENTS_KG, tc, IDB, IDD['Chair'])
            G.add((WP, WPDD.chair, chair))
        elif tn.startswith("направлениеподготовки"):
            tcl = tc.split(" ", maxsplit=3)
            _, _, code, name = tcl
            spec = getfrom(
                DISCIPLINES_KG, upfirst(name), IDB, IDD["Speciality"],
                lambda subj: DISCIPLINES_KG.add((subj, DCID, Literal(code))))
            G.add((WP, IDD.specialty, spec))
        elif tn.startswith("направленность"):
            name = s[-1].tail.strip()
            spec = getfrom(DISCIPLINES_KG, name, IDB, IDD["Discipline"])
            G.add((WP, IDD.profile, spec))
        elif tn.startswith("квалификация"):
            if found(tn, 'бакалавр'):
                if found(tn, 'академ'):
                    G.add((WP, IDD.level, ACBACH))
                elif found(tn, 'прикладн'):
                    G.add((WP, IDD.level, APPLBACH))
                else:
                    G.add((WP, IDD.level, BACHOLOIR))
            elif fond(tn, 'магистрату'):
                G.add((WP, IDD.level, MASTER))
            else:
                print("WARNING: Неизвестный уровень подготовки", tc)
        elif tn.startswith("формаобучения"):
            _, _, stform = tc.split(" ")
            G.add((WP, IDD.studyForm, MURALFORM[stform]))
        elif tn.startswith("рабочаяпрограмма"):
            # TODO try parse string after, as it can be not be bold
            ss = s.getparent()
            while (True):
                ss = ss.getnext()
                if ss is None:
                    break
                name = ss.xpath("string()").strip()
                if name != "":
                    break
            name = " ".join(name.split())
            code, nname = name.split(" ", maxsplit=1)
            if found(code, "."):
                n = nname
            else:
                n = name

            disc = getfrom(DISCIPLINES_KG, n, IDB, IDD["Discipline"])
            G.add((WP, DCTERMS.identifier, Literal(code, lang="ru")))
            G.add((WP, IDD.discipline, disc))

        elif tn.startswith("иркутск"):
            cityn, year = tc.split()[:2]
            G.add((WP, IDD.issued, Literal(year)))

            city = getfrom(DEPARTMENTS_KG, cityn, IDB, DBR['City'])
            G.add((WP, IDD.city, city))

        # TODO: Рабочая программа дисциплины ..


AIMRE = re.compile(r"[Зз]адач[аи].*")


def procaims(section):
    title = section.get("title", "")
    tl = title.lower().strip()
    num = section.get("number")
    assert allwords(tl, "цел", "задач"), "Assertion:" + tl
    for p in section.xpath("//p"):
        t = p.xpath("string()").strip()
        tl = t.lower()
        if tl.startswith('цел'):
            G.add((CDC, WPDD["aim"], Literal(t, lang="ru")))
            continue
        if tl.startswith('задач'):
            G.add((CDC, WPDD["problem"], Literal(t, lang="ru")))
            continue
        if t == "":
            orphanite(p)


def proclistitems(paragraphs,
                  owner=None,
                  otype=None,
                  itemtype=None,
                  removeempty=False):
    ol = None
    owners = []
    if owner is not None:
        owners.append((owners, None))

    if itemtype is None:
        itemtype = WPDD["ListItem"]
    for p in paragraphs:
        t = alltext(p)
        if t == "":
            if removeempty:
                orphanite(p)
            continue

        num, name = listitem(t)

        if num is None:
            ol = None
            p.attrib["li-ignored"] = "1"
            # print ("IGN:", t)
            continue

        if name.strip() == "":
            continue

        if ol is not None:
            fl = num[0]
            if fl.isdigit() or fl in BULLETS:
                pass
            else:
                ol = None
                owner = None

        if ol is None:
            par = p.getparent()
            if num[0].isdigit():
                ol = etree.Element("ol")
            elif num in BULLETS:
                ol = etree.Element("ul")
            else:  # a), b), c) ...
                ol = None
            if ol is not None:
                index = par.index(p)
                par.insert(index, ol)
                ol.text = "\n"
                ol.tail = "\n"
            if otype is not None:  # we store data in the graph
                if owner is None:
                    owner = WPDB[genuuid()]
                    G.add((owner, RDF.type, otype))
                    # TODO: define a kind of question list
                    G.add((WP, WPDD.itemList, owner))
                    owners.append((owner, p))
        if ol is not None:
            p.tag = "li"
            p.clear()
            p.text = name
            p.tail = "\n"
            p.attrib["item"] = num
            orphanite(p)
            ol.append(p)
        if owner is not None and ol is not None:
            q = genuuid(WPDB)
            G.add((q, RDF.type, itemtype))
            G.add((q, RDFS.label, Literal(name, lang="ru")))
            G.add((q, SCH.sku, Literal(num)))
            G.add((q, SCH.member, owner))
    return owners


def proctestsection(section):
    ps = section.xpath(".//p")
    owners = proclistitems(ps,
                           otype=WPDD["QuestionList"],
                           itemtype=WPDD["Question"])
    owner = owners[0]
    if owner is not None:
        G.add((owner[0], RDF.type, WPDD["EvaluationMean"]))

    for p in section.xpath(".//p"):
        t = alltext(p, normalize=True)
        tl = t.lower()
        if allwords(tl, "разработчик"):
            _, name = t.split(":")
            name = name.strip()
            author = getfrom(DEPARTMENTS_KG, name, IDB, FOAF["Person"],
                             lambda subj: DEPARTMENTS_KG.add((subj, FOAF.name,
                                                              Literal(name, lang="ru"))))
            G.add((CDC, SCH.author, author))


def procstudysupport(section):
    pp = None
    for p in section.xpath(".//p"):
        t = alltext(p)
        if t == "":
            orphanite(p)
            continue
        num, rest = splitnumber(t)
        if num is not None:
            pp = p
        else:
            if pp is not None:
                merge(pp, p)
                orphanite(p)
                continue
            pp = p
    owners = proclistitems(section.xpath(".//p"),
                           otype=WPDD["ReferenceList"],
                           itemtype=WPDD["Reference"])
    for owner, p in owners:  # Classify reference lists
        if p is None:
            continue
        t = alltext(p)
        typ = None
        if allwords(t, "основн литератур"):
            typ = "BasicReferences"
        elif allwords(t, "дополнительн литератур"):
            typ = "AuxiliaryReferences"
        elif allwords(t, "баз данн") or allwords(t, "информационн справочн"):
            typ = "ElectronReferences"
        else:
            print("WARNING: неизвестный тип списка литературы '{}'".format(t))
        if typ is not None:
            G.add((owner, RDF.type, WPDD[typ]))
            p.attrib.clear()
            p.attrib["kind"] = typ


def proccontentsection(section):
    pi = None
    lihappend = False

    for p in section.xpath(".//p"):
        t = alltext(p).lower()
        indent = p.get("indent", "0") == "1"
        if indent:
            pi = p
            continue
        if t == "":
            p.getparent().remove(p)
            pi = None
            continue

        code, title = listitem(t)

        if code is not None:
            lihappend = True
            pi = p
            continue

        if pi is not None:
            merge(pi, p)
            orphanite(p)
        else:
            pi = p  # A paragraph without indent

    # This is not necessary
    if lihappend:
        owners = proclistitems(section.xpath(".//p"))

    # split text by sections
    sections = {"_": etree.Element("section")}
    csec = sections["_"]
    for e in section.xpath("./*"):
        if e.tag.startswith("h"):
            num = e.get("section")
            csec = sections[num] = etree.Element("section")
            csec.attrib["number"] = num
            name = alltext(e)
            csec.attrib["title"] = name
            csec.attrib["level"] = "2"
            orphanite(e)
        csec.append(e)
    for num, sec in sections.items():
        t = alltext(sec)
        if t != "":
            procsec(num, sec)  # Recursive
            section.append(sec)


def proccontentsection2(section):  # Level = 2

    def _val(m, group=1):
        v = m.group(group).rstrip(".")
        if found(v, '.'):
            v = float(v)
        else:
            v = int(v)
        return v

    for p in section.xpath("./p"):
        t = alltext(p).lower()
        if allwords(t, "объем дисциплин составл"):
            m = re.search(r"(\d|\.)+\s+(зачетн|зе|з\.е\.)", t)
            if m is None:
                print("WARNING: не распознаны з.е. '{}'".format(t))
            else:
                G.add((WP, WPDD.credit, Literal(_val(m))))

            m = re.search(r"(\d+|\.)\s+(час|ч\.)", t)
            if m is None:
                print("WARNING: не распознаны часы '{}'".format(t))
            else:
                G.add((WP, WPDD.hours, Literal(_val(m))))

        elif allwords(t, "форм промежуточн аттестац"):
            pass


def proccourlocation(section):
    BN = BNode()
    G.add((WP, WPDD.location, BN))
    for p in section.xpath(".//p"):
        t = alltext(p, normalize=True)
        if anywords(t, "предшеств последующ"):
            pred = WPDD.require if allwords(t, "предшеств") else WPDD.ensure
            _, disc = t.rsplit(":", maxsplit=1)
            disc = disc.rsplit(".")[0]
            if found(disc, ";"):
                discs = disc.split(";")  # Suppose disciplines having ','
            else:  # in their titles
                discs = disc.split(',')
            for disc in discs:
                D = WPDB[genuuid()]
                G.add((BN, pred, D))
                G.add((D, RDFS.label, Literal(disc.strip(), lang="ru")))
            continue
        if t == "":
            orphanite(p)


REQDICT = {
    "знать": WPDD.know,
    "уметь": WPDD.ableTo,
    "владеть": WPDD.posess,
}


def procresultsrequirements(section):
    for p in section.xpath(".//p"):
        t = alltext(p, normalize=True)
        tl = t.lower()
        if anywords(tl, "компетенц"):
            m = re.split(COMPETENCERE, t)
            if m is None:
                print("WARNING: Compenence not found '{}'".format(t))
            else:
                matches = m[1:]
                for code, title in pairs(matches):
                    title = title.strip()
                    if title[-1] in [',', '.', ';']:
                        title = title[:-1]
                    C = getfrom(DISCIPLINES_KG, title, IDB, IDD["Compenence"])
                    G.add((CDC, IDD.competence, C))
                    G.add((C, DCTERMS.identifier, Literal(code, lang="ru")))
            continue
        elif anywords(tl.lower(), "знать уметь владеть"):
            m = re.split(REQDESCRRE, t)
            m = m[1:]
            for verb, descr in pairs(m):
                descr = descr.strip().lstrip(":")
                for ch in ":;.":
                    descr = descr.rstrip(ch)
                descr = descr.strip()
                C = genuuid(WPDB)
                pred = REQDICT[verb]
                G.add((CDC, pred, C))
                G.add((C, RDFS.label, Literal(descr, lang="ru")))


def procstudycontent(section):
    # Here we have p, ol, ul and li items
    # P supposed to be higher level topics starting with
    # Тема _.
    # Раздел _.
    # _.
    # TODO: All other elements (texts in the bodies of tags)
    # are located by their hierarchy number.
    h = OrderedDict()
    ph = h

    for e in section.xpath(".//*[self::p or self::li]"):
        t = alltext(e)
        if e.tag == "p":
            # REPEAT: Suppose p be the higher hierarchy member
            num, title = splitnumber(t)
            if num is not None:
                title = title.strip()
                e.clear()
                e.text = title
                e.attrib["item"] = num
                e.tail = "\n"
                ph = OrderedDict()
            else:
                print(
                    "WARNING: Unrecognized element of structure: '{}'".format(
                        t))
                continue
            h[num] = (title, ph)
        else:  # li
            num = e.get("item")
            title = t
            ph[num] = (title, None)

    def _(d, p):
        for k, v in d.items():
            t, sub = v
            BN = BNode()
            G.add((p, WPDD.content, BN))
            G.add((BN, RDF.type, WPDD["Topic"]))
            G.add((BN, RDFS.label, Literal(t, lang="ru")))
            G.add((BN, SCH.sku, Literal(k)))
            if sub is not None:
                _(sub, BN)

    _(h, WP)


def procsrscontent(section):
    text = etree.tostring(section, encoding=str)
    C = genuuid(WPDB)
    G.add((WP, WPDD.independentWork, C))
    G.add((C, CNT.chars, Literal(text, lang="ru")))
    G.add((C, RDF.type, CNT["ContentAsText"]))
    G.add((C, RDF.type, WPDD["IndependedWorkContent"]))


def procsec(number, section):
    level = section.get("level", None)
    if section.tag == "section":
        if number == "_":
            return
        title = section.get("title", "")
        title = title.lower()
        if allwords(title, "цел задач"):
            procaims(section)
        elif allwords(title, "материал текущ контрол аттестац"):
            proctestsection(section)
        elif allwords(title, "содержан структура дисциплин"):
            if level == "1":
                proccontentsection(section)
            elif level == "2":
                proccontentsection2(section)
        elif allwords(title, "учебн методическ информацион обеспечен"):
            procstudysupport(section)
        elif allwords(title, "мест дисциплин структур опоп"):
            proccourlocation(section)
        elif allwords(title, "требован результат дисциплин"):
            procresultsrequirements(section)
        elif allwords(title, "содержан учебн матер"):
            procstudycontent(section)
        elif allwords(title, "указан самостоятельн работ"):
            procsrscontent(section)
        else:
            print("WARNING: Did not process '{}'".format(title))


if __name__ == "__main__":
    preparegraphs()
    fn = 'a.xml'
    conv(fn)
    saveallkgs()
