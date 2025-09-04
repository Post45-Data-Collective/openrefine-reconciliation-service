import requests
import time
import json
import os
import glob
import uuid
from thefuzz import fuzz
from .strategies_helpers import _build_recon_dict, normalize_string, has_numbers, remove_subtitle


extend_work_mapping = {}


headers = {}
auth_timestamp = None

def reauth(OCLC_CLIENT_ID, OCLC_SECRET):
	global headers
	global auth_timestamp

	if auth_timestamp != None:
		sec_left = time.time() - auth_timestamp
		sec_left = 1199 - 1 - int(sec_left)

		if sec_left > 60:
			return True

	response = requests.post(
		'https://oauth.oclc.org/token',
		data={"grant_type": "client_credentials", 'scope': ['wcapi']},
		auth=(OCLC_CLIENT_ID,OCLC_SECRET),
	)
	print(response.text,flush=True)

	response_data = response.json()
	if "access_token" not in response_data:
		print("ERROR: access token not found (BAD KEY/SECRET?)")
		return False

	token = response_data["access_token"]
	auth_timestamp = time.time()

	headers = {
		'accept': 'application/json',
		'Authorization': f'Bearer {token}'
	}
	# print("HEADERS:",headers)

	return True

def _search_worldcat(title,author,config):

	global headers

	# check if we need to reauth 
	reauthOkay = reauth(config['POST45_OCLC_CLIENT_ID'], config['POST45_OCLC_SECRET'])

	# if we did not auth dont do all this
	if reauthOkay == False:
		return False

	url = f'https://americas.discovery.api.oclc.org/worldcat/search/v2/bibs'

	params = {
		'q': f'au:{author} AND ti:{title}',
		'limit': 50
	}

	if author == None:
		params = {
			'q': f'ti:{title}',
			'limit': 50
		}

	print("Doing", url)
	print("params", params)

	try:
		response = requests.get(url,headers=headers,params=params)

	except requests.exceptions.RequestException as e:  # This is the correct syntax
		print("ERROR:", e)
		# create a response 
		return {
			'successful': False,
			'error': str(e),
			"numberOfRecords": 0,
			"bibRecords": []
		}


	data = response.json()
	data['successful'] = True
	data['error'] = None

	if data['numberOfRecords'] == 0:

		data['bibRecords'] = []


	
	# print("data",json.dumps(data),flush=True)
	extracted_data = _extract_bib_data(data)
	return extracted_data
	# print("extracted_data",json.dumps(extracted_data),flush=True)

def process_oclc_query(query, passed_config):
	"""This is what is called from the query endpoint, it will figure out how to process the work query
	"""
	global config
	config = passed_config

	req_ip = query['req_ip']
	del query['req_ip']  # Remove req_ip from the query dictionary to avoid passing it to _build_recon_dict
	
	query_response = {}
	# we need to figure out what type strategy we are going to use based on what they have sent with the request
	for queryId in query:
		data = query[queryId]

		reconcile_item = _build_recon_dict(data)

		author_name = ""

		if reconcile_item['contributor_uncontrolled_last_first'] != False:
			author_name = reconcile_item['contributor_uncontrolled_last_first']
		elif reconcile_item['contributor_uncontrolled_first_last'] != False:
			author_name = reconcile_item['contributor_uncontrolled_first_last']
		elif reconcile_item['contributor_naco_controlled'] != False:
			# OCLC seems to give different results if passed a full naco formed name with life dates
			# it seems to like just having the authors name, so try make the name LESS accurate
			author_name = reconcile_item['contributor_naco_controlled']
			author_name = author_name.split("(")[0]
			author_name = ''.join([i for i in author_name if not i.isdigit()])
			author_name = author_name.replace('-','')

		reconcile_item['author_name'] = author_name

		# if they configured to remove subtitles then do that
		if config.get('POST45_REMOVE_SUBTITLE', False) == True:
			reconcile_item['title'] = remove_subtitle(reconcile_item['title'])

		print("reconcile_item", reconcile_item, flush=True)

		result = _search_oclc(reconcile_item, passed_config)
		print("result", result, flush=True)

		if result.get('successful', False) == False:
			# If the result was not successful, we need to handle the error
			print("Error occurred:", result.get('error', 'Unknown error'), flush=True)
			
			result['or_query_response'] = []
			result['or_query_response'].append({
				"id": "no_uri_error",
				"name": 'ERROR: ' + result.get('error', 'Unknown error'),
				"description": f"Total items: 0",
				"score": 1,
				"match": True,
				"type": [
					{
						"id": "oclc",
						"name": "OCLC_WorldCat_Cluster"
					}
				]
			})

			query_response[queryId] = {
				'result' : result['or_query_response']
			}
			return query_response



		if config.get('POST45_RECONCILIATION_MODE', 'single') == 'cluster':
			result = _cluster_works(result, reconcile_item, req_ip)
		elif config.get('POST45_RECONCILIATION_MODE', 'single') == 'single':
			result = _parse_single_results(result, reconcile_item)

		query_response[queryId] = {
			'result' : result['or_query_response']
		}

	return query_response


