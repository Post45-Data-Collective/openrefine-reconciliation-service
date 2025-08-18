import requests
import json
import xml.etree.ElementTree as ET
import re
import uuid
import os

from thefuzz import fuzz

from .strategies_helpers import _build_recon_dict
from .strategies_helpers import normalize_string
from .strategies_helpers import has_numbers
from .strategies_helpers import remove_subtitle



ID_HEADERS = {
	'User-Agent':'Openrefine Post 45 Reconcilation Client'
}



def process_id_query(query, passed_config):
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

		author_name = ""

		if reconcile_item['contributor_uncontrolled_last_first'] != False:
			author_name = reconcile_item['contributor_uncontrolled_last_first']
		elif reconcile_item['contributor_uncontrolled_first_last'] != False:
			author_name = reconcile_item['contributor_uncontrolled_first_last']
		elif reconcile_item['contributor_naco_controlled'] != False:
			author_name = reconcile_item['contributor_naco_controlled']

		reconcile_item['author_name'] = author_name

		# if they configured to remove subtitles then do that
		if config['POST45_REMOVE_SUBTITLE'] == True:
			reconcile_item['title'] = remove_subtitle(reconcile_item['title'])

		print("reconcile_item", reconcile_item, flush=True)


		result =  _search_id(reconcile_item,passed_config)
		print("result", result, flush=True)


		result =  _enrich_id(result)


		if config['POST45_RECONCILIATION_MODE'] == 'cluster':
			result = _cluster_works(result,reconcile_item,req_ip)
		elif config['POST45_RECONCILIATION_MODE'] == 'single':
			result = _parse_single_results(result,reconcile_item)



		query_reponse[queryId] = {
			'result' : result['or_query_response']
		}

		# print("query_reponsequery_reponsequery_reponsequery_reponse")
		# print(query_reponse)

	return query_reponse







