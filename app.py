import click, json, rdflib, sys
from flask import Flask
from flask.cli import with_appcontext
from local import TRIPLES
from utils import build_database, get_browse, get_info

app = Flask(__name__, instance_relative_config=True)

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
    for b in sorted(get_browse(browse_type).keys()):
        sys.stdout.write('{}\n'.format(b))


@app.cli.command(
    'get-browse-term',
    short_help='Get a subjects or decades browse, by term.'
)
@click.argument('browse_type')
@click.argument('browse_term')
def cli_get_browse(browse_type, browse_term):
    for id in get_browse(browse_type)[browse_term]:
        sys.stdout.write('{}\n'.format(id))


@app.cli.command(
    'get-item',
    short_help='Get information about an item.'
)
@click.argument('identifier')
def cli_get_item(identifier):
    print(
        json.dumps(
            get_info(identifier),
            indent=2
        )
    )
