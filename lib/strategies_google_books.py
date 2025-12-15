import statistics
import requests
import os
import json
import uuid


from thefuzz import fuzz


from .strategies_helpers import _build_recon_dict
from .paths import CACHE_DIR
from .strategies_helpers import normalize_string
from .paths import CACHE_DIR
from .strategies_helpers import has_numbers
from .paths import CACHE_DIR
from .strategies_helpers import remove_subtitle
from .paths import CACHE_DIR


ID_HEADERS = {
	'User-Agent':'Openrefine Post 45 Reconcilation Client'
}





def process_google_books_query(query, passed_config):
	"""This is what is called from the query endpoint, it will figure out how to process the work query
	"""
	global config
	config = passed_config

	req_ip = query['req_ip']
	del query['req_ip']  # Remove req_ip from the query dictionary to avoid passing it to _build_recon_dict
	
	query_reponse = {}
	# we need to figure out what type strategy we are going to use based on what they have sent with the reqest
	for queryId in query:
		data = query[queryId]

		reconcile_item = _build_recon_dict(data)

		author_name = ""

		if reconcile_item['contributor_uncontrolled_last_first'] != False:
			author_name = reconcile_item['contributor_uncontrolled_last_first']
		elif reconcile_item['contributor_uncontrolled_first_last'] != False:
			author_name = reconcile_item['contributor_uncontrolled_first_last']
		elif reconcile_item['contributor_naco_controlled'] != False:
			# google books seems to give different results if passed a full naco formed name with life dates
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

		result = _search_google_books(reconcile_item, passed_config)
		print("result", result, flush=True)

		if config.get('POST45_RECONCILIATION_MODE', 'single') == 'cluster':
			result = _cluster_works(result, reconcile_item, req_ip)
		elif config.get('POST45_RECONCILIATION_MODE', 'single') == 'single':
			result = _parse_single_results(result, reconcile_item)

		query_reponse[queryId] = {
			'result' : result['or_query_response']
		}

	return query_reponse



# def extend_data(ids,properties):
# 	"""
# 		Sent Ids and proeprties it talks to id.loc.gov and returns the reuqested values
# 	"""

# 	response = {"meta":[],"rows":{}}

# 	for p in properties:

# 		if p['id'] == 'ISBN':
# 			response['meta'].append({"id":"ISBN",'name':'ISBN'})
# 		if p['id'] == 'LCCN':
# 			response['meta'].append({"id":"LCCN",'name':'LCCN'})
# 		if p['id'] == 'OCLC':
# 			response['meta'].append({"id":"OCLC",'name':'OCLC'})


# 	for i in ids:

# 		instance_response = None
# 		work_response = None

# 		response['rows'][i]={}

# 		if '/works/' in i:

# 			for p in properties:

# 				if p['id'] == 'ISBN':

# 					if instance_response == None:
# 						instance_response = requests.get(i.replace('/works/','/instances/')+'.bibframe.json')


# 					value = _extend_extract_ISBN(instance_response)
# 					print("valuevaluevaluevalue _extend_extract_ISBN",value)

# 					response['rows'][i]['ISBN'] = value

# 				if p['id'] == 'LCCN':

# 					if instance_response == None:
# 						instance_response = requests.get(i.replace('/works/','/instances/')+'.bibframe.json')


# 					value = _extend_extract_LCCN(instance_response)
# 					print("valuevaluevaluevalue _extend_extract_LCCN",value)
# 					response['rows'][i]['LCCN'] = value

# 				if p['id'] == 'OCLC':

# 					if instance_response == None:
# 						instance_response = requests.get(i.replace('/works/','/instances/')+'.bibframe.json')


# 					value = _extend_extract_OCLC(instance_response)
# 					print("valuevaluevaluevalue _extend_extract_OCLC",value)
# 					response['rows'][i]['OCLC'] = value




# 	print(i)
# 	print(properties)
# 	print(response)
# 	return response




# def _extend_extract_ISBN(instance_response):

# 	try:
# 		graphs=instance_response.json()
# 	except:
# 		print("Error Extend",instance_response)
# 		return("ERROR")


# 	# loop through the graphs and return the value for ISBN
# 	values = []
# 	for g in graphs:
# 		if '@type' in g:
# 			if 'http://id.loc.gov/ontologies/bibframe/Isbn' in g['@type']:
# 				if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value' in g:
# 					for v in g['http://www.w3.org/1999/02/22-rdf-syntax-ns#value']:
# 						if '@value' in v:
# 							values.append({"str":v['@value'].strip()})


