from cProfile import label
from flask import Flask, render_template, jsonify, request
from rdflib import Graph

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

SELECT ?text WHERE {
wpdb:@UUID@ a dbr:Syllabus.
    wpdb:@UUID@ wpdd:courseDC ?dc.
    ?dc wpdd:@WHAT@ ?text
   }
LIMIT 1

"""


#END_OF_GETTERS

DEL_WP_AP = PREFIXES + """

DELETE {
    ?dc wpdd:@WHAT@ ?text .
} WHERE {
    wpdb:@UUID@ a dbr:Syllabus .
    wpdb:@UUID@ wpdd:courseDC ?dc .
    ?dc wpdd:@WHAT@ ?text .
}

"""

INS_WP_AP = PREFIXES + """
INSERT {
    ?dc wpdd:@WHAT@ "@TEXT@" .
} WHERE {
    wpdb:@UUID@ a dbr:Syllabus .
    wpdb:@UUID@ wpdd:courseDC ?dc .
}

"""

QUERIES = [
        (("aim", "problem"), [GET_WP_AP,DEL_WP_AP,INS_WP_AP]),
    ]

def gettemplate(what):
    for t, qs in QUERIES:
        if what in t:
            templ = qs 
    return templ


@app.route("/api/1.0/getwp")  # Get Work ProgramS
def getwp():
    # uuid = request.json["uuid"]
    args = request.args
    uuid = args.get("uuid")
    what = args.get("tag")

    templ = None
    
    templ= gettemplate(what)[0]

    q = templ.replace("@UUID@", uuid).replace("@WHAT@", what)
    text = list(G.query(q))[0][0]
    answer = {
        "text": text,
        "error": 0,
     } 
    #answer = {}
    return jsonify(answer)



def qsubst(query, substs):
    q = query
    for k,v in substs.items():
        q = q.replace(k,v)
    return q

@app.route("/api/1.0/savewp", methods=['POST'])  # Get Work ProgramS
def savewp():
    # uuid = request.json["uuid"]
    js = request.json
    uuid = js["uuid"]
    text = js["text"]
    what = js["tag"]
    print(uuid, text)
    substs = {"@UUID@": uuid, "@WHAT@":what, "@TEXT@":text}
    # queries= [DEL_WP_AP, INS_WP_AP]
    queries= gettemplate(what)[1:]
    for q in queries:
        q1 = qsubst(q, substs)
        print(q1)
        G.update(q1)

    answer = {"uuid": uuid, "error": 0, "msg": "saved"}
    return jsonify(answer)


@app.route("/api/1.0/saveGraph", methods=['POST'])
def saveGraph():
    G.serialize(destination=KG_FILE_NAME)
    return jsonify({"error": 0, "msg": "Saved"})

if __name__ == '__main__':
    getuuid()
    app.run(debug=True)
