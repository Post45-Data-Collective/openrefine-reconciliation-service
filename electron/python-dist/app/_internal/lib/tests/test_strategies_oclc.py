import os
from ..strategies_oclc import (
    _search_worldcat, 
    _add_fuzzy_scores, 
    _cluster_works, 
    _parse_single_results,
    _extract_bib_data,
    _get_creator_name,
    process_oclc_query
)
from ..strategies_helpers import _build_recon_dict

# OCLC configuration dictionary
# Gets values from environment variables if they exist, otherwise sets to None
OCLC_CONFIG = {
    'POST45_OCLC_CLIENT_ID': os.environ.get('OCLC_CLIENT', None),
    'POST45_OCLC_SECRET': os.environ.get('OCLC_SECRET', None),
    'POST45_OCLC_CLUSTER_QUALITY_SCORE': 'high',
    'POST45_OCLC_BOOK_ONLY': False,
    'APP_BASE': 'http://localhost:5001/'
}

recon_query_1 = {'query': 'To the Lighthouse', 'type': 'OCLC_Record', 'req_ip': 'test', 'properties': [{'pid': 'contributor_uncontrolled_last_first', 'v': 'Virginia Woolf'}], 'type_strict': 'should'}
recon_query_2 = {'query': 'To the Lighthouse', 'type': 'OCLC_Record', 'req_ip': 'test', 'properties': [{'pid': 'contributor_uncontrolled_last_first', 'v': 'Virginia Woolf'}, {'pid': 'work_published_year', 'v': '1927'}], 'type_strict': 'should'}

# Sample OCLC data for testing
sample_oclc_data = [
    {
        "oclcNumber": "5119583",
        "isbns": ["0207949999", "9780207949999"],
        "mergedOclcNumbers": ["59196744", "220337150", "623455738"],
        "lccn": None,
        "creator": "Tennant, Kylie",
        "mainTitle": "Foveaux",
        "statementOfResponsibility": None,
        "classifications": {"dewey": "823", "lc": "PR6039.E55 .F6 1968"},
        "subjects": ["Australian fiction", "Roman australien", "Australian fiction"],
        "publicationDate": "[1968]",
        "itemLanguage": "eng",
        "generalFormat": "Book",
        "workId": "131910019"
    },
    {
        "oclcNumber": "1234567",
        "isbns": ["9780156787123"],
        "creator": "Woolf, Virginia",
        "mainTitle": "To the lighthouse",
        "generalFormat": "Book",
        "publicationDate": "1927",
        "itemLanguage": "eng",
        "subjects": ["Fiction", "Modernism"],
        "classifications": {"dewey": "823.912", "lc": "PR6045.O72"}
    },
    {
        "oclcNumber": "7654321",
        "creator": "Woolf, Virginia",
        "mainTitle": "Mrs. Dalloway",
        "generalFormat": "Audiobook",
        "publicationDate": "1925",
        "itemLanguage": "eng"
    }
]

# Sample raw OCLC API response for testing _extract_bib_data
sample_raw_oclc_response = {
    "numberOfRecords": 1,
    "bibRecords": [
        {
            "identifier": {
                "oclcNumber": "5119583",
                "isbns": ["0207949999", "9780207949999"],
                "mergedOclcNumbers": ["59196744", "220337150", "623455738"]
            },
            "title": {
                "mainTitles": [{"text": "Foveaux"}]
            },
            "contributor": {
                "creators": [
                    {
                        "firstName": {"text": "Kylie"},
                        "secondName": {"text": "Tennant"},
                        "type": "person",
                        "relators": [{"term": "Author"}]
                    }
                ]
            },
            "classification": {"dewey": "823", "lc": "PR6039.E55 .F6 1968"},
            "subjects": [
                {"subjectName": {"text": "Australian fiction"}},
                {"subjectName": {"text": "Roman australien"}},
                {"subjectName": {"text": "Australian fiction"}}
            ],
            "date": {"publicationDate": "[1968]"},
            "language": {"itemLanguage": "eng"},
            "format": {"generalFormat": "Book"},
            "work": {"id": "131910019"}
        }
    ]
}


def test__extract_bib_data():
	"""Test the _extract_bib_data function with sample OCLC API response"""
	
	result = _extract_bib_data(sample_raw_oclc_response)
	
	# Check that we get a list
	assert isinstance(result, list), "Result should be a list"
	assert len(result) == 1, "Should have one extracted record"
	
	# Test the extracted record
	record = result[0]
	assert record['oclcNumber'] == "5119583", "OCLC number should be extracted correctly"
	assert record['isbns'] == ["0207949999", "9780207949999"], "ISBNs should be extracted"
	assert record['creator'] == "Tennant, Kylie", "Creator should be formatted correctly"
	assert record['mainTitle'] == "Foveaux", "Main title should be extracted"
	assert record['classifications']['dewey'] == "823", "Dewey classification should be extracted"
	assert record['classifications']['lc'] == "PR6039.E55 .F6 1968", "LC classification should be extracted"
	assert record['subjects'] == ["Australian fiction", "Roman australien", "Australian fiction"], "Subjects should be extracted"
	assert record['publicationDate'] == "[1968]", "Publication date should be extracted"
	assert record['itemLanguage'] == "eng", "Language should be extracted"
	assert record['generalFormat'] == "Book", "Format should be extracted"
	assert record['workId'] == "131910019", "Work ID should be extracted"
	
	print("_extract_bib_data test passed!")


