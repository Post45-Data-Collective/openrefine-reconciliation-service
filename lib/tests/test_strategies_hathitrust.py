from ..strategies_hathitrust import _download_hathitrust_html, _extract_hathitrust_data, _search_hathi, _parse_results
from ..strategies_helpers import _build_recon_dict


recon_query_1 = {'query': 'To the Lighthouse', 'type': 'HathiTrust', 'properties': [{'pid': 'contributor_uncontrolled_last_first', 'v': 'Virginia Woolf'}], 'type_strict': 'should'}



# def test_perform_hathi_search_title():
	
# 	html = _download_hathitrust_html("To the Lighthouse", "Virginia Woolf")
# 	assert 'uc1.32106009698983' in html
# 	assert 'uc1.b4091245' in html


# def test_extract_search_data():
	
# 	html = _download_hathitrust_html("To the Lighthouse", "Virginia Woolf")

# 	data = _extract_hathitrust_data(html)

# 	assert data is not None
# 	assert len(data) > 0
	
# 	print(data)
# 	for record in data:
# 		if 'uc1.32106009698983' in record['data_hdl']:
# 			assert record['title'] == 'To the lighthouse / Virginia Woolf ; foreword by Eudora Welty.'
# 			assert record['author'] == ['Woolf, Virginia, 1882-1941.']
# 			assert record['year_published'] == '1981'
# 			assert record['thumbnail_url'] == 'https://babel.hathitrust.org/cgi/imgsrv/cover?id=uc1.32106009698983;width=250'
# 			assert record['access_status'] == 'Multiple Items'
# 			assert record['record_number'] == '002547937'

# 			break			


def test_title_with_uncontrolled_name():
	
	reconcile_item = _build_recon_dict(recon_query_1)
	data = _search_hathi(reconcile_item)


	assert data is not None
	assert len(data) > 0

	search_results = _parse_results(data,reconcile_item)

	# print(search_results)

	# # we have to sort it, normally open refine will do that
	# newlist = sorted(search_results['or_query_response'], key=lambda d: d['score'],reverse=True)
	
	assert search_results['or_query_response'][0]['id'] == 'https://catalog.hathitrust.org/Record/001838398'
	







