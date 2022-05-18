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
    o.write(b"""<html>""")
    o.write(etree.tostring(tree, encoding="utf-8"))
    o.write(b"""</html>""")
    o.close()
    # Here we have sets of runs, now join them as html strings


if __name__ == "__main__":
    fn = 'a.xml'
    conv(fn)
