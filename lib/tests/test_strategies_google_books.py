from ..strategies_google_books import _search_google_books, _parse_single_results, _cluster_works
from ..strategies_helpers import _build_recon_dict


recon_query_1 = {
    'query': 'The Great Gatsby',
    'type': 'LC_Work_Id',
    'req_ip': 'test',
    'properties': [{'pid': 'contributor_uncontrolled_last_first', 'v': 'F. Scott Fitzgerald'}],
    'type_strict': 'should'
}

recon_query_2 = {
    'query': 'The Great Gatsby',
    'type': 'LC_Work_Id',
    'req_ip': 'test',
    'properties': [
        {'pid': 'contributor_uncontrolled_last_first', 'v': 'F. Scott Fitzgerald'},
        {'pid': 'work_published_year', 'v': '1925'}
    ],
    'type_strict': 'should'
}

recon_query_3 = {
    'query': '1984',
    'type': 'LC_Work_Id',
    'req_ip': 'test',
    'properties': [{'pid': 'contributor_uncontrolled_last_first', 'v': 'George Orwell'}],
    'type_strict': 'should'
}


def test__search_google_books():
    """Test the Google Books search functionality."""
    
    reconcile_item = _build_recon_dict(recon_query_1)
    reconcile_item['author_name'] = 'F. Scott Fitzgerald'
    
    search_results = _search_google_books(
        reconcile_item, 
        {
            'POST45_RECONCILIATION_MODE': 'cluster',
            'POST45_GOOGLE_CLUSTER_QUALITY_SCORE': 'high',
            'POST45_REMOVE_SUBTITLE': True
        }
    )

    print("\n\n\n\n----------\n\n",search_results,flush=True    )
    
    # Test basic structure
    assert 'items' in search_results, "Search results should contain 'items' key"
    assert 'successful' in search_results, "Search results should contain 'successful' key"
    assert 'error' in search_results, "Search results should contain 'error' key"
    
    # Test successful search
    assert search_results['successful'] == True, "Search should be successful"
    assert search_results['error'] == None, "Should have no error"
    
    # Test results content
    if search_results['items'] and len(search_results['items']) > 0:
        first_result = search_results['items'][0]
        
        # Check required fields
        assert 'id' in first_result, "Result should have an 'id'"
        assert 'volumeInfo' in first_result, "Result should have 'volumeInfo'"
        
        volume_info = first_result['volumeInfo']
        
        # Check volume info fields
        assert 'title' in volume_info, "Volume info should have 'title'"
        
        # Check fuzzy scores (only if clustering is enabled)
        if 'fuzzy_score' in first_result:
            assert isinstance(first_result['fuzzy_score'], (int, float)), "Fuzzy score should be numeric"
            # Since we passed 'high' quality score, expect >= 0.90
            assert first_result['fuzzy_score'] >= 0.90, "High quality score should be >= 0.90"
        
        if 'title_score' in first_result:
            assert isinstance(first_result['title_score'], (int, float)), "Title score should be numeric"
        
        if 'author_score' in first_result:
            assert isinstance(first_result['author_score'], (int, float)), "Author score should be numeric"


def test__search_google_books_with_year():
    """Test Google Books search with publication year."""
    
    reconcile_item = _build_recon_dict(recon_query_2)
    reconcile_item['author_name'] = 'F. Scott Fitzgerald'
    reconcile_item['year'] = '1925'
    
    search_results = _search_google_books(
        reconcile_item, 
        {
            'POST45_RECONCILIATION_MODE': 'cluster',
            'POST45_GOOGLE_CLUSTER_QUALITY_SCORE': 'medium',
            'POST45_REMOVE_SUBTITLE': True
        }
    )
    
    assert search_results['successful'] == True, "Search should be successful"
    assert search_results['items'] is not None, "Should have items"
    
    if search_results['items'] and len(search_results['items']) > 0:
        # Check that results are filtered/scored appropriately
        for result in search_results['items'][:5]:  # Check top 5 results
            if 'fuzzy_score' in result:
                # With medium quality, expect >= 0.70
                assert result['fuzzy_score'] >= 0.70, "Medium quality score should be >= 0.70"


