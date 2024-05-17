import json, logging, openpyxl, os, requests, sys
from datetime import datetime
from urllib.parse import urlparse

"""This program downloads IIIF Annotation URLs that it finds in the project
   inventory (an Excel spreadsheet) in the following worksheets and columns:

   UChi_Maps            : ANNOTATION_URL_1 (column 18)
   UCHI_Batch1_June2023 : ANNOTATION_URL   (column 19)
   UCHI_SSMC            : ANNOTATION_URL   (column  9)
"""

SPREADSHEET = 'Copy of Georeferencing-UChicago  (1).xlsx'
SPREADSHEET_INFO = (
    ('UChi_Maps',            18, 'ANNOTATION_URL_1'),
    ('UCHI_Batch1_June2023', 19, 'ANNOTATION_URL'),
    ('UCHI_SSMC',             9, 'ANNOTATION_URL')
)
OUTPUT_DIRECTORY = 'annotations_individual'

def split_url(url):
    """Split a URL into a domain and path.

    Args:
	url: a url, as a string.

    Returns:
	A tuple, containing the domain and path.
    """
    parsed_url = urlparse(url)
    domain = parsed_url.hostname
    filename = parsed_url.path.replace('/', '_')
    if filename.startswith('_'):
        filename = filename[1:]
    if not filename.endswith('.json'):
        filename = filename + '.json'
    return domain, filename

def download_url(url, output_directory):
    """Download a URL to a destination directory. Save it in a <domain> subdirectory.

    Args:
	url: a url, as a string.
        output_directory: the output directory, as a string.

    Side effect:
	Save the URL.
    """
    logging.info('{} download_url() called for {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), url))
    domain, filename = split_url(url)

    d = os.path.join(output_directory, domain)
    if not os.path.exists(d):
        os.mkdir(d)
    if not os.path.exists(os.path.join(d, filename)):
        with open(os.path.join(d, filename), 'wb') as f:
            try: 
                r = requests.get(url)
                if r.status_code == 200 and len(r.content):
                    f.write(r.content)
                logging.info('{} {} {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), r.status_code, url))
            except requests.exceptions.ConnectionError:
                logging.info('{} requests.exceptions.ConnectionError {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), url))
                
def validate_wb(wb):
    """Confirm that the workbook is what we expect it to be.

    Args:
	wb: an openpyxl Workbook object for the project planning Excel
            spreadsheet.

    Side Effects:
	This function raises exceptions when the spreadsheet is invalid in some
        way.
    """
    assert set(wb.sheetnames) == set((
        'UCHI_SSMC', 
        'UCHI_Batch1_June2023', 
        'UChi_Maps', 
        'Chicagoland_maps_Batch1_John_Ju', 
        'Summary'
    ))
    for ws_name, c, col_name in SPREADSHEET_INFO:
        ws = wb[ws_name]
        assert ws.cell(column=c, row=1).value == col_name

def get_annotation_urls(wb):
    """Get IIIF Annotation URLs from the project planning spreadsheet.

    Args:
	wb: an openpyxl Workbook object for the project planning Excel
            spreadsheet.

    Returns:
        a set() of IIIF Annotation URLs.
    """
    urls = set()

    for ws_name, c, col_name in SPREADSHEET_INFO:
        ws = wb[ws_name]
        for r in range(2, ws.max_row + 1):
            v = ws.cell(column=c, row=r).value
            if v:
                v = v.strip()
                if v.startswith('http') and 'annotations.allmaps.org' in v:
                    urls.add(v)
    return urls

def get_version_urls(annotation_url, output_directory):
    """Get URLs from Allmaps list URL.

    Args:
        annotation_ url:  An Allmaps Annotation URL.
        output_directory: The output directory, as a string.

    Side Effect:
        downloads version URL if necessary. 

    Returns:
        a set() of urls.
    """
    if annotation_url.startswith('https://annotations.allmaps.org') and '/images/' in annotation_url:
        version_url = annotation_url.replace('annotations.allmaps.org', 'api.allmaps.org') + '/versions'
        local_filepath = os.path.join(
            output_directory,
            'api.allmaps.org',
            annotation_url.replace('https://annotations.allmaps.org/', '').replace('/', '_') + '_versions.json'
        )
        if not os.path.exists(local_filepath) or os.stat(local_filepath).st_size == 0:
            download_url(version_url, output_directory)

        version_urls = set()
        with open(local_filepath) as f:
            j = json.load(f)
            for item in j:
                version_urls.add(item['version'])
        return version_urls
    else:
        return []
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, filename='out.log')

    wb = openpyxl.load_workbook(SPREADSHEET)
    validate_wb(wb)

    if not os.path.exists(OUTPUT_DIRECTORY):
        os.mkdir(OUTPUT_DIRECTORY)
    annotation_urls = get_annotation_urls(wb)
    for annotation_url in annotation_urls:
        download_url(annotation_url, OUTPUT_DIRECTORY)
    for annotation_url in annotation_urls:
        for version_url in get_version_urls(annotation_url, OUTPUT_DIRECTORY):
            download_url(version_url, OUTPUT_DIRECTORY)