# 	if len(values) == 0:
# 		values=[{}]

# 	return values


# def _extend_extract_LCCN(instance_response):

# 	try:
# 		graphs=instance_response.json()
# 	except:
# 		print("Error Extend",instance_response)
# 		return("ERROR")


# 	# loop through the graphs and return the value for ISBN
# 	values = []
# 	for g in graphs:
# 		if '@type' in g:
# 			if 'http://id.loc.gov/ontologies/bibframe/Lccn' in g['@type']:
# 				if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value' in g:
# 					for v in g['http://www.w3.org/1999/02/22-rdf-syntax-ns#value']:
# 						if '@value' in v:
# 							values.append({"str":v['@value'].strip()})

# 	if len(values) == 0:
# 		values=[{}]

# 	return values


# def _extend_extract_OCLC(instance_response):

# 	try:
# 		graphs=instance_response.json()
# 	except:
# 		print("Error Extend",instance_response)
# 		return("ERROR")


# 	# loop through the graphs and return the value for ISBN
# 	values = []
# 	for g in graphs:
# 		if '@type' in g:
# 			if 'http://id.loc.gov/ontologies/bibframe/OclcNumber' in g['@type']:
# 				if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value' in g:
# 					for v in g['http://www.w3.org/1999/02/22-rdf-syntax-ns#value']:
# 						if '@value' in v:
# 							values.append({"str":v['@value'].strip()})

# 	if len(values) == 0:
# 		values=[{}]

# 	return values


# def _build_title_for_uncontrolled_name_search(title):
# 	"""
# 		takes a tile and parses it for how this endpoint works best

# 	"""

# 	title = title.split(":")[0].strip()
# 	title = title.split(";")[0].strip()


# 	return title


# def _build_recon_dict(recon_query):


# 	reconcile_item = {
# 		'title': _build_title_for_uncontrolled_name_search(recon_query['query']),
# 		'type': recon_query['type'],
# 		'contributor_uncontrolled_last_first': False,
# 		'contributor_uncontrolled_first_last': False
# 	}

# 	for prop in recon_query['properties']:

# 		print(prop)

# 		if prop['pid'] == 'contributor_uncontrolled_last_first':
# 			reconcile_item['contributor_uncontrolled_last_first'] = prop['v']
# 		if prop['pid'] == 'contributor_uncontrolled_first_last':
# 			reconcile_item['contributor_uncontrolled_first_last'] = prop['v']


# 	return reconcile_item




