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
from lib.strategies_hathitrust import process_hathi_query


from lib.strategies_id_loc_gov import extend_data as extend_data_id

from lib.strategies_viaf import extend_data as extend_data_viaf

from lib.strategies_oclc import extend_data as extend_data_worldcat

from lib.strategies_google_books import extend_data as extend_data_google

from lib.strategies_hathitrust import extend_data as extend_data_hathi





import json
import os
import pathlib



 

# if the oclc keys are available as env vars
OCLC_CLIENT_ID = os.environ.get('OCLC_CLIENT_ID', None) 
OCLC_SECRET = os.environ.get('OCLC_SECRET', None) 

HATHI_FULL_SEARCH_ONLY = False




app = Flask(__name__)
app.config['DEBUG'] = True 
CORS(app)
print(manifest)


@app.route("/")
def hello_world():
    global OCLC_CLIENT_ID
    global OCLC_SECRET
    global HATHI_FULL_SEARCH_ONLY

    HATHI_FULL_SEARCH_ONLY = request.args.get('HATHI_FULL_SEARCH_ONLY', None)


    html = '<h1 style="margin-bottom:2em;">Post45 Reconciliation Service Configuration</h1>'
    # they are not set
    if OCLC_CLIENT_ID == None or OCLC_SECRET == None:

        OCLC_CLIENT_ID = request.args.get('OCLC_CLIENT_ID', None)
        OCLC_SECRET = request.args.get('OCLC_SECRET', None)

        if OCLC_CLIENT_ID == None or OCLC_SECRET == None:


            html = html + """
                <h2>Set API Keys:</h2>
                <form action="" method="get">
                    <input type="text" id placeholder="OCLC_CLIENT_ID"   name="OCLC_CLIENT_ID" id="OCLC_CLIENT_ID"  style="width:50%"/>
                    <input type="text" id placeholder="OCLC_SECRET"   name="OCLC_SECRET" id="OCLC_SECRET"  style="width:50%"/>            
                    <input type="submit" value="Set OCLC API Keys" />
                </form>


            """
        else:

            html = html + """

                <h2>Set API Keys:</h2>
                <div>OCLC Keys set</div>

            """
    else:
        
            html = html + """

                <h2>Set API Keys:</h2>
                <div>OCLC Keys set</div>

            """


    HATHI_FULL_SEARCH_ONLY_checked = ""
    if HATHI_FULL_SEARCH_ONLY == "on":
        HATHI_FULL_SEARCH_ONLY_checked = "checked"


    html = html + f"""

        <hr style="margin: 5em 0 5em 0;">
        <h2>HathiTrust Configuration:</h2>
        <div>
            <form action="" method="get">

                <input type="checkbox" placeholder="HATHI_FULL_SEARCH_ONLY" name="HATHI_FULL_SEARCH_ONLY" id="HATHI_FULL_SEARCH_ONLY" {HATHI_FULL_SEARCH_ONLY_checked} />            
                <label for="HATHI_FULL_SEARCH_ONLY">Only return "Full view" resources</label>
                <input style="display:block; margin-top:2em" type="submit" value="Save" />
            </form>
        </div>
    """



    print("HATHI_FULL_SEARCH_ONLY",HATHI_FULL_SEARCH_ONLY,flush=True)

    return html



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

                    if 'type' in query[queryId]:
                            

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

                        if query[queryId]['type'] == 'HathiTrust':
                            print('**',query,flush=True)
                            return process_hathi_query(query, HATHI_FULL_SEARCH_ONLY)
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
                    elif "worldcat.org" in extend_req['ids'][0]:
                        return extend_data_worldcat(extend_req['ids'],extend_req['properties'])
                    elif "googleapis.com" in extend_req['ids'][0]:
                        return extend_data_google(extend_req['ids'],extend_req['properties'])
                    elif "hathitrust.org" in extend_req['ids'][0]:
                        return extend_data_hathi(extend_req['ids'],extend_req['properties'])






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

    if 'hathi' in passed_id:
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

    if 'worldcat.org' in passed_id:
        
        html = ""


        passed_id_escaped = passed_id.replace(":",'_').replace("/",'_')
        if os.path.isfile(f'data/cache/{passed_id_escaped}'):
            data = json.load(open(f'data/cache/{passed_id_escaped}'))

            titles = []

            if 'title' in data:
                if 'mainTitles' in data['title']:
                    if len(data['title']['mainTitles']) > 0:
                        for t in data['title']['mainTitles']:
                            if 'text' in t:
                                titles.append(t['text'])


            too_add = "<ul>"
            for t in titles:
                too_add = too_add + '<li>Title: '+ t +'</li>'


            if 'classification' in data:
                if 'dewey' in data['classification']:
                    too_add = too_add + '<li>Dewey: '+ data['classification']['dewey'] +'</li>'
                if 'lc' in data['classification']:
                    too_add = too_add + '<li>LCC: '+ data['classification']['lc'] +'</li>'


            if 'date' in data:
                if 'publicationDate' in data['date']:

                    too_add = too_add + '<li>Pub Date: '+ data['date']['publicationDate'] +'</li>'




            too_add = too_add + "</ul>"


            html = html + f"""

                <div style="display:flex">
                    <div style="flex:1">{too_add}</div>
                    <div style="flex:1"></div>
                </div>


            """



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

