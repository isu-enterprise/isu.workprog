import requests as rq

ENDPOINT = 'http://py.isu.ru:8000/hs/jsonpost/courses_in_faculty/'
USER = "3c9467d8-b710-11e6-943c-005056100702"
IMIT = 'c526d6c7-9a78-11e6-9438-005056100702'
SEMEVEN = 0
SEMODD = 1
SEMAUTUMN = SEMODD
SEMSPRING = SEMEVEN
HEADERS = {'Content-Type': 'application/json'}


def query(user, faculty=IMIT, profile=None, year=None, term=None):
    """Returns a JSON-parsed data structure.
    Parameters are
    `user` is the GUID of user,
    `faculty` is name of a faculty/institute,
    `profile` is the identifier of a profile/specialty
              (not used now),
    `year` is the year of study start,
    `term` is the semester mark (SEMAUTUMN, SEMSPRING)
    """
    if term is None:
        raise ValueError('term is undefined')
    resp = rq.request(method='POST',
                      url=ENDPOINT,
                      headers=HEADERS,
                      json={
                          "guid": user,
                          "facultet": faculty,
                          "flag_semestr": term
                      })
    if resp.ok:
        return resp.json()
    else:
        print('Return code:', resp.status_code)
        raise RuntimeError('request failed ({})'.format(resp.status_code))


if __name__ == '__main__':
    print(query(user=USER, faculty=IMIT, term=SEMSPRING))