def test__get_creator_name():
	"""Test the _get_creator_name function with different contributor structures"""
	
	# Test with standard creator
	contributor_1 = {
		"creators": [
			{
				"firstName": {"text": "Virginia"},
				"secondName": {"text": "Woolf"},
				"type": "person",
				"relators": [{"term": "Author"}]
			}
		]
	}
	
	result = _get_creator_name(contributor_1)
	assert result == "Woolf, Virginia", "Should format name as Last, First"
	
	# Test with editor (should be skipped)
	contributor_2 = {
		"creators": [
			{
				"firstName": {"text": "John"},
				"secondName": {"text": "Editor"},
				"type": "person",
				"relators": [{"term": "editor"}]
			},
			{
				"firstName": {"text": "Jane"},
				"secondName": {"text": "Author"},
				"type": "person",
				"relators": [{"term": "Author"}]
			}
		]
	}
	
	result = _get_creator_name(contributor_2)
	assert result == "Author, Jane", "Should skip editor and return author"
	
	# Test with no valid creators
	contributor_3 = {
		"creators": [
			{
				"firstName": {"text": "Editor"},
				"secondName": {"text": "Only"},
				"type": "person",
				"relators": [{"term": "editor"}]
			}
		]
	}
	
	result = _get_creator_name(contributor_3)
	assert result is None, "Should return None when no valid creators found"
	
	print("_get_creator_name test passed!")


def test__add_fuzzy_scores():
	"""Test the _add_fuzzy_scores function with sample data"""
	
	reconcile_item = {
		"title": "To the Lighthouse",
		"author_name": "Virginia Woolf"
	}
	
	config = {
		'POST45_OCLC_CLUSTER_QUALITY_SCORE': 'high',
		'POST45_OCLC_BOOK_ONLY': False
	}
	
	result = _add_fuzzy_scores(sample_oclc_data, reconcile_item, config)
	
	# Check structure
	assert result['successful'] == True, "Should be successful"
	assert result['error'] is None, "Should have no error"
	assert 'results' in result, "Should have results key"
	
	results = result['results']
	assert len(results) > 0, "Should have at least one result"
	
	# Check that fuzzy scores were added
	for item in results:
		assert 'fuzzy_score' in item, "Each item should have fuzzy_score"
		assert 'title_score' in item, "Each item should have title_score"
		assert 'author_score' in item, "Each item should have author_score"
		assert 0 <= item['fuzzy_score'] <= 1, "Fuzzy score should be between 0 and 1"
	
	# Check that results are sorted by score
	scores = [item['fuzzy_score'] for item in results]
	assert scores == sorted(scores, reverse=True), "Results should be sorted by score descending"
	
	# The perfect match should have the highest score
	best_match = results[0]
	assert best_match['creator'] == "Woolf, Virginia", "Best match should be Virginia Woolf"
	assert best_match['mainTitle'] == "To the lighthouse", "Best match should be To the Lighthouse"
	assert best_match['fuzzy_score'] >= 0.9, "Perfect match should have high score"
	
	print("_add_fuzzy_scores test passed!")


def test__add_fuzzy_scores_books_only():
	"""Test the _add_fuzzy_scores function with books-only filter"""
	
	reconcile_item = {
		"title": "To the Lighthouse", 
		"author_name": "Virginia Woolf"
	}
	
	config = {
		'POST45_OCLC_CLUSTER_QUALITY_SCORE': 'medium',
		'POST45_OCLC_BOOK_ONLY': True
	}
	
	result = _add_fuzzy_scores(sample_oclc_data, reconcile_item, config)
	
	# Check that only books are included
	results = result['results']
	for item in results:
		assert item['generalFormat'] == 'Book', "Only books should be included when books-only filter is enabled"
	
	# Should exclude the audiobook
	oclc_numbers = [item['oclcNumber'] for item in results]
	assert '7654321' not in oclc_numbers, "Audiobook should be excluded"
	
	print("_add_fuzzy_scores books-only test passed!")


