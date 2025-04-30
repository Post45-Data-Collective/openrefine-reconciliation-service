import requests
import html
import json
import re
import os
from bs4 import BeautifulSoup

from thefuzz import fuzz

from .strategies_helpers import _build_recon_dict
from .strategies_helpers import normalize_string
from .strategies_helpers import has_numbers


HATHI_FULL_SEARCH_ONLY = None


HT_HEADERS = {
	'User-Agent':'Openrefine Post 45 Reconcilation Client'
}





def process_hathi_query(query, HATHI_FULL_SEARCH_ONLY_passed):
	"""This is what is called from the query endpoint, it will figure out how to process the work query
	"""
	global HATHI_FULL_SEARCH_ONLY

	HATHI_FULL_SEARCH_ONLY = HATHI_FULL_SEARCH_ONLY_passed
	
	query_reponse = {}
	# we need to figure out what type strategy we are going to use based on what they have sent with the reqest
	# with viaf personal just do the same search if they provided a title or not
	for queryId in query:

		data = query[queryId]


		reconcile_item = _build_recon_dict(data)
		# print('**',reconcile_item,flush=True)


		result =  _search_hathi(reconcile_item)
		result = _parse_results(result,reconcile_item)


		query_reponse[queryId] = {
			'result' : result['or_query_response']
		}

		# print("query_reponsequery_reponsequery_reponsequery_reponse")
		# print(query_reponse)

	return query_reponse





def _search_hathi(reconcile_item):
	"""
		Do a Hathi  search
	"""	

	if reconcile_item['contributor_uncontrolled_last_first'] != False:
		html = _download_hathitrust_html(reconcile_item['title'], reconcile_item['contributor_uncontrolled_last_first'])
	elif reconcile_item['contributor_uncontrolled_first_last'] != False:
		html = _download_hathitrust_html(reconcile_item['title'], reconcile_item['contributor_uncontrolled_first_last'])
	elif reconcile_item['contributor_naco_controlled'] != False:
		html = _download_hathitrust_html(reconcile_item['title'], reconcile_item['contributor_naco_controlled'])

	data = _extract_hathitrust_data(html)
	
	return data




