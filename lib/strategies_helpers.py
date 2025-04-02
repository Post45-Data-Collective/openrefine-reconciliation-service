import unicodedata
import string
import re
import requests
import os
import xml.etree.ElementTree as ET


GENERIC_HEADERS = {
	'User-Agent':'Openrefine Post45 Reconcilation Client'
}



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
		'birth_year': False,
		'type': recon_query['type'],
	}

	if 'properties' in recon_query:
		for prop in recon_query['properties']:
			if prop['pid'] == 'title':
				reconcile_item['title'] = _build_title_for_uncontrolled_name_search(prop['v'])
			if prop['pid'] == 'birth_year':
				reconcile_item['birth_year'] = _build_birth_year_name_search(prop['v'])


	return reconcile_item




def _build_birth_year_name_search(years):

	all_years = re.findall("[0-9]{4}",years)

	if len(all_years) > 0:
		return all_years[0]
	else:
		return False


def _build_title_for_uncontrolled_name_search(title):
	"""
		takes a tile and parses it for how this endpoint works best

	"""
	title = title.split(":")[0].strip()
	title = title.split(";")[0].strip()
	return title



def _download_viaf_cluster_rdf(uri):

	# if we already downloaded in cache
	passed_id_escaped = uri.replace(":",'_').replace("/",'_')
	if os.path.isfile(f'data/cache/cluster_{passed_id_escaped}'):
		with open(f'data/cache/cluster_{passed_id_escaped}', 'r') as f:
			data = f.read()

		return data

	try:
		useId = uri.split("/")[-1]
		json_data = {
			'reqValues': {
				'recordId': useId,
				'isSourceId': False,
        		'acceptFiletype': 'xml',
			},
			'meta': {
				'env': 'prod',
				'pageIndex': 0,
				'pageSize': 1,
			},
		}
		

		response = requests.post('https://viaf.org/api/cluster-record', headers=GENERIC_HEADERS, json=json_data)

		

		file_name = uri.replace(':','_').replace('/','_')
		with open(f'data/cache/cluster_{file_name}','w') as out:
			out.write(response.text)


		return response.text


	except requests.exceptions.RequestException as e:  
		print("ERROR:", e)
		# create a response 
		return False		






def _extract_identifier_from_viaf_xml(viaf_XML,ident="WKP"):
	
	tree = ET.ElementTree(ET.fromstring(viaf_XML))
	sources = tree.findall("./{http://viaf.org/viaf/terms#}sources")
	if len(sources) > 0:
		sources = sources[0]
	else:
		return False

	for child in sources:
		if f"{ident}|" in child.text:
			value = child.text.split(f"{ident}|")[1]

			# just normalize lc here
			if ident == 'LC':
				value = value.replace(' ','')
			return value
	return False


def _return_lc_suggest2_data(lccn):

	url = f"https://id.loc.gov/authorities/names/suggest2/?q={lccn}"

	try:
		# Send the request
		response = requests.get(url, headers=GENERIC_HEADERS)
		response.raise_for_status()  # Raise an exception for bad status codes
		
		results = response.json()
		
		if results:
			if 'hits' in results:
				if len(results['hits']) > 0:
					if lccn in results['hits'][0]['uri']:
						return results['hits'][0]['more']
			
		

		return False



	except requests.exceptions.RequestException as e:
		print(f"Error making request: {e}")
		return False


def _return_wikidata_value(qid,pid):

	endpoint_url = "https://query.wikidata.org/sparql"
		
	sparql_query = """
		Select ?item ?itemLabel ?value ?valueLabel where{
		  BIND(wd:<QID> AS ?item) 
		  ?item wdt:<PID> ?value
		  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],mul,en". } 
		}
	""".replace('<QID>',qid).replace('<PID>',pid)


	# Set up the request parameters
	params = {
		'query': sparql_query,
		'format': 'json'
	}
	
	# Set headers to identify your application
	headers = {
		'User-Agent': 'Openrefine Post45 Reconcilation Client',
		'Accept': 'application/json'
	}
	
	try:
		# Send the request
		response = requests.get(endpoint_url, params=params, headers=headers)
		response.raise_for_status()  # Raise an exception for bad status codes
		
		results = response.json()
		return_data = []		
		if results:
			for binding in results['results']['bindings']:
				value = binding['value']['value']
				valueLabel = binding['valueLabel']['value']				
				return_item = {
					'value':value,
					'valueLabel':valueLabel
				}
				return_data.append(return_item)
				
		else:
			return_data = False

		if len(return_data) == 0:
			return False
		# Return the JSON results
		return return_data
	
	except requests.exceptions.RequestException as e:
		print(f"Error making request: {e}")
		return None






def wikidata_return_birth_year_from_viaf_uri(uri):
	xml = _download_viaf_cluster_rdf(uri)
	
	if xml == False:
		return False
	qid = _extract_identifier_from_viaf_xml(xml,'WKP')
	if qid == False:
		return False
	birth_date = _return_wikidata_value(qid,'P569')
	if birth_date == False:
		return False


	if len(birth_date) > 0:
		birth_date = birth_date[0]['value']
		birth_date = birth_date.split("-")[0]
		return birth_date
	else:
		return False

	

def lc_return_birth_year_from_viaf_uri(uri):
	xml = _download_viaf_cluster_rdf(uri)
	if xml == False:
		return False
	lccn = _extract_identifier_from_viaf_xml(xml,'LC')
	if lccn == False:
		return False
	data = _return_lc_suggest2_data(lccn)
	if data == False:
		return False


	if 'birthdates' in data:
		if len(data['birthdates']) > 0:
			return data['birthdates'][0].strip().split("-")[0]

	return False


def has_numbers(input_string):
	for char in input_string:
		if char.isdigit():
			return True
	return False



# from thefuzz import fuzz


def normalize_string(s, remove_numbers=False):
	s = str(s)
	s = s.translate(str.maketrans('', '', string.punctuation))
	s = " ".join(s.split())
	s = s.lower()
	s = s.casefold()
	s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
	s = s.replace('the ','')

	if remove_numbers == True:
		remove_digits = str.maketrans('', '', string.digits)
		s = s.translate(remove_digits)

	return s
