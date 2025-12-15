import requests
import html
import json
import re
import os
from thefuzz import fuzz

from typing import Dict, Any, List


from .strategies_helpers import _build_recon_dict
from .paths import CACHE_DIR
from .strategies_helpers import _build_recon_dict_name
from .paths import CACHE_DIR
from .strategies_helpers import normalize_string
from .paths import CACHE_DIR
from .strategies_helpers import has_numbers
from .paths import CACHE_DIR
from .strategies_helpers import wikidata_return_birth_year_from_viaf_uri
from .paths import CACHE_DIR
from .strategies_helpers import lc_return_birth_year_from_viaf_uri
from .paths import CACHE_DIR
from .strategies_helpers import remove_subtitle
from .paths import CACHE_DIR





VIAF_HEADERS = {
	'User-Agent':'Openrefine Post 45 Reconcilation Client'
}





def process_viaf_query(query,passed_config):
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


		reconcile_item = _build_recon_dict_name(data)
		# print('**',reconcile_item,flush=True)


		result =  _search_name(reconcile_item)

		result = _parse_name_results(result,reconcile_item)


		query_reponse[queryId] = {
			'result' : result['or_query_response']
		}

		# print("query_reponsequery_reponsequery_reponsequery_reponse")
		# print(query_reponse)

	return query_reponse





def _search_name(reconcile_item):
	"""
		Do a VIAF names search
	"""	
	url = 'https://viaf.org/api/search'

	

	field = 'local.names'
	if reconcile_item['type'] == 'VIAF_Personal':
		field='local.personalNames'

	query = {
	    "meta": {
	        "env": "prod",
	        "pageIndex": 0,
	        "pageSize": 50
	    },
	    "reqValues": {
	        "field": field,
	        "index": "VIAF",
	        "searchTerms": reconcile_item['name']
	    }
	}


	try:
		response = requests.post(url, json=query, headers=VIAF_HEADERS)
	except requests.exceptions.RequestException as e:  # This is the correct syntax
		print("ERROR:", e)
		# create an empty response
		return {
		    "message": "/api/search Successfully reached!",
		    "queryResult": {
		        "version": {
		            "value": 1.1,
		            "type": "xsd:string"
		        },
		        "numberOfRecords": {
		            "value": 0,
		            "type": "xsd:nonNegativeInteger"
		        },
		        "resultSetIdleTime": {
		            "value": 1,
		            "type": "xsd:positiveInteger"
		        },
		        "records": {
		            "record": []
		        }
		    }
		}

	data = response.json()
	data['successful'] = True
	data['error'] = None
	
	return data




