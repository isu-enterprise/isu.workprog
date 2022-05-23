from flask import Flask, render_template, jsonify, request
from rdflib import Graph

KG_FILE_NAME="a.xml.ttl"

G = Graph()
G.parse(KG_FILE_NAME)

app = Flask(__name__)

@app.route('/')
def main():
    return render_template('index.html')

@app.route("/api/1.0/getwps")  # Get Work ProgramS
def getwps():
    answer = {"rows": [1,2,3], "error":0}
    return jsonify(answer)


GET_WP_AIM = """
PREFIX dbp: <https://dbpedia.org/page/> 
PREFIX dcterms: <http://purl.org/dc/terms/> 
PREFIX idb: <http://irnok.net/ontologies/database/isu/studplan#> 
PREFIX idd: <http://irnok.net/ontologies/isu/studplan#> 
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
PREFIX schema: <https://schema.org/> 
PREFIX wpdb: <http://irnok.net/ontologies/database/isu/workprog#> 
PREFIX wpdd: <http://irnok.net/ontologies/isu/workprog#> 

SELECT ?text WHERE {
    wpdb:@UUID@ a dbp:Syllabus .
    wpdb:@UUID@ wpdd:courseDC ?dc .
    ?dc wpdd:aim ?text .
}
LIMIT 1

"""


@app.route("/api/1.0/getwp")  # Get Work ProgramS
def getwp():
    # uuid = request.json["uuid"]
    uuid = request.args.get("uuid")

    q = GET_WP_AIM.replace("@UUID@", uuid)

    text = list(G.query(q))[0][0]

    answer = {"text": text, "error":0}
    return jsonify(answer)

DEL_WP_AIM = """
PREFIX dbp: <https://dbpedia.org/page/> 
PREFIX dcterms: <http://purl.org/dc/terms/> 
PREFIX idb: <http://irnok.net/ontologies/database/isu/studplan#> 
PREFIX idd: <http://irnok.net/ontologies/isu/studplan#> 
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
PREFIX schema: <https://schema.org/> 
PREFIX wpdb: <http://irnok.net/ontologies/database/isu/workprog#> 
PREFIX wpdd: <http://irnok.net/ontologies/isu/workprog#> 

DELETE {
    ?dc wpdd:aim ?text .
} WHERE {
    wpdb:@UUID@ a dbp:Syllabus .
    wpdb:@UUID@ wpdd:courseDC ?dc .
    ?dc wpdd:aim ?text .
}
"""

INS_WP_AIM = """
PREFIX dbp: <https://dbpedia.org/page/> 
PREFIX dcterms: <http://purl.org/dc/terms/> 
PREFIX idb: <http://irnok.net/ontologies/database/isu/studplan#> 
PREFIX idd: <http://irnok.net/ontologies/isu/studplan#> 
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
PREFIX schema: <https://schema.org/> 
PREFIX wpdb: <http://irnok.net/ontologies/database/isu/workprog#> 
PREFIX wpdd: <http://irnok.net/ontologies/isu/workprog#> 

INSERT {
    ?dc wpdd:aim "@TEXT@" .
} WHERE {
    wpdb:@UUID@ a dbp:Syllabus .
    wpdb:@UUID@ wpdd:courseDC ?dc .
}

"""


@app.route("/api/1.0/savewp", methods=['POST'])  # Get Work ProgramS
def savewp():
    # uuid = request.json["uuid"]

    js = request.json
    uuid = js["uuid"]
    text = js["text"]
    print (uuid, text)

    q1 = DEL_WP_AIM.replace("@UUID@", uuid)
    q2 = INS_WP_AIM.replace("@UUID@", uuid).replace("@TEXT@", text)

    qs=[q1,q2]
    for q in qs:
        G.update(q)

    answer = {"uuid":uuid, "error":0, "msg":"saved" }
    return jsonify(answer)


@app.route("/api/1.0/saveGraph", methods=['POST'])  
def saveGraph():
    G.serialize(destination=KG_FILE_NAME)
    return jsonify({"error":0, "msg":"Saved"})

if __name__ == '__main__':
    app.run(debug=True)