def _search_id(reconcile_item,passed_config):
	"""
		Do a pretty broad and loose name + title search at id.loc.gov
	"""	

	url = 'https://id.loc.gov/resources/works/suggest2/'

	params = {
		'q' : f"{reconcile_item['author_name']} {reconcile_item['title']}".strip(),
		'searchtype': 'keyword',
		'rdftype': 'Text',
		'count': 50,
	}

	# if they have said not to limit by text then remove that param
	if passed_config['POST45_ID_RDFTYPE_TEXT_LIMIT'] == False:
		del params['rdftype']


	try:
		response = requests.get(url, params=params, headers=ID_HEADERS)
	except requests.exceptions.RequestException as e:  # This is the correct syntax
		print("ERROR:", e)
		# create a response 
		return {
			'successful': False,
			'error': str(e),
			'q': params['q'],
			'count':0,
			'pagesize': 10, 
			'start': 1, 
			'sortmethod': 'rank', 
			'searchtype': 'keyword', 
			'directory': '/resources/works/', 
			'hits': []
		}


	data = response.json()
	data['successful'] = True
	data['error'] = None



	# Score each hit based on fuzzy matching
	scored_hits = []
	for hit in data['hits']:
		file_name = hit['uri'].replace(':','_').replace('/','_')
		
		# Initialize score
		score = 0.5  # Base score for being in results
		
		# First, extract all contributors
		contributors = []
		if 'more' in hit and 'contributors' in hit['more']:
			contributors = hit['more']['contributors']
		
		# Also extract author from main label if present
		if 'aLabel' in hit and hit['aLabel'] and '.' in hit['aLabel']:
			# Author is usually before the first period
			main_author = hit['aLabel'].split('.')[0].strip()
			if main_author and main_author not in contributors:
				contributors.append(main_author)
		
		# Extract and clean title from hit
		hit_title = ''
		if 'aLabel' in hit and hit['aLabel']:
			hit_title = hit['aLabel']
			# Remove author portion if present (usually before period)
			if '.' in hit_title:
				hit_title = hit_title.split('.', 1)[-1].strip()
			
			# Remove any contributor strings from the title
			for contributor in contributors:
				if contributor and contributor in hit_title:
					hit_title = hit_title.replace(contributor, '').strip()
					# Clean up any leftover punctuation or spaces
					hit_title = hit_title.lstrip('.,;: ').strip()
		
		# Also check variant titles
		variant_titles = []
		if 'vLabel' in hit and hit['vLabel']:
			clean_variant = hit['vLabel']
			# Remove contributors from variant title
			for contributor in contributors:
				if contributor and contributor in clean_variant:
					clean_variant = clean_variant.replace(contributor, '').strip()
					clean_variant = clean_variant.lstrip('.,;: ').strip()
			if clean_variant:
				variant_titles.append(clean_variant)
				
		if 'more' in hit and 'varianttitles' in hit['more']:
			for vt in hit['more']['varianttitles']:
				clean_vt = vt
				# Remove contributors from each variant title
				for contributor in contributors:
					if contributor and contributor in clean_vt:
						clean_vt = clean_vt.replace(contributor, '').strip()
						clean_vt = clean_vt.lstrip('.,;: ').strip()
				if clean_vt:
					variant_titles.append(clean_vt)
		
		# Test title matching
		title_scores = []
		if reconcile_item['title']:
			# Test main title
			if hit_title:
				title_ratio = fuzz.token_sort_ratio(hit_title, reconcile_item['title'])
				print(f"Title comparison: '{hit_title}' vs '{reconcile_item['title']}' = {title_ratio}", flush=True)
				title_scores.append(title_ratio)
			
			# Test variant titles
			for variant in variant_titles:
				if variant:
					variant_ratio = fuzz.token_sort_ratio(variant, reconcile_item['title'])
					title_scores.append(variant_ratio)
		
		# Get best title score
		best_title_score = max(title_scores) if title_scores else 0
		
		# Test author/contributor matching if author_name is provided
		author_scores = []
		if reconcile_item['author_name'] and reconcile_item['author_name'] != "":
			# We already extracted contributors above
			for contributor in contributors:
				if contributor:
					# Determine if we should remove numbers
					remove_numbers = True
					if has_numbers(contributor) and has_numbers(reconcile_item['author_name']):
						remove_numbers = False
					
					# Normalize and compare
					contrib_normalized = normalize_string(contributor, remove_numbers)
					author_normalized = normalize_string(reconcile_item['author_name'], remove_numbers)
					
					author_ratio = fuzz.token_sort_ratio(contrib_normalized, author_normalized)
					author_scores.append(author_ratio)
					
					print(f"Author comparison: '{contrib_normalized}' vs '{author_normalized}' = {author_ratio}", flush=True)
		
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
		
		# Add score to hit
		hit['fuzzy_score'] = score
		hit['title_score'] = best_title_score
		hit['author_score'] = best_author_score
		scored_hits.append(hit)
		
		print(f"Hit: {hit.get('aLabel', 'N/A')} - Title Score: {best_title_score}, Author Score: {best_author_score}, Final Score: {score}", flush=True)
	
	# Sort hits by score
	data['hits'] = sorted(scored_hits, key=lambda x: x['fuzzy_score'], reverse=True)

	if passed_config['POST45_ID_CLUSTER_QUALITY_SCORE'] == 'very high':
		data['hits'] = [hit for hit in data['hits'] if hit['fuzzy_score'] >= 0.95]
	elif passed_config['POST45_ID_CLUSTER_QUALITY_SCORE'] == 'high':
		data['hits'] = [hit for hit in data['hits'] if hit['fuzzy_score'] >= 0.90]
	elif passed_config['POST45_ID_CLUSTER_QUALITY_SCORE'] == 'medium':
		data['hits'] = [hit for hit in data['hits'] if hit['fuzzy_score'] >= 0.80]
	elif passed_config['POST45_ID_CLUSTER_QUALITY_SCORE'] == 'low':
		data['hits'] = [hit for hit in data['hits'] if hit['fuzzy_score'] >= 0.60]
	elif passed_config['POST45_ID_CLUSTER_QUALITY_SCORE'] == 'very low':
		data['hits'] = [hit for hit in data['hits'] if hit['fuzzy_score'] >= 0.30]


	
	return data