def _parse_name_results(result,reconcile_item):
	"""
		Parse the results based on quality checks other cleanup needed before we send it back to the client
	"""	

	last = None
	first = None

	result['or_query_response'] = []

	## no results found, zero
	if 'records' not in result['queryResult']:
		return result

	for a_hit in result['queryResult']['records']['record']:


		# print(a_hit)
		# print('-------')

		uri = f'http://viaf.org/viaf/{a_hit["recordData"]["VIAFCluster"]["viafID"]}'

		# set the authLabel, really just the most popular label 
		# start off with the viaf id in case we don't find the label.
		authLabel = a_hit["recordData"]["VIAFCluster"]["viafID"]
		if 'mainHeadings' in a_hit["recordData"]["VIAFCluster"]:
			if 'data' in a_hit["recordData"]["VIAFCluster"]['mainHeadings']:
				if len(a_hit["recordData"]["VIAFCluster"]['mainHeadings']['data']) > 0:
					authLabel = html.unescape(str(a_hit["recordData"]["VIAFCluster"]['mainHeadings']['data'][0]['text']))


		# titles are titles the name is connected to
		titles = []
		if 'titles' in a_hit["recordData"]["VIAFCluster"]:
			if 'work' in a_hit["recordData"]["VIAFCluster"]['titles']:
				for work in a_hit["recordData"]["VIAFCluster"]['titles']['work']:

					titles.append(html.unescape(str(work['title'])))



		score = 0.25

		# do basic string comparsions to add to the base score
		# no added info passed we should do some basic fuzzy string comparisons 
		# if they both have numbers then keep them otherwise remove numbers
		remove_numbers = True
		if has_numbers(reconcile_item['name']) == True and has_numbers(authLabel) == True:
			remove_numbers = False
		reconcile_item_name_normalized = normalize_string(reconcile_item['name'],remove_numbers)
		hit_name_normalize = normalize_string(authLabel,remove_numbers)		
		score = score + fuzz.token_sort_ratio(reconcile_item_name_normalized, hit_name_normalize) / 100 - 0.5

		# print('authLabel:',authLabel, score,flush=True)




		# go through and see if we were passed a title does it match one on file
		if 'title' in reconcile_item:
			if reconcile_item['title'] != False:

				for t in titles:

					normalized_t = normalize_string(t).strip()
					normalize_query_title = normalize_string(reconcile_item['title']).strip()

					if len(normalize_query_title) > len(normalized_t):
						# the passed title is larger than the related title
						normalize_query_title = normalize_query_title[0:len(normalized_t)]
					elif len(normalized_t) > len(normalize_query_title):
						# related title is longer
						normalized_t = normalized_t[0:len(normalize_query_title)]




					# exact match, set it to perfect
					if normalize_query_title == normalized_t:
						score = 1						
						break

		was_reconciled_using_birthday = False
		if 'birth_year' in reconcile_item:
			if reconcile_item['birth_year'] != False:

				# if the birth year is in the string and the fuzz match is close then set it to 1				
				if (fuzz.token_sort_ratio(reconcile_item_name_normalized, hit_name_normalize) >= 65):
					if reconcile_item['birth_year'] in authLabel:
						score = 1

					was_reconciled_using_birthday = True


		data = {
			"uri": uri,
			"type": a_hit["recordData"]["VIAFCluster"]["nameType"],
			"authLabel": authLabel,
			'titles':titles,
			'score':score,
			"was_reconciled_using_birthday": was_reconciled_using_birthday
		}



		## put it in the cache for later if we need to generate a preview flyout for it
		file_name = uri.replace(':','_').replace('/','_')
		with open(f'{CACHE_DIR}/{file_name}','w') as out:
			json.dump(a_hit,out)




		result['or_query_response'].append(
			{
				"id": data['uri'],
				"name": data['authLabel'],
				"description": '',
				"score": data['score'],
				"match": True,
				"type": [
					{
					"id": "viaf",
					"name": "VIAF Cluster"
					}
				]
			}
		)


	result['or_query_response'] = sorted(result['or_query_response'], key=lambda item: item['score'],reverse=True)

	counter = 0
	for r in result['or_query_response']:

		counter=counter+1

		if counter>5:
			break

		if r['score'] == 1:
			break


		if 'birth_year' in reconcile_item:
			if reconcile_item['birth_year'] != False:


				wiki_birth_year = wikidata_return_birth_year_from_viaf_uri(r['id'])
				if wiki_birth_year != False:
					if str(wiki_birth_year) == str(reconcile_item['birth_year']):
						r['score'] = 1
						break

				lc_birth_year = lc_return_birth_year_from_viaf_uri(r['id'])
				if lc_birth_year != False:
					if str(lc_birth_year) == str(reconcile_item['birth_year']):
						r['score'] = 1
						break



	# print("----------------")
	# print('result',result['or_query_response'],flush=True)

	return result



def extend_data(ids,properties, passed_config):
	"""
		Sent Ids and proeprties it talks to viaf and returns the reuqested values
	"""

	response = {"meta":[],"rows":{}}

	for p in properties:

		if p['id'] == 'wikidata':
			response['meta'].append({"id":"wikidata",'name':'Wikidata'})
		# if p['id'] == 'LCCN':
		# 	response['meta'].append({"id":"LCCN",'name':'LCCN'})
		# if p['id'] == 'OCLC':
		# 	response['meta'].append({"id":"OCLC",'name':'OCLC'})


	for i in ids:

		response['rows'][i]={}

		for p in properties:

			if p['id'] == 'wikidata':
				print("Checking cache for",i,flush=True)
				# load it from the cache
				passed_id_escaped = i.replace(":",'_').replace("/",'_')
				if os.path.isfile(f'{CACHE_DIR}/{passed_id_escaped}'):
					data = json.load(open(f'{CACHE_DIR}/{passed_id_escaped}'))
					print("data",data,flush=True)
					allQids = re.findall(r"WKP\|Q[0-9]{2,}", json.dumps(data))

					if len(allQids) > 0:
						response['rows'][i]['wikidata'] = [{'str':allQids[0].split("|")[1]}]
					else:
						response['rows'][i]['wikidata'] = [{}]



		# instance_response = None
		# work_response = None

		# response['rows'][i]={}

		# if '/works/' in i:

		# 	for p in properties:

		# 		if p['id'] == 'ISBN':

		# 			if instance_response == None:
		# 				instance_response = requests.get(i.replace('/works/','/instances/')+'.bibframe.json')


		# 			value = _extend_extract_ISBN(instance_response)
		# 			print("valuevaluevaluevalue _extend_extract_ISBN",value)

		# 			response['rows'][i]['ISBN'] = value

		# 		if p['id'] == 'LCCN':

		# 			if instance_response == None:
		# 				instance_response = requests.get(i.replace('/works/','/instances/')+'.bibframe.json')


		# 			value = _extend_extract_LCCN(instance_response)
		# 			print("valuevaluevaluevalue _extend_extract_LCCN",value)
		# 			response['rows'][i]['LCCN'] = value

		# 		if p['id'] == 'OCLC':

		# 			if instance_response == None:
		# 				instance_response = requests.get(i.replace('/works/','/instances/')+'.bibframe.json')


		# 			value = _extend_extract_OCLC(instance_response)
		# 			print("valuevaluevaluevalue _extend_extract_OCLC",value)
		# 			response['rows'][i]['OCLC'] = value





	# print(properties)
	# print(response)
	# print(json.dumps(response,indent=2))
	return response


