import json, os, rdflib, requests, sqlite3, sys, urllib.parse
from rdflib.plugins.sparql import prepareQuery
from sortedcontainers import SortedDict
from config import ALLMAPS_URL_DATA, DB, TRIPLES

import regex as re

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
    con = sqlite3.connect(DB)
    cur = con.cursor()

    for row in cur.execute(
        '''
            select info from item where id=?;
        ''',
        (
            ark,
        )
    ):
        return json.loads(row[0])

def get_info_from_triples(ark):
    g = rdflib.Graph()
    g.parse(TRIPLES)

    info = {}
    for key, predicate in { 
        'creators':     'http://purl.org/dc/elements/1.1/creator',
        'dates':        'http://purl.org/dc/terms/date',
        'descriptions': 'http://purl.org/dc/elements/1.1/description',
        'languages':    'http://purl.org/dc/elements/1.1/language',
        'local_id':     'http://lib.uchicago.edu/identifier',
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

    with open(ALLMAPS_URL_DATA) as f:
        allmaps_urls = json.loads(f.read())

    noid = ark.replace('https://ark.lib.uchicago.edu/', '').replace('ark:/61001/', '').replace('ark:61001/', '')

    info['allmaps_urls'] = [{}]
    try:
        info['allmaps_urls'][0] = allmaps_urls[noid]
    except KeyError:
        print('could not find ' + noid)

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
    for k, value_list in info.items():
        if k in ('allmaps_urls',):
            continue
        else:
            for v in value_list:
                for s in v.split():
                    search_tokens.append(s.upper())
    return ' '.join(search_tokens)


def get_browse(browse_type):
    con = sqlite3.connect(DB)
    cur = con.cursor()

    browse = SortedDict()
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


def convert_raw_query_to_fts(query):
    """
    Convert a raw user query to a series of single words, joined by boolean
    AND, and suitable for passing along to SQLite FTS.

    Parameters:
        query (str): a search string.

    Returns:
        str: search terms cleaned and separated by ' AND '.
    """
    if query:
        # limit queries to 256 characters. (size chosen arbitrarily.)
        query = query[:256]

        # replace all non-unicode letters or numbers in the query with a
        # single space. This should strip out punctuation, etc.
        query = re.sub("[^\\p{L}\\p{N}]+", " ", str(query))

        # replace all whitespace with a single space.
        query = ' '.join(query.split())

    # join all search terms with AND.
    # limit queries to 32 search terms. (size chosen arbitrarily.)
    match_string = []
    for q in query.split(' '):
        match_string.append(q)
    match_string = ' AND '.join(match_string[:32])

    return match_string


def get_search(query, facets=[], sort_type='rank'):
    """
    Get search results.

    Parameters:
        query (str):     a search string.
        facets (list):   a list of strings, where each string begins with a
                         browse/facet type, followed by a colon, followed
                         by the term.
        sort_type (str): e.g., 'rank', 'date'

    Returns:
        list: a list, where each element contains a three-tuple with a
              series identifier, a list of item identifiers with hits in
              that series, and a rank.
    """
    assert sort_type in ('date', 'rank', 'series.id')

    con = sqlite3.connect(DB)
    cur = con.cursor()

    if query:
        query = convert_raw_query_to_fts(query)
  
    subqueries = []
    for _ in facets:
        subqueries.append('''
            select id
            from browse
            where type=?
            and term=?
        ''')

    vars = []
    if query:
        vars.append(query)
    for facet in facets:
        match = re.match('^([^:]*):(.*)$', facet)
        vars.append(match.group(1))
        vars.append(match.group(2))

    # Execute search.

    if query and facets:
        sql = '''
                select id, info, rank
                from item
                where text match ?
                and id in ({})
                order by {};
        '''.format(' intersect '.join(subqueries), sort_type)
    elif query:
        sql = '''
                select id, info, rank
                from item
                where text match ?
                order by {};
        '''.format(sort_type)
    elif facets:
        sql = '''
                select id, info
                from item
                where id in ({})
                order by id
        '''.format(' intersect '.join(subqueries))
    else:
        sql = '''
                select id, info
                from item
                order by id
        '''

    results = []
    for row in cur.execute(sql, vars).fetchall():
        if len(row) == 1:
            results.append([row[0], json.loads(row[1]), 0.0])
        else:
            results.append([row[0], json.loads(row[1]), row[2]])
    return results

def get_allmaps_urls(ark):
    """
    Get Allmaps URLs over HTTP.

    Parameters:
        ark (str): an ARK identifier.

    Returns:
        dict: a dictionary with object-level (ARK) level URLs and image-level
              URLs.
    """
    def get_item_count(ark):
        return len(
            requests.get(
                'https://iiif-collection.lib.uchicago.edu/object/ark:/61001/{}.json'.format(
                    ark.replace('ark:61001/', '').replace('ark:/61001/', '')
                )
            ).json()['items']
        )
    
    def get_image_server_url(ark, n):
        return 'https://iiif-server.lib.uchicago.edu/ark:61001/{}/{:08d}'.format(
            ark.replace('ark:61001/', '').replace('ark:/61001/', ''),
            n
        )

    manifest = 'https://iiif-collection.lib.uchicago.edu/object/ark:/61001/{}.json'.format(
        ark.replace('ark:61001/', '').replace('ark:/61001/', '')
    )
    urls = {
        'editor_url': 'https://editor.allmaps.org/#/collection?url={}'.format(urllib.parse.quote_plus(manifest)),
        'viewer_url': 'https://viewer.allmaps.org/?url={}'.format(urllib.parse.quote_plus(manifest)),
        'image_level_data': []
    }
    for i in range(1, get_item_count(ark) + 1):
        image_server_url = get_image_server_url(ark, i)
        try:
            for item in requests.get(
                'https://annotations.allmaps.org/?url={}'.format(
                    image_server_url
                )
            ).json()['items']:
                map_id = item['id']
                urls['image_level_data'].append({
                    'annotation_url': 'https://annotations.allmaps.org/maps/{}'.format(urllib.parse.quote_plus(map_id)),
                    'xyz_template': 'https://allmaps.xyz/maps/{}/{{z}}/{{x}}/{{y}}.png'.format(urllib.parse.quote_plus(map_id))
                })
        except KeyError:
            print('no items key in https://annotations.allmaps.org/?url={}'.format(
                image_server_url
            ))
            print('try with manifest ' + manifest)
    return urls

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
        info_dict[ark] = get_info_from_triples(ark)

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
        noid = ark.replace('https://ark.lib.uchicago.edu/', '').replace('ark:/61001/', '').replace('ark:61001/', '').strip()

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
