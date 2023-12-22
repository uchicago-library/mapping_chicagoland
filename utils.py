import json, os, rdflib, re, sqlite3, sys
from rdflib.plugins.sparql import prepareQuery
from local import DB, TRIPLES

def get_decade_from_year(s):
    m = re.search('([0-9]{4})', s)
    if m == None:
        return ''
    else:
        return m.group(1)[:3] + '0s'


def get_language_label(c):
    return {
        'eng': 'English',
        'ita': 'Italian'
    }[c]


def get_arks(g):
    """Get a list of ARKs from the project triples.

    Parameters: g(rdflib.Graph) - a graph to search. 

    Returns:
        list: a list of arks.
    """
    arks = set()
    for row in g.query('''
        PREFIX edm: <http://www.europeana.eu/schemas/edm/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?s
        WHERE {
            ?s rdf:type edm:ProvidedCHO .
        }
    '''):
        arks.add(str(row[0]))
    return list(arks)


def get_info(ark):
    g = rdflib.Graph()
    g.parse(TRIPLES)

    info = {}
    for key, predicate in { 
        'creators':     'http://purl.org/dc/elements/1.1/creator',
        'dates':        'http://purl.org/dc/terms/date',
        'descriptions': 'http://purl.org/dc/elements/1.1/description',
        'languages':    'http://purl.org/dc/elements/1.1/language',
        'local_id':     'http://lib.uchicago.edu/local_preservation_identifier',
        'publishers':   'http://purl.org/dc/elements/1.1/publisher',
        'spatials':     'http://purl.org/dc/terms/spatial',
        'subjects':     'http://purl.org/dc/elements/1.1/subject',
        'types':        'http://purl.org/dc/elements/1.1/type',
        'years':        'http://purl.org/dc/terms/date',
        'titles':        'http://purl.org/dc/elements/1.1/title'
        
    }.items():
        results = set()
        for row in g.query(
            prepareQuery('''
                PREFIX dc: <http://purl.org/dc/elements/1.1/>
                PREFIX dcterms: <http://purl.org/dc/terms/>

                SELECT ?o
                WHERE {
                    ?cho ?predicate ?o .
                }
            '''),
            initBindings={
                'cho': rdflib.URIRef(ark),
                'predicate': rdflib.URIRef(predicate)
            }
        ):
            results.add(str(row[0]))
        info[key] = sorted(list(results))

    # decades
    decades = set()
    for year in info['years']:
        decade = get_decade_from_year(year)
        if decade:
            decades.add(decade)
    info['decades'] = sorted(list(decades))

    # languages
    for i in range(len(info['languages'])):
        info['languages'][i] = get_language_label(info['languages'][i])
   
    # permanent_urls
    info['permanent_urls'] = [ark] 
    
    # rights  /aggregation edm:rights
    rights = set()
    for row in g.query(
        prepareQuery('''
            PREFIX edm: <http://www.europeana.eu/schemas/edm/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                
            SELECT ?rights
            WHERE {
                ?aggregation edm:rights ?rights .
            }
        '''),
        initBindings={
            'aggregation': rdflib.URIRef(ark + '/aggregation')
        }
    ):
        rights.add(str(row[0]))
    info['rights'] = sorted(list(rights))

    return info


def get_search_tokens(info):
    """
    Get the search tokens for a given info block.

    Parameters:
        info (dict): an info dictionary.

    Returns:
        str: a string that can be searched via SQLite.
    """
    search_tokens = []
    for value_list in info.values():
        for v in value_list:
            for s in v.split():
                search_tokens.append(s.upper())
    return ' '.join(search_tokens)


def get_browse(browse_type):
    con = sqlite3.connect(DB)
    cur = con.cursor()

    browse = {}
    for row in cur.execute(
        ''' 
            select term, id from browse where type=? order by id;
        ''',
        (
            browse_type,
        )
    ):
        term = row[0]
        id = row[1]
        if not term in browse:
            browse[term] = []
        browse[term].append(id)
    return browse


def build_database():
    """
    Build SQLite database.

    Parameters:
        None
    """
    g = rdflib.Graph()
    g.parse(TRIPLES)

    # build info dictionary
    info_dict = {}
    for ark in get_arks(g):
        info_dict[ark] = get_info(ark)

    if os.path.exists(DB):
        os.remove(DB)

    con = sqlite3.connect(DB)
    cur = con.cursor()

    # build tables
    cur.execute('begin')

    cur.execute('''
        create table browse(
            type text,
            term text,
            id text
        );
    ''')

    cur.execute('''
        create virtual table item using fts5(
            id,
            dbid,
            info,
            text,
            year
        );
    ''')

    cur.execute('commit')

    # load data
    cur.execute('begin')

    for browse_type in (
        'decades',
        'subjects'
    ):
        for ark, info in info_dict.items():
            for v in info[browse_type]:
                cur.execute(
                    '''
                        insert into browse(type, term, id)
                        values (?, ?, ?);
                    ''',
                    (
                        browse_type,
                        v,
                        ark
                    )
                )

    for ark, info in info_dict.items():
        if 'years' in info and len(info['years']) > 0:
            year = info['years'][0]
        else:
            year = ''

        cur.execute(
            '''
                insert into item(
                    id,
                    dbid,
                    info,
                    text,
                    year
                )
                values(?, ?, ?, ?, ?)
            ''',
            (
                ark,
                info['local_id'][0],
                json.dumps(info),
                get_search_tokens(info),
                year
            )
        )
    cur.execute('commit')