def test__cluster_works():
	"""Test the _cluster_works function"""
	
	data = {'results': sample_oclc_data}
	reconcile_item = {
		"title": "To the Lighthouse",
		"author_name": "Virginia Woolf"
	}
	req_ip = "test_ip"
	
	result = _cluster_works(data, reconcile_item, req_ip)
	
	# Check structure
	assert 'or_query_response' in result, "Should have or_query_response"
	assert len(result['or_query_response']) == 1, "Should have one cluster result"
	
	cluster_result = result['or_query_response'][0]
	assert cluster_result['score'] == 1, "Cluster should have score of 1"
	assert cluster_result['match'] == True, "Cluster should be marked as match"
	assert cluster_result['type'][0]['id'] == 'oclc', "Type should be oclc"
	assert cluster_result['type'][0]['name'] == 'OCLC_WorldCat_Cluster', "Type name should be correct"
	assert cluster_result['id'].startswith('http://localhost:5001/cluster/oclc/'), "Should have correct cluster URL"
	assert f"Clustered Works: {len(sample_oclc_data)}" in cluster_result['name'], "Should show count of clustered works"
	
	print("_cluster_works test passed!")


def test__parse_single_results():
	"""Test the _parse_single_results function"""
	
	data = {'results': sample_oclc_data}
	reconcile_item = {
		"title": "To the Lighthouse",
		"author_name": "Virginia Woolf",
		"work_published_year": "1927"
	}
	
	result = _parse_single_results(data, reconcile_item)
	
	# Check structure
	assert 'or_query_response' in result, "Should have or_query_response"
	
	responses = result['or_query_response']
	assert len(responses) == len(sample_oclc_data), "Should have one response per input item"
	
	# Check each response
	for response in responses:
		assert 'id' in response, "Each response should have id"
		assert 'name' in response, "Each response should have name"
		assert 'description' in response, "Each response should have description"
		assert 'score' in response, "Each response should have score"
		assert 'match' in response, "Each response should have match"
		assert 'type' in response, "Each response should have type"
		
		assert response['id'].startswith('http://www.worldcat.org/oclc/'), "ID should be WorldCat URL"
		assert response['type'][0]['id'] == 'oclc_work', "Type should be oclc_work"
		assert response['type'][0]['name'] == 'OCLC WorldCat Work', "Type name should be correct"
		assert 0 <= response['score'] <= 100, "Score should be between 0 and 100"
		
		# Match should be consistent with score
		if response['score'] > 80:
			assert response['match'] == True, "High scores should be marked as matches"
		else:
			assert response['match'] == False, "Low scores should not be marked as matches"
	
	# Check that results are sorted by score
	scores = [resp['score'] for resp in responses]
	assert scores == sorted(scores, reverse=True), "Results should be sorted by score descending"
	
	# Year boost should apply to the 1927 publication
	woolf_lighthouse = next((r for r in responses if r['score'] > 90 and 'lighthouse' in r['name'].lower()), None)
	assert woolf_lighthouse is not None, "Should find the Virginia Woolf To the Lighthouse result"
	
	print("_parse_single_results test passed!")


def test__search_worldcat():
	"""Test _search_worldcat - this will be mocked or skipped if no OCLC credentials"""
	
	# Only run this test if we have OCLC credentials
	if not (OCLC_CONFIG['POST45_OCLC_CLIENT_ID'] and OCLC_CONFIG['POST45_OCLC_SECRET']):
		print("Skipping _search_worldcat test - no OCLC credentials available")
		return
	
	print("Running live OCLC search test...")
	result = _search_worldcat("To the Lighthouse", "Virginia Woolf", OCLC_CONFIG)
	
	# Basic structure checks
	assert isinstance(result, list), "Result should be a list"
	assert len(result) > 0, "Should have at least one result"
	
	# Check first result structure
	first_result = result[0]
	expected_fields = ['oclcNumber', 'mainTitle', 'creator']
	for field in expected_fields:
		assert field in first_result, f"Result should contain {field}"
	
	print("Live OCLC search test passed!")



# import os
# from ..strategies_oclc import _search_worldcat #, _enrich_id, _parse_single_results
# from ..strategies_helpers import _build_recon_dict

# # OCLC configuration dictionary
# # Gets values from environment variables if they exist, otherwise sets to None
# OCLC_CONFIG = {
#     'POST45_OCLC_CLIENT_ID': os.environ.get('OCLC_CLIENT', None),
#     'POST45_OCLC_SECRET': os.environ.get('OCLC_SECRET', None)
# }

# recon_query_1 = {'query': 'To the Lighthouse', 'type': 'LC_Work_Id', 'req_ip': 'test', 'properties': [{'pid': 'contributor_uncontrolled_last_first', 'v': 'Virginia Woolf'}], 'type_strict': 'should'}
# recon_query_2 = {'query': 'To the Lighthouse', 'type': 'LC_Work_Id', 'req_ip': 'test', 'properties': [{'pid': 'contributor_uncontrolled_last_first', 'v': 'Virginia Woolf'}, {'pid': 'work_published_year', 'v': '1927'}], 'type_strict': 'should'}


# def test__search_worldcat():

