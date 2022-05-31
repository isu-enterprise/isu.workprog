from cProfile import label
from flask import Flask, render_template, jsonify, request
from rdflib import Graph
import logging

KG_FILE_NAME = "a.xml.ttl"

G = Graph()
G.parse(KG_FILE_NAME)

app = Flask(__name__)

WP_UUID = None


def getuuid():
    global WP_UUID
    uuid = list(G.query(GET_WP_UUID))[0][0].lstrip("<").rstrip(">")
    uuid = uuid.replace("http://irnok.net/ontologies/database/isu/workprog#",
                        "")
    print(uuid)
    WP_UUID = uuid
    return uuid


@app.route('/')
def main():
    global WP_UUID
    print(WP_UUID)
    return render_template('index.html', WP_UUID=WP_UUID)


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

GET_WP_UUID = PREFIXES + """

SELECT ?uuid WHERE {
    ?uuid a dbr:Syllabus .
}

LIMIT 1
"""

GET_WP_AP = PREFIXES + """

SELECT ?text
WHERE
{
    wpdb:@UUID@ a dbr:Syllabus .
    wpdb:@UUID@ wpdd:courseDC ?dc .
    ?dc wpdd:@TAG@ ?text .       #@@
}

LIMIT 1

"""
GET_WP_QUEST = PREFIXES + """

SELECT ?quest ?number ?label WHERE {
# SELECT * WHERE {
    ?syll a dbr:Syllabus .
    ?syll wpdd:itemList ?itemlist .
    ?s a dbr:Syllabus .
    ?s  wpdd:itemList  ?itemlist .
    ?itemlist a wpdd:EvaluationMean .
    ?quest schema:member ?itemlist .
    ?quest schema:sku ?number .
    ?quest rdfs:label ?label  .
   }

"""

#END_OF_GETTERS

DEL_WP_AP = PREFIXES + """

DELETE
{
    ?dc wpdd:@TAG@ ?text .
}
WHERE
{
    wpdb:@UUID@ a dbr:Syllabus .
    wpdb:@UUID@ wpdd:courseDC ?dc .
    ?dc wpdd:@TAG@ ?text .
}

"""

INS_WP_AP = PREFIXES + """
INSERT
{
    ?dc wpdd:@TAG@ "@TEXT@" .
}
WHERE
{
    wpdb:@UUID@ a dbr:Syllabus .
    wpdb:@UUID@ wpdd:courseDC ?dc .
}

"""

QUERIES = [
    (("aim", "problem"), [GET_WP_AP, DEL_WP_AP, INS_WP_AP]),
]


def gettemplates(what):
    for t, qs in QUERIES:
        if what in t:
            return qs
    return None


def qsubst(query, substs):
    q = query
    for k, v in substs.items():
        if isinstance(v, str):
            q = q.replace("@" + k.upper() + "@", v)
    return q


def lprint(s):
    sl = s.split("\n")
    for c, s in enumerate(sl):
        q = c + 1
        print ("{} {}".format(q, s.rstrip()))

@app.route("/api/1.0/qwp", methods=['POST'])  # Get Work ProgramS
def savewp():
    js = request.json
    uuid = js["uuid"]
    text = js["text"]
    what = js["tag"]
    op = js["op"]

    templates = gettemplates(what)

    if templates is None:
        msg = "Cannot find template for '{}'.".format(js)
        logging.error(msg)
        raise RuntimeError(msg)

    if op == "save":
        queries = templates[1:]
    else:
        queries = templates[:1]

    answer = {}

    for q in queries:
        q1 = qsubst(q, js)
        lprint(q1)
        if (op == "save"):
            G.update(q1)
        else:
            text = list(G.query(q1))[0][0]
            answer["text"] = str(text)

    answer.update({"uuid": uuid, "error": 0, "msg": op + "ed"})
    print(answer)
    return jsonify(answer)


@app.route("/api/1.0/saveGraph", methods=['POST'])
def saveGraph():
    G.serialize(destination=KG_FILE_NAME)
    return jsonify({"error": 0, "msg": "Saved"})


if __name__ == '__main__':
    getuuid()
    app.run(debug=True)