def _search_oclc(reconcile_item, passed_config):
	"""
	Do a search at OCLC/WorldCat with fuzzy matching and scoring
	"""	
	
	# Use the existing _search_worldcat function
	data = _search_worldcat(reconcile_item['title'], reconcile_item['author_name'], passed_config)
	
	if data == False:
		# this means there was an API issue
		return {'successful': False, 'error': 'API issue (are OCLC key set?)', 'results': []}

	# Add fuzzy scores to the results
	data = _add_fuzzy_scores(data, reconcile_item, passed_config)
	
	return data


def _add_fuzzy_scores(data, reconcile_item, passed_config):
	"""
	Add fuzzy matching scores to OCLC/WorldCat search results
	"""
	
	if not data or not isinstance(data, list):
		return {'successful': True, 'error': None, 'results': []}
	
	scored_items = []
	for item in data:
		# Initialize score
		score = 0.5  # Base score for being in results
		
		# Extract title
		item_title = item.get('mainTitle', '')
		
		# Extract author
		item_author = item.get('creator', '')
		
		# Test title matching
		title_scores = []
		if reconcile_item['title'] and item_title:
			title_ratio = fuzz.token_sort_ratio(item_title, reconcile_item['title'])
			print(f"Title comparison: '{item_title}' vs '{reconcile_item['title']}' = {title_ratio}", flush=True)
			title_scores.append(title_ratio)
		
		# Get best title score
		best_title_score = max(title_scores) if title_scores else 0
		
		# Test author/contributor matching if author_name is provided
		author_scores = []
		if reconcile_item['author_name'] and reconcile_item['author_name'] != "" and item_author:
			# Determine if we should remove numbers
			remove_numbers = True
			if has_numbers(item_author) and has_numbers(reconcile_item['author_name']):
				remove_numbers = False
			
			# Normalize and compare
			author_normalized = normalize_string(item_author, remove_numbers)
			query_author_normalized = normalize_string(reconcile_item['author_name'], remove_numbers)
			
			author_ratio = fuzz.token_sort_ratio(author_normalized, query_author_normalized)
			author_scores.append(author_ratio)
			
			print(f"Author comparison: '{author_normalized}' vs '{query_author_normalized}' = {author_ratio}", flush=True)
		
		# Get best author score
		best_author_score = max(author_scores) if author_scores else 0
		
		# Calculate final score
		if reconcile_item['author_name'] and reconcile_item['author_name'] != "":
			# Both title and author matter
			if best_title_score > 80 and best_author_score > 80:
				score = 0.95
			elif best_title_score > 70 and best_author_score > 95:
				score = 0.90
			elif best_title_score > 50 and best_author_score >= 100:
				score = 0.85
			elif best_title_score > 60 or best_author_score > 60:
				score = 0.60
			else:
				score = 0.30
		else:
			# Only title matters
			if best_title_score > 90:
				score = 0.95
			elif best_title_score > 80:
				score = 0.85
			elif best_title_score > 70:
				score = 0.70
			elif best_title_score > 50:
				score = 0.50
			else:
				score = 0.30
		
		# Add score to item
		item['fuzzy_score'] = score
		item['title_score'] = best_title_score
		item['author_score'] = best_author_score
		scored_items.append(item)
		
		print(f"Hit: {item_title} - Title Score: {best_title_score}, Author Score: {best_author_score}, Final Score: {score}", flush=True)
	
	# Sort items by score
	scored_items = sorted(scored_items, key=lambda x: x['fuzzy_score'], reverse=True)
	
	# Apply quality score filtering if configured
	if passed_config.get('POST45_OCLC_CLUSTER_QUALITY_SCORE') == 'very high':
		scored_items = [item for item in scored_items if item['fuzzy_score'] >= 0.95]
	elif passed_config.get('POST45_OCLC_CLUSTER_QUALITY_SCORE') == 'high':
		scored_items = [item for item in scored_items if item['fuzzy_score'] >= 0.90]
	elif passed_config.get('POST45_OCLC_CLUSTER_QUALITY_SCORE') == 'medium':
		scored_items = [item for item in scored_items if item['fuzzy_score'] >= 0.80]
	elif passed_config.get('POST45_OCLC_CLUSTER_QUALITY_SCORE') == 'low':
		scored_items = [item for item in scored_items if item['fuzzy_score'] >= 0.60]
	elif passed_config.get('POST45_OCLC_CLUSTER_QUALITY_SCORE') == 'very low':
		scored_items = [item for item in scored_items if item['fuzzy_score'] >= 0.30]
	
	# Apply books-only filtering if configured
	if passed_config.get('POST45_OCLC_BOOK_ONLY', False):
		print("Filtering for books only...", flush=True)
		filtered_items = []
		for item in scored_items:
			if item.get('generalFormat') == 'Book':
				filtered_items.append(item)
				print(f"Including book: {item.get('mainTitle', 'Unknown')} - Format: {item.get('generalFormat')}", flush=True)
			else:
				print(f"Excluding non-book: {item.get('mainTitle', 'Unknown')} - Format: {item.get('generalFormat')}", flush=True)
		scored_items = filtered_items
	
	return {'successful': True, 'error': None, 'results': scored_items}