# 	searh_results ={"numberOfRecords": 2208, "bibRecords": [{"identifier": {"oclcNumber": "857110087", "isbns": ["9781782125457", "1782125450"], "externalIdentifiers": [{"oclcSymbol": "UKMGB", "systemControlNumber": "016478653"}, {"oclcSymbol": "DKDLA", "systemControlNumber": "870970-basis:45663752"}], "mergedOclcNumbers": ["903595444"]}, "title": {"mainTitles": [{"text": "Virginia Woolf collection / by Virginia Woolf"}]}, "contributor": {"creators": [{"firstName": {"text": "Virginia"}, "secondName": {"text": "Woolf"}, "isPrimary": True, "includes": [{"title": "Mrs. Dalloway"}, {"title": "Orlando"}, {"title": "To the lighthouse"}, {"title": "Room of one's own"}], "type": "person", "creatorNotes": ["1882-1941, author."], "relators": [{"term": "Author", "alternateTerm": "aut"}]}], "statementOfResponsibility": {"text": "by Virginia Woolf."}}, "classification": {"dewey": "823.912", "lc": "PR6045.O72"}, "publishers": [{"publisherName": {"text": "Arcturus"}, "publicationPlace": "London"}], "date": {"publicationDate": "2013", "machineReadableDate": "2013", "createDate": "20130626", "replaceDate": "20250624"}, "language": {"itemLanguage": "eng", "catalogingLanguage": "eng"}, "format": {"generalFormat": "Book", "specificFormat": "PrintBook", "materialTypes": ["fic"]}, "description": {"physicalDescription": "pages cm", "contents": [{"contentNote": {"text": "Mrs Dalloway -- Orlando -- To the lighthouse -- A room of one's own."}}], "peerReviewed": "N"}, "work": {"id": "9028459844", "count": 13}, "editionCluster": {"id": "ea7c4dc69523e9a2387318a871372c1d"}, "database": {"source": "xwc", "collection": "xwc"}}, {"identifier": {"oclcNumber": "225416640", "isbns": ["4841100024", "9784841100020"]}, "title": {"mainTitles": [{"text": "Virginia Woolf / edited with an introduction and notes by Tadanobu Sakamoto"}], "seriesTitles": [{"seriesTitle": "Seminars on modern English and American literature", "volume": "no. 10"}, {"seriesTitle": "Seminars on modern English and American literature", "volume": "no. 10"}], "uniformTitles": ["Works. Selections. 1980"]}, "contributor": {"creators": [{"firstName": {"text": "Virginia"}, "secondName": {"text": "Woolf"}, "isPrimary": True, "includes": [{"title": "Mrs. Dalloway in Bond Street"}, {"title": "To the lighthouse"}], "type": "person", "creatorNotes": ["1882-1941."]}, {"firstName": {"text": "\u5742\u672c\u516c\u5ef6", "romanizedText": "Tadanobu", "languageCode": "JA", "textDirection": "LTR"}, "secondName": {"romanizedText": "Sakamoto", "languageCode": "JA", "textDirection": "LTR"}, "isPrimary": False, "type": "person", "creatorNotes": ["1931-"]}, {"firstName": {"text": "Tadanobu"}, "secondName": {"text": "Sakamoto"}, "isPrimary": False, "type": "person", "creatorNotes": ["1931- editor."], "relators": [{"term": "Editor", "alternateTerm": "edt"}]}], "statementOfResponsibility": {"text": "edited with an introduction and notes by Tadanobu Sakamoto."}}, "subjects": [{"subjectName": {"text": "Woolf, Virginia, 1882-1941 Criticism and interpretation"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "personalName"}, {"subjectName": {"text": "Woolf, Virginia, 1882-1941"}, "vocabulary": "fast", "subjectType": "personalName", "uri": "https://id.oclc.org/worldcat/entity/E39PBJqKgYt3RrY4vtrh9j9CcP"}, {"subjectName": {"text": "English fiction 20th century"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "topic"}, {"subjectName": {"text": "Roman anglais 20e sie\u0300cle"}, "vocabulary": "R\u00e9pertoire de vedettes-mati\u00e8re", "subjectType": "topic"}, {"subjectName": {"text": "English fiction"}, "vocabulary": "fast", "subjectType": "topic"}, {"subjectName": {"text": "Criticism, interpretation, etc"}, "vocabulary": "fast", "subjectType": "genreFormTerm"}, {"subjectName": {"text": "1900-1999"}, "vocabulary": "fast", "subjectType": "chronologyTerm"}], "classification": {"dewey": "823", "lc": "PR6045.O72 A6 1980"}, "publishers": [{"publisherName": {"text": "\u5c71\u53e3\u66f8\u5e97", "romanizedText": "Yamaguchi Shoten", "languageCode": "JA", "textDirection": "LTR"}, "publicationPlace": "Kyo\u0304to-shi"}], "date": {"publicationDate": "1980", "machineReadableDate": "1980", "createDate": "20010522", "replaceDate": "20250529"}, "language": {"itemLanguage": "jpn", "catalogingLanguage": "eng"}, "note": {"languageNotes": ["Text in English, introduction and notes in Japanese"]}, "format": {"generalFormat": "Book", "specificFormat": "PrintBook", "materialTypes": ["fic"]}, "description": {"physicalDescription": "ii pages, 1 unnumbered leaf, 250 pages, 2 unnumbered leaves ; 22 cm", "genres": ["Criticism, interpretation, etc"], "contents": [{"contentNote": {"text": "Preface --Introduction --Text: Modern fiction, Mrs. Dalloway in Bond Street, To the lighthouse [abridged] --Critics on Virginia Woolf: Elizabeth Boyd, James Hafley, D.S. Savage, N.C. Thakur, M.C. Bradbrook --Notes --Bibliography --Chronology."}}], "bibliographies": [{"text": "Includes bibliographical references"}], "peerReviewed": "N"}, "work": {"id": "2287347962", "count": 104}, "editionCluster": {"id": "a6c91b48287de72c206ef11693f5afa9"}, "database": {"source": "xwc", "collection": "xwc"}}, {"identifier": {"oclcNumber": "910650560", "isbns": ["9781782125457", "1782125450"], "externalIdentifiers": [{"oclcSymbol": "DKDLA", "systemControlNumber": "870970-basis:45663752"}]}, "title": {"mainTitles": [{"text": "Virginia Woolf collection"}]}, "contributor": {"creators": [{"firstName": {"text": "Virginia"}, "secondName": {"text": "Woolf"}, "isPrimary": True, "type": "person", "creatorNotes": ["aut"], "relators": [{"term": "Author", "alternateTerm": "aut"}]}]}, "classification": {"dewey": "823.912"}, "publishers": [{"publisherName": {"text": "Arcturus"}, "publicationPlace": "London"}], "date": {"publicationDate": "2013", "machineReadableDate": "2013", "createDate": "20150603", "replaceDate": "20250624"}, "language": {"itemLanguage": "eng", "catalogingLanguage": "dan"}, "note": {"generalNotes": [{"text": "Originaludgaver: 1925, 1927, 1928 og 1928", "local": "N"}]}, "format": {"generalFormat": "Book", "specificFormat": "PrintBook", "materialTypes": ["fic"]}, "description": {"physicalDescription": "704 sider", "contents": [{"contentNote": {"text": "Mrs Dalloway -- Orlando -- To the lighthouse -- A room of one's own"}, "titles": ["Mrs Dalloway --", "Orlando --", "To the lighthouse --", "A room of one's own"]}], "peerReviewed": "N"}, "work": {"id": "9028459844", "count": 13}, "editionCluster": {"id": "ea7c4dc69523e9a2387318a871372c1d"}, "database": {"source": "xwc", "collection": "xwc"}}, {"identifier": {"oclcNumber": "1346516965", "isbns": ["9781398819306", "1398819301"], "externalIdentifiers": [{"oclcSymbol": "UKMGB", "systemControlNumber": "020744955"}]}, "title": {"mainTitles": [{"text": "The Virginia Woolf collection / Virginia Woolf"}], "uniformTitles": ["Novels. Selections"]}, "contributor": {"creators": [{"firstName": {"text": "Virginia"}, "secondName": {"text": "Woolf"}, "isPrimary": True, "includes": [{"title": "Voyage out"}, {"title": "Mrs. Dalloway"}, {"title": "Orlando"}, {"title": "To the lighthouse"}, {"title": "Room of one's own"}], "type": "person", "creatorNotes": ["1882-1941, author."], "relators": [{"term": "Author", "alternateTerm": "aut"}]}], "statementOfResponsibility": {"text": "Virginia Woolf."}}, "subjects": [{"subjectName": {"text": "Sex role Fiction"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "topic"}, {"subjectName": {"text": "Ro\u0302le selon le sexe Romans, nouvelles, etc"}, "vocabulary": "R\u00e9pertoire de vedettes-mati\u00e8re", "subjectType": "topic"}, {"subjectName": {"text": "Manners and customs"}, "vocabulary": "fast", "subjectType": "topic"}, {"subjectName": {"text": "Sex role"}, "vocabulary": "fast", "subjectType": "topic"}, {"subjectName": {"text": "London (England) Social life and customs Fiction"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "geographicalTerm"}, {"subjectName": {"text": "Londres (Angleterre) M\u0153urs et coutumes Romans, nouvelles, etc"}, "vocabulary": "R\u00e9pertoire de vedettes-mati\u00e8re", "subjectType": "geographicalTerm"}, {"subjectName": {"text": "England London"}, "vocabulary": "fast", "subjectType": "geographicalTerm", "uri": "https://id.oclc.org/worldcat/entity/E39PBJp68ckpMtKGHPFWQrwDMP"}, {"subjectName": {"text": "Fiction"}, "vocabulary": "fast", "subjectType": "genreFormTerm"}], "classification": {"dewey": "823.912"}, "publishers": [{"publisherName": {"text": "Arcturus"}, "publicationPlace": "London"}], "date": {"publicationDate": "2022", "machineReadableDate": "2022", "createDate": "20220909", "replaceDate": "20250623"}, "language": {"itemLanguage": "eng", "catalogingLanguage": "eng"}, "format": {"generalFormat": "Book", "specificFormat": "PrintBook", "materialTypes": ["fic"]}, "description": {"physicalDescription": "5 volumes ; 20 cm", "genres": ["Fiction", "Romans, nouvelles, etc"], "contents": [{"contentNote": {"text": "The voyage out -- Mrs Dalloway -- Orlando -- To the lighthouse -- A room of one's own."}}], "peerReviewed": "N"}, "work": {"id": "9028459844", "count": 13}, "editionCluster": {"id": "258384fa90762e69afd0737abeff29c8"}, "database": {"source": "xwc", "collection": "xwc"}}, {"identifier": {"oclcNumber": "52253858"}, "title": {"mainTitles": [{"text": "Virginia Woolf papers, 1902-1956"}]}, "contributor": {"creators": [{"firstName": {"text": "Virginia"}, "secondName": {"text": "Woolf"}, "isPrimary": True, "includes": [{"title": "Common reader"}, {"title": "Orlando"}, {"title": "To the lighthouse"}], "type": "person", "creatorNotes": ["1882-1941."]}, {"firstName": {"text": "Lytton"}, "secondName": {"text": "Strachey"}, "isPrimary": False, "type": "person", "creatorNotes": ["1880-1932."]}, {"firstName": {"text": "Leonard"}, "secondName": {"text": "Woolf"}, "isPrimary": False, "type": "person", "creatorNotes": ["1880-1969."]}]}, "subjects": [{"subjectName": {"text": "Woolf, Virginia, 1882-1941"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "personalName"}, {"subjectName": {"text": "Bell, Quentin"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "personalName"}, {"subjectName": {"text": "Davidson, Angus, 1898-1982"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "personalName"}, {"subjectName": {"text": "Mansfield, Katherine, 1888-1923"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "personalName"}, {"subjectName": {"text": "Strachey, Lytton, 1880-1932"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "personalName"}, {"subjectName": {"text": "Walpole, Hugh, 1884-1941"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "personalName"}, {"subjectName": {"text": "Sackville-West, V. 1892-1962"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "personalName"}, {"subjectName": {"text": "Woolf, Leonard, 1880-1969"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "personalName"}, {"subjectName": {"text": "Bell, Quentin"}, "vocabulary": "fast", "subjectType": "personalName", "uri": "https://id.oclc.org/worldcat/entity/E39PBJrRhPMHW3B7Qhx6CBWbh3"}, {"subjectName": {"text": "Davidson, Angus, 1898-1982"}, "vocabulary": "fast", "subjectType": "personalName", "uri": "https://id.oclc.org/worldcat/entity/E39PBJk94DdTPpG4WPB6JP3fbd"}, {"subjectName": {"text": "Mansfield, Katherine, 1888-1923"}, "vocabulary": "fast", "subjectType": "personalName", "uri": "https://id.oclc.org/worldcat/entity/E39PBJkxGRhx8GMq7HMBCyBVmd"}, {"subjectName": {"text": "Sackville-West, V. 1892-1962"}, "vocabulary": "fast", "subjectType": "personalName", "uri": "https://id.oclc.org/worldcat/entity/E39PBJpdKf4ft3vqpbT4trt7pP"}, {"subjectName": {"text": "Strachey, Lytton, 1880-1932"}, "vocabulary": "fast", "subjectType": "personalName", "uri": "https://id.oclc.org/worldcat/entity/E39PBJdGQ9mVqbYFQTVT6PcVmd"}, {"subjectName": {"text": "Walpole, Hugh, 1884-1941"}, "vocabulary": "fast", "subjectType": "personalName", "uri": "https://id.oclc.org/worldcat/entity/E39PBJghhwp9hgxfgh3VmkjcT3"}, {"subjectName": {"text": "Woolf, Leonard, 1880-1969"}, "vocabulary": "fast", "subjectType": "personalName", "uri": "https://id.oclc.org/worldcat/entity/E39PBJgMFGDXhMgqqgwxWGVpyd"}, {"subjectName": {"text": "Woolf, Virginia, 1882-1941"}, "vocabulary": "fast", "subjectType": "personalName", "uri": "https://id.oclc.org/worldcat/entity/E39PBJqKgYt3RrY4vtrh9j9CcP"}, {"subjectName": {"text": "Hogarth Press"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "corporateName"}, {"subjectName": {"text": "Hogarth Press"}, "vocabulary": "fast", "subjectType": "corporateName", "uri": "https://id.oclc.org/worldcat/entity/E39QH7Jmp3fBTc9PQvGphBCHRg"}, {"subjectName": {"text": "Bloomsbury group"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "topic"}, {"subjectName": {"text": "Novelists, English 20th century Biography Sources"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "topic"}, {"subjectName": {"text": "Women novelists, English 20th century Biography Sources"}, "vocabulary": "Library of Congress Subject Headings", "subjectType": "topic"}, {"subjectName": {"text": "Groupe de Bloomsbury"}, "vocabulary": "R\u00e9pertoire de vedettes-mati\u00e8re", "subjectType": "topic"}, {"subjectName": {"text": "Bloomsbury group"}, "vocabulary": "fast", "subjectType": "topic"}, {"subjectName": {"text": "Novelists, English"}, "vocabulary": "fast", "subjectType": "topic"}, {"subjectName": {"text": "Women novelists, English"}, "vocabulary": "fast", "subjectType": "topic"}, {"subjectName": {"text": "1900-1999"}, "vocabulary": "fast", "subjectType": "chronologyTerm"}], "date": {"publicationDate": "1902", "machineReadableDate": "1956", "createDate": "20030515", "replaceDate": "20250712"}, "language": {"itemLanguage": "eng", "catalogingLanguage": "eng"}, "note": {"ownershipAndCustodialHistories": ["The bulk of the collection was assembled by Frances Hooper (1892-1986) and bequeathed to Smith College in 1986."]}, "format": {"generalFormat": "Archv"}, "digitalAccessAndLocations": [{"uri": "https://findingaids.smith.edu/repositories/3/resources/405", "publicNote": "Connect to finding aid."}], "description": {"physicalDescription": "2.25 linear ft. (6 boxes)", "genres": ["Biography Sources"], "summaries": [{"text": "Woolf papers include correspondence, reading notes, drafts of essays and short stories, printed ephemera and photographs. Includes letters from Woolf to Quentin Bell, Angus Davidson, Katherine Mansfield, Hugh Walpole and Vita Sackville-West. Also includes her corrected page proofs of The common reader, Orlando, and To the lighthouse"}], "peerReviewed": "N"}, "work": {"id": "9274831", "count": 1}, "editionCluster": {"id": "2a98fa80837350b7279c626337c5b306"}, "database": {"source": "xwc", "collection": "xwc"}}], "successful": True, "error": None}

