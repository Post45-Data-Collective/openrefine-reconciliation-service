import requests
import html
import json
from .strategies_helpers import _build_recon_dict
from .strategies_helpers import _build_recon_dict_name
from .strategies_helpers import normalize_string




VIAF_HEADERS = {
	'User-Agent':'Openrefine Post 45 Reconcilation Client'
}





def process_viaf_query(query):
	"""This is what is called from the query endpoint, it will figure out how to process the work query
	"""
	
	query_reponse = {}
	# we need to figure out what type strategy we are going to use based on what they have sent with the reqest
	# with viaf personal just do the same search if they provided a title or not
	for queryId in query:

		data = query[queryId]


		reconcile_item = _build_recon_dict_name(data)
		print('**',reconcile_item,flush=True)


		result =  _search_name(reconcile_item)
		result = _parse_name_results(result,reconcile_item)


		query_reponse[queryId] = {
			'result' : result['or_query_response']
		}

		print("query_reponsequery_reponsequery_reponsequery_reponse")
		print(query_reponse)

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
	        "index": "viaf",
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
					authLabel = a_hit["recordData"]["VIAFCluster"]['mainHeadings']['data'][0]['text']


		# titles are titles the name is connected to
		titles = []
		if 'titles' in a_hit["recordData"]["VIAFCluster"]:
			if 'work' in a_hit["recordData"]["VIAFCluster"]['titles']:
				for work in a_hit["recordData"]["VIAFCluster"]['titles']['work']:
					titles.append(html.unescape(work['title']))




		score = 0.5

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



		data = {
			"uri": uri,
			"type": a_hit["recordData"]["VIAFCluster"]["nameType"],
			"authLabel": authLabel,
			'titles':titles,
			'score':score
		}


		## put it in the cache for later if we need to generate a preview flyout for it
		file_name = uri.replace(':','_').replace('/','_')
		with open(f'data/cache/{file_name}','w') as out:
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



	return result




