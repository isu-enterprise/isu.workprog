import requests as rq
from lxml.html import parse, tostring, fromstring
import os

ISU_BASE = "http://old.isu.ru/"
DIR_BASE = ISU_BASE + "ru/about/programs/"
FILE_BASE = ISU_BASE
BASE_OUT_DIR = "/mnt/bck/isu-studprogs-dowloaded"

LIST = "./list.html"
LIST_URL = "http://old.isu.ru/control/jsp/show_edu_profile_list.jsp?"\
           "sort=&code_filter=&direction_filter=&profile_filter=&faculty_filter=0&"\
           "program_filter=undefined"

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

        self.faculty = None

        # load
        self.mural = None
        self.year = None
        self.href = None

        self.root = os.getcwd()

    def accept(self, row):
        print("ACCEPT:", row)
        self.code, self.name, self.profile, _, self.faculty = row

    def prog(self, href, rest):
        self.href = href
        self.mural, self.year = [
            t.strip() for t in rest.rsplit(',', maxsplit=1)
        ]
        print("PROG:", href, self.mural, self.year)
        self.chdir()
        self.dload()

    def chdir(self):
        self.cd(self.root)
        if self.mural is not None:
            guess = 0
            p = self.mkpath(guess=guess)
            try:
                self.cd(p)
                return
            except FileNotFoundError:
                pass
            while True:
                p = self.mkpath(guess=guess)
                try:
                    os.makedirs(p)
                    break
                except FileExistsError:
                    guess += 1
                    if guess > 10:
                        raise SystemExit(1)
            self.cd(p)

    def cd(self, path):
        os.chdir(path)
        print("CD:", path)

    def mkpath(self, guess=0):
        if guess:
            guess = '-' + str(guess)
        else:
            guess = ''

        bl = BASE_OUT_DIR
        l = (self.faculty, self.code, self.name, self.profile,
             self.mural, self.year)
        l = [a[:100] for a in l]
        if guess:
            l[4] += guess
        l = [bl] + l
        s = "{}/{}/{}-{}/{}/{}/{}".format(*l)
        s = s.replace(" ", "-")
        return s

    def dload(self):
        href = DIR_BASE + "/" + self.href
        rc = rq.get(href)
        if rc.status_code == 200:
            page = fromstring(rc.text)
        else:
            raise KeyError("No Page")
        # print(tostring(page, encoding=str))
        self.process(page)
        # raise SystemExit(0)

    def process(self, page):
        # http://old.isu.ru/filearchive/edu_files/B1.V.06_Algoritmy_teorii_grafov_3700.pdf
        hrefs = page.xpath("//a/@href")
        for h in hrefs:
            href = FILE_BASE + str(h)
            href = href.strip()
            if href.endswith('pdf') or href.endswith("PDF"):
                CMD = 'wget -c -nc "{}"'.format(href)
                print("CMD:", CMD)
                os.system(CMD)
                # quit()
            else:
                print("SKIP:", href)


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
        PROG.prog(hr, load)
        print("ROWS:", rows)
        process(b, rows - 1)


if __name__ == "__main__":
    process(BODY)