def _enrich_id(data):
	"""
	Enrich hits with additional metadata from id.loc.gov RDF/XML
	"""
	
	# Define XML namespaces
	namespaces = {
		'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
		'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
		'bf': 'http://id.loc.gov/ontologies/bibframe/',
		'bflc': 'http://id.loc.gov/ontologies/bflc/',
		'madsrdf': 'http://www.loc.gov/mads/rdf/v1#',
		'lclocal': 'http://id.loc.gov/ontologies/lclocal/'
	}
	
	# Enrich the hits with additional information
	for hit in data.get('hits', []):
		# Check if hit has instance information
		instance_uri = None
		if 'more' in hit and 'instance' in hit['more']:
			instance_uri = hit['more']['instance']
		
		if not instance_uri:
			print(f"No instance URI found for hit: {hit.get('uri', 'unknown')}", flush=True)
			continue
		
		# Convert instance URI to CBD endpoint
		# From: http://id.loc.gov/resources/instances/2143880
		# To: http://id.loc.gov/resources/instances/2143880.cbd.rdf
		cbd_url = f"{instance_uri}.cbd.rdf"
		
		print(f"Fetching CBD data from: {cbd_url}", flush=True)
		
		try:
			# Fetch the CBD RDF data
			response = requests.get(cbd_url, headers=ID_HEADERS, timeout=10)
			response.raise_for_status()
			
			# Parse the XML
			root = ET.fromstring(response.text)
			
			# Extract data from bf:Work element
			work_elem = root.find('.//bf:Work', namespaces)
			if work_elem is not None:
				# Extract originDate
				origin_date = work_elem.find('.//bf:originDate', namespaces)
				if origin_date is not None:
					hit['originDate'] = origin_date.text
				
				# Extract language
				language_elem = work_elem.find('.//bf:language', namespaces)
				if language_elem is not None:
					# The language element usually has an rdf:resource attribute pointing to language URI
					lang_resource = language_elem.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
					if lang_resource:
						# Extract language code from URI (e.g., http://id.loc.gov/vocabulary/languages/eng -> eng)
						lang_code = lang_resource.split('/')[-1] if '/' in lang_resource else lang_resource
						hit['language'] = lang_code
				
				# Extract subjects
				subjects = []
				for subject in work_elem.findall('.//bf:subject/bf:Topic/rdfs:label', namespaces):
					if subject.text:
						subjects.append(subject.text)
				if subjects:
					hit['subjects'] = subjects
				
				# Extract genre forms
				genre_forms = []
				for genre in work_elem.findall('.//bf:genreForm/bf:GenreForm/rdfs:label', namespaces):
					if genre.text:
						genre_forms.append(genre.text)
				if genre_forms:
					hit['genreForms'] = genre_forms
			
			# Extract data from bf:Instance element(s)
			# Note: The CBD may contain multiple instances
			instances_data = []
			for instance_elem in root.findall('.//bf:Instance', namespaces):
				instance_info = {}
				
				# Extract responsibilityStatement
				resp_stmt = instance_elem.find('.//bf:responsibilityStatement', namespaces)
				if resp_stmt is not None:
					instance_info['responsibilityStatement'] = resp_stmt.text
				
				# Extract identifiers (ISBN, LCCN, etc.)
				identifiers = []
				
				# Get ISBNs
				for isbn_elem in instance_elem.findall('.//bf:identifiedBy/bf:Isbn', namespaces):
					isbn_value = isbn_elem.find('rdf:value', namespaces)
					isbn_qualifier = isbn_elem.find('bf:qualifier', namespaces)
					if isbn_value is not None and isbn_value.text:
						isbn_info = {'type': 'ISBN', 'value': isbn_value.text}
						if isbn_qualifier is not None and isbn_qualifier.text:
							isbn_info['qualifier'] = isbn_qualifier.text
						identifiers.append(isbn_info)
				
				# Get LCCN
				for lccn_elem in instance_elem.findall('.//bf:identifiedBy/bf:Lccn', namespaces):
					lccn_value = lccn_elem.find('rdf:value', namespaces)
					if lccn_value is not None and lccn_value.text:
						identifiers.append({'type': 'LCCN', 'value': lccn_value.text.strip()})
				
				# Get OCLC numbers if present
				for oclc_elem in instance_elem.findall('.//bf:identifiedBy/bf:OclcNumber', namespaces):
					oclc_value = oclc_elem.find('rdf:value', namespaces)
					if oclc_value is not None and oclc_value.text:
						identifiers.append({'type': 'OCLC', 'value': oclc_value.text.strip()})
				
				if identifiers:
					instance_info['identifiers'] = identifiers
				
				# Extract publication information from ProvisionActivity
				provision_activities = []
				for prov_elem in instance_elem.findall('.//bf:provisionActivity/bf:ProvisionActivity', namespaces):
					prov_info = {}
					
					# Get date
					date_elem = prov_elem.find('bf:date', namespaces)
					if date_elem is not None and date_elem.text:
						prov_info['date'] = date_elem.text
					
					# Get simple place
					place_elem = prov_elem.find('bflc:simplePlace', namespaces)
					if place_elem is not None and place_elem.text:
						prov_info['place'] = place_elem.text
					
					# Get simple agent (publisher)
					agent_elem = prov_elem.find('bflc:simpleAgent', namespaces)
					if agent_elem is not None and agent_elem.text:
						prov_info['agent'] = agent_elem.text
					
					if prov_info:
						provision_activities.append(prov_info)
				
				if provision_activities:
					instance_info['provisionActivities'] = provision_activities
				
				# Extract publicationStatement (often a consolidated version)
				pub_stmt = instance_elem.find('.//bf:publicationStatement', namespaces)
				if pub_stmt is not None and pub_stmt.text:
					instance_info['publicationStatement'] = pub_stmt.text
				
				# Extract extent (page count)
				extent_elem = instance_elem.find('.//bf:extent/bf:Extent/rdfs:label', namespaces)
				if extent_elem is not None and extent_elem.text:
					instance_info['extent'] = extent_elem.text
				
				# Extract dimensions
				dimensions_elem = instance_elem.find('.//bf:dimensions', namespaces)
				if dimensions_elem is not None and dimensions_elem.text:
					instance_info['dimensions'] = dimensions_elem.text
				
				# Extract edition statement
				edition_elem = instance_elem.find('.//bf:editionStatement', namespaces)
				if edition_elem is not None and edition_elem.text:
					instance_info['editionStatement'] = edition_elem.text
				
				# Add instance info if we found any data
				if instance_info:
					instances_data.append(instance_info)
			
			# Store the first instance data at the top level for convenience
			if instances_data:
				# Merge first instance data into hit
				first_instance = instances_data[0]
				for key, value in first_instance.items():
					hit[key] = value
				
				# Store all instances if there are multiple
				if len(instances_data) > 1:
					hit['allInstances'] = instances_data
			
			hit['enriched'] = True
			
		except requests.RequestException as e:
			print(f"Error fetching CBD data for {cbd_url}: {e}", flush=True)
			hit['enriched'] = False
			hit['enrichment_error'] = str(e)
		except ET.ParseError as e:
			print(f"Error parsing XML from {cbd_url}: {e}", flush=True)
			hit['enriched'] = False
			hit['enrichment_error'] = f"XML parse error: {str(e)}"
		except Exception as e:
			print(f"Unexpected error enriching {hit.get('uri', 'unknown')}: {e}", flush=True)
			hit['enriched'] = False
			hit['enrichment_error'] = str(e)
	
	return data