def _search_google_books(reconcile_item, passed_config):
	"""
		Do a search at Google Books API with fuzzy matching and scoring
	"""	

	url = 'https://www.googleapis.com/books/v1/volumes'

	q_string = f"intitle:{reconcile_item['title']}"
	if reconcile_item['author_name'] and reconcile_item['author_name'] != "":
		q_string = q_string + f" inauthor:{reconcile_item['author_name']}"

	params = {
		'q' : q_string,
		'projection': 'full',
		'maxResults': 40  # Increase from default 10 to get more results to score
	}
	print(params, flush=True)

	try:
		response = requests.get(url, params=params, headers=ID_HEADERS)
	except requests.exceptions.RequestException as e:
		print("ERROR:", e, flush=True)
		# create a response 
		return {
			'successful': False,
			'error': str(e),
			'kind': 'books#volumes',
			'totalItems': 0,
			'items': []
		}

	data = response.json()
	data['successful'] = True
	data['error'] = None

	if 'totalItems' not in data or data['totalItems'] == 0:
		data['items'] = []
		return data

	# Score each hit based on fuzzy matching
	scored_items = []
	for item in data.get('items', []):
		# Initialize score
		score = 0.5  # Base score for being in results
		
		# Extract volume info
		volume_info = item.get('volumeInfo', {})
		
		# Extract title
		item_title = volume_info.get('title', '')
		item_subtitle = volume_info.get('subtitle', '')
		if item_subtitle:
			full_title = f"{item_title}: {item_subtitle}"
		else:
			full_title = item_title
		
		# Extract authors
		authors = volume_info.get('authors', [])
		
		# Test title matching
		title_scores = []
		if reconcile_item['title']:
			if item_title:
				title_ratio = fuzz.token_sort_ratio(item_title, reconcile_item['title'])
				print(f"Title comparison: '{item_title}' vs '{reconcile_item['title']}' = {title_ratio}", flush=True)
				title_scores.append(title_ratio)
			
			# Also test full title with subtitle
			if full_title != item_title:
				full_title_ratio = fuzz.token_sort_ratio(full_title, reconcile_item['title'])
				title_scores.append(full_title_ratio)
		
		# Get best title score
		best_title_score = max(title_scores) if title_scores else 0
		
		# Test author/contributor matching if author_name is provided
		author_scores = []
		if reconcile_item['author_name'] and reconcile_item['author_name'] != "":
			for author in authors:
				if author:
					# Determine if we should remove numbers
					remove_numbers = True
					if has_numbers(author) and has_numbers(reconcile_item['author_name']):
						remove_numbers = False
					
					# Normalize and compare
					author_normalized = normalize_string(author, remove_numbers)
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
		
		print(f"Hit: {volume_info.get('title', 'N/A')} - Title Score: {best_title_score}, Author Score: {best_author_score}, Final Score: {score}", flush=True)
	
	# Sort items by score
	data['items'] = sorted(scored_items, key=lambda x: x['fuzzy_score'], reverse=True)
	
	# Apply quality score filtering if configured
	if passed_config.get('POST45_GOOGLE_CLUSTER_QUALITY_SCORE') == 'very high':
		data['items'] = [item for item in data['items'] if item['fuzzy_score'] >= 0.95]
	elif passed_config.get('POST45_GOOGLE_CLUSTER_QUALITY_SCORE') == 'high':
		data['items'] = [item for item in data['items'] if item['fuzzy_score'] >= 0.90]
	elif passed_config.get('POST45_GOOGLE_CLUSTER_QUALITY_SCORE') == 'medium':
		data['items'] = [item for item in data['items'] if item['fuzzy_score'] >= 0.80]
	elif passed_config.get('POST45_GOOGLE_CLUSTER_QUALITY_SCORE') == 'low':
		data['items'] = [item for item in data['items'] if item['fuzzy_score'] >= 0.60]
	elif passed_config.get('POST45_GOOGLE_CLUSTER_QUALITY_SCORE') == 'very low':
		data['items'] = [item for item in data['items'] if item['fuzzy_score'] >= 0.30]
	
	return data


def _parse_single_results(data, reconcile_item):
	"""
	Parse the results from _search_google_books and format them for OpenRefine
	"""
	result = {}
	result['or_query_response'] = []
	
	# Process each hit from the scored results
	for item in data.get('items', []):
		# Start with the existing fuzzy score
		final_score = item.get('fuzzy_score', 0.5)
		
		# Check if we should boost score based on publication year
		if reconcile_item.get('work_published_year') and reconcile_item['work_published_year'] != False:
			user_year = str(reconcile_item['work_published_year'])
			
			# Check published date in volumeInfo
			year_match = False
			volume_info = item.get('volumeInfo', {})
			
			if 'publishedDate' in volume_info and volume_info['publishedDate']:
				if user_year in str(volume_info['publishedDate']):
					year_match = True
					print(f"Year match found in publishedDate: {volume_info['publishedDate']} matches {user_year}", flush=True)
			
			# Boost score if year matches
			if year_match:
				final_score = min(final_score + 1.0, 1.0)  # Add 1 but cap at 1.0
				print(f"Boosted score for {item.get('id', 'unknown')} from {item.get('fuzzy_score', 0.5)} to {final_score} due to year match", flush=True)
		
		# Cache the item
		uri = 'https://www.googleapis.com/books/v1/volumes/' + item['id']
		file_name = uri.replace(':','_').replace('/','_')
		with open(f'{CACHE_DIR}/google_books_{file_name}','w') as out:
			json.dump(item, out)
		
		# Create the OpenRefine response item
		volume_info = item.get('volumeInfo', {})
		title = volume_info.get('title', '')
		subtitle = volume_info.get('subtitle', '')
		display_title = f"{title}: {subtitle}" if subtitle else title
		
		result['or_query_response'].append({
			"id": uri,
			"name": display_title,
			"description": volume_info.get('description', '')[:200] if 'description' in volume_info else '',
			"score": final_score,
			"match": final_score > 0.8,  # Consider it a match if score > 0.8
			"type": [
				{
					"id": "google_books",
					"name": "Google Books Volume"
				}
			]
		})
	
	# Sort the results by score in descending order
	result['or_query_response'] = sorted(result['or_query_response'], key=lambda item: item['score'], reverse=True)
	return result


