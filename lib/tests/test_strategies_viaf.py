from ..strategies_viaf import _search_name, _parse_name_results
from ..strategies_helpers import _build_recon_dict_name


recon_query_1 = {'query': 'Goodman, Paul', 'type': 'VIAF_Personal', 'properties': [{'pid': 'title', 'v': 'The state of nature'}], 'type_strict': 'should'}


def test_personal_name_with_title_search():
	
	reconcile_item = _build_recon_dict_name(recon_query_1)
	data = _search_name(reconcile_item)

	search_results = _parse_name_results(data,reconcile_item)
	
	assert search_results['or_query_response'][0]['name'] == 'Goodman, Paul, 1911-1972'
	assert search_results['or_query_response'][0]['score'] == 1




	






