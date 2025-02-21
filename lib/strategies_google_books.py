import requests

from .strategies_helpers import _build_recon_dict


ID_HEADERS = {
	'User-Agent':'Openrefine Post 45 Reconcilation Client'
}





def process_google_books_work_query(query):
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
		author_name = False
		if reconcile_item['contributor_uncontrolled_last_first'] != False:
			author_name = reconcile_item['contributor_uncontrolled_last_first']
		elif reconcile_item['contributor_uncontrolled_first_last'] != False: 
			author_name = reconcile_item['contributor_uncontrolled_first_last']

		elif reconcile_item['contributor_naco_controlled'] != False: 
			# google books seems to give different results if passed a full naco formed name with life dates
			# it seems to like just having the authors name, so try make the name LESS accurate
			author_name = reconcile_item['contributor_naco_controlled']
			author_name = author_name.split("(")[0]
			author_name = ''.join([i for i in author_name if not i.isdigit()])
			author_name = author_name.replace('-','')

			# if ',' in author_name:
			# 	author_name = author_name.split(',')



		result =  _search_title(reconcile_item['title'], author_name)
		result = _parse_title_results(result,reconcile_item['title'],author_name)


		query_reponse[queryId] = {
			'result' : result['or_query_response']
		}

		# contributor_uncontrolled_last_first




		

	print("SENDING:!!!!")
	print(query_reponse)


	return query_reponse



# def extend_data(ids,properties):
# 	"""
# 		Sent Ids and proeprties it talks to id.loc.gov and returns the reuqested values
# 	"""

# 	response = {"meta":[],"rows":{}}

# 	for p in properties:

# 		if p['id'] == 'ISBN':
# 			response['meta'].append({"id":"ISBN",'name':'ISBN'})
# 		if p['id'] == 'LCCN':
# 			response['meta'].append({"id":"LCCN",'name':'LCCN'})
# 		if p['id'] == 'OCLC':
# 			response['meta'].append({"id":"OCLC",'name':'OCLC'})


# 	for i in ids:

# 		instance_response = None
# 		work_response = None

# 		response['rows'][i]={}

# 		if '/works/' in i:

# 			for p in properties:

# 				if p['id'] == 'ISBN':

# 					if instance_response == None:
# 						instance_response = requests.get(i.replace('/works/','/instances/')+'.bibframe.json')


# 					value = _extend_extract_ISBN(instance_response)
# 					print("valuevaluevaluevalue _extend_extract_ISBN",value)

# 					response['rows'][i]['ISBN'] = value

# 				if p['id'] == 'LCCN':

# 					if instance_response == None:
# 						instance_response = requests.get(i.replace('/works/','/instances/')+'.bibframe.json')


# 					value = _extend_extract_LCCN(instance_response)
# 					print("valuevaluevaluevalue _extend_extract_LCCN",value)
# 					response['rows'][i]['LCCN'] = value

# 				if p['id'] == 'OCLC':

# 					if instance_response == None:
# 						instance_response = requests.get(i.replace('/works/','/instances/')+'.bibframe.json')


# 					value = _extend_extract_OCLC(instance_response)
# 					print("valuevaluevaluevalue _extend_extract_OCLC",value)
# 					response['rows'][i]['OCLC'] = value




# 	print(i)
# 	print(properties)
# 	print(response)
# 	return response




# def _extend_extract_ISBN(instance_response):

# 	try:
# 		graphs=instance_response.json()
# 	except:
# 		print("Error Extend",instance_response)
# 		return("ERROR")


# 	# loop through the graphs and return the value for ISBN
# 	values = []
# 	for g in graphs:
# 		if '@type' in g:
# 			if 'http://id.loc.gov/ontologies/bibframe/Isbn' in g['@type']:
# 				if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value' in g:
# 					for v in g['http://www.w3.org/1999/02/22-rdf-syntax-ns#value']:
# 						if '@value' in v:
# 							values.append({"str":v['@value'].strip()})


# 	if len(values) == 0:
# 		values=[{}]

# 	return values


# def _extend_extract_LCCN(instance_response):

# 	try:
# 		graphs=instance_response.json()
# 	except:
# 		print("Error Extend",instance_response)
# 		return("ERROR")


# 	# loop through the graphs and return the value for ISBN
# 	values = []
# 	for g in graphs:
# 		if '@type' in g:
# 			if 'http://id.loc.gov/ontologies/bibframe/Lccn' in g['@type']:
# 				if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value' in g:
# 					for v in g['http://www.w3.org/1999/02/22-rdf-syntax-ns#value']:
# 						if '@value' in v:
# 							values.append({"str":v['@value'].strip()})

# 	if len(values) == 0:
# 		values=[{}]

# 	return values


# def _extend_extract_OCLC(instance_response):

# 	try:
# 		graphs=instance_response.json()
# 	except:
# 		print("Error Extend",instance_response)
# 		return("ERROR")


# 	# loop through the graphs and return the value for ISBN
# 	values = []
# 	for g in graphs:
# 		if '@type' in g:
# 			if 'http://id.loc.gov/ontologies/bibframe/OclcNumber' in g['@type']:
# 				if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value' in g:
# 					for v in g['http://www.w3.org/1999/02/22-rdf-syntax-ns#value']:
# 						if '@value' in v:
# 							values.append({"str":v['@value'].strip()})

# 	if len(values) == 0:
# 		values=[{}]

# 	return values


# def _build_title_for_uncontrolled_name_search(title):
# 	"""
# 		takes a tile and parses it for how this endpoint works best

# 	"""

# 	title = title.split(":")[0].strip()
# 	title = title.split(";")[0].strip()


# 	return title


# def _build_recon_dict(recon_query):


# 	reconcile_item = {
# 		'title': _build_title_for_uncontrolled_name_search(recon_query['query']),
# 		'type': recon_query['type'],
# 		'contributor_uncontrolled_last_first': False,
# 		'contributor_uncontrolled_first_last': False
# 	}

# 	for prop in recon_query['properties']:

# 		print(prop)

# 		if prop['pid'] == 'contributor_uncontrolled_last_first':
# 			reconcile_item['contributor_uncontrolled_last_first'] = prop['v']
# 		if prop['pid'] == 'contributor_uncontrolled_first_last':
# 			reconcile_item['contributor_uncontrolled_first_last'] = prop['v']


# 	return reconcile_item




def _search_title(title,name):
	"""
		Do a pretty search at google
	"""	

	url = 'https://www.googleapis.com/books/v1/volumes'


	q_string = f'intitle:{title}'
	if name != False:
		q_string = q_string + f'+inauthor:{name}'


	params = {
		'q' : q_string,
		'projection': 'full'
	}
	print(params)


	try:
		response = requests.get(url, params=params, headers=ID_HEADERS)
	except requests.exceptions.RequestException as e:  # This is the correct syntax
		print("ERROR:", e)
		# create a response 
		return {
			'successful': False,
			'error': str(e),
			'kind': 'books#volumes',
			'totalItems': 0,
			'params': params,
			'items': []
		}


	data = response.json()
	data['successful'] = True
	data['error'] = None

	if data['totalItems'] == 0:

		data['items'] = []

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

	for a_hit in result['items']:

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


		result['or_query_response'].append(
			{
				"id": 'https://www.googleapis.com/books/v1/volumes/' + a_hit['id'],
				"name": a_hit['volumeInfo']['title'],
				"description": '',
				"score": score,
				"match": True,
				"type": [
					{
					"id": "google",
					"name": "Google Volume"
					}
				]
			}
		)



	return result