def _cluster_works(records, reconcile_item, req_ip):
	"""
	Cluster Google Books results
	"""
	global config

	if 'items' in records:
		records = records['items']
	
	all_clusters = {
		'cluster' :  records,
		'cluster_excluded' : []
	}
	
	result = {}
	result['or_query_response'] = []
	
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

	use_uri = config['APP_BASE'] + 'cluster/google_books/' + use_id
	all_clusters['orginal'] = {
		'title': reconcile_item['title'],
		'author': reconcile_item['author_name'],
	}
	with open(f'{CACHE_DIR}/cluster_google_books_{use_id}','w') as out:
		json.dump(all_clusters, out)
	
	with open(f'{CACHE_DIR}/cluster_cache_google_books_{req_ip}','a') as out:
		out.write(f'cluster_google_books_{use_id}\n')
	
	result['or_query_response'].append({
			"id": use_uri,
			"name": f"Clustered: {len(all_clusters['cluster'])}, Excluded: {len(all_clusters['cluster_excluded'])}",
			"description": '',
			"score": 1,
			"match": True,
			"type": [
				{
				"id": "google_books",
				"name": "Google_Books_Cluster"
			}
		]
	})
	
	return result







def extend_data(ids, properties, passed_config):
	"""
	Sent Ids and properties it talks to Google Books and returns the requested values
	"""

	response = {"meta":[],"rows":{}}

	for p in properties:

		if p['id'] == 'ISBN':
			response['meta'].append({"id":"ISBN",'name':'ISBN'})
		if p['id'] == 'description':
			response['meta'].append({"id":"description",'name':'Description'})

		if p['id'] == 'pageCount':
			response['meta'].append({"id":"pageCount",'name':'Page Count'})

		if p['id'] == 'language':
			response['meta'].append({"id":"language",'name':'Language'})

		if p['id'] == 'language':
			response['meta'].append({"id":"language",'name':'Language'})

		if p['id'] == 'title':
			response['meta'].append({"id":"title",'name':'Mode Title'})


    # "cluster": [
    #     {
    #         "kind": "books#volume",
    #         "id": "hKxm-sXHlOUC",
    #         "etag": "AWmuWel5Q0g",
    #         "selfLink": "https://www.googleapis.com/books/v1/volumes/hKxm-sXHlOUC",
    #         "volumeInfo": {
    #             "title": "Death of a Puppeteer",
    #             "authors": [
    #                 "William Gray Beyer"



		# if p['id'] == 'LCCN':
		# 	response['meta'].append({"id":"LCCN",'name':'LCCN'})
		# if p['id'] == 'OCLC':
		# 	response['meta'].append({"id":"OCLC",'name':'OCLC'})


	for i in ids:
		response['rows'][i]={}

		if 'volumes/' in i:
			# Single volume
			for p in properties:
				if p['id'] == 'ISBN':
					# load it from the cache
					passed_id_escaped = i.replace(":",'_').replace("/",'_')
					if os.path.isfile(f'{CACHE_DIR}/{passed_id_escaped}'):
						data = json.load(open(f'{CACHE_DIR}/{passed_id_escaped}'))
					
					isbns = []

					if 'volumeInfo' in data:
						if 'industryIdentifiers' in data['volumeInfo']:

							for ident in data['volumeInfo']['industryIdentifiers']:
								if 'type' in ident:
									if 'ISBN' in ident['type']:
										isbns.append(ident['identifier'])




					if len(isbns) > 0:
						response['rows'][i]['ISBN'] = []
						for isbn in isbns:
							response['rows'][i]['ISBN'].append({'str':isbn})
					
					

						# fill-down
					else:
						response['rows'][i]['ISBN'] = [{}]

				elif p['id'] == 'description':
					# load it from the cache
					passed_id_escaped = i.replace(":",'_').replace("/",'_')
					if os.path.isfile(f'{CACHE_DIR}/{passed_id_escaped}'):
						data = json.load(open(f'{CACHE_DIR}/{passed_id_escaped}'))
					
					description = ""

					if 'volumeInfo' in data:
						if 'description' in data['volumeInfo']:

							description = data['volumeInfo']['description']


					if len(description) > 0:
						response['rows'][i]['description'] = [{'str':description}]
					else:
						response['rows'][i]['description'] = [{}]


				elif p['id'] == 'pageCount':
					# load it from the cache
					passed_id_escaped = i.replace(":",'_').replace("/",'_')
					if os.path.isfile(f'{CACHE_DIR}/{passed_id_escaped}'):
						data = json.load(open(f'{CACHE_DIR}/{passed_id_escaped}'))
					
					pageCount = None

					if 'volumeInfo' in data:
						if 'pageCount' in data['volumeInfo']:

							pageCount = data['volumeInfo']['pageCount']


					if pageCount != None:
						response['rows'][i]['pageCount'] = [{'str':str(pageCount)}]
					else:
						response['rows'][i]['pageCount'] = [{}]

				elif p['id'] == 'language':
					# load it from the cache
					passed_id_escaped = i.replace(":",'_').replace("/",'_')
					if os.path.isfile(f'{CACHE_DIR}/{passed_id_escaped}'):
						data = json.load(open(f'{CACHE_DIR}/{passed_id_escaped}'))
					
					language = None

					if 'volumeInfo' in data:
						if 'language' in data['volumeInfo']:

							language = data['volumeInfo']['language']


					if language != None:
						response['rows'][i]['language'] = [{'str':language}]
					else:
						response['rows'][i]['language'] = [{}]






		elif 'cluster/google_books' in i:
			# Cluster of volumes
			uuid_val = i.split('/')[-1]
			filename = f'{CACHE_DIR}/cluster_google_books_{uuid_val}'
			if os.path.isfile(filename):
				data = json.load(open(filename))
				print(data, flush=True)
				
				# Extract data from cluster items
				for p in properties:
					if p['id'] == 'ISBN':
						isbn_values = []
						seen_isbns = set()
						for item in data.get('cluster', []):
							volume_info = item.get('volumeInfo', {})
							if 'industryIdentifiers' in volume_info:
								for identifier in volume_info['industryIdentifiers']:
									if 'ISBN' in identifier.get('type', ''):
										isbn = identifier['identifier']
										if isbn not in seen_isbns:
											seen_isbns.add(isbn)
											isbn_values.append({"str": isbn})
						response['rows'][i]['ISBN'] = isbn_values if isbn_values else [{}]
					
					elif p['id'] == 'description':
						desc_values = []
						seen_desc = set()
						for item in data.get('cluster', []):
							volume_info = item.get('volumeInfo', {})
							if 'description' in volume_info and volume_info['description']:
								desc = volume_info['description']
								if desc not in seen_desc:
									seen_desc.add(desc)
									desc_values.append({"str": desc})
						response['rows'][i]['description'] = desc_values if desc_values else [{}]
					
					elif p['id'] == 'pageCount':
						page_values = []
						seen_pages = set()
						for item in data.get('cluster', []):
							volume_info = item.get('volumeInfo', {})
							if 'pageCount' in volume_info and volume_info['pageCount']:
								page_count = str(volume_info['pageCount'])
								if page_count not in seen_pages:
									seen_pages.add(page_count)
									page_values.append({"str": page_count})
						response['rows'][i]['pageCount'] = page_values if page_values else [{}]
					
					elif p['id'] == 'language':
						lang_values = []
						seen_langs = set()
						for item in data.get('cluster', []):
							volume_info = item.get('volumeInfo', {})
							if 'language' in volume_info and volume_info['language']:
								lang = volume_info['language']
								if lang not in seen_langs:
									seen_langs.add(lang)
									lang_values.append({"str": lang})
						response['rows'][i]['language'] = lang_values if lang_values else [{}]

					elif p['id'] == 'title':
						all_titles = []

						for item in data.get('cluster', []):
							volume_info = item.get('volumeInfo', {})
							if 'title' in volume_info and volume_info['title']:
								all_titles.append(volume_info['title'])
								
						# get the mode avg of all_titles
						mode_title = statistics.mode(all_titles) if all_titles else None

						response['rows'][i]['title'] = [{"str": mode_title}] if mode_title else [{}]






    # "cluster": [
    #     {
    #         "kind": "books#volume",
    #         "id": "hKxm-sXHlOUC",
    #         "etag": "AWmuWel5Q0g",
    #         "selfLink": "https://www.googleapis.com/books/v1/volumes/hKxm-sXHlOUC",
    #         "volumeInfo": {
    #             "title": "Death of a Puppeteer",
    #             "authors": [
    #                 "William Gray Beyer"









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


