from lxml import etree
import re
from pprint import pprint


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
    for _id, style in styles.items():
        print("{}={}".format(_id, style))

    lines = tree.xpath('//text')
    print(len(lines))
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

    ofilename = "o-" + filename
    o = open(ofilename, "wb")
    o.write(etree.tostring(tree, encoding="utf-8"))
    lines = tree.xpath('//text[@bold="1"]')
    print(len(lines))
    # lines=tree.xpath('//text[@bold="1"]')
    for line in lines:
        # print(len(line))
        # print(etree.tostring(line,encoding=str))
        # printel(line)
        pass
    #массив нижних линий, что-то выше 2/3 вверх, остальное вниз pt линии не принадлежит

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
    ofilename = "s2-" + filename + ".xhtml"
    o = open(ofilename, "wb")
    # o.write(b"""<html>""")
    o.write(etree.tostring(tree, encoding="utf-8"))
    # o.write(b"""</html>""")
    o.close()

    #change empty <div><span>...</span><div>, where ... is empty to <p/>
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

    # Joinig itself # TODO: Kills text at headers 1., 2. etc.
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
            t = span.xpath("string()").strip()
            t = t[0]
            # if t.isalpha() and t.islower():
            if not (t.isdigit() or t in ["-"]):
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

    # Paragraph having "bold" and text staring from digit -> <hX>

    for p in tree.xpath('//p[@bold="1"]'):
        t = p.xpath("string()").strip()
        c = t[0]
        if c.isdigit():
            p.clear()
            num, _ = t.split(" ", maxsplit=1)
            nums = num.split(".")
            if nums[-1] == "":
                nums = nums[:-1]
            p.tag = "h"+str(len(nums))
            p.text = t
            p.attrib["section"] = ".".join(nums)

    # split text by sections
    SECTIONS = {"_" : etree.Element("section")}
    csec = SECTIONS["_"]
    for e in tree.xpath("/body/*"):
        if e.tag.startswith("h1"):
            num = e.get("section")
            csec = SECTIONS[num] = etree.Element("section")
            csec.attrib["number"] = num
            csec.attrib["title"] = e.xpath("string()").strip()
        csec.append(e)
    # TODO: subsections... h2, etc.

    tree = etree.Element("html", lang="ru")
    body = etree.SubElement(tree, "body")
    header = etree.SubElement(body, "header")
    header.append(TITLEPAGE)
    for k, v in SECTIONS.items():
        body.append(v)

    ofilename = "m-" + filename + ".html"
    o = open(ofilename, "wb")
    o.write(b"<!DOCTYPE html >\n")
    o.write(etree.tostring(tree, encoding="utf-8", pretty_print=True))
    o.close()


if __name__ == "__main__":
    fn = 'a.xml'
    conv(fn)