# 	# if we have the oclc creds available do a live search instead
# 	if OCLC_CONFIG['POST45_OCLC_CLIENT_ID'] and OCLC_CONFIG['POST45_OCLC_SECRET']:
# 		print("DOING LIVE SEARCH",flush=True)
# 		searh_results = _search_worldcat("To the Lighthouse", "Virginia Woolf", OCLC_CONFIG)



# 	reconcile_item = _build_recon_dict(recon_query_1)
# 	reconcile_item['author_name'] = 'Virginia Woolf'
# 	search_results = _search_id(reconcile_item, {'POST45_ID_RDFTYPE_TEXT_LIMIT': True, 'POST45_RECONCILIATION_MODE': 'cluster', 'POST45_ID_CLUSTER_QUALITY_SCORE': 'high'})
# 	assert search_results['count'] > 0
# 	assert search_results['hits'][0]['suggestLabel'] == 'Woolf, Virginia, 1882-1941. To the lighthouse'
# 	assert search_results['hits'][0]['fuzzy_score'] == 0.95
# 	# we passed 'high' so we expect all fuzzy scores to be >= 0.90
# 	assert all(h['fuzzy_score'] >= 0.90 for h in search_results['hits'])

# def test__enrich_id():

# 	reconcile_item = _build_recon_dict(recon_query_1)
# 	reconcile_item['author_name'] = 'Virginia Woolf'
# 	search_results = _search_id(reconcile_item, {'POST45_ID_RDFTYPE_TEXT_LIMIT': True, 'POST45_RECONCILIATION_MODE': 'cluster', 'POST45_ID_CLUSTER_QUALITY_SCORE': 'high'})

