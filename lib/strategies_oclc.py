import requests
import time

from .strategies_helpers import _build_recon_dict




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

	print(OCLC_CLIENT_ID)
	response = requests.post(
		'https://oauth.oclc.org/token',
		data={"grant_type": "client_credentials", 'scope': ['wcapi']},
		auth=(OCLC_CLIENT_ID,OCLC_SECRET),
	)
	print(response.text)
	token = response.json()["access_token"]
	auth_timestamp = time.time()

	headers = {
		'accept': 'application/json',
		'Authorization': f'Bearer {token}'
	}
	print("HEADERS:",headers)



def process_oclc_query(query, OCLC_CLIENT_ID, OCLC_SECRET):
	"""This is what is called from the query endpoint, it will figure out how to process the work query


	"""

	reauth(OCLC_CLIENT_ID, OCLC_SECRET)

	print("Using HEADERS:",headers)

	print(query)
	query_reponse = {}
	# we need to figure out what type strategy we are going to use based on what they have sent with the reqest
	for queryId in query:
		print(queryId)
		print(query[queryId])
		print('---------')

		data = query[queryId]


		reconcile_item = _build_recon_dict(data)

		# decide how to proceed
		print("reconcile_item",reconcile_item)
		author_name = False
		if reconcile_item['contributor_uncontrolled_last_first'] != False:
			author_name = reconcile_item['contributor_uncontrolled_last_first']
		elif reconcile_item['contributor_uncontrolled_first_last'] != False: 
			author_name = reconcile_item['contributor_uncontrolled_first_last']

		elif reconcile_item['contributor_naco_controlled'] != False: 
			# google books seems to give different results if passed a full naco formed name with life dates
			# it seems to like just having the authors name, so try make the name LESS accurate
			author_name = reconcile_item['contributor_naco_controlled']

		print("HERE")

		result =  _search_title(reconcile_item['title'], author_name)
		print("result 1",result)
		result = _parse_title_results(result,reconcile_item['title'],author_name)
		print("result 2",result)
		print("HERE2")

		query_reponse[queryId] = {
			'result' : result['or_query_response']
		}

		# contributor_uncontrolled_last_first




		

	print("SENDING:!!!!")
	print(query_reponse)


	return query_reponse




def _search_title(title,name):
	"""
		Do a pretty search at google
	"""	
	global headers



	url = f'https://americas.discovery.api.oclc.org/worldcat/search/v2/bibs'

	params = {
		'q': f'au:{name} AND ti:{title}'
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


def _parse_title_results(result,title,author):
	"""
		Parse the results based on quality checks other cleanup needed before we send it back to the client
	"""	

	last = None
	first = None

	# # split out the parts of the name
	# if reconcile_item['contributor_uncontrolled_last_first'] != False:
	# 	last = reconcile_item['contributor_uncontrolled_last_first'].split(',')[0].strip().split(' ')[0]

	# 	first = reconcile_item['contributor_uncontrolled_last_first'].split(',')[1].strip().split(' ')[0]

	# if reconcile_item['contributor_uncontrolled_first_last'] != False:
	# 	last = reconcile_item['contributor_uncontrolled_first_last'].split(',')[1].strip().split(' ')[0]
	# 	first = reconcile_item['contributor_uncontrolled_first_last'].split(',')[0].strip().split(' ')[0]


	result['or_query_response'] = []

	for a_hit in result['bibRecords']:

		# if it was in the response from the server that means it matched something, so give it a basline score
		score = 0.5
		print("----a_hit-----")
		print(a_hit)
		print("last",last)
		print("first",first)
		a_hit['first'] = first
		a_hit['last'] = last

		# if the last name is not the first thing in AAP then we got a problem
		# TODO

		oclc = a_hit['identifier']['oclcNumber']
		title = ""

		if 'title' in a_hit:
			if 'mainTitles' in a_hit['title']:
				if len(a_hit['title']['mainTitles']) > 0:
					if 'text' in a_hit['title']['mainTitles'][0]:
						title = a_hit['title']['mainTitles'][0]['text']

		result['or_query_response'].append(
			{
				"id": 'https://worldcat.org/oclc/' + oclc,
				"name": title,
				"description": '',
				"score": score,
				"match": True,
				"type": [
					{
					"id": "oclc",
					"name": "OCLC Number"
					}
				]
			}
		)



	return result




