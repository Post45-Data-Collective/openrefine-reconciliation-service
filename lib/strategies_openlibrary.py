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




OPENLIBRARY_HEADERS = {
	'Accept': 'application/json',
	'User-Agent': 'Openrefine Post 45 Reconciliation Client'
}






def _search_title(reconcile_item, passed_config):
	"""
	Search Open Library for titles using search API and apply fuzzy scoring to the results
	"""

	author = reconcile_item.get('author_name', '')
	title = reconcile_item.get('title', '')

	# Build Open Library search URL
	params = {}
	if title:
		params['title'] = title
	if author:
		params['author'] = author

	# Add limit
	params['limit'] = '50'

	# Build query string
	query_parts = []
	for key, value in params.items():
		query_parts.append(f"{key}={quote(value)}")
	query_string = "&".join(query_parts)

	url = f"https://openlibrary.org/search.json?{query_string}"
	# print("url", url, flush=True)
	headers = OPENLIBRARY_HEADERS

	try:
		response = requests.get(url, headers=headers)
		data = response.json()
	except requests.exceptions.RequestException as e:
		print("ERROR:", e)
		return {'successful': False, 'error': str(e), 'or_query_response': []}

	# print("Raw search results from Open Library:", data, flush=True)

	# Parse results and apply fuzzy scoring
	scored_results = []

	if 'docs' in data:
		for doc in data['docs']:
			# Extract work data
			work_key = doc.get('key', '')
			work_title = doc.get('title', '')

			# Extract author data
			result_authors = doc.get('author_name', [])
			result_author = result_authors[0] if result_authors else ""

			# Skip results with no title
			if not work_title:
				continue

			# Calculate fuzzy scores
			title_score = 0
			author_score = 0

			# Score title (always do this)
			if title and work_title:
				title_score = fuzz.token_sort_ratio(normalize_string(title), normalize_string(work_title))
				# print(f"Title comparison: '{title}' vs '{work_title}' = {title_score}", flush=True)

			# Score author (only if author was provided and result has author)
			if author and author != "" and result_author:
				# Determine if we should remove numbers
				remove_numbers = True
				if has_numbers(result_author) and has_numbers(author):
					remove_numbers = False

				author_normalized = normalize_string(result_author, remove_numbers)
				query_author_normalized = normalize_string(author, remove_numbers)

				author_score = fuzz.token_sort_ratio(author_normalized, query_author_normalized)
				# print(f"Author comparison: '{author_normalized}' vs '{query_author_normalized}' = {author_score}", flush=True)

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

			# Create a scored result with additional metadata
			scored_result = {
				'work_key': work_key,
				'work_title': work_title,
				'result_author': result_author,
				'first_publish_year': doc.get('first_publish_year'),
				'edition_count': doc.get('edition_count'),
				'cover_i': doc.get('cover_i'),
				'language': doc.get('language', []),
				'title_score': title_score,
				'author_score': author_score,
				'fuzzy_score': final_score
			}

			scored_results.append(scored_result)
			# print(f"Scored item: {work_title} - Title: {title_score}, Author: {author_score}, Final: {final_score}", flush=True)

	# Sort by fuzzy_score (descending)
	scored_results = sorted(scored_results, key=lambda x: x['fuzzy_score'], reverse=True)

	# print(f"Total scored results: {len(scored_results)}", flush=True)
	# print(f"Top results after sorting: {scored_results[:3] if len(scored_results) > 3 else scored_results}", flush=True)

	result = {}
	result['or_query_response'] = []
	for hit in scored_results:
		# Create description with author and year if available
		description_parts = []
		if hit.get('result_author'):
			description_parts.append(f"by {hit['result_author']}")
		if hit.get('first_publish_year'):
			description_parts.append(f"({hit['first_publish_year']})")
		description = " ".join(description_parts)

		# Create display name
		display_name = hit.get('work_title', 'Unknown')
		if hit.get('result_author'):
			display_name = f"{hit['work_title']} | {hit['result_author']}"

		result['or_query_response'].append({
			"id": f"https://openlibrary.org{hit.get('work_key', '/works/ERROR')}",
			"name": display_name,
			"description": description,
			"score": hit.get('fuzzy_score', 0),
			"match": hit.get('fuzzy_score', 0) > 0.8,  # Consider it a match if score > 0.8
			"type": [
				{
					"id": "openlibrary:Work",
					"name": "Open Library Work"
				}
			]
		})

	return result


def process_openlibrary_title_query(query, passed_config):
	"""This is what is called from the query endpoint for title searches"""
	global config
	config = passed_config

	req_ip = query['req_ip']
	del query['req_ip']  # Remove req_ip from the query dictionary to avoid passing it to _build_recon_dict

	query_response = {}
	# we need to figure out what type strategy we are going to use based on what they have sent with the request
	for queryId in query:
		data = query[queryId]
		# print()
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