# 	# make the result set a little smaller for testing
# 	search_results['hits'] = search_results['hits'][:2]
	
# 	enriched_results = _enrich_id(search_results)
# 	print('enriched_results', enriched_results,flush=True)
	
# 	# Test that the overall structure is preserved
# 	assert 'hits' in enriched_results, "Results should contain 'hits' key"
# 	assert len(enriched_results['hits']) == 2, "Should have 2 hits as limited"
# 	assert enriched_results.get('successful') == True, "Results should be marked as successful"
# 	assert enriched_results.get('error') == None, "Should have no error"
	
# 	# Test enrichment for each hit
# 	for hit in enriched_results['hits']:
# 		# Check that original fields are preserved
# 		assert 'uri' in hit, "Original URI should be preserved"
# 		assert 'suggestLabel' in hit, "Original suggestLabel should be preserved"
# 		assert 'fuzzy_score' in hit, "Fuzzy score should be preserved"
# 		assert 'title_score' in hit, "Title score should be preserved"
# 		assert 'author_score' in hit, "Author score should be preserved"
# 		assert 'more' in hit, "Original 'more' field should be preserved"
		
# 		# Check enrichment status
# 		if hit.get('enriched'):
# 			# If enriched successfully, check for expected fields
			
# 			# Check for Work-level fields (may or may not be present depending on the data)
# 			if 'originDate' in hit:
# 				assert isinstance(hit['originDate'], str), "originDate should be a string"
			