def _parse_single_results(data, reconcile_item):
	"""
	Parse the results from _search_id and format them for OpenRefine
	"""
	result = {}
	result['or_query_response'] = []
	
	# Process each hit from the scored results
	for hit in data.get('hits', []):
		# Start with the existing fuzzy score
		final_score = hit.get('fuzzy_score', 0.5)
		
		# Check if we should boost score based on publication year
		if reconcile_item.get('work_published_year') and reconcile_item['work_published_year'] != False:
			user_year = str(reconcile_item['work_published_year'])
			
			# Check enriched data for matching dates
			year_match = False
			
			# Check originDate first (from Work element)
			if 'originDate' in hit and hit['originDate']:
				if user_year in str(hit['originDate']):
					year_match = True
					print(f"Year match found in originDate: {hit['originDate']} matches {user_year}", flush=True)
			
			# Check provisionActivities dates (from Instance element)
			if not year_match and 'provisionActivities' in hit:
				for activity in hit['provisionActivities']:
					if 'date' in activity and activity['date']:
						if user_year in str(activity['date']):
							year_match = True
							print(f"Year match found in provisionActivity: {activity['date']} matches {user_year}", flush=True)
							break
			
			
			# Boost score if year matches
			if year_match:
				final_score = min(final_score + 1.0, 1.0)  # Add 1 but cap at 1.0
				print(f"Boosted score for {hit.get('uri', 'unknown')} from {hit.get('fuzzy_score', 0.5)} to {final_score} due to year match", flush=True)
		

		file_name = hit['uri'].replace(':','_').replace('/','_')
		with open(f"data/cache/id.loc.gov_{file_name}",'w') as out:
			json.dump(hit,out)

		# Create the OpenRefine response item
		result['or_query_response'].append({
			"id": hit['uri'],
			"name": hit.get('aLabel', hit.get('suggestLabel', '')),
			"description": '',
			"score": final_score,
			"match": final_score > 0.8,  # Consider it a match if score > 0.8
			"type": [
				{
					"id": "bf:work",
					"name": "Bibframe Work"
				}
			]
		})
	
	# Sort the results by score in descending order
	result['or_query_response'] = sorted(result['or_query_response'], key=lambda item: item['score'], reverse=True)
	return result