def _parse_results(data,reconcile_item):
	"""
		Parse the results based on quality checks other cleanup needed before we send it back to the client
	"""	

	last = None
	first = None
	result = {}

	result['or_query_response'] = []

	## no results found, zero
	if len(data) == 0:
		return result
	
	for a_hit in data:
		a_hit['score'] = 0.25

	# git more points to the first hits from the server
	initial_increment = 0.1
	decrement = 0.01
	for index, item in enumerate(data):
		increment = initial_increment - (index * decrement)
		if increment > 0:
			if 'score' in item: # Check if score key exists
				item['score'] += increment
			else: # Initialize score if it doesn't exist
				item['score'] = increment 

	for a_hit in data:



		# hathi trust results have full statement of responsibility, try to split off main title from isbd punctuation
		hathi_main_title = a_hit['title'].split("/")[0]
		hathi_main_title = hathi_main_title.split(";")[0]
		hathi_main_title = hathi_main_title.split(":")[0]

		hathi_main_title = hathi_main_title.strip()

		user_main_title = False
		if reconcile_item['title'] != False:			
			user_main_title = reconcile_item['title'].split("/")[0]
			user_main_title = user_main_title.split(";")[0]
			user_main_title = user_main_title.split(":")[0]
			user_main_title = user_main_title.strip()


		if hathi_main_title != False and user_main_title != False:
			
			score = 0
			hathi_main_title = normalize_string(hathi_main_title,False)
			user_main_title = normalize_string(user_main_title,False)		
			aResult = fuzz.token_sort_ratio(hathi_main_title, user_main_title) / 200 - 0.25
			score = score + aResult
			
			# print("hathi_main_title::",hathi_main_title )
			# print("user_main_title::",user_main_title )
			# print("aResult",aResult, "score", score,flush=True) 
			a_hit['score'] = a_hit['score'] + score




		# print(hathi_main_title,flush=True)
		# print(user_main_title,flush=True)

		user_name = False
		if reconcile_item['contributor_uncontrolled_last_first'] != False:
			user_name = reconcile_item['contributor_uncontrolled_last_first']
		elif reconcile_item['contributor_uncontrolled_first_last'] != False:
			user_name = reconcile_item['contributor_uncontrolled_first_last']
		elif reconcile_item['contributor_naco_controlled'] != False:
			user_name = reconcile_item['contributor_naco_controlled']

		if user_name != False:
			score = 0
			for author in a_hit['author']:

				# do basic string comparsions to add to the base score
				# no added info passed we should do some basic fuzzy string comparisons 
				# if they both have numbers then keep them otherwise remove numbers
				remove_numbers = True
				if has_numbers(user_name) == True and has_numbers(author) == True:
					remove_numbers = False
				reconcile_item_name_normalized = normalize_string(user_name,remove_numbers)
				hit_name_normalize = normalize_string(author,remove_numbers)		
				aResult = fuzz.token_sort_ratio(reconcile_item_name_normalized, hit_name_normalize) / 200 - 0.25
				score = score + aResult
				# print('authLabel:',author, '| user_name:', user_name, aResult, " # ", score,flush=True)
				a_hit['score'] = a_hit['score'] + score




		print(a_hit)
		print('-------')


		with open(f"data/cache/hathi_{a_hit['record_number']}",'w') as out:
			json.dump(a_hit,out)

		result['or_query_response'].append(
			{
				"id": f"https://catalog.hathitrust.org/Record/{a_hit['record_number']}",
				"name": a_hit['title'],
				"description": '',
				"score": a_hit['score'],
				"match": True,
				"type": [
					{
					"id": "hathi",
					"name": "HathiTrust"
					}
				]
			}
		)


	result['or_query_response'] = sorted(result['or_query_response'], key=lambda item: item['score'],reverse=True)




	# 	uri = f'http://viaf.org/viaf/{a_hit["recordData"]["VIAFCluster"]["viafID"]}'

	# 	# set the authLabel, really just the most popular label 
	# 	# start off with the viaf id in case we don't find the label.
	# 	authLabel = a_hit["recordData"]["VIAFCluster"]["viafID"]
	# 	if 'mainHeadings' in a_hit["recordData"]["VIAFCluster"]:
	# 		if 'data' in a_hit["recordData"]["VIAFCluster"]['mainHeadings']:
	# 			if len(a_hit["recordData"]["VIAFCluster"]['mainHeadings']['data']) > 0:
	# 				authLabel = html.unescape(str(a_hit["recordData"]["VIAFCluster"]['mainHeadings']['data'][0]['text']))


	# 	# titles are titles the name is connected to
	# 	titles = []
	# 	if 'titles' in a_hit["recordData"]["VIAFCluster"]:
	# 		if 'work' in a_hit["recordData"]["VIAFCluster"]['titles']:
	# 			for work in a_hit["recordData"]["VIAFCluster"]['titles']['work']:

	# 				titles.append(html.unescape(str(work['title'])))



	# 	score = 0.25

	# 	# do basic string comparsions to add to the base score
	# 	# no added info passed we should do some basic fuzzy string comparisons 
	# 	# if they both have numbers then keep them otherwise remove numbers
	# 	remove_numbers = True
	# 	if has_numbers(reconcile_item['name']) == True and has_numbers(authLabel) == True:
	# 		remove_numbers = False
	# 	reconcile_item_name_normalized = normalize_string(reconcile_item['name'],remove_numbers)
	# 	hit_name_normalize = normalize_string(authLabel,remove_numbers)		
	# 	score = score + fuzz.token_sort_ratio(reconcile_item_name_normalized, hit_name_normalize) / 100 - 0.5

	# 	# print('authLabel:',authLabel, score,flush=True)




	# 	# go through and see if we were passed a title does it match one on file
	# 	if 'title' in reconcile_item:
	# 		if reconcile_item['title'] != False:

	# 			for t in titles:

	# 				normalized_t = normalize_string(t).strip()
	# 				normalize_query_title = normalize_string(reconcile_item['title']).strip()

	# 				if len(normalize_query_title) > len(normalized_t):
	# 					# the passed title is larger than the related title
	# 					normalize_query_title = normalize_query_title[0:len(normalized_t)]
	# 				elif len(normalized_t) > len(normalize_query_title):
	# 					# related title is longer
	# 					normalized_t = normalized_t[0:len(normalize_query_title)]




	# 				# exact match, set it to perfect
	# 				if normalize_query_title == normalized_t:
	# 					score = 1						
	# 					break

	# 	was_reconciled_using_birthday = False
	# 	if 'birth_year' in reconcile_item:
	# 		if reconcile_item['birth_year'] != False:

	# 			# if the birth year is in the string and the fuzz match is close then set it to 1				
	# 			if (fuzz.token_sort_ratio(reconcile_item_name_normalized, hit_name_normalize) >= 65):
	# 				if reconcile_item['birth_year'] in authLabel:
	# 					score = 1

	# 				was_reconciled_using_birthday = True


	# 	data = {
	# 		"uri": uri,
	# 		"type": a_hit["recordData"]["VIAFCluster"]["nameType"],
	# 		"authLabel": authLabel,
	# 		'titles':titles,
	# 		'score':score,
	# 		"was_reconciled_using_birthday": was_reconciled_using_birthday
	# 	}



	# 	## put it in the cache for later if we need to generate a preview flyout for it
	# 	file_name = uri.replace(':','_').replace('/','_')
	# 	with open(f'data/cache/{file_name}','w') as out:
	# 		json.dump(a_hit,out)



	# counter = 0
	# for r in result['or_query_response']:

	# 	counter=counter+1

	# 	if counter>5:
	# 		break

	# 	if r['score'] == 1:
	# 		break


	# 	if 'birth_year' in reconcile_item:
	# 		if reconcile_item['birth_year'] != False:


	# 			wiki_birth_year = wikidata_return_birth_year_from_viaf_uri(r['id'])
	# 			if wiki_birth_year != False:
	# 				if str(wiki_birth_year) == str(reconcile_item['birth_year']):
	# 					r['score'] = 1
	# 					break

	# 			lc_birth_year = lc_return_birth_year_from_viaf_uri(r['id'])
	# 			if lc_birth_year != False:
	# 				if str(lc_birth_year) == str(reconcile_item['birth_year']):
	# 					r['score'] = 1
	# 					break



	# print("----------------")
	# print('result',result['or_query_response'],flush=True)

	return result



