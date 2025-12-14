import requests
import html
import json
import re
import os
from thefuzz import fuzz
from urllib.parse import quote

from typing import Dict, Any, List

from .strategies_helpers import _build_recon_dict
from .strategies_helpers import normalize_string
from .strategies_helpers import has_numbers
from .strategies_helpers import remove_subtitle





WIKIDATA_HEADERS = {
	'Accept': 'application/sparql-results+json',
	'User-Agent': 'Openrefine Post 45 Reconciliation Client'
}








def _search_title(reconcile_item, passed_config):
	"""
	Search Wikidata for titles using SPARQL and apply fuzzy scoring to the results
	"""
	
	author = reconcile_item.get('author_name', '')
	title = reconcile_item.get('title', '')
	
	# Build EntitySearch SPARQL query for Wikidata
	# Create search term - combine author and title if both are provided
	search_term = title
	
	# Escape quotes in search term
	search_term = search_term.replace('"', '\\"')
	
	sparql_query = f"""
	SELECT ?item ?itemLabel ?author ?authorLabel ?creator ?creatorLabel WHERE {{
	  SERVICE wikibase:mwapi {{
	    bd:serviceParam wikibase:api "EntitySearch" .
	    bd:serviceParam wikibase:endpoint "www.wikidata.org" .
	    bd:serviceParam mwapi:search "{search_term}" .
	    bd:serviceParam mwapi:language "en" .
	    ?item wikibase:apiOutputItem mwapi:item .
	    ?num wikibase:apiOrdinal true .
	  }}
	  OPTIONAL {{
	    ?item wdt:P50 ?author .
	  }}
	  OPTIONAL {{
	    ?item wdt:P170 ?creator .
	  }}
	  
	  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en" . }}
	}}
	LIMIT 50
	"""

	url = f"https://query.wikidata.org/sparql?query={quote(sparql_query)}"
	headers = WIKIDATA_HEADERS

	try:
		response = requests.get(url, headers=headers)
		data = response.json()
	except requests.exceptions.RequestException as e:
		print("ERROR:", e)
		return {'successful': False, 'error': str(e), 'or_query_response': []}

	print("Raw SPARQL results from Wikidata:", data, flush=True)
	
	# Parse SPARQL results and apply fuzzy scoring
	scored_results = []
	
	if 'results' in data and 'bindings' in data['results']:
		for binding in data['results']['bindings']:
			# Extract item data
			item_uri = binding.get('item', {}).get('value', '')
			item_label = binding.get('itemLabel', {}).get('value', '')
			
			# Extract author/creator data (prioritize author over creator)
			result_author = ""
			if 'authorLabel' in binding:
				result_author = binding['authorLabel'].get('value', '')
			elif 'creatorLabel' in binding:
				result_author = binding['creatorLabel'].get('value', '')
			
			# Skip results with no proper label (Q-IDs)
			if item_label.startswith('Q') and not any(c.isalpha() for c in item_label[1:]):
				continue
			
			# Calculate fuzzy scores
			title_score = 0
			author_score = 0
			
			# Score title (always do this)
			if title and item_label:
				title_score = fuzz.token_sort_ratio(normalize_string(title), normalize_string(item_label))
				print(f"Title comparison: '{title}' vs '{item_label}' = {title_score}", flush=True)
			
			# Score author (only if author was provided and result has author)
			if author and author != "" and result_author:
				# Determine if we should remove numbers
				remove_numbers = True
				if has_numbers(result_author) and has_numbers(author):
					remove_numbers = False
				
				author_normalized = normalize_string(result_author, remove_numbers)
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
				'wikidata_id': item_uri.replace('http://www.wikidata.org/entity/', ''),
				'item_label': item_label,
				'result_author': result_author,
				'title_score': title_score,
				'author_score': author_score,
				'fuzzy_score': final_score
			}
			
			scored_results.append(scored_result)
			print(f"Scored item: {item_label} - Title: {title_score}, Author: {author_score}, Final: {final_score}", flush=True)
	
	# Sort by fuzzy_score (descending)
	scored_results = sorted(scored_results, key=lambda x: x['fuzzy_score'], reverse=True)
	
	print(f"Total scored results: {len(scored_results)}", flush=True)
	print(f"Top results after sorting: {scored_results[:3] if len(scored_results) > 3 else scored_results}", flush=True)
	
	result = {}
	result['or_query_response'] = []
	for hit in scored_results:
		# Create description with author if available
		description = ""
		if hit.get('result_author'):
			description = f"by {hit['result_author']}"
		
		# Create display name
		display_name = hit.get('item_label', 'Unknown')
		if hit.get('result_author'):
			display_name = f"{hit['item_label']} | {hit['result_author']}"

		result['or_query_response'].append({
			"id": f"http://www.wikidata.org/entity/{hit.get('wikidata_id', 'ERROR')}",
			"name": display_name,
			"description": description,
			"score": hit.get('fuzzy_score', 0),
			"match": hit.get('fuzzy_score', 0) > 0.8,  # Consider it a match if score > 0.8
			"type": [
				{
					"id": "wikidata:Work",
					"name": "Wikidata Work"
				}
			]
		})

	return result


def process_wikidata_title_query(query, passed_config):
	"""This is what is called from the query endpoint for title searches"""
	global config
	config = passed_config

	req_ip = query['req_ip']
	del query['req_ip']  # Remove req_ip from the query dictionary to avoid passing it to _build_recon_dict
	
	query_response = {}
	# we need to figure out what type strategy we are going to use based on what they have sent with the request
	for queryId in query:
		data = query[queryId]
		print()
		reconcile_item = _build_recon_dict(data)
		
		author_name = ""

		if reconcile_item['contributor_uncontrolled_last_first'] != False:
			author_name = reconcile_item['contributor_uncontrolled_last_first']
		elif reconcile_item['contributor_uncontrolled_first_last'] != False:
			author_name = reconcile_item['contributor_uncontrolled_first_last']
		elif reconcile_item['contributor_naco_controlled'] != False:
			# Clean up NACO controlled names for better searching
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