def _cluster_works(data, reconcile_item, req_ip):
	"""
	Cluster OCLC/WorldCat results by workId - but flatten to match standard format
	"""
	global config
	
	if 'results' in data:
		records = data['results']
	else:
		records = data if isinstance(data, list) else []
	
	# For consistency with other strategies, just use the flat list
	# The workId grouping is preserved in each record
	all_clusters = {
		'cluster': records,  # Note: using 'cluster' to match existing typo in codebase
		'cluster_excluded': [],
		'orginal': {  # Note: using 'orginal' to match existing typo in codebase
			'title': reconcile_item['title'],
			'author': reconcile_item['author_name'],
		}
	}
	
	# Store cluster data
	use_id = str(uuid.uuid4())
	# for unit tests, config might not be set
	# try:
	# 	config
	# except NameError:
	# 	config = {}


	## need this for unit tests


	try:
		if 'APP_BASE' not in config:
			config['APP_BASE'] = 'http://localhost:5001/'
	except:
		config = {'APP_BASE': 'http://localhost:5001/'}

	# if config['APP_BASE'] doesn't end in a '/' add it
	if not config['APP_BASE'].endswith('/'):
		config['APP_BASE'] += '/'

	use_uri = config['APP_BASE'] + 'cluster/oclc/' + use_id
	
	with open(f'data/cache/cluster_oclc_{use_id}','w') as out:
		json.dump(all_clusters, out)
	
	with open(f'data/cache/cluster_cache_oclc_{req_ip}','a') as out:
		out.write(f'cluster_oclc_{use_id}\n')
	
	# Count work clusters for display

	
	result = {}
	result['or_query_response'] = []
	result['or_query_response'].append({
		"id": use_uri,
		"name": f"Clustered Works: {len(all_clusters['cluster'])}",
		"description": f"Total items: {len(records)}",
		"score": 1,
		"match": True,
		"type": [
			{
				"id": "oclc",
				"name": "OCLC_WorldCat_Cluster"
			}
		]
	})
	
	return result


