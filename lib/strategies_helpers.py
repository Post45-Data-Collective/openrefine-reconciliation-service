import unicodedata
import string

def _build_recon_dict(recon_query):

	reconcile_item = {
		'title': _build_title_for_uncontrolled_name_search(recon_query['query']),
		'type': recon_query['type'],
		'contributor_uncontrolled_last_first': False,
		'contributor_uncontrolled_first_last': False,
		'contributor_naco_controlled': False
	}

	if 'properties' in recon_query:

		for prop in recon_query['properties']:
			if prop['pid'] == 'contributor_uncontrolled_last_first':
				reconcile_item['contributor_uncontrolled_last_first'] = prop['v']
			if prop['pid'] == 'contributor_uncontrolled_first_last':
				reconcile_item['contributor_uncontrolled_first_last'] = prop['v']
			if prop['pid'] == 'contributor_naco_controlled':
				reconcile_item['contributor_naco_controlled'] = prop['v']

	return reconcile_item


def _build_recon_dict_name(recon_query):

	reconcile_item = {
		'name': recon_query['query'],
		'title': False,
		'type': recon_query['type'],
	}

	if 'properties' in recon_query:
		for prop in recon_query['properties']:
			if prop['pid'] == 'title':
				reconcile_item['title'] = _build_title_for_uncontrolled_name_search(prop['v'])


	return reconcile_item



def _build_title_for_uncontrolled_name_search(title):
	"""
		takes a tile and parses it for how this endpoint works best

	"""
	title = title.split(":")[0].strip()
	title = title.split(";")[0].strip()
	return title






# from thefuzz import fuzz


def normalize_string(s):
    s = str(s)
    s = s.translate(str.maketrans('', '', string.punctuation))
    s = " ".join(s.split())
    s = s.lower()
    s = s.casefold()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = s.replace('the','')
    return s
