import requests
import sqlite3
import html
import json
import re
import os
# from bs4 import BeautifulSoup
import uuid
import string

from thefuzz import fuzz

from .strategies_helpers import _build_recon_dict
from .strategies_helpers import normalize_string
from .strategies_helpers import has_numbers
from .strategies_helpers import remove_subtitle


config = {
}

HT_HEADERS = {
	'User-Agent':'Openrefine Post 45 Reconcilation Client',
}

def verify_sqlite_ready():
	"""Makes sure that the sqlite library works as well as FTS5 extension works"""
	try:
		import sqlite3
		con = sqlite3.connect(':memory:')
		cur = con.cursor()
		cur.execute('pragma compile_options;')
		available_pragmas = cur.fetchall()
		con.close()
		# print(available_pragmas)
		if ('ENABLE_FTS5',) in available_pragmas:
			return True
		else:
			return False
	except Exception as e:
		print(f"SQLite error: {e}")
		return False


def process_hathi_query(query, passed_config):
	"""This is what is called from the query endpoint, it will figure out how to process the work query
	"""
	global config
	config = passed_config


	req_ip = query['req_ip']
	del query['req_ip']  # Remove req_ip from the query dictionary to avoid passing it to _build_recon_dict
	
	query_reponse = {}
	# we need to figure out what type strategy we are going to use based on what they have sent with the reqest
	# with viaf personal just do the same search if they provided a title or not
	for queryId in query:
		


		data = query[queryId]


		reconcile_item = _build_recon_dict(data)
		# print('**',reconcile_item,flush=True)

		# if they configured to remove subtitles then do that
		if config['POST45_REMOVE_SUBTITLE'] == True:
			reconcile_item['title'] = remove_subtitle(reconcile_item['title'])




		result =  _search_hathi(reconcile_item)

		if config['POST45_RECONCILIATION_MODE'] == 'cluster':
			result = _cluster_works(result,reconcile_item,req_ip)
		elif config['POST45_RECONCILIATION_MODE'] == 'single':
			result = _parse_results(result,reconcile_item)



		query_reponse[queryId] = {
			'result' : result['or_query_response']
		}

		# print("query_reponsequery_reponsequery_reponsequery_reponse")
		# print(query_reponse)

	return query_reponse



def escape_fts5_string(query):
    escaped_query = query.replace('"', '""')
    return f'"{escaped_query}"'

	
def remove_punctuation(text):
	translator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
	text = text.translate(translator)
	# Remove extra spaces created by replacing punctuation with spaces
	text = re.sub(r'\s+', ' ', text).strip()

	return text


def _search_hathi(reconcile_item):
	"""
		Do a Hathi  search
	"""	
	print("SEArCHING HATHI", reconcile_item, flush=True)
	if reconcile_item['contributor_uncontrolled_last_first'] != False:
		records = _search_local_hathi_db(reconcile_item['title'], reconcile_item['contributor_uncontrolled_last_first'])
	elif reconcile_item['contributor_uncontrolled_first_last'] != False:
		records = _search_local_hathi_db(reconcile_item['title'], reconcile_item['contributor_uncontrolled_first_last'])
	elif reconcile_item['contributor_naco_controlled'] != False:
		records = _search_local_hathi_db(reconcile_item['title'], reconcile_item['contributor_naco_controlled'])

	# print("&&&&&records")
	# print(records)

	
	return records


