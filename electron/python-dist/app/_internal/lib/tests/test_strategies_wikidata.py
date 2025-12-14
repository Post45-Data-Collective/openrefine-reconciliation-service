from ..strategies_wikidata import _search_title
from ..strategies_helpers import _build_recon_dict, _build_recon_dict_name



def test__search_title():
    

	results = _search_title({'title': 'To the Lighthouse', 'author_name': 'Woolf, Virginia'}, {})
	
	assert results['or_query_response'][0]['id'] == 'http://www.wikidata.org/entity/Q478016'
	print("Search results:", results, flush=True	)