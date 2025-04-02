
from ..strategies_helpers import _download_viaf_cluster_rdf
from ..strategies_helpers import _extract_identifier_from_viaf_xml
from ..strategies_helpers import _return_wikidata_value
from ..strategies_helpers import wikidata_return_birth_year_from_viaf_uri
from ..strategies_helpers import _return_lc_suggest2_data
from ..strategies_helpers import lc_return_birth_year_from_viaf_uri





def test_viaf_cluster_download():
	
	viaf_rdf_data = _download_viaf_cluster_rdf('https://viaf.org/en/viaf/2481446')
	assert '<ns1:viafID>2481446</ns1:viafID>' in viaf_rdf_data

	
def test_extract_identifier():	
	viaf_rdf_data = _download_viaf_cluster_rdf('https://viaf.org/en/viaf/2481446')

	wikidata = _extract_identifier_from_viaf_xml(viaf_rdf_data,'WKP')

	assert wikidata == 'Q299965'
	
	lc = _extract_identifier_from_viaf_xml(viaf_rdf_data,'LC')

	assert lc == 'n50010027'





def test_return_wikidata_value():


	r = _return_wikidata_value('Q299965','P569')

	assert '1914-03-01' in r[0]['value']


	r = _return_wikidata_value('Q299965','P568')
	assert r == False


	# print(r[0])


def test_wikidata_return_birth_year_from_viaf_uri():

	date = wikidata_return_birth_year_from_viaf_uri('https://viaf.org/en/viaf/2481446')

	assert date == '1914'

	# no date in wikidata
	date = wikidata_return_birth_year_from_viaf_uri('https://viaf.org/en/viaf/75676253')

	assert date == False

def test_return_lc_suggest2_data():

	viaf_rdf_data = _download_viaf_cluster_rdf('http://viaf.org/viaf/75676253')
	lccn = _extract_identifier_from_viaf_xml(viaf_rdf_data,'LC')

	data = _return_lc_suggest2_data(lccn)

	assert 'Actors' in data['occupations']

	assert _return_lc_suggest2_data('n0344034') == False


def test_lc_return_birth_year_from_viaf_uri():

	date = lc_return_birth_year_from_viaf_uri('https://viaf.org/en/viaf/75676253')
	assert date == '1960'