def _cluster_works(records,reconcile_item,req_ip):

	author=''
	if reconcile_item['contributor_uncontrolled_last_first'] != False:
		author = reconcile_item['contributor_uncontrolled_last_first']
	elif reconcile_item['contributor_uncontrolled_first_last'] != False:
		author = reconcile_item['contributor_uncontrolled_first_last']
	elif reconcile_item['contributor_naco_controlled'] != False:
		author = reconcile_item['contributor_naco_controlled']

	all_clusters = {
		'cluster' :  [],
		'cluster_excluded' : []
	}
	# print("$$$$$$$records")
	# print(records)

	for record in records:
		# print("------record")
		# print(record)
		# remove any statement of responsiblity from the title
		hathi_main_title = record['title'].split("/")[0]
		# keep any subtitle in another variable
		hathi_main_title_variant = hathi_main_title
		# remove the subtitle from the main title		
		hathi_main_title = remove_subtitle(hathi_main_title)



		hathi_main_title_ratio = fuzz.token_sort_ratio(hathi_main_title, reconcile_item['title'])
		hathi_main_title_variant_ratio = fuzz.token_sort_ratio(hathi_main_title_variant, reconcile_item['title'])

		hathi_title_match_ratio = max(hathi_main_title_ratio, hathi_main_title_variant_ratio)

		if author != '':
			# test the author
			# do basic string comparsions to add to the base score
			# no added info passed we should do some basic fuzzy string comparisons 
			# if they both have numbers then keep them otherwise remove numbers
			remove_numbers = True
			if has_numbers(record['author']) == True and has_numbers(author) == True:
				remove_numbers = False
			reconcile_item_name_normalized = normalize_string(record['author'],remove_numbers)
			hit_name_normalize = normalize_string(author,remove_numbers)		
			aResult = fuzz.token_sort_ratio(reconcile_item_name_normalized, hit_name_normalize) 
			print(reconcile_item_name_normalized, "|||", hit_name_normalize, "|||", aResult, flush=True)
			print('authLabel:',author, '| user_name:', record['author'], aResult, " # ", flush=True)
			




		print("hathi_main_title", hathi_main_title, "|||", hathi_main_title_ratio)
		print("hathi_main_title_variant", hathi_main_title_variant, "|||", hathi_main_title_variant_ratio)
		if author == '':			
			if hathi_title_match_ratio > 80:
				all_clusters['cluster'].append(record)
			else:
				all_clusters['cluster_excluded'].append(record)
		else:
			if hathi_title_match_ratio > 80 and aResult > 80:
				all_clusters['cluster'].append(record)
			# if the title is sligghtly off but the author matches well then we can still include it
			elif hathi_title_match_ratio > 70 and aResult > 95:
				all_clusters['cluster'].append(record)		
			elif hathi_title_match_ratio > 50 and aResult >= 100:
				all_clusters['cluster'].append(record)								
			else:
				all_clusters['cluster_excluded'].append(record)


		# print(record)
		# print(hathi_main_title, "|||", hathi_main_title_ratio)
		# print(hathi_main_title_variant, "|||", hathi_main_title_variant_ratio)
		# print(hathi_main_title_variant)
	result = {}
	result['or_query_response'] = []
	print("---------all_clusters")
	print(all_clusters,flush=True)
	score = 1
	
	use_id = str(uuid.uuid4())

	## need this for unit tests
	if 'APP_BASE' not in config:
		config['APP_BASE'] = 'http://localhost:5001/'
# 	
	use_uri = config['APP_BASE'] + 'cluster/hathi/' + use_id
	all_clusters['orginal'] = {
		'title': reconcile_item['title'],
		'author': author,
	}
	with open(f'data/cache/cluster_hathi_{use_id}','w') as out:
		json.dump(all_clusters,out)

	with open(f'data/cache/cluster_cache_hathi_{req_ip}','a') as out:
		out.write(f'cluster_hathi_{use_id}\n')

	result['or_query_response'].append({
			"id": use_uri,
			"name": f"clustered: {len(all_clusters['cluster'])}, Excluded: {len(all_clusters['cluster_excluded'])}",
			"description": '',
			"score": score,
			"match": True,
			"type": [
				{
				"id": "hathi",
				"name": "HathiTrust"
				}
			]
		}
	)

	return result

