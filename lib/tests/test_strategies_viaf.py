from ..strategies_viaf import _search_name, _parse_name_results
from ..strategies_helpers import _build_recon_dict_name


recon_query_1 = {'query': 'Goodman, Paul', 'type': 'VIAF_Personal', 'properties': [{'pid': 'title', 'v': 'The state of nature'}], 'type_strict': 'should'}
# recon_query_2 = {'query': 'Miller, Matthew', 'type': 'VIAF_Personal', 'properties': [], 'type_strict': 'should'}
recon_query_2 = {'query': 'Lucas, Curtis', 'type': 'VIAF_Personal', 'properties': [], 'type_strict': 'should'}

recon_query_3 = {'query': 'Goodman, Paul', 'type': 'VIAF_Personal', 'properties': [{'pid': 'birth_year', 'v': '1911-1972.'}], 'type_strict': 'should'}
# recon_query_3 = {'query': 'Foster, Michael', 'type': 'VIAF_Personal', 'properties': [{'pid': 'birth_year', 'v': '1904-'}], 'type_strict': 'should'}

# recon_query_3 = {'query': 'Micheaux, Oscar', 'type': 'VIAF_Personal', 'properties': [{'pid': 'birth_year', 'v': '1884-1951'}], 'type_strict': 'should'}



def test_personal_name_with_title_search():
	
	reconcile_item = _build_recon_dict_name(recon_query_1)
	data = _search_name(reconcile_item)

	search_results = _parse_name_results(data,reconcile_item)
	
	assert search_results['or_query_response'][0]['name'] == 'Goodman, Paul, 1911-1972'
	assert search_results['or_query_response'][0]['score'] == 1




def test_personal_name_no_extra_data():
	
	reconcile_item = _build_recon_dict_name(recon_query_2)
	data = _search_name(reconcile_item)

	search_results = _parse_name_results(data,reconcile_item)

	# we have to sort it, normally open refine will do that
	newlist = sorted(search_results['or_query_response'], key=lambda d: d['score'],reverse=True)
	
	assert newlist[0]['name'] == 'Lucas, Curtis, 1914-'
	assert newlist[0]['score'] > 0.5



def test_personal_with_birth_year():
	
	reconcile_item = _build_recon_dict_name(recon_query_3)
	data = _search_name(reconcile_item)

	search_results = _parse_name_results(data,reconcile_item)

	# we have to sort it, normally open refine will do that
	newlist = sorted(search_results['or_query_response'], key=lambda d: d['score'],reverse=True)
	
	assert newlist[0]['name'] == 'Goodman, Paul, 1911-1972'
	assert newlist[0]['score'] == 1



	
	