def _parse_single_results(data, reconcile_item):
	"""
	Parse the results from _search_oclc and format them for OpenRefine
	"""
	result = {}
	result['or_query_response'] = []
	
	records = data.get('results', []) if isinstance(data, dict) else data if isinstance(data, list) else []
	
	# Process each hit from the scored results
	for item in records:
		# Start with the existing fuzzy score
		final_score = item.get('fuzzy_score', 0.5)
		
		# Check if we should boost score based on publication year
		if reconcile_item.get('work_published_year') and reconcile_item['work_published_year'] != False:
			user_year = str(reconcile_item['work_published_year'])
			
			# Check published date
			year_match = False
			
			if 'publicationDate' in item and item['publicationDate']:
				if user_year in str(item['publicationDate']):
					year_match = True
					print(f"Year match found in publicationDate: {item['publicationDate']} matches {user_year}", flush=True)
			
			# Boost score if year matches
			if year_match:
				final_score = min(final_score + 0.1, 1.0)  # Add 0.1 but cap at 1.0
				print(f"Boosted score for {item.get('oclcNumber', 'unknown')} from {item.get('fuzzy_score', 0.5)} to {final_score} due to year match", flush=True)
		
		# Cache the item
		oclc_number = item.get('oclcNumber', str(uuid.uuid4()))
		file_name = f"oclc_{oclc_number}".replace(':','_').replace('/','_')
		with open(f'data/cache/{file_name}','w') as out:
			json.dump(item, out)
		
		# Create the OpenRefine response item
		title = item.get('mainTitle', '')
		author = item.get('creator', '')
		display_name = f"{title} / {author}" if author else title
		
		# Build description from available fields
		description_parts = []
		if item.get('statementOfResponsibility'):
			description_parts.append(item['statementOfResponsibility'])
		if item.get('publicationDate'):
			description_parts.append(f"Published: {item['publicationDate']}")
		if item.get('generalFormat'):
			description_parts.append(f"Format: {item['generalFormat']}")
		description = '; '.join(description_parts)[:200]
		
		result['or_query_response'].append({
			"id": f"http://www.worldcat.org/oclc/{oclc_number}",
			"name": display_name,
			"description": description,
			"score": final_score * 100,  # Convert to 0-100 scale
			"match": final_score > 0.8,  # Consider it a match if score > 0.8
			"type": [
				{
					"id": "oclc_work",
					"name": "OCLC WorldCat Work"
				}
			]
		})
	
	# Sort the results by score in descending order
	result['or_query_response'] = sorted(result['or_query_response'], key=lambda item: item['score'], reverse=True)
	return result