def _search_local_hathi_db(title, author, test_mode=False):
	"""
	Searches the FTS5 table for author and title, then retrieves
	full records from the 'records' table using the rowid.
	"""

	db_path = "data/hathi/hathitrust.db" if not test_mode else "data/hathi/hathitrust_test.db"

	conn = None
	results = []
	try:
		conn = sqlite3.connect(db_path)
		cursor = conn.cursor()

		# Step 1: Search the FTS5 table
		fts_query = """
		SELECT rowid 
		FROM author_title 
		WHERE title MATCH ? AND author MATCH ? 
		ORDER BY rank;
		"""
		print(fts_query, (remove_punctuation(title), remove_punctuation(author)))
		for row in cursor.fetchall():
			print(row)

		cursor.execute(fts_query, (remove_punctuation(title), remove_punctuation(author)))
		rowids = [row[0] for row in cursor.fetchall()]

		if not rowids:
			print("No matching records found in author_title FTS table.")
			return []

		# Step 2: Retrieve records from the 'records' table using the rowids
		# We can use a placeholder for a list of IDs
		placeholders = ','.join('?' for _ in rowids)
		records_query = f"SELECT * FROM records WHERE ht_bib_key IN ({placeholders});"
		
		cursor.execute(records_query, rowids)
		column_names = [description[0] for description in cursor.description]
		
		for row in cursor.fetchall():
			results.append(dict(zip(column_names, row)))

	except sqlite3.Error as e:
		print(db_path)
		print(f"Current working directory: {os.getcwd()}")
		print(f"Database error during search: {e}")
	finally:
		if conn:
			conn.close()
	return results







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


	print("reconcile_item", reconcile_item, flush=True)
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


	print("a_hit['score'] 1", a_hit['score'], flush=True)

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


		print("a_hit['score'] 2", a_hit['score'], flush=True)

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
			author =  a_hit['author']

			# do basic string comparsions to add to the base score
			# no added info passed we should do some basic fuzzy string comparisons 
			# if they both have numbers then keep them otherwise remove numbers
			remove_numbers = True
			if has_numbers(user_name) == True and has_numbers(author) == True:
				remove_numbers = False
			reconcile_item_name_normalized = normalize_string(user_name,remove_numbers)
			hit_name_normalize = normalize_string(author,remove_numbers)	
			print("reconcile_item_name_normalized", reconcile_item_name_normalized, "||| hit_name_normalize", hit_name_normalize, flush=True)

			aResult = fuzz.token_sort_ratio(reconcile_item_name_normalized, hit_name_normalize) / 200 - 0.25
			score = score + aResult
			# print('authLabel:',author, '| user_name:', user_name, aResult, " # ", score,flush=True)
			a_hit['score'] = a_hit['score'] + score


		if 'work_published_year' in reconcile_item:
			if reconcile_item['work_published_year'] != False:
				pub_year = str(reconcile_item['work_published_year'])
				if a_hit['rights_date_used'] != '':
					# if the rights date is not empty then we can use it
					# this is the date that the work was published
					print(">>>>>>pub_year", pub_year, "rights_date_used", a_hit['rights_date_used'], flush=True)
					if pub_year in a_hit['rights_date_used']:
						a_hit['score'] = a_hit['score'] + 0.25




		print("a_hit['score'] 3", a_hit['score'], flush=True)

		print(a_hit)
		print('-------')


		with open(f"data/cache/hathi_{a_hit['ht_bib_key']}",'w') as out:
			json.dump(a_hit,out)

		result['or_query_response'].append(
			{
				"id": f"https://catalog.hathitrust.org/Record/{a_hit['ht_bib_key']}",
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


	return result



def extract_identifiers(record_dict):
    """
    Extract hdl, LCCN, OCLC identifiers from a HathiTrust record dictionary.
    
    Args:
        record_dict: Dictionary containing HathiTrust record data with keys like:
            - htid: HathiTrust item identifier (used as hdl)
            - lccn: Library of Congress Control Number
            - oclc_num: OCLC number
    
    Returns:
        Dictionary with extracted identifiers:
            - hdl: HathiTrust identifier (htid)
            - LCCN: Library of Congress Control Number
            - OCLC: OCLC number
    """
    identifiers = {}
    
    # Extract HDL (HathiTrust identifier)
    if 'htid' in record_dict and record_dict['htid']:
        identifiers['hdl'] = record_dict['htid'].split("|")
    
    # Extract LCCN
    if 'lccn' in record_dict and record_dict['lccn']:
        identifiers['LCCN'] = record_dict['lccn'].split(",")
    
    # Extract OCLC
    if 'oclc_num' in record_dict and record_dict['oclc_num']:
        identifiers['OCLC'] = record_dict['oclc_num'].split(",")
    


    return identifiers


def extend_data(ids,properties,passed_config):
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


		if 'cluster/hathi' in i:

			response['rows'][i] = {}
			response['rows'][i]['hdl'] = []
			response['rows'][i]['LCCN'] = []
			response['rows'][i]['OCLC'] = []
			response['rows'][i]['thumbnail'] = []

			uuid_val = i.split('/')[-1]

			filename = f'data/cache/cluster_hathi_{uuid_val}'
			if os.path.isfile(filename):
				data = json.load(open(filename))

				for rec in data['cluster']:

					rec_data = extract_identifiers(rec)


					print("rec_data", rec_data, flush=True)
					for p in properties:

						if p['id'] == 'hdl':
							if 'hdl' in rec_data:
								for value in rec_data['hdl']:
									response['rows'][i]['hdl'].append({'str':value})
						if p['id'] == 'OCLC':
							if 'OCLC' in rec_data:
								for value in rec_data['OCLC']:
									response['rows'][i]['OCLC'].append({'str':value})
						if p['id'] == 'LCCN':
							if 'LCCN' in rec_data:
								for value in rec_data['LCCN']:
									response['rows'][i]['LCCN'].append({'str':value})
						if p['id'] == 'thumbnail':
							if 'hdl' in rec_data:
								for value in rec_data['hdl']:
									response['rows'][i]['thumbnail'].append({'str':f"https://babel.hathitrust.org/cgi/imgsrv/cover?id={value};width=250"})

		else:

			response['rows'][i] = {}
			response['rows'][i]['hdl'] = []
			response['rows'][i]['LCCN'] = []
			response['rows'][i]['OCLC'] = []
			response['rows'][i]['thumbnail'] = []

			hathi_id = i.split("/")[-1]
			data = None
			if os.path.isfile(f'data/cache/hathi_{hathi_id}'):
				data = json.load(open(f'data/cache/hathi_{hathi_id}'))

				rec_data = extract_identifiers(data)
				for p in properties:

					if p['id'] == 'hdl':
						if 'hdl' in rec_data:
							for value in rec_data['hdl']:
								response['rows'][i]['hdl'].append({'str':value})
					if p['id'] == 'OCLC':
						if 'OCLC' in rec_data:
							for value in rec_data['OCLC']:
								response['rows'][i]['OCLC'].append({'str':value})
					if p['id'] == 'LCCN':
						if 'LCCN' in rec_data:
							for value in rec_data['LCCN']:
								response['rows'][i]['LCCN'].append({'str':value})
					if p['id'] == 'thumbnail':
						if 'hdl' in rec_data:
							for value in rec_data['hdl']:
								response['rows'][i]['thumbnail'].append({'str':f"https://babel.hathitrust.org/cgi/imgsrv/cover?id={value};width=250"})




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
					print("valuesvaluesvaluesvalues",values)
					response['rows'][row_id][field] = [{"str": '|'.join(values)}] if values else [{}]
					print(response['rows'][row_id][field])


	# print(properties)
	# print(response)
	# print(json.dumps(response,indent=2))
	return response


# def _download_hathitrust_html(title='', author='', isbn=''):

# 	params = {
# 		'adv': '1',
# 		'lookfor[]': [],
# 		'type[]': [],
# 		'bool[]': [],
# 	}

# 	if title.strip() != '':
# 		params['lookfor[]'].append(title)
# 		params['type[]'].append('title')

# 	if author.strip() != '':
# 		params['lookfor[]'].append(author)
# 		params['type[]'].append('author')

# 	if isbn.strip() != '':
# 		params['lookfor[]'].append(isbn)
# 		params['type[]'].append('isn')

# 	if len(params['type[]']) == 1:
# 		del params['bool[]']
# 	elif len(params['type[]']) == 2:
# 		params['bool[]'] = 'AND'
# 	elif len(params['type[]']) == 3:
# 		params['bool[]'] = ['AND','AND']

# 	if HATHI_FULL_SEARCH_ONLY != None:
# 		params['ft'] = 'ft'

# 	print(params)
# 	base_url = "https://catalog.hathitrust.org/Search/Home"

# 	# testing for the URL
# 	# s = requests.Session()
# 	# req = requests.Request('GET', base_url, params=params)
# 	# prepped = s.prepare_request(req)
# 	# print(prepped.url)
# 	try:
# 		response = requests.get(base_url, params=params, headers=HT_HEADERS, timeout=10) # Added timeout
# 		response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
# 		return response.text
# 	except requests.exceptions.Timeout as e:
# 		print(f"Error: Request timed out: {e}")
# 		# print("URL:", response.history[0].url if response.history else response.url)  # Print the URL for debugging
# 		return None
# 	except requests.exceptions.HTTPError as e:
# 		print(f"Error: HTTP Error: {e.response.status_code} {e.response.reason}")
# 		# print("URL:", response.history[0].url if response.history else response.url)  # Print the URL for debugging
# 		return None
# 	except requests.exceptions.ConnectionError as e:
# 		print(f"Error: Connection Error: {e}")
# 		# print("URL:", response.history[0].url if response.history else response.url)  # Print the URL for debugging
# 		return None
# 	except requests.exceptions.RequestException as e:
# 		print(f"Error: An unexpected error occurred during the request: {e}")
# 		# print("URL:", response.history[0].url if response.history else response.url)  # Print the URL for debugging
# 		return None
		




# def _extract_hathitrust_data(html_content):
# 	"""
# 	Parses HathiTrust search results HTML to extract book data.

# 	Args:
# 		html_content: A string containing the HTML source of the search results page.

# 	Returns:
# 		A list of dictionaries, where each dictionary represents a book record
# 		and contains the following keys:
# 		- 'title': The title of the book (str).
# 		- 'author': A list of authors (list of str).
# 		- 'year_published': The publication year (str).
# 		- 'data_hdl': The data-hdl identifier (str).
# 		- 'thumbnail_url': The URL of the cover thumbnail (str).
# 		- 'access_status': The access status text (e.g., "Multiple Items", 
# 						   "Limited (search only)", "Full view") (str).
# 		- 'record_number': The numeric record ID extracted from the catalog 
# 						   record URL (str), or None if not found.
# 	"""
# 	print("--------html_content--------")
# 	print(html_content)	
# 	print("-----xxxx---html_content-----xxxx---")

	soup = BeautifulSoup(html_content, 'html.parser')
# 	results_list = []

# 	# Find all article tags representing individual records
# 	records = soup.select('section#section article.record')

# 	for record in records:
# 		book_data = {
# 			'title': None,
# 			'author': [],
# 			'year_published': None,
# 			'data_hdl': None,
# 			'thumbnail_url': None,
# 			'access_status': None,
# 			'record_number': None,
# 		}

# 		# --- Extract Title ---
# 		title_tag = record.select_one('h3.record-title span.title')
# 		if title_tag:
# 			book_data['title'] = title_tag.get_text(strip=True)

# 		# --- Extract Authors ---
# 		# Find the dt tag containing "Author" and then get its subsequent dd siblings within the same grid
# 		author_dt = record.find('dt', string='Author')
# 		if author_dt:
# 			author_grid = author_dt.find_parent(class_='grid')
# 			if author_grid:
# 				# Select all dd tags specifically within that grid
# 				author_dds = author_grid.find_all('dd', recursive=False) 
# 				for dd in author_dds:
# 					book_data['author'].append(dd.get_text(strip=True))
# 			# Fallback if grid structure not found (less precise)
# 			# elif author_dt:
# 			#     for dd in author_dt.find_next_siblings('dd'):
# 			#         # Stop if we hit the next dt tag
# 			#         if dd.find_previous_sibling('dt') != author_dt:
# 			#             break
# 			#         book_data['author'].append(dd.get_text(strip=True))


# 		# --- Extract Year Published ---
# 		year_dt = record.find('dt', string='Published')
# 		if year_dt:
# 			year_dd = year_dt.find_next_sibling('dd')
# 			if year_dd:
# 				book_data['year_published'] = year_dd.get_text(strip=True)

# 		# --- Extract data-hdl and Thumbnail URL ---
# 		cover_div = record.select_one('div.cover')
# 		if cover_div:
# 			book_data['data_hdl'] = cover_div.get('data-hdl')
# 			img_tag = cover_div.find('img', class_='bookCover')
# 			if img_tag and img_tag.has_attr('src'):
# 				# Prepend 'https:' if the URL starts with '//'
# 				src = img_tag['src']
# 				if src.startswith('//'):
# 					book_data['thumbnail_url'] = 'https:' + src
# 				else:
# 					book_data['thumbnail_url'] = src


# 		# --- Extract Access Status and Record Number ---
# 		access_container = record.select_one('.resource-access-container .list-group')
# 		if access_container:
# 			links = access_container.find_all('a', class_='list-group-item')
# 			if links:
# 				# Get Record Number from the *first* link (Catalog Record)
# 				first_link = links[0]
# 				href_catalog = first_link.get('href')
# 				if href_catalog:
# 					# Use regex to find the number after /Record/
# 					match = re.search(r'/Record/(\d+)', href_catalog)
# 					if match:
# 						book_data['record_number'] = match.group(1)

# 				# Get Access Status from the *last* link
# 				last_link = links[-1]
# 				book_data['access_status'] = last_link.get_text(strip=True)


# 		results_list.append(book_data)

# 	return results_list