def _cluster_works(records,reconcile_item,req_ip):




	if 'hits' in records:
		records = records['hits']


	all_clusters = {
		'cluster' :  records,
		'cluster_excluded' : []
	}

	result = {}
	result['or_query_response'] = []
	
	use_id = str(uuid.uuid4())


	## need this for unit tests
	if 'APP_BASE' not in config:
		config['APP_BASE'] = 'http://localhost:5001/'


	use_uri = config['APP_BASE'] + 'cluster/id/' + use_id
	all_clusters['orginal'] = {
		'title': reconcile_item['title'],
		'author': reconcile_item['author_name'],
	}
	with open(f'data/cache/cluster_id_{use_id}','w') as out:
		json.dump(all_clusters,out)

	with open(f'data/cache/cluster_cache_id_{req_ip}','a') as out:
		out.write(f'cluster_id_{use_id}\n')

	result['or_query_response'].append({
			"id": use_uri,
			"name": f"clustered: {len(all_clusters['cluster'])}, Excluded: {len(all_clusters['cluster_excluded'])}",
			"description": '',
			"score": 1,
			"match": True,
			"type": [
				{
				"id": "id",
				"name": "LC_Work_Id"
			}
		]
	})

	return result


def _parse_title_uncontrolled_name_results(result,reconcile_item):
	"""
		Parse the results based on quality checks other cleanup needed before we send it back to the client
	"""	
	print("here")
	last = None
	first = None

	# split out the parts of the name
	if reconcile_item['contributor_uncontrolled_last_first'] != False:
		last = reconcile_item['contributor_uncontrolled_last_first'].split(',')[0].strip().split(' ')[0]

		first = reconcile_item['contributor_uncontrolled_last_first'].split(',')[1].strip().split(' ')[0]

	if reconcile_item['contributor_uncontrolled_first_last'] != False:
		last = reconcile_item['contributor_uncontrolled_first_last'].split(',')[1].strip().split(' ')[0]
		first = reconcile_item['contributor_uncontrolled_first_last'].split(',')[0].strip().split(' ')[0]




	print("hits",result['hits'])
	print("here2")

	result['or_query_response'] = []

	for a_hit in result['hits']:

		# if it was in the response from the server that means it matched something, so give it a basline score
		score = 0.5
		# print("----a_hit-----")
		# print(a_hit)
		# print("last",last)
		# print("first",first)
		a_hit['first'] = first
		a_hit['last'] = last

		# if the last name is not the first thing in AAP then we got a problem
		# TODO


		result['or_query_response'].append(
			{
				"id": a_hit['uri'],
				"name": a_hit['aLabel'],
				"description": '',
				"score": score,
				"match": True,
				"type": [
					{
					"id": "bf:work",
					"name": "Bibframe Work"
					}
				]
			}
		)



	return result






