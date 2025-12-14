from ..strategies_id_loc_gov import _search_id, _enrich_id, _parse_single_results
from ..strategies_helpers import _build_recon_dict


recon_query_1 = {'query': 'To the Lighthouse', 'type': 'LC_Work_Id', 'req_ip': 'test', 'properties': [{'pid': 'contributor_uncontrolled_last_first', 'v': 'Virginia Woolf'}], 'type_strict': 'should'}
recon_query_2 = {'query': 'To the Lighthouse', 'type': 'LC_Work_Id', 'req_ip': 'test', 'properties': [{'pid': 'contributor_uncontrolled_last_first', 'v': 'Virginia Woolf'}, {'pid': 'work_published_year', 'v': '1927'}], 'type_strict': 'should'}


def test__search_id():

	reconcile_item = _build_recon_dict(recon_query_1)
	reconcile_item['author_name'] = 'Virginia Woolf'
	search_results = _search_id(reconcile_item, {'POST45_ID_RDFTYPE_TEXT_LIMIT': True, 'POST45_RECONCILIATION_MODE': 'cluster', 'POST45_ID_CLUSTER_QUALITY_SCORE': 'high'})
	assert search_results['count'] > 0
	assert search_results['hits'][0]['suggestLabel'] == 'Woolf, Virginia, 1882-1941. To the lighthouse'
	assert search_results['hits'][0]['fuzzy_score'] == 0.95
	# we passed 'high' so we expect all fuzzy scores to be >= 0.90
	assert all(h['fuzzy_score'] >= 0.90 for h in search_results['hits'])

def test__enrich_id():

	reconcile_item = _build_recon_dict(recon_query_1)
	reconcile_item['author_name'] = 'Virginia Woolf'
	search_results = _search_id(reconcile_item, {'POST45_ID_RDFTYPE_TEXT_LIMIT': True, 'POST45_RECONCILIATION_MODE': 'cluster', 'POST45_ID_CLUSTER_QUALITY_SCORE': 'high'})

	# make the result set a little smaller for testing
	search_results['hits'] = search_results['hits'][:2]
	
	enriched_results = _enrich_id(search_results)
	print('enriched_results', enriched_results,flush=True)
	
	# Test that the overall structure is preserved
	assert 'hits' in enriched_results, "Results should contain 'hits' key"
	assert len(enriched_results['hits']) == 2, "Should have 2 hits as limited"
	assert enriched_results.get('successful') == True, "Results should be marked as successful"
	assert enriched_results.get('error') == None, "Should have no error"
	
	# Test enrichment for each hit
	for hit in enriched_results['hits']:
		# Check that original fields are preserved
		assert 'uri' in hit, "Original URI should be preserved"
		assert 'suggestLabel' in hit, "Original suggestLabel should be preserved"
		assert 'fuzzy_score' in hit, "Fuzzy score should be preserved"
		assert 'title_score' in hit, "Title score should be preserved"
		assert 'author_score' in hit, "Author score should be preserved"
		assert 'more' in hit, "Original 'more' field should be preserved"
		
		# Check enrichment status
		if hit.get('enriched'):
			# If enriched successfully, check for expected fields
			
			# Check for Work-level fields (may or may not be present depending on the data)
			if 'originDate' in hit:
				assert isinstance(hit['originDate'], str), "originDate should be a string"
			
			if 'language' in hit:
				assert isinstance(hit['language'], str), "language should be a string"
				# Language codes are typically 3 letters (e.g., 'eng', 'fre', 'spa')
				assert len(hit['language']) == 3, "Language code should be 3 characters"
			
			if 'subjects' in hit:
				assert isinstance(hit['subjects'], list), "subjects should be a list"
				for subject in hit['subjects']:
					assert isinstance(subject, str), "Each subject should be a string"
			
			if 'genreForms' in hit:
				assert isinstance(hit['genreForms'], list), "genreForms should be a list"
				for genre in hit['genreForms']:
					assert isinstance(genre, str), "Each genre form should be a string"
			
			# Check for Instance-level fields
			if 'responsibilityStatement' in hit:
				assert isinstance(hit['responsibilityStatement'], str), "responsibilityStatement should be a string"
			
			if 'publicationStatement' in hit:
				assert isinstance(hit['publicationStatement'], str), "publicationStatement should be a string"
			
			if 'editionStatement' in hit:
				assert isinstance(hit['editionStatement'], str), "editionStatement should be a string"
			
			if 'extent' in hit:
				assert isinstance(hit['extent'], str), "extent should be a string"
			
			if 'dimensions' in hit:
				assert isinstance(hit['dimensions'], str), "dimensions should be a string"
			
			# Check identifiers structure
			if 'identifiers' in hit:
				assert isinstance(hit['identifiers'], list), "identifiers should be a list"
				for identifier in hit['identifiers']:
					assert isinstance(identifier, dict), "Each identifier should be a dictionary"
					assert 'type' in identifier, "Identifier should have a type"
					assert 'value' in identifier, "Identifier should have a value"
					assert identifier['type'] in ['ISBN', 'LCCN', 'OCLC'], "Type should be ISBN, LCCN, or OCLC"
					# ISBN may have a qualifier
					if identifier['type'] == 'ISBN' and 'qualifier' in identifier:
						assert isinstance(identifier['qualifier'], str), "ISBN qualifier should be a string"
			
			# Check provision activities structure
			if 'provisionActivities' in hit:
				assert isinstance(hit['provisionActivities'], list), "provisionActivities should be a list"
				for activity in hit['provisionActivities']:
					assert isinstance(activity, dict), "Each provision activity should be a dictionary"
					# Each activity may have date, place, and/or agent
					if 'date' in activity:
						assert isinstance(activity['date'], str), "Date should be a string"
					if 'place' in activity:
						assert isinstance(activity['place'], str), "Place should be a string"
					if 'agent' in activity:
						assert isinstance(activity['agent'], str), "Agent should be a string"
			
			# Check for multiple instances handling
			if 'allInstances' in hit:
				assert isinstance(hit['allInstances'], list), "allInstances should be a list"
				assert len(hit['allInstances']) > 1, "allInstances should contain multiple instances"
				for instance in hit['allInstances']:
					assert isinstance(instance, dict), "Each instance should be a dictionary"
					# Each instance may have similar fields to the main hit
		
		elif 'enrichment_error' in hit:
			# If enrichment failed, check error handling
			assert hit.get('enriched') == False, "Failed enrichment should be marked as False"
			assert isinstance(hit['enrichment_error'], str), "Error message should be a string"
			print(f"Enrichment failed for {hit.get('uri', 'unknown')}: {hit['enrichment_error']}")
		
		else:
			# Hit may not have been enriched at all (e.g., no instance URI)
			print(f"Hit not enriched: {hit.get('uri', 'unknown')} - possibly missing instance URI")


def test__parse_single_results():
	reconcile_item = _build_recon_dict(recon_query_2)
	reconcile_item['author_name'] = 'Virginia Woolf'
	search_results = _search_id(reconcile_item, {'POST45_ID_RDFTYPE_TEXT_LIMIT': True, 'POST45_RECONCILIATION_MODE': 'single', 'POST45_ID_CLUSTER_QUALITY_SCORE': 'high'})
	# make the result set a little smaller for testing
	search_results['hits'] = search_results['hits'][:5]	
	enriched_results = _enrich_id(search_results)
	results = _parse_single_results(enriched_results, reconcile_item)
	assert results['or_query_response'][0]['id'] == 'http://id.loc.gov/resources/works/8737676'