def extend_data(ids, properties, passed_config):
	"""
	Sent Ids and properties it talks to OCLC/WorldCat and returns the requested values
	"""
	# print(ids, properties,flush=True)
	response = {"meta":[],"rows":{}}
	
	for p in properties:
		if p['id'] == 'ISBN':
			response['meta'].append({"id":"ISBN",'name':'ISBN'})
		if p['id'] == 'LCCN':
			response['meta'].append({"id":"LCCN",'name':'LCCN'})
		if p['id'] == 'OCLC':
			response['meta'].append({"id":"OCLC",'name':'OCLC Number'})
		if p['id'] == 'subjects':
			response['meta'].append({"id":"subjects",'name':'Subjects'})
		if p['id'] == 'language':
			response['meta'].append({"id":"language",'name':'Language'})
		if p['id'] == 'format':
			response['meta'].append({"id":"format",'name':'Format'})
	
		if p['id'] == 'isbn_cluster':
			response['meta'].append({"id":"isbn_cluster",'name':'ISBN Cluster'})

		if p['id'] == 'dewey':
			response['meta'].append({"id":"dewey",'name':'Dewey Decimal Classification'})
		if p['id'] == 'lcc':
			response['meta'].append({"id":"lcc",'name':'Library of Congress Classification'})


		if p['id'] == 'work':
			response['meta'].append({"id":"work",'name':'Work ID'})
		if p['id'] == 'title':
			response['meta'].append({"id":"title",'name':'Mode Title'})



	for i in ids:
		response['rows'][i]={}
		
		if '/oclc/' in i and 'cluster/oclc' not in i:
			# Single OCLC record
			oclc_number = i.split('/')[-1]
			cache_file = f'data/cache/oclc_{oclc_number}'
			
			if os.path.isfile(cache_file):
				data = json.load(open(cache_file))
				
				for p in properties:
					if p['id'] == 'ISBN':
						isbns = data.get('isbns', [])
						if isbns:
							response['rows'][i]['ISBN'] = [{'str': isbn} for isbn in isbns]
						else:
							response['rows'][i]['ISBN'] = [{}]
					
					elif p['id'] == 'LCCN':
						lccn = data.get('lccn')
						if lccn:
							response['rows'][i]['LCCN'] = [{'str': lccn}]
						else:
							response['rows'][i]['LCCN'] = [{}]
					
					elif p['id'] == 'OCLC':
						oclc = data.get('oclcNumber')
						if oclc:
							response['rows'][i]['OCLC'] = [{'str': oclc}]
						else:
							response['rows'][i]['OCLC'] = [{}]
					
					elif p['id'] == 'subjects':
						subjects = data.get('subjects', [])
						if subjects:
							response['rows'][i]['subjects'] = [{'str': subj} for subj in subjects]
						else:
							response['rows'][i]['subjects'] = [{}]
					
					elif p['id'] == 'language':
						lang = data.get('itemLanguage')
						if lang:
							response['rows'][i]['language'] = [{'str': lang}]
						else:
							response['rows'][i]['language'] = [{}]
					
					elif p['id'] == 'format':
						fmt = data.get('generalFormat')
						if fmt:
							response['rows'][i]['format'] = [{'str': fmt}]
						else:
							response['rows'][i]['format'] = [{}]
		
		elif 'cluster/oclc' in i:

			# Cluster of OCLC records
			uuid_val = i.split('/')[-1]
			filename = f'data/cache/cluster_oclc_{uuid_val}'
			print("filename",filename,flush=True)
			if os.path.isfile(filename):
				data = json.load(open(filename))
				print(data, flush=True)
				
				# Extract data from cluster items (using standard cluster format)
				for p in properties:
					if p['id'] == 'isbn_cluster':
						isbn_values = []
						seen_isbns = set()
						for item in data.get('cluster', []):
							isbns = item.get('isbns', [])
							if isbns != None:
								for isbn in isbns:
									if isbn not in seen_isbns:
										if isbn != None:
											seen_isbns.add(isbn)
											isbn_values.append({"str": isbn})
						response['rows'][i]['isbn_cluster'] = isbn_values if isbn_values else [{}]
					

					elif p['id'] == 'dewey':
						dewey_values = []
						seen_deweys = set()
						for item in data.get('cluster', []):
							classifications = item.get('classifications', None)
							if classifications != None:
									
								dewey = item.get('classifications', {}).get('dewey')
								if dewey and dewey not in seen_deweys:
									seen_deweys.add(dewey)
									dewey_values.append({"str": dewey})
						response['rows'][i]['dewey'] = dewey_values if dewey_values else [{}]

					elif p['id'] == 'lcc':
						lcc_values = []
						seen_lccs = set()
						for item in data.get('cluster', []):
							classifications = item.get('classifications', None)
							if classifications != None:
								lcc = item.get('classifications', {}).get('lc')
								if lcc and lcc not in seen_lccs:
									seen_lccs.add(lcc)
									lcc_values.append({"str": lcc})
						response['rows'][i]['lcc'] = lcc_values if lcc_values else [{}]

					elif p['id'] == 'work':
						work_values = []
						seen_works = set()
						for item in data.get('cluster', []):
							work = item.get('workId')
							if work and work not in seen_works:
								seen_works.add(work)
								work_values.append({"str": work})
						response['rows'][i]['work'] = work_values if work_values else [{}]





					elif p['id'] == 'LCCN':
						lccn_values = []
						seen_lccns = set()
						for item in data.get('cluster', []):
							lccn = item.get('lccn')
							if lccn and lccn not in seen_lccns:
								seen_lccns.add(lccn)
								lccn_values.append({"str": lccn})
						response['rows'][i]['LCCN'] = lccn_values if lccn_values else [{}]
					
					elif p['id'] == 'OCLC':
						oclc_values = []
						seen_oclcs = set()
						for item in data.get('cluster', []):
							oclc = item.get('oclcNumber')
							if oclc and oclc not in seen_oclcs:
								seen_oclcs.add(oclc)
								oclc_values.append({"str": oclc})
						response['rows'][i]['OCLC'] = oclc_values if oclc_values else [{}]
					
					elif p['id'] == 'subjects':
						subject_values = []
						seen_subjects = set()
						for item in data.get('cluster', []):
							subj_list = item.get('subjects', [])
							if subj_list != None:
								for subj in subj_list:
									if subj not in seen_subjects:
										seen_subjects.add(subj)
										subject_values.append({"str": subj})
						response['rows'][i]['subjects'] = subject_values if subject_values else [{}]
					
					elif p['id'] == 'language':
						lang_values = []
						seen_langs = set()
						for item in data.get('cluster', []):
							lang = item.get('itemLanguage')
							if lang and lang not in seen_langs:
								seen_langs.add(lang)
								lang_values.append({"str": lang})
						response['rows'][i]['language'] = lang_values if lang_values else [{}]
					
					elif p['id'] == 'format':
						format_values = []
						seen_formats = set()
						for item in data.get('cluster', []):
							fmt = item.get('generalFormat')
							if fmt and fmt not in seen_formats:
								seen_formats.add(fmt)
								format_values.append({"str": fmt})
						response['rows'][i]['format'] = format_values if format_values else [{}]
	
					elif p['id'] == 'title':
						titles = []
						for item in data.get('cluster', []):
							title = item.get('mainTitle',None)
							if title:
								titles.append(title)
						
						# make title the mode of all the strings in titles
						if titles:
							mode_title = max(set(titles), key=titles.count)
							response['rows'][i]['title'] = [{"str": mode_title}]
						else:
							response['rows'][i]['title'] = [{}]









	print(i, flush=True)
	print(properties, flush=True)
	print(response, flush=True)
	
	# If join mode is enabled, convert lists to pipe-delimited strings
	if passed_config and passed_config.get('POST45_DATA_EXTEND_MODE') == 'join':
		for row_id in response['rows']:
			for field in response['rows'][row_id]:
				if isinstance(response['rows'][row_id][field], list):
					# Extract the 'str' value from each dict and join with pipes
					values = []
					for item in response['rows'][row_id][field]:
						if isinstance(item, dict) and 'str' in item:
							values.append(item['str'])
					print("values", values, flush=True)
					response['rows'][row_id][field] = [{"str": '|'.join(values)}] if values else [{}]
					print(response['rows'][row_id][field], flush=True)
	
	return response


