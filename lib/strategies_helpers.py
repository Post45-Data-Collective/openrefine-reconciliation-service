import unicodedata
import string
import re
import requests
import os
import xml.etree.ElementTree as ET
import json

GENERIC_HEADERS = {
	'User-Agent':'Openrefine Post45 Reconcilation Client'
}



def _build_recon_dict(recon_query):
	# print("being passed:",recon_query, flush=True)
	reconcile_item = {
		'title': _build_title_for_uncontrolled_name_search(recon_query['query']),
		'type': recon_query['type'],
		'contributor_uncontrolled_last_first': False,
		'contributor_uncontrolled_first_last': False,
		'contributor_naco_controlled': False,
		'work_published_year': False
	}

	if 'properties' in recon_query:

		for prop in recon_query['properties']:
			if prop['pid'] == 'contributor_uncontrolled_last_first':
				reconcile_item['contributor_uncontrolled_last_first'] = prop['v']
			if prop['pid'] == 'contributor_uncontrolled_first_last':
				reconcile_item['contributor_uncontrolled_first_last'] = prop['v']
			if prop['pid'] == 'contributor_naco_controlled':
				reconcile_item['contributor_naco_controlled'] = prop['v']
			if prop['pid'] == 'work_published_year':
				reconcile_item['work_published_year'] = prop['v']

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
	# we added a better function to remove subtitles that is configurable so dont do it automatically
	# title = title.split(":")[0].strip()
	# title = title.split(";")[0].strip()
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



def reset_cluster_cache(req_ip, query):
		
	for queryId in query:

		if 'type' in query[queryId]:

			if query[queryId]['type'] == 'LC_Work_Id':
				if os.path.isfile(f'data/cache/cluster_cache_id_{req_ip}'):
					os.remove(f'data/cache/cluster_cache_id_{req_ip}')

				with open(f'data/cache/cluster_cache_id_{req_ip}','w') as out:
					out.write('')

			if query[queryId]['type'] == 'Google_Books':
				if os.path.isfile(f'data/cache/cluster_cache_google_{req_ip}'):
					os.remove(f'data/cache/cluster_cache_google_{req_ip}')

				with open(f'data/cache/cluster_cache_google_{req_ip}','w') as out:
					out.write('')

			if query[queryId]['type'] == 'HathiTrust':
				if os.path.isfile(f'data/cache/cluster_cache_hathi_{req_ip}'):
					os.remove(f'data/cache/cluster_cache_hathi_{req_ip}')

				with open(f'data/cache/cluster_cache_hathi_{req_ip}','w') as out:
					out.write('')


def build_cluster_data(req_ip,service):
	"""
		Builds the cluster data for the given request IP.
		This function reads the cluster cache file and builds a dictionary of clusters.
	"""
	if not os.path.isfile(f'data/cache/cluster_cache_{service}_{req_ip}'):
		return {}
	
	print(f"Building cluster data for {req_ip}"	)
	all_clusters = {}
	cluster_stats = {}
	cluster_stats_lang = {}
	
	with open(f'data/cache/cluster_cache_{service}_{req_ip}','r') as f:
		for line in f:
			print(line)
			line = line.strip()
			if os.path.isfile(f'data/cache/{line}'):
				with open(f'data/cache/{line}', 'r') as cluster_file:
					cluster_data = cluster_file.read()
					cluster_data = json.loads(cluster_data)
					

					clusters = cluster_data['cluster'] + cluster_data['cluster_excluded']
					this_cluster_lang = []
					for item in clusters:
						lang = item.get('lang')
						if lang not in this_cluster_lang:
							this_cluster_lang.append(lang)

						if lang:
							cluster_stats_lang[lang] = cluster_stats_lang.get(lang, 0) + 1
					
					print(this_cluster_lang)
					all_clusters[line] = {
						'data': cluster_data,
						'languages': this_cluster_lang,
						'id': line
					}


	print("Cluster stats by language:", cluster_stats_lang	)

	return {
		'clusters': all_clusters,
		'languages': cluster_stats_lang,
	}
	


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


def remove_subtitle(title):
	"""
	Remove subtitle and descriptive phrases from a title string.
	
	First removes text after colons ":" or semicolons ";"
	Then removes common descriptive phrases that typically appear at the end of titles.
	
	Args:
		title (str): The title string to process
		
	Returns:
		str: The cleaned title with subtitles and descriptive phrases removed
	"""
	if not title or not isinstance(title, str):
		return title
	
	# Make a copy to work with
	cleaned_title = title.strip()
	
	# First, remove text after colons or semicolons
	cleaned_title = cleaned_title.split(":")[0].strip()
	cleaned_title = cleaned_title.split(";")[0].strip()
	cleaned_title = cleaned_title.split(", by")[0].strip()

	# Define phrases to remove (in order of specificity - longer phrases first)
	phrases_to_remove = [
		"a science-fiction novel",
		"an original novel",
		"and other stories",
		"a collection of",
		"an anthology of",
		"selected stories",
		"selected works",
		"a conversation piece",
		"translated from the",
		"myths and legends",
		"a novel of",
		"a story of",
		"the story of",
		"a tale of",
		"memoirs of",
		"scenes from",
		"consisting of",
		"retold from",
		"short stories",
		"folk tales",
		"fairy tales",
		"a novel",
		"a mystery",
		"a reminiscence",
		"a romance",
		"a tale",
		"a fable",
		"a chronicle",
		"a satire",
		"a diversion",
		"a trilogy",
		"stories",
		"novellas",
		"or,",
		", by",
		"by"
	]
	
	# Convert to lowercase for case-insensitive matching
	cleaned_lower = cleaned_title.lower()
	
	# Look for each phrase and remove it (and everything after it) if found
	for phrase in phrases_to_remove:
		phrase_lower = phrase.lower()
		
		# Find the phrase in the title
		pos = cleaned_lower.find(phrase_lower)
		
		if pos != -1:
			# Check if this phrase appears near the end or is preceded by appropriate separators
			# We'll be flexible and look for phrases that start with word boundaries
			before_phrase = cleaned_lower[:pos].strip()
			
			# Check if the phrase is at word boundary (preceded by space, comma, or start of string)
			if pos == 0 or cleaned_lower[pos-1] in [' ', ',', '-', '(']:
				# Additional check: make sure we're not cutting off too much of a short title
				if len(before_phrase) >= 10:  # Keep at least 10 characters of the main title
					cleaned_title = cleaned_title[:pos].strip()
					cleaned_lower = cleaned_title.lower()
					break  # Stop after first match to avoid over-trimming
	
	# Clean up any trailing punctuation and whitespace
	cleaned_title = cleaned_title.rstrip(' ,-()').strip()
	
	return cleaned_title
