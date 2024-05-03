# Mapping Chicagoland

## Installling locally

```console
python3 -m venv venv
source venv/bin/activate
git clone https://github.com/uchicago-library/mapping_chicagoland.git
cd mapping_chicagoland
pip install -r requirements.txt
```

## Sample config.py
You'll need to add a config.py to the main project directory- it should go next to app.py. 
You can get this from another developer, or start with the following template:

```python
BASE = 'https://ark.lib.uchicago.edu/ark:61001/'
COLLECTION_TITLE = 'Mapping Chicagoland'
DB = 'mapping_chicagoland.db'
TRIPLES = 'mapping_chicagoland.ttl'
ALLMAPS_URL_DATA = 'allmaps_data.json'
```

Another developer should be able to get you access to pre-built versions of all of the files
listed above.

## Implementation Notes

This site uses a build process that takes linked data triples (a .ttl file) and imports them
into an SQLite database for faster browsing and full-text search. I have added a few subcommands
to the flask command to help manage the site. 

See all commands:
```console
flask
```

Build the SQLite database from linked data triples:
```console
flask build-database
```

Build a JSON lookup of AllMaps data (basically prec-caching these requests):
```console
flask build-allmaps-url-lookup &lt;noid-list&gt;
```

View lists of browses:
```console
flask get-browse subjects
flask get-browse decades
```

View an individual browse term:
```console
flask get-browse decades 1940s
```

View data for an individual item:
```console
flask get-item https://ark.lib.uchicago.edu/ark:61001/b2wr9j53qw3r
```

## AllMaps API Notes
[See this notebook.](https://www.kaggle.com/code/leventhalmapcenter/allmaps-u-chicago/notebook)