def extend_data(ids,properties):
	"""
		Sent Ids and proeprties it talks to viaf and returns the reuqested values
	"""

	response = {"meta":[],"rows":{}}

	for p in properties:

		if p['id'] == 'hdl':
			response['meta'].append({"id":"hdl",'name':'hdl'})
		if p['id'] == 'LCCN':
			response['meta'].append({"id":"LCCN",'name':'LCCN'})
		if p['id'] == 'OCLC':
			response['meta'].append({"id":"OCLC",'name':'OCLC'})
		if p['id'] == 'thumbnail':
			response['meta'].append({"id":"thumbnail",'name':'thumbnail'})


	for i in ids:

		response['rows'][i]={}


		hathi_id = i.split("/")[-1]
		data = None
		if os.path.isfile(f'data/cache/hathi_full_{hathi_id}'):
			data = json.load(open(f'data/cache/hathi_full_{hathi_id}'))
		else:
			# download the full record

			api_url = f"https://catalog.hathitrust.org/api/volumes/full/recordnumber/{hathi_id}.json"
			try:
				api_response = requests.get(api_url, headers=HT_HEADERS, timeout=15) # Increased timeout slightly
				api_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

				# Attempt to parse the JSON response
				data = api_response.json()

				# Save the downloaded data to cache
				try:
					with open(f'data/cache/hathi_full_{hathi_id}', 'w') as f:
						json.dump(data, f, indent=2) # Save formatted JSON
				except IOError as e:
					print(f"Error writing to cache file: {e}")
				except Exception as e: # Catch other potential file writing errors
					print(f"An unexpected error occurred writing cache file: {e}")

			except requests.exceptions.HTTPError as errh:
				print(f"Http Error fetching {api_url}: {errh.response.status_code} {errh.response.reason}")
				# Optionally log response body for debugging 4xx/5xx errors
				# print(f"Response body: {errh.response.text}")
			except requests.exceptions.ConnectionError as errc:
				print(f"Error Connecting fetching {api_url}: {errc}")
			except requests.exceptions.Timeout as errt:
				print(f"Timeout Error fetching {api_url}: {errt}")
			except requests.exceptions.RequestException as err:
				print(f"Oops: Something Else went wrong fetching {api_url}: {err}")
			except json.JSONDecodeError as e:
				# This happens if the response isn't valid JSON
				print(f"Error decoding JSON from {api_url}: {e}")
				print(f"Response status code: {api_response.status_code}")
				print(f"Response text: {api_response.text[:500]}...") # Log part of the non-JSON response text

		for p in properties:

			if p['id'] == 'hdl':
				print(data['items'],flush=True)
				if data != None:
					if "items" in data:
						hlds = []
						for hdl in data["items"]:
							if "htid" in hdl:
								hlds.append(hdl['htid'])
						
						if len(hlds) > 0:
							response['rows'][i]['hdl'] = [{'str':"|".join(hlds)}]	
						else:
							response['rows'][i]['htid'] = [{}]

			if p['id'] == 'OCLC':

				if data != None:
					if "records" in data:
						oclcs = []
						for rec_id in data["records"]:
							oclcs = oclcs + data["records"][rec_id]['oclcs']
						if len(oclcs) > 0:
							response['rows'][i]['OCLC'] = [{'str':"|".join(oclcs)}]	
						else:
							response['rows'][i]['OCLC'] = [{}]
			
			if p['id'] == 'ISBN':

				if data != None:
					if "records" in data:
						isbns = []
						for rec_id in data["records"]:
							isbns = isbns + data["records"][rec_id]['isbns']
						if len(isbns) > 0:
							response['rows'][i]['ISBN'] = [{'str':"|".join(isbns)}]	
						else:
							response['rows'][i]['ISBN'] = [{}]
			
			if p['id'] == 'LCCN':

				if data != None:
					if "records" in data:
						lccns = []
						for rec_id in data["records"]:
							lccns = lccns + data["records"][rec_id]['lccns']
						if len(lccns) > 0:
							response['rows'][i]['LCCN'] = [{'str':"|".join(lccns)}]	
						else:
							response['rows'][i]['LCCN'] = [{}]

			if p['id'] == 'thumbnail':


				if os.path.isfile(f'data/cache/hathi_{hathi_id}'):
					data = json.load(open(f'data/cache/hathi_{hathi_id}'))

					if 'thumbnail_url' in data:
						response['rows'][i]['thumbnail'] = [{'str':data['thumbnail_url']}]


	# print(properties)
	# print(response)
	# print(json.dumps(response,indent=2))
	return response


