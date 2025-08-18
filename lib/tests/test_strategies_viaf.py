from ..strategies_viaf import _search_name, _parse_name_results, _search_title
from ..strategies_helpers import _build_recon_dict, _build_recon_dict_name


recon_query_1 = {'query': 'Goodman, Paul', 'type': 'VIAF_Personal', 'properties': [{'pid': 'title', 'v': 'The state of nature'}], 'type_strict': 'should'}
# recon_query_2 = {'query': 'Miller, Matthew', 'type': 'VIAF_Personal', 'properties': [], 'type_strict': 'should'}
recon_query_2 = {'query': 'Lucas, Curtis', 'type': 'VIAF_Personal', 'properties': [], 'type_strict': 'should'}

recon_query_3 = {'query': 'Goodman, Paul', 'type': 'VIAF_Personal', 'properties': [{'pid': 'birth_year', 'v': '1911-1972.'}], 'type_strict': 'should'}
# recon_query_3 = {'query': 'Foster, Michael', 'type': 'VIAF_Personal', 'properties': [{'pid': 'birth_year', 'v': '1904-'}], 'type_strict': 'should'}

# recon_query_3 = {'query': 'Micheaux, Oscar', 'type': 'VIAF_Personal', 'properties': [{'pid': 'birth_year', 'v': '1884-1951'}], 'type_strict': 'should'}


recon_query_4 = {'query': 'Ralph Ellison', 'type': 'VIAF_Personal', 'properties': [{'pid': 'birth_year', 'v': '1914'}], 'type_strict': 'should'}

recon_query_5 = {'query': 'Tester, Michael', 'type': 'VIAF_Personal', 'properties': [{'pid': 'birth_year', 'v': '1960'}], 'type_strict': 'should'}



recon_query_title_1 = {'query': 'To the Lighthouse', 'type': 'VIAF_Title', 'req_ip': 'test', 'properties': [{'pid': 'contributor_uncontrolled_last_first', 'v': 'Virginia Woolf'}], 'type_strict': 'should'}




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
	print("data",data,flush=True)
	search_results = _parse_name_results(data,reconcile_item)
	print("search_results",search_results,flush=True)
	print(search_results['or_query_response'],flush=True)
	# we have to sort it, normally open refine will do that
	newlist = sorted(search_results['or_query_response'], key=lambda d: d['score'],reverse=True)
	
	assert newlist[0]['name'] == 'Goodman, Paul, 1911-1972'
	assert newlist[0]['score'] == 1



def test_personal_with_birth_year_but_not_in_heading1():

	reconcile_item = _build_recon_dict_name(recon_query_4)
	data = _search_name(reconcile_item)

	search_results = _parse_name_results(data,reconcile_item)

	# we have to sort it, normally open refine will do that
	newlist = sorted(search_results['or_query_response'], key=lambda d: d['score'],reverse=True)

	assert newlist[0]['id'] == 'http://viaf.org/viaf/2481446'
	
def test_personal_with_birth_year_but_not_in_heading2():

	reconcile_item = _build_recon_dict_name(recon_query_5)
	data = _search_name(reconcile_item)

	search_results = _parse_name_results(data,reconcile_item)

	# we have to sort it, normally open refine will do that
	newlist = sorted(search_results['or_query_response'], key=lambda d: d['score'],reverse=True)

	assert newlist[0]['id'] == 'http://viaf.org/viaf/75676253'



def test__search_title():
	"""Test the _search_title function with Virginia Woolf's To the Lighthouse"""
	
	reconcile_item = {"author_name": "Virginia Woolf", "title": "To the Lighthouse"}
	results = _search_title(reconcile_item, {})
	print("Full results:", results)
	
	# Check that we have results
	assert 'or_query_response' in results, "Results should have or_query_response key"
	assert len(results['or_query_response']) > 0, "Should have at least one result"
	
	response = results['or_query_response']
	
	# Test the first result (should be the best match)
	first_result = response[0]
	assert first_result['score'] == 0.95, f"First result should have score 0.95, got {first_result['score']}"
	assert first_result['match'] == True, "First result should be a match (score > 0.8)"
	assert 'Woolf, Virginia' in first_result['name'], "First result should contain author name"
	assert 'To the lighthouse' in first_result['name'], "First result should contain title"
	assert first_result['id'].startswith('http://viaf.org/viaf/'), "ID should be a VIAF URL"
	assert first_result['type'][0]['id'] == 'viaf:Work', "Type should be viaf:Work"
	assert first_result['type'][0]['name'] == 'VIAF Work', "Type name should be VIAF Work"
	
	# Test scoring distribution
	high_score_count = sum(1 for r in response if r['score'] >= 0.9)
	medium_score_count = sum(1 for r in response if 0.5 <= r['score'] < 0.9)
	low_score_count = sum(1 for r in response if r['score'] < 0.5)
	
	assert high_score_count >= 1, "Should have at least one high-scoring result (>= 0.9)"
	print(f"Score distribution: High: {high_score_count}, Medium: {medium_score_count}, Low: {low_score_count}")
	
	# Test that results are properly sorted (highest scores should come first within same source count)
	# Based on the data, items with total_sources=16 should come before total_sources=1
	viaf_183441155_indices = [i for i, r in enumerate(response) if '183441155' in r['id']]
	other_indices = [i for i, r in enumerate(response) if '183441155' not in r['id']]
	
	if viaf_183441155_indices and other_indices:
		# The first occurrence of 183441155 (which has total_sources=16) should come before
		# items with lower total_sources
		assert min(viaf_183441155_indices) < max(other_indices), \
			"Results with higher total_sources should generally come first"
	
	# Test match flag consistency
	for result in response:
		if result['score'] > 0.8:
			assert result['match'] == True, f"Result with score {result['score']} should have match=True"
		else:
			assert result['match'] == False, f"Result with score {result['score']} should have match=False"
	
	# Test that all results have required fields
	for i, result in enumerate(response):
		assert 'id' in result, f"Result {i} missing 'id' field"
		assert 'name' in result, f"Result {i} missing 'name' field"
		assert 'description' in result, f"Result {i} missing 'description' field"
		assert 'score' in result, f"Result {i} missing 'score' field"
		assert 'match' in result, f"Result {i} missing 'match' field"
		assert 'type' in result, f"Result {i} missing 'type' field"
		assert isinstance(result['score'], (int, float)), f"Result {i} score should be numeric"
		assert 0 <= result['score'] <= 1, f"Result {i} score should be between 0 and 1"
		assert isinstance(result['match'], bool), f"Result {i} match should be boolean"
	
	print("All assertions passed!")


def test__search_title_no_author():
	"""Test the _search_title function with only a title (no author)"""
	
	reconcile_item = {"author_name": "", "title": "To the Lighthouse"}
	results = _search_title(reconcile_item, {})
	print("Results without author:", results)
	
	# Check that we have results
	assert 'or_query_response' in results, "Results should have or_query_response key"
	assert len(results['or_query_response']) > 0, "Should have at least one result"
	
	response = results['or_query_response']
	
	# When no author is provided, scoring should be based on title only
	# The best match should still have a high score if the title matches well
	first_result = response[0]
	assert first_result['score'] > 0.5, f"First result should have reasonable score even without author, got {first_result['score']}"
	assert 'lighthouse' in first_result['name'].lower(), "First result should contain the title"
	
	# Test that all results have valid scores based on title-only matching
	for result in response:
		assert 0 <= result['score'] <= 1, f"Score should be between 0 and 1, got {result['score']}"
		# Without author, match threshold is still 0.8
		if result['score'] > 0.8:
			assert result['match'] == True
		else:
			assert result['match'] == False
	


