from cProfile import label
from flask import Flask, render_template, jsonify, request
from rdflib import Graph
from common import WPDB, WPDD

KG_FILE_NAME = "a.xml.ttl"

G = Graph()
G.parse(KG_FILE_NAME)
app = Flask(__name__)

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

QQ = PREFIXES + """

SELECT * WHERE {
    ?s a dbr:Syllabus .
}

"""

q = GET_WP_QUEST

# q = QQ

print(q)

ans = G.query(q,
              initBindings={
                  "syll": WPDB["f76d01a6-dbb0-11ec-83cd-704d7b84fd9f"],
                  "mur": "cur"
              })

ans.serialize(destination="_.txt", format="csv", encoding="utf-8")

# print(text)
# answer = {"text": text}
# print(answer)

#for uuid, num, lab in ans:
#    print("{}. {}".format(num, lab))