def extend_data(ids, properties, passed_config):
	"""
	Extend Open Library work data with additional properties
	Fetches individual work data from the Open Library API
	"""

	# print("Open Library Extend Data Called", flush=True)
	# print("IDs:", ids, flush=True)
	# print("Properties:", properties, flush=True)

	extend_response = {
		"meta": [],
		"rows": {}
	}

	# Build metadata for requested properties
	property_map = {
		"description": {"id": "description", "name": "Description"},
		"subjects": {"id": "subjects", "name": "Subjects"},
		"subject_places": {"id": "subject_places", "name": "Subject Places"},
		"subject_people": {"id": "subject_people", "name": "Subject People"},
		"subject_times": {"id": "subject_times", "name": "Subject Times"},
		"first_publish_year": {"id": "first_publish_year", "name": "First Publish Year"},
		"covers": {"id": "covers", "name": "Cover IDs"},
		"edition_count": {"id": "edition_count", "name": "Edition Count"},
		"title": {"id": "title", "name": "Title"},
		# Edition-based properties (from /editions.json endpoint)
		"isbn_13": {"id": "isbn_13", "name": "ISBN 13"},
		"isbn_10": {"id": "isbn_10", "name": "ISBN 10"},
		"pagination": {"id": "pagination", "name": "Pagination"},
		"publishers": {"id": "publishers", "name": "Publishers"},
		"oclc_numbers": {"id": "oclc_numbers", "name": "OCLC Numbers"},
		"lc_classifications": {"id": "lc_classifications", "name": "LCC Classifications"},
		"dewey_decimal_class": {"id": "dewey_decimal_class", "name": "Dewey Decimal Class"},
		"identifiers.amazon": {"id": "identifiers.amazon", "name": "Amazon ID"},
		"identifiers.better_world_books": {"id": "identifiers.better_world_books", "name": "Better World Books ID"},
	}

	# Properties that require fetching from the editions endpoint
	edition_properties = {
		"isbn_13", "isbn_10", "pagination", "publishers", "oclc_numbers",
		"lc_classifications", "dewey_decimal_class", "identifiers.amazon",
		"identifiers.better_world_books"
	}

	for prop in properties:
		if prop['id'] in property_map:
			extend_response['meta'].append(property_map[prop['id']])

	# Check if any edition properties are requested
	requested_prop_ids = {prop['id'] for prop in properties}
	needs_editions = bool(requested_prop_ids & edition_properties)

	# Process each work ID
	for work_id in ids:
		# Extract work key from URL
		work_key = work_id
		if 'openlibrary.org' in work_id:
			# Extract work key from URL like https://openlibrary.org/works/OL45804W
			work_key = work_id.split('openlibrary.org')[-1]

		# Build response for this work
		work_response = {}
		work_data = {}
		editions_data = []

		# Fetch work data if needed for work-level properties
		work_level_props = {"description", "subjects", "subject_places", "subject_people",
						   "subject_times", "first_publish_year", "covers", "edition_count", "title"}
		if requested_prop_ids & work_level_props:
			work_json_key = work_key + '.json' if not work_key.endswith('.json') else work_key
			url = f"https://openlibrary.org{work_json_key}"
			try:
				response = requests.get(url, headers=OPENLIBRARY_HEADERS)
				work_data = response.json()
				# print(f"Fetched work data for {work_key}: {work_data}", flush=True)
			except requests.exceptions.RequestException as e:
				print(f"Error fetching work data for {work_key}: {e}", flush=True)

		# Fetch editions data if needed
		if needs_editions:
			# Remove .json if present, then add /editions.json
			editions_key = work_key.replace('.json', '') + '/editions.json'
			editions_url = f"https://openlibrary.org{editions_key}"
			try:
				response = requests.get(editions_url, headers=OPENLIBRARY_HEADERS)
				editions_response = response.json()
				editions_data = editions_response.get('entries', [])
				# print(f"Fetched {len(editions_data)} editions for {work_key}", flush=True)
			except requests.exceptions.RequestException as e:
				print(f"Error fetching editions data for {work_key}: {e}", flush=True)

		try:
			for prop in properties:
				prop_id = prop['id']

				if prop_id == "description":
					# Description can be a string or an object with 'value' key
					desc = work_data.get('description', '')
					if isinstance(desc, dict):
						desc = desc.get('value', '')
					work_response[prop_id] = [{"str": desc}] if desc else []

				elif prop_id == "subjects":
					subjects = work_data.get('subjects', [])
					work_response[prop_id] = [{"str": subj} for subj in subjects]

				elif prop_id == "subject_places":
					subject_places = work_data.get('subject_places', [])
					work_response[prop_id] = [{"str": place} for place in subject_places]

				elif prop_id == "subject_people":
					subject_people = work_data.get('subject_people', [])
					work_response[prop_id] = [{"str": person} for person in subject_people]

				elif prop_id == "subject_times":
					subject_times = work_data.get('subject_times', [])
					work_response[prop_id] = [{"str": time} for time in subject_times]

				elif prop_id == "first_publish_year":
					# This comes from search results, not individual work endpoint
					work_response[prop_id] = []

				elif prop_id == "covers":
					covers = work_data.get('covers', [])
					# Filter out -1 values (invalid covers)
					covers = [c for c in covers if c != -1]
					work_response[prop_id] = [{"str": str(cover_id)} for cover_id in covers]

				elif prop_id == "edition_count":
					# This comes from search results, not individual work endpoint
					work_response[prop_id] = []

				elif prop_id == "title":
					title = work_data.get('title', '')
					work_response[prop_id] = [{"str": title}] if title else []

				# Edition-based properties - aggregate from all editions
				elif prop_id == "isbn_13":
					all_isbn13 = set()
					for edition in editions_data:
						for isbn in edition.get('isbn_13', []):
							all_isbn13.add(isbn)
					work_response[prop_id] = [{"str": isbn} for isbn in sorted(all_isbn13)]

				elif prop_id == "isbn_10":
					all_isbn10 = set()
					for edition in editions_data:
						for isbn in edition.get('isbn_10', []):
							all_isbn10.add(isbn)
					work_response[prop_id] = [{"str": isbn} for isbn in sorted(all_isbn10)]

				elif prop_id == "pagination":
					all_pagination = set()
					for edition in editions_data:
						pagination = edition.get('pagination')
						if pagination:
							all_pagination.add(pagination)
					work_response[prop_id] = [{"str": p} for p in sorted(all_pagination)]

				elif prop_id == "publishers":
					all_publishers = set()
					for edition in editions_data:
						for publisher in edition.get('publishers', []):
							all_publishers.add(publisher)
					work_response[prop_id] = [{"str": p} for p in sorted(all_publishers)]

				elif prop_id == "oclc_numbers":
					all_oclc = set()
					for edition in editions_data:
						for oclc in edition.get('oclc_numbers', []):
							all_oclc.add(oclc)
					work_response[prop_id] = [{"str": o} for o in sorted(all_oclc)]

				elif prop_id == "lc_classifications":
					all_lcc = set()
					for edition in editions_data:
						for lcc in edition.get('lc_classifications', []):
							all_lcc.add(lcc)
					work_response[prop_id] = [{"str": lcc} for lcc in sorted(all_lcc)]

				elif prop_id == "dewey_decimal_class":
					all_dewey = set()
					for edition in editions_data:
						for dewey in edition.get('dewey_decimal_class', []):
							all_dewey.add(dewey)
					work_response[prop_id] = [{"str": d} for d in sorted(all_dewey)]

				elif prop_id == "identifiers.amazon":
					all_amazon = set()
					for edition in editions_data:
						identifiers = edition.get('identifiers', {})
						for amazon_id in identifiers.get('amazon', []):
							all_amazon.add(amazon_id)
					work_response[prop_id] = [{"str": a} for a in sorted(all_amazon)]

				elif prop_id == "identifiers.better_world_books":
					all_bwb = set()
					for edition in editions_data:
						identifiers = edition.get('identifiers', {})
						for bwb_id in identifiers.get('better_world_books', []):
							all_bwb.add(bwb_id)
					work_response[prop_id] = [{"str": b} for b in sorted(all_bwb)]

			extend_response['rows'][work_id] = work_response

		except Exception as e:
			print(f"Error processing data for {work_key}: {e}", flush=True)
			# Return empty values for this work
			work_response = {}
			for prop in properties:
				work_response[prop['id']] = []
			extend_response['rows'][work_id] = work_response

	print("Final extend response:", extend_response, flush=True)

	# If join mode is enabled, convert lists to pipe-delimited strings
	if passed_config and passed_config.get('POST45_DATA_EXTEND_MODE') == 'join':
		for row_id in extend_response['rows']:
			for field in extend_response['rows'][row_id]:
				if isinstance(extend_response['rows'][row_id][field], list):
					# Extract the 'str' value from each dict and join with pipes
					values = []
					for item in extend_response['rows'][row_id][field]:
						if isinstance(item, dict) and 'str' in item:
							values.append(item['str'])
					print("values", values, flush=True)
					extend_response['rows'][row_id][field] = [{"str": '|'.join(values)}] if values else [{}]
					print(extend_response['rows'][row_id][field], flush=True)

	return extend_response
