from ..strategies_id_loc_gov import _parse_title_uncontrolled_name_results
from ..strategies_helpers import _build_recon_dict



recon_query_1 = {'query': 'The bomb that fell on America', 'type': 'LC_Work_Id', 'properties': [{'pid': 'contributor_uncontrolled_last_first', 'v': 'Hagedorn, Hermann'}], 'type_strict': 'should'}
id_reponse_1 = {'q': 'Hagedorn, Hermann The bomb that fell on America', 'count': 2, 'pagesize': 10, 'start': 1, 'sortmethod': 'rank', 'searchtype': 'keyword', 'directory': '/resources/works/', 'hits': [{'suggestLabel': 'Hagedorn, Hermann, 1882-1964 The bomb that fell on America', 'uri': 'http://id.loc.gov/resources/works/9747877', 'aLabel': 'Hagedorn, Hermann, 1882-1964 The bomb that fell on America', 'vLabel': '', 'code': '', 'rank': '9831'}, {'suggestLabel': 'Hagedorn, Hermann, 1882-1964 The bomb that fell on America', 'uri': 'http://id.loc.gov/resources/works/6489697', 'aLabel': 'Hagedorn, Hermann, 1882-1964 The bomb that fell on America', 'vLabel': '', 'code': '', 'rank': '8123'}], 'successful': True, 'error': None}





def test__build_recon_dict():
	
	reconcile_item = _build_recon_dict(recon_query_1)
	assert reconcile_item['title'] == 'The bomb that fell on America'
	assert reconcile_item['contributor_uncontrolled_last_first'] == 'Hagedorn, Hermann'



def test__parse_title_uncontrolled_name_results():


	reconcile_item = _build_recon_dict(recon_query_1)
	print('reconcile_item',reconcile_item)
	results = _parse_title_uncontrolled_name_results(id_reponse_1,reconcile_item)

	

	






