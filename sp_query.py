from rdflib import Graph, RDF, RDFS

KGFILE = "studplan.ttl"

KG = Graph()
KG.parse(KGFILE)


def query(q):
    res = KG.query(q)
    return res


QUERY1 = """
PREFIX dbr: <https://dbpedia.org/page/>
PREFIX idb: <http://irnok.net/ontologies/database/isu/studplan#>
prefix idd: <http://irnok.net/ontologies/isu/studplan#>
prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
prefix xsd: <http://www.w3.org/2001/XMLSchema#>

# SELECT ?disc_name ?prof_name ?spec_name
SELECT ?prof_name ?spec_name ?term_name
WHERE {
  ?fac a dbr:Faculty .
  ?fac idd:hasDiscipline ?disc .
  ?disc a idd:Discipline .
#  ?disc rdfs:label ?disc_name .
  ?disc idd:profile ?prof .
  ?prof rdfs:label ?prof_name .
  ?disc idd:specialty ?spec .
  ?spec a idd:Speciality .
  ?spec rdfs:label ?spec_name .
  ?disc idd:term ?term .
  ?term rdfs:label ?term_name .
  FILTER langMatches( lang(?term_name), "ru" ) .
}

"""

if __name__ == '__main__':
    from pprint import pprint
    for row in query(QUERY1):
        pprint(row)