def _search_title(title,name):
	"""
		Do a pretty search at google
	"""	
	global headers



	url = f'https://americas.discovery.api.oclc.org/worldcat/search/v2/bibs'

	params = {
		'q': f'au:{name} AND ti:{title}',
		'limit': 50
	}

	print("Doing", url)
	print("params", params)

	try:
		response = requests.get(url,headers=headers,params=params)

	except requests.exceptions.RequestException as e:  # This is the correct syntax
		print("ERROR:", e)
		# create a response 
		return {
			'successful': False,
			'error': str(e),
			"numberOfRecords": 0,
			"bibRecords": []
		}


	data = response.json()
	data['successful'] = True
	data['error'] = None

	if data['numberOfRecords'] == 0:

		data['bibRecords'] = []

	# print("*******")	
	# print(name, title)
	# print(data)
	# print("------------")

	return data



def _get_creator_name(contributor_info):
	"""
	Finds and formats the name of a suitable creator (author).

	It searches for the first person in the 'creators' list who is not explicitly
	an editor, compiler, narrator, etc. This aligns with the "creator only"
	requirement. The name is formatted as "Last, First" if possible.

	Args:
		contributor_info (dict): The 'contributor' part of a bib record.

	Returns:
		str or None: The formatted creator name, or None if no suitable
						creator is found.
	"""
	if not isinstance(contributor_info, dict):
		return None
	creators = contributor_info.get('creators')
	if not isinstance(creators, list):
		return None

	# Roles that disqualify a person from being a "creator only"
	non_creator_roles = {
		'editor', 'compiler', 'voice actor', 'ed.lit', 'mitwirkender',
		'buchgestalter', 'herausgeber', 'drucker', 'buchbinder', 'issuing body',
		'hörfunkproduzent', 'verlag', 'regisseur', 'synchronsprecher', 'narrator'
	}

	for creator in creators:
		# Skip non-dictionary items or non-person contributors
		if not isinstance(creator, dict) or creator.get('type') != 'person':
			continue

		is_creator_only = True
		relators = creator.get('relators')
		if isinstance(relators, list):
			for relator in relators:
				# Check if the relator term indicates a non-creator role
				term = (relator or {}).get('term', '').lower()
				if term in non_creator_roles:
					is_creator_only = False
					break
		
		if is_creator_only:
			# Found a suitable creator, now format their name
			first_name_val = creator.get('firstName')
			second_name_val = creator.get('secondName')

			first_name, second_name = None, None
			
			if isinstance(first_name_val, dict):
				first_name = first_name_val.get('text')
			elif isinstance(first_name_val, str):
				first_name = first_name_val

			if isinstance(second_name_val, dict):
				second_name = second_name_val.get('text')
			elif isinstance(second_name_val, str):
				second_name = second_name_val
			
			# Format name as "Last, First" if both parts are available
			if second_name and first_name:
				return f"{second_name}, {first_name}"
			elif second_name:
				return second_name
			elif first_name:
				return first_name
			# If no name parts found, continue to the next creator in the list
	
	return None # No suitable creator found



