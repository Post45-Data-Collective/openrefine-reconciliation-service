
from ..strategies_hathitrust import verify_sqlite_ready, _search_local_hathi_db, _cluster_works, _parse_results

from ..strategies_helpers import _build_recon_dict


recon_query_1 = {'query': 'To the Lighthouse', 'type': 'HathiTrust', 'properties': [{'pid': 'contributor_uncontrolled_last_first', 'v': 'Virginia Woolf'}], 'type_strict': 'should'}

recon_query_2 = {'query': 'To the Lighthouse', 'type': 'HathiTrust', 'properties': [{'pid': 'contributor_uncontrolled_last_first', 'v': 'Virginia Woolf'}, {'pid': 'work_published_year', 'v': '1955'}], 'type_strict': 'should'}


def test_search_local_hathi_db():
	records = _search_local_hathi_db('To the Lighthouse', 'Virginia Woolf', test_mode=True)
	all_ht_bib_keys = [r['ht_bib_key'] for r in records]
	assert 182174 in all_ht_bib_keys
	assert 7103126 in all_ht_bib_keys

	records = _search_local_hathi_db('To the Lighthouse', 'Woolf, Virginia, 1882-1941', test_mode=True)
	all_ht_bib_keys = [r['ht_bib_key'] for r in records]
	assert 182174 in all_ht_bib_keys
	assert 7103126 in all_ht_bib_keys


def test_cluster_works():
	reconcile_item = _build_recon_dict(recon_query_1)
	records = _search_local_hathi_db(reconcile_item['title'], reconcile_item['contributor_uncontrolled_last_first'], test_mode=True)
	clusters = _cluster_works(records, reconcile_item, 'test')
	assert clusters['or_query_response'][0]['name'].lower() == 'clustered: 9, excluded: 0'

def test_single_match():
	reconcile_item = _build_recon_dict(recon_query_2)
	records = _search_local_hathi_db(reconcile_item['title'], reconcile_item['contributor_uncontrolled_last_first'], test_mode=True)
	match = _parse_results(records, reconcile_item)

	found_record = False
	for r in match['or_query_response']:
		if r['id'] == 'https://catalog.hathitrust.org/Record/182174':
			found_record = True
	# print("-------")
	# print(match)
	assert found_record == True