def _download_hathitrust_html(title='', author='', isbn=''):

	params = {
		'adv': '1',
		'lookfor[]': [],
		'type[]': [],
		'bool[]': [],
	}

	if title.strip() != '':
		params['lookfor[]'].append(title)
		params['type[]'].append('all')

	if author.strip() != '':
		params['lookfor[]'].append(author)
		params['type[]'].append('all')

	if isbn.strip() != '':
		params['lookfor[]'].append(isbn)
		params['type[]'].append('isn')

	if len(params['type[]']) == 1:
		del params['bool[]']
	elif len(params['type[]']) == 2:
		params['bool[]'] = 'AND'
	elif len(params['type[]']) == 3:
		params['bool[]'] = ['AND','AND']

	if HATHI_FULL_SEARCH_ONLY != None:
		params['ft'] = 'ft'

	print(params)
	base_url = "https://catalog.hathitrust.org/Search/Home"

	# testing for the URL
	# s = requests.Session()
	# req = requests.Request('GET', base_url, params=params)
	# prepped = s.prepare_request(req)
	# print(prepped.url)
	try:
		response = requests.get(base_url, params=params, headers=HT_HEADERS, timeout=10) # Added timeout
		response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
		return response.text
	except requests.exceptions.Timeout as e:
		print(f"Error: Request timed out: {e}")
		return None
	except requests.exceptions.HTTPError as e:
		print(f"Error: HTTP Error: {e.response.status_code} {e.response.reason}")
		return None
	except requests.exceptions.ConnectionError as e:
		print(f"Error: Connection Error: {e}")
		return None
	except requests.exceptions.RequestException as e:
		print(f"Error: An unexpected error occurred during the request: {e}")
		return None