# 			if 'language' in hit:
# 				assert isinstance(hit['language'], str), "language should be a string"
# 				# Language codes are typically 3 letters (e.g., 'eng', 'fre', 'spa')
# 				assert len(hit['language']) == 3, "Language code should be 3 characters"
			
# 			if 'subjects' in hit:
# 				assert isinstance(hit['subjects'], list), "subjects should be a list"
# 				for subject in hit['subjects']:
# 					assert isinstance(subject, str), "Each subject should be a string"
			
# 			if 'genreForms' in hit:
# 				assert isinstance(hit['genreForms'], list), "genreForms should be a list"
# 				for genre in hit['genreForms']:
# 					assert isinstance(genre, str), "Each genre form should be a string"
			
# 			# Check for Instance-level fields
# 			if 'responsibilityStatement' in hit:
# 				assert isinstance(hit['responsibilityStatement'], str), "responsibilityStatement should be a string"
			
# 			if 'publicationStatement' in hit:
# 				assert isinstance(hit['publicationStatement'], str), "publicationStatement should be a string"
			
# 			if 'editionStatement' in hit:
# 				assert isinstance(hit['editionStatement'], str), "editionStatement should be a string"
			
# 			if 'extent' in hit:
# 				assert isinstance(hit['extent'], str), "extent should be a string"
			
