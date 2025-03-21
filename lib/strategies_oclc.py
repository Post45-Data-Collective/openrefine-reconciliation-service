import requests
import time
import json
import os
import glob
from .strategies_helpers import _build_recon_dict


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

	safe_title = "".join(c for c in title if c.isalpha() or c.isdigit() or c==' ').rstrip()
	safe_author = "".join(c for c in author if c.isalpha() or c.isdigit() or c==' ').rstrip()

	safe_title = "".join(safe_title.split())
	safe_author = "".join(safe_author.split())

	with open(f'data/cache/worldcat_search_{safe_title}_{safe_author}','w') as out:
		json.dump(result['bibRecords'],out)


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

		uri = 'https://worldcat.org/oclc/' + oclc

		file_name = uri.replace(':','_').replace('/','_')
		with open(f'data/cache/{file_name}','w') as out:
			json.dump(a_hit,out)


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

def _build_extend_work_mapping():
	global extend_work_mapping

	for file in glob.glob('data/cache/worldcat_search_*'):
		print(file)
		data = json.load(open(file))

		
		for record in data:

			work_id=None
			if 'work' in record:
				if 'id' in record['work']:
					work_id = record['work']['id']
					print(work_id)

			if work_id != None:
				isbns = []
				if 'identifier' in record:
					if 'isbns' in record['identifier']:

						if isinstance(record['identifier']['isbns'], list) == False:
							record['identifier']['isbns'] = [record['identifier']['isbns']]

						isbns = isbns + record['identifier']['isbns']



				if work_id not in extend_work_mapping: 
					extend_work_mapping[work_id] = []

				extend_work_mapping[work_id]= extend_work_mapping[work_id] + isbns

				extend_work_mapping[work_id] = list(set(extend_work_mapping[work_id]))
				print(extend_work_mapping[work_id])


	print("Building")
	print(extend_work_mapping)


def extend_data(ids,properties):
	global extend_work_mapping


	"""
		Sent Ids and proeprties it talks to viaf and returns the reuqested values
	"""


	response = {"meta":[],"rows":{}}

	for p in properties:

		if p['id'] == 'dewey':
			response['meta'].append({"id":"dewey",'name':'Dewey (DDC)'})
		if p['id'] == 'isbn_cluster':
			response['meta'].append({"id":"isbn_cluster",'name':'ISBN Cluster'})


	for i in ids:

		response['rows'][i]={}

		for p in properties:

			if p['id'] == 'dewey':

				# load it from the cache
				passed_id_escaped = i.replace(":",'_').replace("/",'_')
				if os.path.isfile(f'data/cache/{passed_id_escaped}'):
					data = json.load(open(f'data/cache/{passed_id_escaped}'))

					dewey = ""
					if 'classification' in data:
						if 'dewey' in data['classification']:
							dewey = data['classification']['dewey']


					if len(dewey) > 0:
						response['rows'][i]['dewey'] = [{'str':dewey}]
					else:
						response['rows'][i]['dewey'] = [{}]

			if p['id'] == 'isbn_cluster':

				passed_id_escaped = i.replace(":",'_').replace("/",'_')
				if os.path.isfile(f'data/cache/{passed_id_escaped}'):
					data = json.load(open(f'data/cache/{passed_id_escaped}'))

					if 'work' in data:
						if 'id' in data['work']:
							work_id = data['work']['id']


							# is the work id already in the mapping?
							if work_id in extend_work_mapping:

								response['rows'][i]['isbn_cluster'] = [{'str':"|".join(extend_work_mapping[work_id])}]

							else:

								_build_extend_work_mapping()
								if work_id in extend_work_mapping:
									response['rows'][i]['isbn_cluster'] = [{'str':"|".join(extend_work_mapping[work_id])}]
								else:
									response['rows'][i]['isbn_cluster'] = [{}]





	print(properties)
	print(response)
	print(json.dumps(response,indent=2))
	return response