def _extract_hathitrust_data(html_content):
	"""
	Parses HathiTrust search results HTML to extract book data.

	Args:
		html_content: A string containing the HTML source of the search results page.

	Returns:
		A list of dictionaries, where each dictionary represents a book record
		and contains the following keys:
		- 'title': The title of the book (str).
		- 'author': A list of authors (list of str).
		- 'year_published': The publication year (str).
		- 'data_hdl': The data-hdl identifier (str).
		- 'thumbnail_url': The URL of the cover thumbnail (str).
		- 'access_status': The access status text (e.g., "Multiple Items", 
						   "Limited (search only)", "Full view") (str).
		- 'record_number': The numeric record ID extracted from the catalog 
						   record URL (str), or None if not found.
	"""
	soup = BeautifulSoup(html_content, 'html.parser')
	results_list = []

	# Find all article tags representing individual records
	records = soup.select('section#section article.record')

	for record in records:
		book_data = {
			'title': None,
			'author': [],
			'year_published': None,
			'data_hdl': None,
			'thumbnail_url': None,
			'access_status': None,
			'record_number': None,
		}

		# --- Extract Title ---
		title_tag = record.select_one('h3.record-title span.title')
		if title_tag:
			book_data['title'] = title_tag.get_text(strip=True)

		# --- Extract Authors ---
		# Find the dt tag containing "Author" and then get its subsequent dd siblings within the same grid
		author_dt = record.find('dt', string='Author')
		if author_dt:
			author_grid = author_dt.find_parent(class_='grid')
			if author_grid:
				# Select all dd tags specifically within that grid
				author_dds = author_grid.find_all('dd', recursive=False) 
				for dd in author_dds:
					book_data['author'].append(dd.get_text(strip=True))
			# Fallback if grid structure not found (less precise)
			# elif author_dt:
			#     for dd in author_dt.find_next_siblings('dd'):
			#         # Stop if we hit the next dt tag
			#         if dd.find_previous_sibling('dt') != author_dt:
			#             break
			#         book_data['author'].append(dd.get_text(strip=True))


		# --- Extract Year Published ---
		year_dt = record.find('dt', string='Published')
		if year_dt:
			year_dd = year_dt.find_next_sibling('dd')
			if year_dd:
				book_data['year_published'] = year_dd.get_text(strip=True)

		# --- Extract data-hdl and Thumbnail URL ---
		cover_div = record.select_one('div.cover')
		if cover_div:
			book_data['data_hdl'] = cover_div.get('data-hdl')
			img_tag = cover_div.find('img', class_='bookCover')
			if img_tag and img_tag.has_attr('src'):
				# Prepend 'https:' if the URL starts with '//'
				src = img_tag['src']
				if src.startswith('//'):
					book_data['thumbnail_url'] = 'https:' + src
				else:
					book_data['thumbnail_url'] = src


		# --- Extract Access Status and Record Number ---
		access_container = record.select_one('.resource-access-container .list-group')
		if access_container:
			links = access_container.find_all('a', class_='list-group-item')
			if links:
				# Get Record Number from the *first* link (Catalog Record)
				first_link = links[0]
				href_catalog = first_link.get('href')
				if href_catalog:
					# Use regex to find the number after /Record/
					match = re.search(r'/Record/(\d+)', href_catalog)
					if match:
						book_data['record_number'] = match.group(1)

				# Get Access Status from the *last* link
				last_link = links[-1]
				book_data['access_status'] = last_link.get_text(strip=True)


		results_list.append(book_data)

	return results_list
