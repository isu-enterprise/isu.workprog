from pickle import LIST
from flask import Flask, render_template, jsonify, request
from rdflib import Graph, URIRef, Literal
import logging
from pprint import pprint
from common import IDD, WPDD, WPDB, genuuid
# from distiller import distill
from pyRdfa import pyRdfa
from json import loads
import io
from jinja2 import Environment, BaseLoader

KG_FILE_NAME = "a.xml.ttl"
INDEX_HTML = 'index-copy.html'

G = Graph()
G.parse(KG_FILE_NAME)

app = Flask(__name__)

WP_URI = None


def getuuid():
    global WP_URI
    uri = list(G.query(GET_WP_URI))[0][0]
    print(uri)
    WP_URI = uri
    return uri


@app.route('/')
def main():
    global WP_URI
    print(WP_URI)
    return render_template(INDEX_HTML, WP_URI=WP_URI)


@app.route("/api/1.0/getwps")  # Get Work ProgramS
def getwps():
    answer = {"rows": [1, 2, 3], "error": 0}
    return jsonify(answer)


PREFIXES = """
PREFIX dbp: <https://dbpedia.org/page/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX idb: <http://irnok.net/ontologies/database/isu/studplan#>
PREFIX idd: <http://irnok.net/ontologies/isu/studplan#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <https://schema.org/>
PREFIX wpdb: <http://irnok.net/ontologies/database/isu/workprog#>
PREFIX wpdd: <http://irnok.net/ontologies/isu/workprog#>

"""

GET_WP_URI = PREFIXES + """

SELECT ?uuid WHERE {
    ?uuid a dbr:Syllabus .
}

LIMIT 1
"""

GET_WP_AP = PREFIXES + """

SELECT ?text
WHERE
{
    ?wpuri a dbr:Syllabus .
    ?wpuri wpdd:courseDC ?dc .
    ?dc ?pred ?text .       #@@
}

LIMIT 1

"""
GET_WP_QUEST = PREFIXES + """

SELECT ?quest ?number ?label WHERE {
    ?syll a dbr:Syllabus .
    ?syll wpdd:itemList ?itemlist .
    ?s a dbr:Syllabus .
    ?s  wpdd:itemList  ?itemlist .
    ?itemlist a wpdd:EvaluationMean .
    ?quest schema:member ?itemlist .
    ?quest schema:sku ?number .
    ?quest rdfs:label ?label  .
   }
LIMIT 1
"""

#END_OF_GETTERS

DEL_WP_AP = PREFIXES + """

DELETE
{
    ?dc ?pred ?text1 .
}
WHERE
{
    ?wpuri a dbr:Syllabus .
    ?wpuri wpdd:courseDC ?dc .
    ?dc ?pred ?text1 .
}

"""

INS_WP_AP = PREFIXES + """
INSERT
{
    ?dc ?pred ?text .
}
WHERE
{
    ?wpuri a dbr:Syllabus .
    ?wpuri wpdd:courseDC ?dc .
}

"""

GET_LIST = PREFIXES + """
SELECT ?list ?uri ?label
WHERE
{
    ?list a wpdd:ItemList .
    ?uri schema:member ?list .
    ?uri a wpdd:ListItem .
    ?uri a ?pred .
    ?uri rdfs:label ?label .
}
"""

DELETE_LIST = PREFIXES + """
DELETE
{
    ?uri schema:member ?list .
    ?uri rdfs:label ?label .
}
WHERE
{
    ?list a wpdd:ItemList .
    ?uri schema:member ?list .
    ?uri a wpdd:ListItem .
    ?uri a ?pred .
    ?uri rdfs:label ?label .
}
"""

QTEMPLATE = \
"""<div property="wpdd:itemList" typeof="wpdd:ItemList wpdd:QuestionList" class="item-list" about="{{list}}">
  <ol id="listeditor-Question">
    {% for item in bindings %}
    <li class="edit-itemlist"
      rev="schema:member" typeof="wpdd:ListItem wpdd:Question" resource="{{item.uri.value}}">
      <div
        property="rdfs:label"
        lang="ru"
        class="edit-list-label"
        contenteditable="true"
    >{{item.label.value}}</div>
    </li>
    {% endfor %}
  </ol>
</div>
"""

QUERIES = [(("aim", "problem", "requiredDisciplines"),
            [GET_WP_AP, DEL_WP_AP, INS_WP_AP], WPDD, None),
           (("Question", ), [GET_LIST, DELETE_LIST], WPDD, QTEMPLATE)]


def gettemplates(pred):
    for t, qs, ns, jt in QUERIES:
        if pred in t:
            return qs, ns[pred], jt
    return None


def create_list(quest):

    return 0


def lprint(s):
    sl = s.split("\n")
    for c, s in enumerate(sl):
        q = c + 1
        print("{} {}".format(q, s.rstrip()))


def html2list(html):
    print(html)
    return ["1", "2"]


@app.route("/api/1.0/qwp", methods=['POST'])  # Get Work ProgramS
def savewp():
    global G
    js = request.json
    pprint(js)

    op = js["op"]
    html = js.get("html", None)
    ng = Graph()

    if html is not None and op == "save":
        del js["html"]
        inf = io.StringIO(html)
        graph = pyRdfa().graph_from_source(inf)
        graph.serialize(destination="pyRdfa.ttl", format="turtle", encoding="utf8")
        # ng = distill(js["wpuri"], html, lambda: genuuid(WPDB))

    pred = js["pred"]
    queries = gettemplates(pred)
    if queries is None:
        pprint(js)
        error = {"error": 0, "msg": "Bad request to the endpoint ''"}
        pprint(error)
        pprint(js)
        return jsonify(error)

    # import pudb; pu.db

    templates, pred, jtemplate = queries
    js["pred"] = pred
    js["wpuri"] = URIRef(js["wpuri"])

    if templates is None:
        msg = "Cannot find template for '{}'.".format(js)
        logging.error(msg)
        raise RuntimeError(msg)

    if op == "save":
        queries = templates[1:]
    else:
        queries = templates[:1]

    answer = {}
    del js["op"]

    for q in queries:
        lprint(q)
        if (op == "save"):
            if "text" in js:
                js["text"] = Literal(js["text"], lang="ru")
            G.update(q, initBindings=js)
        else:
            if "text" in js:
                del js['text']
                text = list(G.query(q, initBindings=js))[0][0]
                answer["text"] = str(text)
            else:
                l = G.query(q, initBindings=js)
                i = io.BytesIO()
                l.serialize(destination=i, format='json', encoding="utf8")
                pprint(i.getvalue())
                i.seek(0, 0)
                json = loads(i.getvalue())
                if jtemplate is not None:
                    rtemplate = Environment(
                        loader=BaseLoader).from_string(jtemplate)
                    about = json["results"]["bindings"][0]["list"]["value"]
                    data = {
                        "list": about,
                        "bindings": json["results"]["bindings"]
                    }
                    data = rtemplate.render(**data)
                    answer["html"] = data
                else:
                    data = json
                    answer["json"] = data

                print(data)

    G += ng

    done = op + "ed".replace("ee", "e")
    answer.update({"wpuri": js["wpuri"], "error": 0, "msg": op + "ed"})
    print(answer)
    return jsonify(answer)


@app.route("/api/1.0/saveGraph", methods=['POST'])
def saveGraph():
    G.serialize(destination=KG_FILE_NAME)
    return jsonify({"error": 0, "msg": "Saved"})


getuuid()

if __name__ == '__main__':
    app.run(debug=True)