def extend_data(ids,properties,passed_config):
	"""
		Sent Ids and proeprties it talks to id.loc.gov and returns the reuqested values
	"""

	response = {"meta":[],"rows":{}}

	for p in properties:

		if p['id'] == 'ISBN':
			response['meta'].append({"id":"ISBN",'name':'ISBN'})
		if p['id'] == 'LCCN':
			response['meta'].append({"id":"LCCN",'name':'LCCN'})
		if p['id'] == 'OCLC':
			response['meta'].append({"id":"OCLC",'name':'OCLC'})
		if p['id'] == 'subjects':
			response['meta'].append({"id":"subjects",'name':'Subject Headings'})
		if p['id'] == 'URI':
			response['meta'].append({"id":"URI",'name':'Work URI'})
		if p['id'] == 'genres':
			response['meta'].append({"id":"genres",'name':'Genres'})


	for i in ids:

		instance_response = None
		work_response = None

		response['rows'][i]={}

		if '/works/' in i:

			for p in properties:

				if p['id'] == 'ISBN':

					if instance_response == None:
						instance_response = requests.get(i.replace('/works/','/instances/')+'.bibframe.json')


					value = _extend_extract_ISBN(instance_response)
					print("valuevaluevaluevalue _extend_extract_ISBN",value)

					response['rows'][i]['ISBN'] = value

				if p['id'] == 'LCCN':

					if instance_response == None:
						instance_response = requests.get(i.replace('/works/','/instances/')+'.bibframe.json')


					value = _extend_extract_LCCN(instance_response)
					print("valuevaluevaluevalue _extend_extract_LCCN",value)
					response['rows'][i]['LCCN'] = value

				if p['id'] == 'OCLC':

					if instance_response == None:
						instance_response = requests.get(i.replace('/works/','/instances/')+'.bibframe.json')

					value = _extend_extract_OCLC(instance_response)
					print("valuevaluevaluevalue _extend_extract_OCLC",value)
					response['rows'][i]['OCLC'] = value

				if p['id'] == 'URI':

					response['rows'][i]['URI'] = [{'str': i}]
				
				if p['id'] == 'subjects':
					
					if work_response == None:
						work_response = requests.get(i+'.json')
					
					value = _extend_extract_subject(work_response)
					print("valuevaluevaluevalue _extend_extract_subject",value)
					response['rows'][i]['subjects'] = value
				
				if p['id'] == 'genres':
					
					if work_response == None:
						work_response = requests.get(i+'.json')
					
					value = _extend_extract_genreForm(work_response)
					print("valuevaluevaluevalue _extend_extract_genreForm",value)
					response['rows'][i]['genres'] = value


		elif 'cluster/id' in i:

			uuid_val = i.split('/')[-1]

			filename = f'data/cache/cluster_id_{uuid_val}'
			if os.path.isfile(filename):
				data = json.load(open(filename))
				print(data,flush=True)
				
				# Extract data from cluster items
				for p in properties:
					if p['id'] == 'ISBN':
						isbn_values = []
						for item in data.get('cluster', []):
							if 'identifiers' in item:
								for identifier in item['identifiers']:
									if identifier.get('type') == 'ISBN':
										isbn_info = {"str": identifier['value']}
										if 'qualifier' in identifier:
											isbn_info['qualifier'] = identifier['qualifier']
										isbn_values.append(isbn_info)
						response['rows'][i]['ISBN'] = isbn_values if isbn_values else [{}]
					
					elif p['id'] == 'LCCN':
						lccn_values = []
						for item in data.get('cluster', []):
							if 'identifiers' in item:
								for identifier in item['identifiers']:
									if identifier.get('type') == 'LCCN':
										lccn_values.append({"str": identifier['value']})
						response['rows'][i]['LCCN'] = lccn_values if lccn_values else [{}]
					
					elif p['id'] == 'OCLC':
						oclc_values = []
						for item in data.get('cluster', []):
							if 'identifiers' in item:
								for identifier in item['identifiers']:
									if identifier.get('type') == 'OCLC':
										oclc_values.append({"str": identifier['value']})
						response['rows'][i]['OCLC'] = oclc_values if oclc_values else [{}]
					
					elif p['id'] == 'subjects':
						subjects_values = []
						for item in data.get('cluster', []):
							if 'subjects' in item and item['subjects']:
								for subject in item['subjects']:
									subjects_values.append({"str": subject})
						# Remove duplicates while preserving order
						seen = set()
						unique_subjects = []
						for subj in subjects_values:
							if subj['str'] not in seen:
								seen.add(subj['str'])
								unique_subjects.append(subj)
						response['rows'][i]['subjects'] = unique_subjects if unique_subjects else [{}]
					
					elif p['id'] == 'URI':
						uri_values = []
						for item in data.get('cluster', []):
							if 'uri' in item and item['uri']:
								uri_values.append({"str": item['uri']})
						response['rows'][i]['URI'] = uri_values if uri_values else [{}]
					
					elif p['id'] == 'genres':
						genres_values = []
						seen_genres = set()
						for item in data.get('cluster', []):
							# Check genreForms field (from enriched data)
							if 'genreForms' in item and item['genreForms']:
								for genre in item['genreForms']:
									if genre not in seen_genres:
										seen_genres.add(genre)
										genres_values.append({"str": genre})
							# Also check genres in more section
							elif 'more' in item and 'genres' in item['more'] and item['more']['genres']:
								for genre in item['more']['genres']:
									if genre not in seen_genres:
										seen_genres.add(genre)
										genres_values.append({"str": genre})
						response['rows'][i]['genres'] = genres_values if genres_values else [{}]




	print(i)
	print(properties)
	print(response)
	
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
	
	return response