def test__cluster_works():
    """Test the clustering functionality for Google Books results."""
    
    # Create mock search results
    mock_records = [
        {
            'id': 'book1',
            'volumeInfo': {
                'title': 'The Great Gatsby',
                'authors': ['F. Scott Fitzgerald'],
                'publishedDate': '1925',
                'publisher': 'Scribner',
                'industryIdentifiers': [
                    {'type': 'ISBN_13', 'identifier': '9780743273565'},
                    {'type': 'ISBN_10', 'identifier': '0743273567'}
                ]
            }
        },
        {
            'id': 'book2',
            'volumeInfo': {
                'title': 'The Great Gatsby: Special Edition',
                'authors': ['F. Scott Fitzgerald'],
                'publishedDate': '1925-04-10',
                'publisher': 'Scribner & Sons'
            }
        },
        {
            'id': 'book3',
            'volumeInfo': {
                'title': 'The Great Gatsby',
                'authors': ['Fitzgerald, F. Scott'],
                'publishedDate': '1926',
                'description': 'A classic American novel'
            }
        }
    ]
    
    reconcile_item = _build_recon_dict(recon_query_1)
    reconcile_item['author_name'] = 'F. Scott Fitzgerald'
    
    clustered_results = _cluster_works(mock_records, reconcile_item, 'test_ip')
    print("clustered_resultsclustered_resultsclustered_resultsclustered_results",clustered_results,flush=True)
    # Test clustering structure
    assert isinstance(clustered_results['or_query_response'], list), "Clustered results should be a list"
    
    if len(clustered_results['or_query_response']) > 0:
        first_cluster = clustered_results['or_query_response'][0]
        

        
        # Check scores
        assert 'score' in first_cluster, "Should have score score"
        assert 'name' in first_cluster, "Should have name score"

        




def test__parse_single_results():
    """Test parsing results for single reconciliation mode."""
    
    reconcile_item = _build_recon_dict(recon_query_1)
    reconcile_item['author_name'] = 'F. Scott Fitzgerald'
    
    # Create mock enriched data
    mock_data = {
        'items': [
            {
                'id': 'book1',
                'fuzzy_score': 0.95,
                'title_score': 0.98,
                'author_score': 0.92,
                'volumeInfo': {
                    'title': 'The Great Gatsby',
                    'authors': ['F. Scott Fitzgerald'],
                    'publishedDate': '1925',
                    'publisher': 'Scribner',
                    'pageCount': 180,
                    'categories': ['Fiction', 'Classics'],
                    'industryIdentifiers': [
                        {'type': 'ISBN_13', 'identifier': '9780743273565'}
                    ],
                    'imageLinks': {
                        'thumbnail': 'http://example.com/thumbnail.jpg'
                    }
                }
            },
            {
                'id': 'book2',
                'fuzzy_score': 0.85,
                'title_score': 0.88,
                'author_score': 0.82,
                'volumeInfo': {
                    'title': 'The Great Gatsby: Annotated',
                    'authors': ['F. Scott Fitzgerald'],
                    'publishedDate': '1925'
                }
            }
        ],
        'successful': True,
        'error': None
    }
    
    results = _parse_single_results(mock_data, reconcile_item)
    
    # Test basic structure
    assert 'or_query_response' in results, "Should have 'or_query_response' key"
    assert isinstance(results['or_query_response'], list), "Response should be a list"
    
    # Test first result
    if len(results['or_query_response']) > 0:
        first_result = results['or_query_response'][0]
        
        # Check required OpenRefine fields
        assert 'id' in first_result, "Result should have 'id'"
        assert 'name' in first_result, "Result should have 'name'"
        assert 'score' in first_result, "Result should have 'score'"
        assert 'match' in first_result, "Result should have 'match' field"
        assert 'type' in first_result, "Result should have 'type' field"
        
        # Check score is reasonable
        assert isinstance(first_result['score'], (int, float)), "Score should be numeric"
        assert 0 <= first_result['score'] <= 1, "Score should be between 0 and 1"
        
        # Check that match is boolean
        assert isinstance(first_result['match'], bool), "Match should be boolean"
        
        # Check type structure
        assert isinstance(first_result['type'], list), "Type should be a list"
        if len(first_result['type']) > 0:
            assert 'id' in first_result['type'][0], "Type should have 'id'"
            assert 'name' in first_result['type'][0], "Type should have 'name'"


def test__search_google_books_with_numeric_title():
    """Test Google Books search with numeric title (like '1984')."""
    
    reconcile_item = _build_recon_dict(recon_query_3)
    reconcile_item['author_name'] = 'George Orwell'
    
    search_results = _search_google_books(
        reconcile_item, 
        {
            'POST45_RECONCILIATION_MODE': 'single',
            'POST45_GOOGLE_CLUSTER_QUALITY_SCORE': 'high',
            'POST45_REMOVE_SUBTITLE': False
        }
    )
    
    assert search_results['successful'] == True, "Search should be successful"
    
    # Numeric titles might need special handling
    if search_results['items'] and len(search_results['items']) > 0:
        # Check that we got relevant results
        found_orwell = False
        for result in search_results['items'][:10]:
            if 'volumeInfo' in result and 'authors' in result['volumeInfo']:
                authors = result['volumeInfo']['authors']
                for author in authors:
                    if 'Orwell' in author:
                        found_orwell = True
                        break
        
        # We expect to find at least one Orwell book in top results
        assert found_orwell, "Should find George Orwell in results for '1984'"