def _extract_bib_data(data):
    """
    Extracts and simplifies bibliographic data from a complex JSON structure.

    This function processes a dictionary containing bibliographic records and
    extracts a predefined set of fields into a simplified list of dictionaries.
    It includes checks for the existence of data at each level of the structure,
    setting the value to None if a piece of data is missing.

    Args:
        data (dict): The input data structure, expected to contain a 'bibRecords' key
                     with a list of record dictionaries.

    Returns:
        list: A list of simplified dictionaries, where each dictionary represents
              one bibliographic record with the extracted fields. Returns an empty
              list if the input data is invalid or contains no records.
    """

    if not isinstance(data, dict) or not isinstance(data.get('bibRecords'), list):
        return []

    simplified_records = []

    for record in data['bibRecords']:
        if not isinstance(record, dict):
            continue

        # Safely get nested dictionaries, defaulting to an empty dict if missing or None
        identifier = record.get('identifier') or {}
        title_info = record.get('title') or {}
        contributor_info = record.get('contributor') or {}
        date_info = record.get('date') or {}
        language_info = record.get('language') or {}
        format_info = record.get('format') or {}
        work_info = record.get('work') or {}

        # Extract main title from the first entry in the mainTitles list
        main_titles = title_info.get('mainTitles')
        main_title_text = None
        if isinstance(main_titles, list) and main_titles:
            first_title = main_titles[0]
            if isinstance(first_title, dict):
                main_title_text = first_title.get('text')

        # Extract statement of responsibility
        sor = contributor_info.get('statementOfResponsibility')
        sor_text = (sor or {}).get('text')
            
        # Extract subjects as a simple list of strings
        subjects_list = record.get('subjects')
        subjects_str_list = None
        if isinstance(subjects_list, list):
            subjects_str_list = []
            for s in subjects_list:
                subject_name = (s or {}).get('subjectName')
                if isinstance(subject_name, dict):
                    text = subject_name.get('text')
                    if text:
                        subjects_str_list.append(text)

        # Assemble the simplified record dictionary
        simplified_record = {
            'oclcNumber': identifier.get('oclcNumber'),
            'isbns': identifier.get('isbns'),
            'mergedOclcNumbers': identifier.get('mergedOclcNumbers'),
            'lccn': identifier.get('lccn'),
            'creator': _get_creator_name(contributor_info),
            'mainTitle': main_title_text,
            'statementOfResponsibility': sor_text,
            'classifications': record.get('classification'),
            'subjects': subjects_str_list,
            'publicationDate': date_info.get('publicationDate'),
            'itemLanguage': language_info.get('itemLanguage'),
            'generalFormat': format_info.get('generalFormat'),
            'workId': work_info.get('id')
        }
        
        simplified_records.append(simplified_record)

    return simplified_records