def _extend_extract_subject(work_response):
	"""
	Extract subject headings from JSON-LD work response
	Returns list of subject labels
	"""
	try:
		graphs = work_response.json()
	except:
		print("Error parsing JSON response", work_response)
		return []
	
	# First, find the main Work object and extract subject URIs
	subject_uris = []
	for graph_item in graphs:
		if '@type' in graph_item:
			# Check if this is the Work object
			if any('bibframe/Work' in t for t in graph_item.get('@type', [])):
				# Extract subject URIs
				subjects = graph_item.get('http://id.loc.gov/ontologies/bibframe/subject', [])
				for subject in subjects:
					if '@id' in subject:
						subject_uris.append(subject['@id'])
	
	# Now create a mapping of URIs to labels from all graph items
	uri_to_label = {}
	for graph_item in graphs:
		if '@id' in graph_item:
			item_id = graph_item['@id']
			# Check if this item has a label
			labels = graph_item.get('http://www.w3.org/2000/01/rdf-schema#label', [])
			if labels:
				# Get the first English label (or any label if no language specified)
				label_text = None
				for label in labels:
					if isinstance(label, dict):
						if '@language' in label and label['@language'] == 'en':
							label_text = label.get('@value', '')
							break
						elif '@value' in label and not label_text:
							label_text = label.get('@value', '')
				
				if label_text:
					uri_to_label[item_id] = label_text
	
	# Build the return values using the labels
	values = []
	for uri in subject_uris:
		if uri in uri_to_label:
			values.append({"str": uri_to_label[uri]})
		else:
			# Fallback to URI if no label found
			values.append({"str": uri})
	
	if len(values) == 0:
		values = [{}]
		
	return values


