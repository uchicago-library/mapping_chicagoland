import click, json, rdflib, sys
from flask import Flask, render_template, request, send_from_directory
from flask.cli import with_appcontext
from local import BASE, COLLECTION_TITLE, TRIPLES
from utils import build_database, get_browse, get_info, get_search

import regex as re

app = Flask(
    __name__, 
    instance_relative_config=True,
    static_folder='static'
)

# CLI

@app.cli.command(
    'build-database',
    short_help='Build the website\'s SQLite database.'
)
def cli_build_database():
    build_database()


@app.cli.command(
    'get-browse',
    short_help='Get a subjects or decades browse.'
)
@click.argument('browse_type')
def cli_get_browse(browse_type):
    sys.stdout.write(
        json.dumps(
            get_browse(browse_type),
            indent=2
        )
    )


@app.cli.command(
    'get-browse-term',
    short_help='Get a subjects or decades browse, by term.'
)
@click.argument('browse_type')
@click.argument('browse_term')
def cli_get_browse(browse_type, browse_term):
    sys.stdout.write(
        json.dumps(
            get_browse(browse_type)[browse_term],
            indent=2
        )
    )


@app.cli.command(
    'get-item',
    short_help='Get information about an item.'
)
@click.argument('identifier')
def cli_get_item(identifier):
    sys.stdout.write(
        json.dumps(
            get_info(identifier),
            indent=2
        )
    )


@app.cli.command(
    'search',
    short_help='Search item metadata.'
)
@click.argument('query')
def cli_search(query):
    sys.stdout.write(
        json.dumps(
            get_search(query),
            indent=2
        )
    )


# WEB INTERFACE


@app.route('/browse/')
def web_browse():
    title_slugs = {
        'decades':  'Browse by Decade',
        'subjects': 'Browse by Subject'
    }

    browse_type = request.args.get('type')
    if browse_type not in title_slugs.keys():
        app.logger.debug(
            'in {}(), type parameter not a key in browses dict.'.format(
                sys._getframe().f_code.co_name
            )
        )
        abort(400)

    browse_term = request.args.get('term')

    if browse_term:
        if browse_type:
            title_slug = 'Results with' + \
                         ' ' + browse_type + ': ' + browse_term
        else:
            title_slug = 'Results for search' + \
                         ': ' + browse_term

        sort_field = 'id'
        if browse_type == 'decades':
            sort_field = 'date'

        results = []
        for identifier in get_browse(browse_type)[browse_term]:
            results.append((identifier, get_info(identifier)))

        return render_template(
            'search.html',
            collection_title=COLLECTION_TITLE,
            facets=[],
            query=browse_term,
            query_field=browse_type,
            results=results,
            title_slug=title_slug
        )
    else:
        results = []
        for b, identifiers in get_browse(browse_type).items():
            results.append((b, len(identifiers)))

        browse_sort = request.args.get('sort')
 
        if browse_sort == 'count':
            results.sort(key=lambda r: r[1], reverse=True)

        return render_template(
            'browse.html',
            collection_title=COLLECTION_TITLE,
            title_slug=title_slugs[browse_type],
            browse_terms=results,
            browse_type=browse_type
        )

@app.route('/')
def web_home():
    return render_template(
        'home.html',
        collection_title=COLLECTION_TITLE
    )

@app.route('/item/<noid>/')
def web_item(noid):
    if not re.match('^[a-z0-9]{12}$', noid):
        app.logger.debug(
            'in {}(), user-supplied noid appears invalid.'.format(
                sys._getframe().f_code.co_name
            )
        )
        abort(400)

    item_data = get_info(BASE + noid)

    try:
        title_slug = item_data['titles'][0]
    except (IndexError, KeyError):
        title_slug = ''

    breadcrumb = item_data['titles'][0]
    
    return render_template(
        'item.html',
        **(item_data | { 'collection_title': COLLECTION_TITLE, 'title_slug': title_slug, 'breadcrumb': breadcrumb })
    )

@app.route('/search/')
def web_search():
    facets = request.args.getlist('facet')
    query = request.args.get('query')
    sort_type = request.args.get('sort', 'rank')

    results = get_search(query, facets, sort_type)

    '''
    processed_results = []
    for db_series in db_results:
        series_data = mlc_db.get_series(db_series[0])
        series_data['access_rights'] = get_access_label_obj(series_data)

        series_data['sub_items'] = []
        for i in db_series[1]:
            info = mlc_db.get_info(i)
            series_data['sub_items'].append(info)
        series_data['sub_items'].sort(key=sortListOfItems)
        processed_results.append((db_series[0], series_data))
    '''

    if facets:
        title_slug = 'Search Results for' + ' ' + facets[0]
    elif query:
        title_slug = 'Search Results for' + ' \'' + query + '\''
    else:
        title_slug = 'Search Results'

    return render_template(
        'search.html',
        collection_title=COLLECTION_TITLE,
        facets=[],
        query=query,
        query_field='',
        results=results,
        title_slug=title_slug
    )
