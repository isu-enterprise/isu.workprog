import requests as rq
from lxml.html import parse, tostring, fromstring

DIR_BASE = "http://old.isu.ru/ru/about/programs/"

LIST = "./list.html"
LIST_URL = "http://old.isu.ru/control/jsp/show_edu_profile_list.jsp?sort=&code_filter=&direction_filter=&profile_filter=&faculty_filter=0&program_filter=undefined"

LI = open(LIST).read()
LIST_T = fromstring(LI)

#TRS=LIST_T.xpath("//tr")
#HEADER=TRS[0]
#HS=HEADER.xpath(".//th")
#print([str(H.text_content()) for H in HS])
#BODY=TRS[1:]
#print(tostring(TRS[-1],encoding=str))
BODY = LIST_T.xpath("//tbody/tr")


class Program(object):

    def __init__(self):
        self.code = None
        self.name = None
        self.profile = None
        self.load = None
        self.faculty = None
        self.mural = None
        self.year = None
        self.href = None

    def accept(self, row):
        print("ACCEPT:", row)
        self.code, self.name, self.profile, self.load, self.faculty = row

    def prog(self, href, rest):
        self.href = href
        self.mural, self.year = [t.strip() for t in rest.rsplit(',', maxsplit=1)]
        print("PROG:", href, self.mural, self.year)


PROG = Program()


def process(body, rows=0):
    global PROG
    if not body:
        return
    r = body[0]
    hr = r.xpath(".//a/@href")[0]
    load = r.xpath(".//a")[0].text_content()
    b = body[1:]
    if rows > 0:
        PROG.prog(hr, load)
        process(b, rows - 1)
    else:
        cols = r.xpath(".//td")
        try:
            rows = int(cols[0].attrib["rowspan"])
        except IndexError:
            rows = 0
        except KeyError:
            rows = 0
        txts = [c.text_content() for c in cols[1:]]
        txts = cols[0].xpath('.//text()') + txts
        PROG.accept(txts)
        PROG.prog(hr,load)
        print("ROWS:", rows)
        process(b, rows - 1)


if __name__ == "__main__":
    process(BODY)
