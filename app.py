from flask import Flask
from flask_cors import CORS
from flask import request, redirect 
from lib.schemas.manifest import manifest
from lib.schemas.suggest_property import suggest_property
from lib.schemas.suggest_extend import suggest_extend


from lib.strategies_id_loc_gov import process_id_loc_gov_work_query
from lib.strategies_google_books import process_google_books_work_query
from lib.strategies_oclc import process_oclc_query
from lib.strategies_viaf import process_viaf_query

from lib.strategies_id_loc_gov import extend_data as extend_data_id

from lib.strategies_viaf import extend_data as extend_data_viaf







import json
import os
import pathlib






OCLC_CLIENT_ID = None
OCLC_SECRET = None





app = Flask(__name__)
app.config['DEBUG'] = True 
CORS(app)
print(manifest)


@app.route("/")
def hello_world():
    global OCLC_CLIENT_ID
    global OCLC_SECRET

    # they are not set
    if OCLC_CLIENT_ID == None or OCLC_SECRET == None:

        OCLC_CLIENT_ID = request.args.get('OCLC_CLIENT_ID', None)
        OCLC_SECRET = request.args.get('OCLC_SECRET', None)

        if OCLC_CLIENT_ID == None or OCLC_SECRET == None:


            return """
                <h1>Set API Keys:</h1>
                <form action="" method="get">
                    <input type="text" id placeholder="OCLC_CLIENT_ID"   name="OCLC_CLIENT_ID" id="OCLC_CLIENT_ID"  style="width:50%"/>
                    <input type="text" id placeholder="OCLC_SECRET"   name="OCLC_SECRET" id="OCLC_SECRET"  style="width:50%"/>            
                    <input type="submit" value="Set OCLC API Keys" />
                </form>


            """
        else:

            return """

                <h1>Set API Keys:</h1>
                <div>OCLC Keys set</div>

            """
    else:

            return """

                <h1>Set API Keys:</h1>
                <div>OCLC Keys set</div>

            """

@app.route("/api/v1/reconcile", methods = ['GET', 'POST', 'DELETE'])
def return_manifest():
    """Returns the OR manifest json response.

    This is the root url of the service
    """

    if request.method == 'GET':

        return manifest

    if request.method == 'POST':
        has_body = False
        post_data = None

        


        try:
            if 'queries' in request.form:



                query = json.loads(request.form['queries'])


                for queryId in query:
                    if query[queryId]['type'] == 'LC_Work_Id':
                        return process_id_loc_gov_work_query(query)
                        break

                    if query[queryId]['type'] == 'Google_Books':
                        return process_google_books_work_query(query)
                        break

                    if query[queryId]['type'] == 'OCLC_Record':
                        return process_oclc_query(query, OCLC_CLIENT_ID, OCLC_SECRET)
                        break

                    if query[queryId]['type'] == 'VIAF_Personal':
                        print('**',query,flush=True)
                        return process_viaf_query(query)
                        break




        except Exception as e: 
            print(e)
            pass


        if 'extend' in request.form:


            extend_req = json.loads(request.form['extend'])


            if 'ids' in extend_req:
                if len(extend_req['ids'])>0:
                    if "id.loc.gov" in extend_req['ids'][0]:
                        return extend_data_id(extend_req['ids'],extend_req['properties'])
                    elif "viaf.org" in extend_req['ids'][0]:
                        return extend_data_viaf(extend_req['ids'],extend_req['properties'])
                    else:
                        return ""



        
        return manifest



@app.route("/api/v1/reconcile/suggest/property")
def suggest_properties():
    return suggest_property


@app.route("/api/v1/reconcile/extend_suggest")
def suggest_exten():

    return suggest_extend(request.args.get('type', None))







@app.route("/api/v1/redirect")
def view_redirect():
    """
        Takes an ?id param and redirects it to the web page for it

    """

    passed_id = request.args.get('id')

    if 'id.loc.gov' in passed_id:
        return redirect(passed_id, code=302)

    if 'googleapis' in passed_id:
        return redirect(passed_id, code=302)

    if 'worldcat' in passed_id:
        return redirect(passed_id, code=302)

    if 'viaf' in passed_id:
        return redirect(passed_id, code=302)



@app.route("/api/v1/preview")
def view_preview():
    """
        Takes an ?id param and builds a little preview for it

    """

    passed_id = request.args.get('id')
    html = ""
    if 'id.loc.gov' in passed_id:

        passed_id_escaped = passed_id.replace(":",'_').replace("/",'_')
        if os.path.isfile(f'data/cache/{passed_id_escaped}'):
            data = json.load(open(f'data/cache/{passed_id_escaped}'))


            too_add = '<ul>'

            if 'more' in data:
                if 'rdftype' in data['more']:
                    if data['more']['rdftype'] != '':
                        too_add = too_add + f"<li>Type: {data['more']['rdftype']}</li>"


            html = f"""
            <h2>{data['aLabel']}</h2>
            <div>{data['vLabel']}</div>

            <div><a href="{data['uri']}" target="_blank">Link</a></div>
            <div>{too_add}</div>

            """

    if 'viaf.org' in passed_id:

        passed_id_escaped = passed_id.replace(":",'_').replace("/",'_')
        if os.path.isfile(f'data/cache/{passed_id_escaped}'):
            data = json.load(open(f'data/cache/{passed_id_escaped}'))

            name_type = ""
            names = []
            titles = []

            if 'recordData' in data:
                if 'VIAFCluster' in data['recordData']:
                    if 'mainHeadings' in data['recordData']['VIAFCluster']:
                        if 'data' in data['recordData']['VIAFCluster']['mainHeadings']:

                            for d in data['recordData']['VIAFCluster']['mainHeadings']['data']:
                                names.append(d['text'])

                    if 'titles' in data['recordData']['VIAFCluster']:
                        if 'work' in data['recordData']['VIAFCluster']['titles']:
                            for w in data['recordData']['VIAFCluster']['titles']['work']:
                                titles.append(w['title'])

                    if 'nameType' in data['recordData']['VIAFCluster']:
                        name_type = data['recordData']['VIAFCluster']['nameType']

                        

                        


            html = ""

            html = html + 'Type: ' + name_type




            too_add = "<ul>"
            for nl in names:
                too_add = too_add + '<li>'+ nl +'</li>'
            too_add = too_add + "</ul>"

            too_add2 = "<ul>"

            for t in titles:
                too_add2 = too_add2 + '<li>'+ t +'</li>'
            too_add2 = too_add2 + "</ul>"



            html = html + f"""

                <div style="display:flex">
                    <div style="flex:1">{too_add}</div>
                    <div style="flex:1">{too_add2}</div>
                </div>


            """



            # if 'more' in data:
            #     if 'rdftype' in data['more']:
            #         if data['more']['rdftype'] != '':
            #             too_add = too_add + f"<li>Type: {data['more']['rdftype']}</li>"


            # html = f"""
            # <h2>{data['aLabel']}</h2>
            # <div>{data['vLabel']}</div>

            # <div><a href="{data['uri']}" target="_blank">Link</a></div>
            # <div>{too_add}</div>

            # """




    return f"<html><body style=\"font-size:12px;\">{html}</body></html>"
    # if 'id.loc.gov' in passed_id:
    #     return redirect(passed_id, code=302)



import shutil

# setup the cache directory
# try:
#     shutil.rmtree('data/cache')
# except:
#     print('error rm')
#     pass

try:
    pathlib.Path("data/cache/").mkdir(parents=True, exist_ok=True)
except:
    print('error create')
    pass

