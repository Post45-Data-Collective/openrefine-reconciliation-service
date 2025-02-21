import requests
import json

from .strategies_helpers import _build_recon_dict



ID_HEADERS = {
	'User-Agent':'Openrefine Post 45 Reconcilation Client'
}


def process_id_loc_gov_work_query(query):
	"""This is what is called from the query endpoint, it will figure out how to process the work query


	"""


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

		if reconcile_item['contributor_uncontrolled_last_first'] != False:
			# make the call to id.loc.gov
			result = _search_title_uncontrolled_name(reconcile_item['title'], reconcile_item['contributor_uncontrolled_last_first'])
			# parse the response into a open refine result
			result = _parse_title_uncontrolled_name_results(result,reconcile_item)

			# format it for this query

			query_reponse[queryId] = {
				'result' : result['or_query_response']
			}

		# contributor_uncontrolled_last_first




		

	print("SENDING:!!!!")
	print(query_reponse)


	return query_reponse



def extend_data(ids,properties):
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




	print(i)
	print(properties)
	print(response)
	return response




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







def _search_title_uncontrolled_name(title,name):
	"""
		Do a pretty broad and loose name + title search at id.loc.gov
	"""	

	url = 'https://id.loc.gov/resources/works/suggest2/'

	params = {
		'q' : f"{name} {title}",
		'searchtype': 'keyword'
	}


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

	# we are going to save the individual records results in the cache dir for use later
	for hit in data['hits']:
		file_name = hit['uri'].replace(':','_').replace('/','_')
		with open(f'data/cache/{file_name}','w') as out:
			json.dump(hit,out)
		



	print(name, title)
	print(data)
	print("------------")

	return data


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