# 			if 'dimensions' in hit:
# 				assert isinstance(hit['dimensions'], str), "dimensions should be a string"
			
# 			# Check identifiers structure
# 			if 'identifiers' in hit:
# 				assert isinstance(hit['identifiers'], list), "identifiers should be a list"
# 				for identifier in hit['identifiers']:
# 					assert isinstance(identifier, dict), "Each identifier should be a dictionary"
# 					assert 'type' in identifier, "Identifier should have a type"
# 					assert 'value' in identifier, "Identifier should have a value"
# 					assert identifier['type'] in ['ISBN', 'LCCN', 'OCLC'], "Type should be ISBN, LCCN, or OCLC"
# 					# ISBN may have a qualifier
# 					if identifier['type'] == 'ISBN' and 'qualifier' in identifier:
# 						assert isinstance(identifier['qualifier'], str), "ISBN qualifier should be a string"
			
# 			# Check provision activities structure
# 			if 'provisionActivities' in hit:
# 				assert isinstance(hit['provisionActivities'], list), "provisionActivities should be a list"
# 				for activity in hit['provisionActivities']:
# 					assert isinstance(activity, dict), "Each provision activity should be a dictionary"
# 					# Each activity may have date, place, and/or agent
# 					if 'date' in activity:
# 						assert isinstance(activity['date'], str), "Date should be a string"
# 					if 'place' in activity:
# 						assert isinstance(activity['place'], str), "Place should be a string"
# 					if 'agent' in activity:
# 						assert isinstance(activity['agent'], str), "Agent should be a string"
			
# 			# Check for multiple instances handling
# 			if 'allInstances' in hit:
# 				assert isinstance(hit['allInstances'], list), "allInstances should be a list"
# 				assert len(hit['allInstances']) > 1, "allInstances should contain multiple instances"
# 				for instance in hit['allInstances']:
# 					assert isinstance(instance, dict), "Each instance should be a dictionary"
# 					# Each instance may have similar fields to the main hit
		
# 		elif 'enrichment_error' in hit:
# 			# If enrichment failed, check error handling
# 			assert hit.get('enriched') == False, "Failed enrichment should be marked as False"
# 			assert isinstance(hit['enrichment_error'], str), "Error message should be a string"
# 			print(f"Enrichment failed for {hit.get('uri', 'unknown')}: {hit['enrichment_error']}")
		
# 		else:
# 			# Hit may not have been enriched at all (e.g., no instance URI)
# 			print(f"Hit not enriched: {hit.get('uri', 'unknown')} - possibly missing instance URI")


# def test__parse_single_results():
# 	reconcile_item = _build_recon_dict(recon_query_2)
# 	reconcile_item['author_name'] = 'Virginia Woolf'
# 	search_results = _search_id(reconcile_item, {'POST45_ID_RDFTYPE_TEXT_LIMIT': True, 'POST45_RECONCILIATION_MODE': 'single', 'POST45_ID_CLUSTER_QUALITY_SCORE': 'high'})
# 	# make the result set a little smaller for testing
# 	search_results['hits'] = search_results['hits'][:5]	
# 	enriched_results = _enrich_id(search_results)
# 	results = _parse_single_results(enriched_results, reconcile_item)
# 	assert results['or_query_response'][0]['id'] == 'http://id.loc.gov/resources/works/8737676'