### ---------------- TITLES





def process_viaf_title_query(query, passed_config):
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

		

		result = _search_title(reconcile_item, passed_config)
		

		query_response[queryId] = {
			'result' : result['or_query_response']
		}

	return query_response






def _parse_viaf_headings(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses a VIAF API response to extract key details for each record.

    This function navigates the nested data structure to find the list of
    records. For each record, it extracts:
    - The VIAF ID.
    - All 'text' values from the 'mainHeadings.data' list.
    - A count of these main headings.
    - The total number of sources listed across all headings for that record.

    It safely handles cases where data might be missing or where a single item is
    not enclosed in a list. It also unescapes HTML entities in the text for
    better readability.

    Args:
        data: A dictionary representing the JSON response from the VIAF API.

    Returns:
        A list of dictionaries, where each dictionary corresponds to an input
        record and contains four keys:
        - 'viaf_id': The VIAF identifier for the record.
        - 'headings': A list of the 'text' values from 'mainHeadings'.
        - 'count': An integer representing the total number of main headings.
        - 'total_sources': The sum of the counts of all sources ('s' key)
                           across all main headings in that record.
        Returns an empty list if the input data is malformed or contains no
        records.
    """
    results = []
    print("data from viaf", data, flush=True)
    # Safely navigate to the list of records using .get() to avoid KeyErrors.
    records = data.get('queryResult', {}).get('records', {}).get('record', [])

    # Ensure we are always working with a list.
    if records and not isinstance(records, list):
        records = [records]

    for record in records:
        # Navigate to the VIAFCluster level, which contains the ID and headings.
        viaf_cluster = record.get('recordData', {}).get('VIAFCluster', {})
        
        # Safely extract the viafID.
        viaf_id = viaf_cluster.get('viafID')

        # Safely navigate to the mainHeadings data list.
        main_headings_list = viaf_cluster.get('mainHeadings', {}).get('data', [])
            
        # Ensure main_headings_list is a list for consistency.
        if main_headings_list and not isinstance(main_headings_list, list):
            main_headings_list = [main_headings_list]

        headings_text = []
        total_sources_count = 0

        # Iterate through each heading to extract text and count sources.
        for heading in main_headings_list:
            if isinstance(heading, dict):
                # Extract the text and unescape HTML entities.
                if 'text' in heading:
                    headings_text.append(html.unescape(heading['text']))
                
                # Safely get the list of sources and add its length to the total.
                sources_list = heading.get('sources', {}).get('s', [])
                total_sources_count += len(sources_list)

        headings_count = len(headings_text)

        results.append({
            'viaf_id': viaf_id,
            'headings': headings_text,
            'count': headings_count,
            'total_sources': total_sources_count
        })

        


    return results

def _search_title(reconcile_item, passed_config):
	"""
	Search VIAF for titles and apply fuzzy scoring to the results
	"""
	
	author = reconcile_item.get('author_name', '')
	title = reconcile_item.get('title', '')
	
	url = 'https://viaf.org/api/search'

	query = {
		'reqValues': {
			'field': 'local.uniformTitleWorks',
			'index': 'VIAF',
			'searchTerms': f'{author} {title}' if author else title,
		},
		'meta': {
			'env': 'prod',
			'pageIndex': 0,
			'pageSize': 50,
		},
	}

	headings = []

	try:
		response = requests.post(url, json=query, headers=VIAF_HEADERS)
		# process response
		headings = _parse_viaf_headings(response.json())
	except requests.exceptions.RequestException as e:  # This is the correct syntax
		print("ERROR:", e)
		return {'successful': False, 'error': str(e), 'results': []}

	print("Raw headings from VIAF:", headings, flush=True)
	
	# Apply fuzzy scoring to each heading
	scored_results = []
	
	for item in headings:
		if 'headings' not in item:
			continue
			
		# Process each heading variant
		for heading in item['headings']:
			# Split on "|" to separate author and title
			parts = heading.split('|')
			
			heading_author = ""
			heading_title = ""
			
			if len(parts) >= 2:
				# Format: "Author | Title"
				heading_author = parts[0].strip()
				heading_title = parts[1].strip()
			elif len(parts) == 1:
				# No separator, try to parse it differently
				# Could be "Title, by Author" or just "Title"
				text = parts[0].strip()
				if ', by ' in text.lower():
					title_parts = text.split(', by ', 1)
					heading_title = title_parts[0].strip()
					heading_author = title_parts[1].strip() if len(title_parts) > 1 else ""
				else:
					# Assume it's just a title
					heading_title = text
			
			# Calculate fuzzy scores
			title_score = 0
			author_score = 0
			
			# Score title (always do this)
			if title and heading_title:
				title_score = fuzz.token_sort_ratio(normalize_string(title), normalize_string(heading_title))
				print(f"Title comparison: '{title}' vs '{heading_title}' = {title_score}", flush=True)
			
			# Score author (only if author was provided)
			if author and author != "" and heading_author:
				# Determine if we should remove numbers
				remove_numbers = True
				if has_numbers(heading_author) and has_numbers(author):
					remove_numbers = False
				
				author_normalized = normalize_string(heading_author, remove_numbers)
				query_author_normalized = normalize_string(author, remove_numbers)
				
				author_score = fuzz.token_sort_ratio(author_normalized, query_author_normalized)
				print(f"Author comparison: '{author_normalized}' vs '{query_author_normalized}' = {author_score}", flush=True)
			
			# Calculate final score
			if author and author != "":
				# Both author and title matter
				if title_score >= 80 and author_score >= 80:
					final_score = 0.95
				elif title_score >= 70 and author_score >= 90:
					final_score = 0.90
				elif title_score >= 60 and author_score >= 85:
					final_score = 0.85
				elif title_score >= 50 and author_score >= 80:
					final_score = 0.75
				elif title_score >= 60 or author_score >= 60:
					final_score = 0.60
				else:
					final_score = 0.30
			else:
				# Only title matters
				if title_score >= 90:
					final_score = 0.95
				elif title_score >= 80:
					final_score = 0.85
				elif title_score >= 70:
					final_score = 0.70
				elif title_score >= 60:
					final_score = 0.60
				elif title_score >= 50:
					final_score = 0.50
				else:
					final_score = 0.30
			
			# Create a scored result
			scored_result = {
				'viaf_id': item.get('viaf_id', ''),
				'heading': heading,
				'heading_author': heading_author,
				'heading_title': heading_title,
				'count': item.get('count', 0),
				'total_sources': item.get('total_sources', 0),
				'title_score': title_score,
				'author_score': author_score,
				'fuzzy_score': final_score
			}
			
			scored_results.append(scored_result)
			print(f"Scored heading: {heading} - Title: {title_score}, Author: {author_score}, Final: {final_score}", flush=True)
	
	# Sort by total_sources (descending) first, then by fuzzy_score (descending)
	scored_results = sorted(scored_results, key=lambda x: (x['total_sources'], x['fuzzy_score']), reverse=True)
	
	print(f"Total scored results: {len(scored_results)}", flush=True)
	print(f"Top results after sorting: {scored_results[:3] if len(scored_results) > 3 else scored_results}", flush=True)
	
	result = {}
	result['or_query_response'] = []
	for hit in scored_results:

		result['or_query_response'].append({
			"id": f"http://viaf.org/viaf/{hit.get('viaf_id', 'ERROR')}",
			"name": hit.get('heading', 'ERROR'),
			"description": '',
			"score": hit.get('fuzzy_score', 0),
			"match": hit.get('fuzzy_score', 0) > 0.8,  # Consider it a match if score > 0.8
			"type": [
				{
					"id": "viaf:Work",
					"name": "VIAF Work"
				}
			]
		})



	return result


