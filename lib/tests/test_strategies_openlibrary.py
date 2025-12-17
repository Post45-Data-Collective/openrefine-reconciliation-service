from ..strategies_openlibrary import _search_title
from ..strategies_helpers import _build_recon_dict, _build_recon_dict_name



def test__search_title():



	results = _search_title({'title': 'Fantastic Mr Fox', 'author_name': 'Roald Dahl'}, {})

	assert results['or_query_response'][0]['id'] == 'https://openlibrary.org/works/OL45804W'
	print("Search results:", results, flush=True	)


def test__search_title_lord_of_rings():


	results = _search_title({'title': 'The Lord of the Rings', 'author_name': 'J.R.R. Tolkien'}, {})

	# Check that we get results and the top result has high score
	assert len(results['or_query_response']) > 0
	assert results['or_query_response'][0]['score'] > 0.8
	print("Search results:", results, flush=True	)
