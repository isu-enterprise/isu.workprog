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

    # Here we have sets of runs, now join them as html strings

    divs = tree.xpath("//div")

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
        if o1.text is not None and len(o1)==0:
            o1.text += o2.text if o2.text is not None else ""

        # >foo<><
        elif len(o1) != 0:
            # ...| >bar<>< |=> >foo<>bar<><
            o1[-1].tail = o2.text # if o2.text is None nothing changed

        # o1.text is None and len(o1) == 0, i.e. o1 is empty
        mv()

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

    #change empty <div><span>...</span><div>, where ... is empty to <p/>
    divs = tree.xpath("//div")
    for div in divs:
        if len(div) != 1:
            continue
        sp = div[0]
        if sp.text is None:
            if len(sp) == 1:
                el = sp[0]
                if el.text is None or el.text.strip() == "":
                    div.tag = "p"
                    div.clear()
        elif sp.text.strip() == "":
            div.tag = "p"
            div.clear()

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

    # Now we can remove sections/pages

    bodies = tree.xpath("//body")
    for body in bodies:
        ndivs=[]
        for sec in body:
            for div in sec:
                ndivs.append(div)
        body.clear()
        for d in ndivs:
            body.append(d)
        del ndivs

    # Join divs with spans staring at the same "left" value,
    # The second span must start with a lower case letter
    # first check if there is div with more than one span

    divs = tree.xpath("//div")
    _dc=False
    for div in divs:
        if len(div) > 1:
            _dc=True
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
    # spans = tree.xpath("//span")
    # pspan = None
    # nspans = []
    # for span in spans:
    #     if pspan is None:
    #         pspan = span
    #         nspans.append(span)
    #         continue
    #     if pspan.get("left") == span.get("left"):
    #         # pt = pspan.text_content()
    #         t = span.xpath('string()').strip() # Extracts all strings
    #         if True: #t[0].islower():                 # from the subtree
    #             merge(pspan, span)
    #             printel(pspan)
    #             printel(span)
    #             pspan.attrib["par"] = "rest"   # Sign that the join is a
    #             continue                       # paragraph body
    #     nspans.append(span)
    #     pspan = span

    # for body in bodies:
    #     body.clear()
    #     for span in nspans:
    #         body.append(span)

    # Merge "par" = "rest" spans to a span with "ident"="1"
    # spans = tree.xpath("//span")
    # pspan = None
    # for span in spans:
    #     if span.get("ident", None) == "1":
    #         pspan = span
    #         continue

    #     if span.get("par", None) == "rest":
    #         if pspan is not None:
    #             merge(pspan, span)
    #             span.getparent().remove(span)
    #             pspan.tag = "p"
    #             pspan = None
    #             continue
    #         else:
    #             span.tag = "p"
    #             pspan = None
    #             continue

    #     elif pspan is not None and pspan.get("ident", None) is None:
    #         # This is copied from above, just to mention
    #         # that the processing could be different
    #         if pspan is not None:
    #             merge(pspan, span)
    #             span.getparent().remove(span)
    #             # pspan.tag = "p"
    #             pspan = None
    #             continue
    #         else:
    #             span.tag = "p"
    #             pspan = None
    #             continue

    #     pspan = None


    ofilename = "m-" + filename + ".xhtml"
    o = open(ofilename, "wb")
    o.write(etree.tostring(tree, encoding="utf-8"))
    o.close()


if __name__ == "__main__":
    fn = 'a.xml'
    conv(fn)