def _extend_extract_genreForm(work_response):
	"""
	Extract genre/form headings from JSON-LD work response
	Returns list of genre labels
	"""
	try:
		graphs = work_response.json()
	except:
		print("Error parsing JSON response", work_response)
		return []
	
	# First, find the main Work object and extract genreForm URIs
	genre_uris = []
	for graph_item in graphs:
		if '@type' in graph_item:
			# Check if this is the Work object
			if any('bibframe/Work' in t for t in graph_item.get('@type', [])):
				# Extract genreForm URIs
				genres = graph_item.get('http://id.loc.gov/ontologies/bibframe/genreForm', [])
				for genre in genres:
					if '@id' in genre:
						genre_uris.append(genre['@id'])
	
	# Now create a mapping of URIs to labels from all graph items
	uri_to_label = {}
	for graph_item in graphs:
		if '@id' in graph_item:
			item_id = graph_item['@id']
			# Check if this is a GenreForm object
			types = graph_item.get('@type', [])
			if any('GenreForm' in t for t in types):
				# Get the label
				labels = graph_item.get('http://www.w3.org/2000/01/rdf-schema#label', [])
				if labels:
					# Get the first English label (or any label if no language specified)
					label_text = None
					for label in labels:
						if isinstance(label, dict):
							if '@language' in label and label['@language'] == 'en':
								label_text = label.get('@value', '')
								break
							elif '@value' in label and not label_text:
								label_text = label.get('@value', '')
					
					if label_text:
						uri_to_label[item_id] = label_text
	
	# Build the return values using the labels
	values = []
	for uri in genre_uris:
		if uri in uri_to_label:
			values.append({"str": uri_to_label[uri]})
		else:
			# Fallback to URI if no label found
			values.append({"str": uri})
	
	if len(values) == 0:
		values = [{}]
		
	return values


def _extend_extract_ISBN(instance_response):

	try:
		graphs=instance_response.json()
	except:
		print("Error Extend",instance_response)
		return("ERROR")


	# loop through the graphs and return the value for ISBN
	values = []
	for g in graphs:
		if '@type' in g:
			if 'http://id.loc.gov/ontologies/bibframe/Isbn' in g['@type']:
				if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value' in g:
					for v in g['http://www.w3.org/1999/02/22-rdf-syntax-ns#value']:
						if '@value' in v:
							values.append({"str":v['@value'].strip()})


	if len(values) == 0:
		values=[{}]

	return values


def _extend_extract_LCCN(instance_response):

	try:
		graphs=instance_response.json()
	except:
		print("Error Extend",instance_response)
		return("ERROR")


	# loop through the graphs and return the value for ISBN
	values = []
	for g in graphs:
		if '@type' in g:
			if 'http://id.loc.gov/ontologies/bibframe/Lccn' in g['@type']:
				if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value' in g:
					for v in g['http://www.w3.org/1999/02/22-rdf-syntax-ns#value']:
						if '@value' in v:
							values.append({"str":v['@value'].strip()})

	if len(values) == 0:
		values=[{}]

	return values


def _extend_extract_OCLC(instance_response):

	try:
		graphs=instance_response.json()
	except:
		print("Error Extend",instance_response)
		return("ERROR")


	# loop through the graphs and return the value for ISBN
	values = []
	for g in graphs:
		if '@type' in g:
			if 'http://id.loc.gov/ontologies/bibframe/OclcNumber' in g['@type']:
				if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value' in g:
					for v in g['http://www.w3.org/1999/02/22-rdf-syntax-ns#value']:
						if '@value' in v:
							values.append({"str":v['@value'].strip()})

	if len(values) == 0:
		values=[{}]

	return values

