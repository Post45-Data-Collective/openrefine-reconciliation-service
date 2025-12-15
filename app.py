from flask import Flask, render_template, current_app, jsonify
from flask_cors import CORS
from flask import request, redirect 
from lib.schemas.manifest import manifest
from lib.schemas.suggest_property import suggest_property
from lib.schemas.suggest_extend import suggest_extend

from lib.strategies_id_loc_gov import process_id_query
from lib.strategies_google_books import process_google_books_query
from lib.strategies_oclc import process_oclc_query
from lib.strategies_viaf import process_viaf_query, process_viaf_title_query
from lib.strategies_hathitrust import process_hathi_query
from lib.strategies_wikidata import process_wikidata_title_query
from lib.strategies_helpers import reset_cluster_cache, build_cluster_data


from lib.strategies_id_loc_gov import extend_data as extend_data_id
from lib.strategies_viaf import extend_data as extend_data_viaf
from lib.strategies_oclc import extend_data as extend_data_worldcat
from lib.strategies_google_books import extend_data as extend_data_google
from lib.strategies_hathitrust import extend_data as extend_data_hathi
from lib.paths import get_hathi_data_dir, CACHE_DIR




import json
import os
import pathlib
from html import escape



 
# if the oclc keys are available as env vars
OCLC_CLIENT_ID = os.environ.get('OCLC_CLIENT_ID', None) 
OCLC_SECRET = os.environ.get('OCLC_SECRET', None) 
OCLC_KEYS_SET_VIA_ENV = False

if OCLC_CLIENT_ID != None or OCLC_SECRET != None:
    OCLC_KEYS_SET_VIA_ENV = True
    
HATHI_FULL_SEARCH_ONLY = False


app = Flask(__name__)
app.config['DEBUG'] = True 

app.config.update(
    POST45_RECONCILIATION_MODE='cluster', # 'single' or 'cluster'
    POST45_DATA_EXTEND_MODE='join', # or 'row'
    POST45_REMOVE_SUBTITLE=True, # if True it will remove subtitles from titles during matching
    APP_BASE="http://127.0.0.1:5001/",

    POST45_STARTING_NEW_RECONCILIATION=True, # if True it will reset the cluster cache when starting a new reconciliation

    # id.loc.gov
    POST45_ID_RDFTYPE_TEXT_LIMIT=True, # if True it will restrict searchs to Text RDF Types
    POST45_ID_CLUSTER_QUALITY_SCORE='high', # very high, high, medium, low, very low

    # Google Books
    POST45_GOOGLE_CLUSTER_QUALITY_SCORE='high', # very high, high, medium, low, very low
    
    # OCLC configuration
    POST45_OCLC_KEYS_SET_VIA_ENV=OCLC_KEYS_SET_VIA_ENV,
    POST45_OCLC_CLIENT_ID=OCLC_CLIENT_ID,
    POST45_OCLC_SECRET=OCLC_SECRET,
    POST45_OCLC_CLUSTER_QUALITY_SCORE='high', # very high, high, medium, low, very low
    POST45_OCLC_BOOK_ONLY=False, # Filter to only include books in OCLC results
    
)
if os.environ.get('OR_IP') is not None:
  app.config['APP_BASE'] = os.environ.get('OR_IP')




CORS(app)
print(manifest)







@app.route("/")
def hello_world():


    config_as_dict = dict(current_app.config)

    if config_as_dict.get('POST45_OCLC_KEYS_SET_VIA_ENV') == True:
        config_as_dict['POST45_OCLC_CLIENT_ID'] = "<set via env var>"
        config_as_dict['POST45_OCLC_SECRET'] = "<set via env var>"

    return render_template('index.html', config=config_as_dict)


    # html = '<h1 style="margin-bottom:2em;">Post45 Reconciliation Service Configuration</h1>'
    # # they are not set
    # if OCLC_CLIENT_ID == None or OCLC_SECRET == None:

    #     OCLC_CLIENT_ID = request.args.get('OCLC_CLIENT_ID', None)
    #     OCLC_SECRET = request.args.get('OCLC_SECRET', None)

    #     if OCLC_CLIENT_ID == None or OCLC_SECRET == None:


    #         html = html + """
    #             <h2>Set API Keys:</h2>
    #             <form action="" method="get">
    #                 <input type="text" id placeholder="OCLC_CLIENT_ID"   name="OCLC_CLIENT_ID" id="OCLC_CLIENT_ID"  style="width:50%"/>
    #                 <input type="text" id placeholder="OCLC_SECRET"   name="OCLC_SECRET" id="OCLC_SECRET"  style="width:50%"/>            
    #                 <input type="submit" value="Set OCLC API Keys" />
    #             </form>


    #         """
    #     else:

    #         html = html + """

    #             <h2>Set API Keys:</h2>
    #             <div>OCLC Keys set</div>

    #         """
    # else:
        
    #         html = html + """

    #             <h2>Set API Keys:</h2>
    #             <div>OCLC Keys set</div>

    #         """


    # HATHI_FULL_SEARCH_ONLY_checked = ""
    # if HATHI_FULL_SEARCH_ONLY == "on":
    #     HATHI_FULL_SEARCH_ONLY_checked = "checked"


    # html = html + f"""

    #     <hr style="margin: 5em 0 5em 0;">
    #     <h2>HathiTrust Configuration:</h2>
    #     <div>
    #         <form action="" method="get">

    #             <input type="checkbox" placeholder="HATHI_FULL_SEARCH_ONLY" name="HATHI_FULL_SEARCH_ONLY" id="HATHI_FULL_SEARCH_ONLY" {HATHI_FULL_SEARCH_ONLY_checked} />            
    #             <label for="HATHI_FULL_SEARCH_ONLY">Only return "Full view" resources</label>
    #             <input style="display:block; margin-top:2em" type="submit" value="Save" />
    #         </form>
    #     </div>
    # """



    # print("HATHI_FULL_SEARCH_ONLY",HATHI_FULL_SEARCH_ONLY,flush=True)

    # return html

@app.route("/cluster/hathi/<hathi_uuid>")
def cluster_hathi(hathi_uuid):

    if os.path.isfile(f'{CACHE_DIR}/cluster_hathi_{hathi_uuid}'):
        data = json.load(open(f'{CACHE_DIR}/cluster_hathi_{hathi_uuid}'))
        json_data = jsonify(data).get_data(as_text=True)

    return render_template('cluster.html', data=json_data, cluster_id=f'cluster_hathi_{hathi_uuid}')

@app.route("/cluster/id/<id_uuid>")
def cluster_id(id_uuid):

    if os.path.isfile(f'{CACHE_DIR}/cluster_id_{id_uuid}'):
        data = json.load(open(f'{CACHE_DIR}/cluster_id_{id_uuid}'))
        json_data = jsonify(data).get_data(as_text=True)

    return render_template('cluster.html', data=json_data, cluster_id=f'cluster_id_{id_uuid}')

@app.route("/cluster/google_books/<google_uuid>")
def cluster_google_books(google_uuid):

    if os.path.isfile(f'{CACHE_DIR}/cluster_google_books_{google_uuid}'):
        data = json.load(open(f'{CACHE_DIR}/cluster_google_books_{google_uuid}'))
        json_data = jsonify(data).get_data(as_text=True)

    return render_template('cluster.html', data=json_data, cluster_id=f'cluster_google_books_{google_uuid}')

@app.route("/cluster/oclc/<oclc_uuid>")
def cluster_oclc(oclc_uuid):

    if os.path.isfile(f'{CACHE_DIR}/cluster_oclc_{oclc_uuid}'):
        data = json.load(open(f'{CACHE_DIR}/cluster_oclc_{oclc_uuid}'))
        json_data = jsonify(data).get_data(as_text=True)

    return render_template('cluster.html', data=json_data, cluster_id=f'cluster_oclc_{oclc_uuid}')


@app.route("/clusters/<service>")
def clusters(service):

    req_ip = request.remote_addr
    cluster_data = {}
    if os.path.isfile(f'{CACHE_DIR}/cluster_cache_{service}_{req_ip}'):
        cluster_data = build_cluster_data(req_ip,service)

    return render_template('clusters.html', data=cluster_data)


@app.route("/api/v1/reconcile", methods = ['GET', 'POST', 'DELETE'])
def return_manifest():
    """Returns the OR manifest json response.

    This is the root url of the service
    """

    if request.method == 'GET':

        # reset the cluster caching since they are starting a new reconciliation
        print("Resetting cluster cache for", request.remote_addr, flush=True    )
        app.config['POST45_STARTING_NEW_RECONCILIATION'] = True
        print("RESETTING CLUSTER CACHE 1", flush=True)
        # reset_cluster_cache(request.remote_addr,query)

        return manifest

    if request.method == 'POST':
        has_body = False
        post_data = None

        


        # try:
        if 'queries' in request.form:


            query = json.loads(request.form['queries'])
            
            
            # this is the best way I can find so far to know if they are 
            # doing a reconciliation req or the preview page for starting the reconciliation
            # we are configed to send 1 query at a time, this preview page sends 10
            # if it is the preview page then we want to clear the cluster
            if len(query) == 10:
                app.config['POST45_STARTING_NEW_RECONCILIATION'] = True
                print("RESETTING CLUSTER CACHE 2", flush=True)

            # we use the ip address to keep the cluster cache files seperate
            # if we are not running locally
            query['req_ip'] = request.remote_addr


            for queryId in query:

                if 'type' in query[queryId]:

                    if app.config['POST45_STARTING_NEW_RECONCILIATION'] == True:
                        print("DELETEING CLUSTER CACHE", flush=True )
                        reset_cluster_cache(request.remote_addr, query)
                        app.config['POST45_STARTING_NEW_RECONCILIATION'] = False


                    if query[queryId]['type'] == 'LC_Work_Id':
                        return process_id_query(query, current_app.config)
                        break

                    if query[queryId]['type'] == 'Google_Books':
                        query['req_ip'] = request.remote_addr
                        return process_google_books_query(query, current_app.config)
                        break

                    if query[queryId]['type'] == 'OCLC_Record':
                        query['req_ip'] = request.remote_addr
                        return process_oclc_query(query, current_app.config)
                        break

                    if query[queryId]['type'] == 'VIAF_Personal':
                        # print('**',query,flush=True)
                        return process_viaf_query(query,current_app.config)
                        break

                    if query[queryId]['type'] == 'VIAF_Title':
                        # print('**',query,flush=True)
                        return process_viaf_title_query(query,current_app.config)
                        break
                    if query[queryId]['type'] == 'Wikidata_Title':
                        # print('**',query,flush=True)
                        return process_wikidata_title_query(query,current_app.config)
                        break





                    if query[queryId]['type'] == 'HathiTrust':
                        # print('**',query,flush=True)
                        process_result =  process_hathi_query(query, current_app.config)
                        print("Do Cluster WORK here....",flush=True)
                        return process_result
                        break

                    

        else:
            print("No queries in request.form", flush=True  )
 
        if 'extend' in request.form:


            extend_req = json.loads(request.form['extend'])
            if 'ids' in extend_req:
                if len(extend_req['ids'])>0:
                    if "id.loc.gov" in extend_req['ids'][0] or "cluster/id" in extend_req['ids'][0]:
                        return extend_data_id(extend_req['ids'],extend_req['properties'], current_app.config)
                    elif "viaf.org" in extend_req['ids'][0]:
                        return extend_data_viaf(extend_req['ids'],extend_req['properties'], current_app.config)
                    elif "worldcat.org" in extend_req['ids'][0] or "cluster/oclc" in extend_req['ids'][0]:
                        return extend_data_worldcat(extend_req['ids'],extend_req['properties'], current_app.config)
                    elif "googleapis.com" in extend_req['ids'][0] or "cluster/google_books" in extend_req['ids'][0]:
                        return extend_data_google(extend_req['ids'],extend_req['properties'], current_app.config)
                    elif "hathitrust.org" in extend_req['ids'][0] or "cluster/hathi" in extend_req['ids'][0]:
                        return extend_data_hathi(extend_req['ids'],extend_req['properties'], current_app.config)






                    else:
                        return ""



        
        return manifest



@app.route("/api/v1/reconcile/suggest/property")
def suggest_properties():
    return suggest_property


@app.route("/api/v1/reconcile/extend_suggest")
def suggest_exten():

    return suggest_extend(request.args.get('type', None))


@app.route("/api/local/hathi_db_exists")
def hathi_db_exists():
    """
    Returns JSON with true/false indicating if the HathiTrust database exists
    """
    hathi_dir = get_hathi_data_dir()
    db_path = hathi_dir / 'hathitrust.db'
    exists = os.path.exists(db_path)
    return jsonify({"exists": exists})


@app.route("/api/local/build_hathi_db", methods=['POST'])
def build_hathi_db():
    """
    Starts the HathiTrust database building process in the background
    """
    import threading
    from lib.strategies_hathitrust_build_db import main as build_db_main

    def run_build():
        try:
            # Run the build function directly
            build_db_main()
        except Exception as e:
            print(f"Error building database: {e}")

    # Start the build process in a background thread
    thread = threading.Thread(target=run_build)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "started", "message": "Database build process started"})


@app.route("/api/local/hathi_build_status")
def hathi_build_status():
    """
    Returns the current status of the HathiTrust database building process
    """
    hathi_dir = get_hathi_data_dir()
    status_file = hathi_dir / 'build_status.json'
    
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r') as f:
                status_data = json.load(f)
            return jsonify(status_data)
        except:
            return jsonify({"status": "unknown", "message": "Could not read status file"})
    else:
        # Check if database exists (build might be complete)
        db_path = hathi_dir / 'hathitrust.db'
        if os.path.exists(db_path):
            return jsonify({"status": "complete", "message": "Database exists"})
        else:
            return jsonify({"status": "idle", "message": "No build in progress"})


@app.route("/api/v1/redirect")
def view_redirect():
    """
        Takes an ?id param and redirects it to the web page for it

    """

    passed_id = request.args.get('id')

    if 'id.loc.gov' in passed_id:
        return redirect(passed_id, code=302)
    if 'cluster/id' in passed_id:
        return redirect(passed_id, code=302)
    if 'cluster/google_books' in passed_id:
        return redirect(passed_id, code=302)
    if 'cluster/oclc' in passed_id:
        return redirect(passed_id, code=302)
    if 'googleapis' in passed_id:
        return redirect(passed_id, code=302)

    if 'worldcat' in passed_id:
        return redirect(passed_id, code=302)

    if 'viaf' in passed_id:
        return redirect(passed_id, code=302)

    if 'hathi' in passed_id:
        return redirect(passed_id, code=302)
    if 'wikidata.org' in passed_id:
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
        if os.path.isfile(f'{CACHE_DIR}/id.loc.gov_{passed_id_escaped}'):
            data = json.load(open(f'{CACHE_DIR}/id.loc.gov_{passed_id_escaped}'))

            print(data, flush=True  )
            too_add = '<ul>'

            # Add RDF types from more section
            if 'more' in data:
                if 'rdftype' in data['more']:
                    if data['more']['rdftype'] != '':
                        too_add = too_add + f"<li>Type: {data['more']['rdftype']}</li>"
                
                # Add languages from more section
                if 'languages' in data['more'] and data['more']['languages']:
                    languages_str = ', '.join(data['more']['languages'])
                    too_add = too_add + f"<li>Languages: {languages_str}</li>"

            # Add responsibility statement from enriched data
            if 'responsibilityStatement' in data and data['responsibilityStatement']:
                too_add = too_add + f"<li>Responsibility: {escape(data['responsibilityStatement'])}</li>"
            
            # Add publication dates from enriched data
            if 'originDate' in data and data['originDate']:
                too_add = too_add + f"<li>Origin Date: {data['originDate']}</li>"
            
            if 'provisionActivities' in data and data['provisionActivities']:
                for activity in data['provisionActivities']:
                    if 'date' in activity and activity['date']:
                        pub_info = f"Publication: {activity['date']}"
                        if 'place' in activity and activity['place']:
                            pub_info += f", {activity['place']}"
                        if 'agent' in activity and activity['agent']:
                            pub_info += f", {activity['agent']}"
                        too_add = too_add + f"<li>{pub_info}</li>"
                        break  # Just show the first publication activity
            
            # Add identifiers
            if 'identifiers' in data and data['identifiers']:
                for identifier in data['identifiers'][:3]:  # Show first 3 identifiers
                    id_info = f"{identifier['type']}: {identifier['value']}"
                    if 'qualifier' in identifier and identifier['qualifier']:
                        id_info += f" ({identifier['qualifier']})"
                    too_add = too_add + f"<li>{id_info}</li>"
            
            too_add = too_add + '</ul>'

            html = f"""
            <h2>{escape(data['aLabel'])}</h2>
            <div>{escape(data.get('vLabel', ''))}</div>

            <div><a href="{data['uri']}" target="_blank">Link</a></div>
            <div>{too_add}</div>

            """

    if 'viaf.org' in passed_id:

        passed_id_escaped = passed_id.replace(":",'_').replace("/",'_')
        if os.path.isfile(f'{CACHE_DIR}/{passed_id_escaped}'):
            data = json.load(open(f'{CACHE_DIR}/{passed_id_escaped}'))

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
        else:

            return """
                No Preview Data

            """


    if 'worldcat.org' in passed_id:
        
        html = ""

        id = passed_id.split('/')[-1]

        print("----",f'{CACHE_DIR}/oclc_{id}',flush=True)
        if os.path.isfile(f'{CACHE_DIR}/oclc_{id}'):
            data = json.load(open(f'{CACHE_DIR}/oclc_{id}'))

            too_add = "<ul>"
            
            # Main title
            if 'mainTitle' in data and data['mainTitle']:
                too_add = too_add + f'<li><strong>Title:</strong> {escape(data["mainTitle"])}</li>'
            
            # Creator/Author
            if 'creator' in data and data['creator']:
                too_add = too_add + f'<li><strong>Author:</strong> {escape(data["creator"])}</li>'
            
            # Statement of Responsibility
            if 'statementOfResponsibility' in data and data['statementOfResponsibility']:
                too_add = too_add + f'<li><strong>Responsibility:</strong> {escape(data["statementOfResponsibility"])}</li>'
            
            # Publication Date
            if 'publicationDate' in data and data['publicationDate']:
                too_add = too_add + f'<li><strong>Publication Date:</strong> {escape(data["publicationDate"])}</li>'
            
            # Language
            if 'itemLanguage' in data and data['itemLanguage']:
                too_add = too_add + f'<li><strong>Language:</strong> {escape(data["itemLanguage"])}</li>'
            
            # Format
            if 'generalFormat' in data and data['generalFormat']:
                too_add = too_add + f'<li><strong>Format:</strong> {escape(data["generalFormat"])}</li>'
            
            # Classifications
            if 'classifications' in data and data['classifications']:
                if isinstance(data['classifications'], dict):
                    if 'dewey' in data['classifications']:
                        too_add = too_add + f'<li><strong>Dewey:</strong> {escape(data["classifications"]["dewey"])}</li>'
                    if 'lc' in data['classifications']:
                        too_add = too_add + f'<li><strong>LC:</strong> {escape(data["classifications"]["lc"])}</li>'
            
            # OCLC Number
            if 'oclcNumber' in data and data['oclcNumber']:
                too_add = too_add + f'<li><strong>OCLC Number:</strong> {escape(data["oclcNumber"])}</li>'
            
            # ISBNs
            if 'isbns' in data and data['isbns']:
                isbn_list = ', '.join([escape(str(isbn)) for isbn in data['isbns'][:3]])  # Show first 3
                if len(data['isbns']) > 3:
                    isbn_list += f' ... ({len(data["isbns"])} total)'
                too_add = too_add + f'<li><strong>ISBN(s):</strong> {isbn_list}</li>'
            
            # LCCN
            if 'lccn' in data and data['lccn']:
                too_add = too_add + f'<li><strong>LCCN:</strong> {escape(data["lccn"])}</li>'
            
            # Subjects
            if 'subjects' in data and data['subjects']:
                subject_list = ', '.join([escape(str(subj)) for subj in data['subjects'][:3]])  # Show first 3
                if len(data['subjects']) > 3:
                    subject_list += f' ... ({len(data["subjects"])} total)'
                too_add = too_add + f'<li><strong>Subjects:</strong> {subject_list}</li>'
            
            # Work ID
            if 'workId' in data and data['workId']:
                too_add = too_add + f'<li><strong>Work ID:</strong> {escape(data["workId"])}</li>'
            
            # Fuzzy score (if present from reconciliation)
            if 'fuzzy_score' in data:
                score_percent = int(data['fuzzy_score'] * 100)
                too_add = too_add + f'<li><strong>Match Score:</strong> {score_percent}%</li>'

            too_add = too_add + "</ul>"

            # Create header with title and author
            header = ""
            if 'mainTitle' in data and data['mainTitle']:
                header = f"<h2>{escape(data['mainTitle'])}</h2>"
                if 'creator' in data and data['creator']:
                    header += f"<div style='font-size: 1.1em; margin-bottom: 0.5em;'>by {escape(data['creator'])}</div>"

            html = header + f"""
                <div style="display:flex">
                    <div style="flex:1">{too_add}</div>
                    <div style="flex:1"></div>
                </div>
            """

    if 'cluster/id' in passed_id:
        
        html = ""


        passed_id_escaped = passed_id.split('/')[-1]

        if os.path.isfile(f'{CACHE_DIR}/cluster_id_{passed_id_escaped}'):
            data = json.load(open(f'{CACHE_DIR}/cluster_id_{passed_id_escaped}'))



            clustered = '<div>id.loc.gov Clustered:</div><ul>'
            for d in data['cluster']:
                clustered = clustered + f'<li>{escape(d["aLabel"])}  </li>'
            clustered = clustered + '</ul>'

            if len(data['cluster_excluded']) > 0:
                clustered  = clustered + '<div>Excluded:</div><ul>'

                for d in data['cluster_excluded']:
                    clustered = clustered + f'<li>{escape(d["aLabel"])}  </li>'


                clustered = clustered + '</ul>'

            html = f"<div style=\"font-size: 1.25em\">{clustered}</div>"


    if 'cluster/hathi' in passed_id:
        
        html = ""


        passed_id_escaped = passed_id.split('/')[-1]

        if os.path.isfile(f'{CACHE_DIR}/cluster_hathi_{passed_id_escaped}'):
            data = json.load(open(f'{CACHE_DIR}/cluster_hathi_{passed_id_escaped}'))



            clustered = '<div>HathiTrust Clustered:</div><ul>'
            for d in data['cluster']:
                clustered = clustered + f'<li>{escape(d["author"])} --- {escape(d["title"])}  </li>'
            clustered = clustered + '</ul>'

            if len(data['cluster_excluded']) > 0:
                clustered  = clustered + '<div>Excluded:</div><ul>'

                for d in data['cluster_excluded']:
                    clustered = clustered + f'<li>{escape(d["author"])} --- {escape(d["title"])}  </li>'


                clustered = clustered + '</ul>'

            html = f"<div style=\"font-size: 1.25em\">{clustered}</div>"

    if 'cluster/google_books' in passed_id:
        
        html = ""


        passed_id_escaped = passed_id.split('/')[-1]

        if os.path.isfile(f'{CACHE_DIR}/cluster_google_books_{passed_id_escaped}'):
            data = json.load(open(f'{CACHE_DIR}/cluster_google_books_{passed_id_escaped}'))



            clustered = '<div>Google Books Clustered:</div><ul>'
            for d in data['cluster']:
                volume_info = d.get('volumeInfo', {})
                title = volume_info.get('title', 'Unknown Title')
                authors = ', '.join(volume_info.get('authors', ['Unknown Author']))
                clustered = clustered + f'<li>{escape(authors)} --- {escape(title)}  </li>'
            clustered = clustered + '</ul>'

            if len(data['cluster_excluded']) > 0:
                clustered  = clustered + '<div>Excluded:</div><ul>'

                for d in data['cluster_excluded']:
                    volume_info = d.get('volumeInfo', {})
                    title = volume_info.get('title', 'Unknown Title')
                    authors = ', '.join(volume_info.get('authors', ['Unknown Author']))
                    clustered = clustered + f'<li>{escape(authors)} --- {escape(title)}  </li>'


                clustered = clustered + '</ul>'

            html = f"<div style=\"font-size: 1.25em\">{clustered}</div>"

    if 'cluster/oclc' in passed_id:
        
        html = ""


        passed_id_escaped = passed_id.split('/')[-1]

        if os.path.isfile(f'{CACHE_DIR}/cluster_oclc_{passed_id_escaped}'):
            data = json.load(open(f'{CACHE_DIR}/cluster_oclc_{passed_id_escaped}'))



            clustered = '<div>OCLC/WorldCat Clustered:</div><ul>'
            for d in data['cluster']:
                # Extract creator and main title from OCLC data structure
                creator = d.get('creator', 'Unknown Author')
                title = d.get('mainTitle', 'Unknown Title')
                # Add OCLC number if available
                oclc_num = d.get('oclcNumber', '')
                if oclc_num:
                    clustered = clustered + f'<li>{escape(creator)} --- {escape(title)} (OCLC: {escape(oclc_num)})</li>'
                else:
                    clustered = clustered + f'<li>{escape(creator)} --- {escape(title)}</li>'
            clustered = clustered + '</ul>'

            if len(data['cluster_excluded']) > 0:
                clustered  = clustered + '<div>Excluded:</div><ul>'

                for d in data['cluster_excluded']:
                    creator = d.get('creator', 'Unknown Author')
                    title = d.get('mainTitle', 'Unknown Title')
                    oclc_num = d.get('oclcNumber', '')
                    if oclc_num:
                        clustered = clustered + f'<li>{escape(creator)} --- {escape(title)} (OCLC: {escape(oclc_num)})</li>'
                    else:
                        clustered = clustered + f'<li>{escape(creator)} --- {escape(title)}</li>'


                clustered = clustered + '</ul>'

            html = f"<div style=\"font-size: 1.25em\">{clustered}</div>"

            # titles = []

            # if 'title' in data:
            #     if 'mainTitles' in data['title']:
            #         if len(data['title']['mainTitles']) > 0:
            #             for t in data['title']['mainTitles']:
            #                 if 'text' in t:
            #                     titles.append(t['text'])


            # too_add = "<ul>"
            # for t in titles:
            #     too_add = too_add + '<li>Title: '+ t +'</li>'


            # if 'classification' in data:
            #     if 'dewey' in data['classification']:
            #         too_add = too_add + '<li>Dewey: '+ data['classification']['dewey'] +'</li>'
            #     if 'lc' in data['classification']:
            #         too_add = too_add + '<li>LCC: '+ data['classification']['lc'] +'</li>'


            # if 'date' in data:
            #     if 'publicationDate' in data['date']:

            #         too_add = too_add + '<li>Pub Date: '+ data['date']['publicationDate'] +'</li>'




            # too_add = too_add + "</ul>"


            # html = html + f"""

            #     <div style="display:flex">
            #         <div style="flex:1">{too_add}</div>
            #         <div style="flex:1"></div>
            #     </div>


            # """
    if 'wikidata.org' in passed_id:
        html = """
            No Preview Data

        """        


    return f"<html><body style=\"font-size:12px;\">{html}</body></html>"
    # if 'id.loc.gov' in passed_id:
    #     return redirect(passed_id, code=302)



@app.route("/api/local/save_cluster", methods=['POST'])
def save_cluster():
    """
    Saves cluster data to a cache file
    Expects JSON body with:
    - data: the cluster data to save
    - cluster_id: the filename (without extension) to save in data/cache/
    """
    try:
        # Get JSON data from request
        request_data = request.get_json()
        
        if not request_data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract data and cluster_id
        data = request_data.get('data')
        cluster_id = request_data.get('cluster_id')
        
        if not data:
            return jsonify({"error": "Missing 'data' field"}), 400
        
        if not cluster_id:
            return jsonify({"error": "Missing 'cluster_id' field"}), 400
        
        # Ensure cache directory exists
        cache_dir = pathlib.Path(f'{CACHE_DIR}')
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Save data to file (no .json extension, matching existing pattern)
        file_path = cache_dir / cluster_id
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return jsonify({
            "status": "success",
            "message": f"Cluster saved to {file_path}",
            "cluster_id": cluster_id
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to save cluster: {str(e)}"
        }), 500

@app.route("/api/local/set_config", methods=['POST'])
def set_config():
    """
    Updates app configuration with provided valid properties
    Expects JSON body with configuration properties to update
    Valid properties: POST45_RECONCILIATION_MODE, POST45_DATA_EXTEND_MODE, POST45_REMOVE_SUBTITLE, APP_BASE, DEBUG
    """
    try:
        # Get JSON data from request
        request_data = request.get_json()
        
        if not request_data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Define valid configuration keys that can be updated
        valid_config_keys = {
            'POST45_RECONCILIATION_MODE': ['single', 'cluster'],  # Valid values
            'POST45_DATA_EXTEND_MODE': ['join', 'row'],  # Valid values
            'POST45_REMOVE_SUBTITLE': [True, False],  # Boolean values
            'APP_BASE': None,  # Any string value
            'DEBUG': [True, False],  # Boolean values
            'POST45_ID_RDFTYPE_TEXT_LIMIT': [True, False],  # Boolean values
            'POST45_ID_CLUSTER_QUALITY_SCORE': ['very high', 'high', 'medium', 'low', 'very low'],  # Valid values
            'POST45_GOOGLE_CLUSTER_QUALITY_SCORE': ['very high', 'high', 'medium', 'low', 'very low'],  # Valid values
            'POST45_OCLC_CLUSTER_QUALITY_SCORE': ['very high', 'high', 'medium', 'low', 'very low'],  # Valid values
            'POST45_OCLC_KEYS_SET_VIA_ENV': [True, False],  # Boolean values
            'POST45_OCLC_CLIENT_ID': None,  # Any string value
            'POST45_OCLC_SECRET': None,  # Any string value
            'POST45_OCLC_BOOK_ONLY': [True, False]  # Boolean values
        }
        
        updated_configs = {}
        invalid_configs = {}
        
        # Process each configuration item
        for key, value in request_data.items():
            if key in valid_config_keys:
                # Check if value is valid for keys with restricted values
                allowed_values = valid_config_keys[key]
                if allowed_values is None or value in allowed_values:
                    app.config[key] = value
                    updated_configs[key] = value
                else:
                    invalid_configs[key] = f"Invalid value '{value}'. Allowed values: {allowed_values}"
            else:
                invalid_configs[key] = "Not a valid configuration key"
        
        # Prepare response
        response = {
            "status": "success" if updated_configs else "no_updates",
            "updated": updated_configs,
            "current_config": {
                'POST45_RECONCILIATION_MODE': app.config.get('POST45_RECONCILIATION_MODE'),
                'POST45_DATA_EXTEND_MODE': app.config.get('POST45_DATA_EXTEND_MODE'),
                'POST45_REMOVE_SUBTITLE': app.config.get('POST45_REMOVE_SUBTITLE'),
                'APP_BASE': app.config.get('APP_BASE'),
                'DEBUG': app.config.get('DEBUG'),
                'POST45_ID_RDFTYPE_TEXT_LIMIT': app.config.get('POST45_ID_RDFTYPE_TEXT_LIMIT'),
                'POST45_ID_CLUSTER_QUALITY_SCORE': app.config.get('POST45_ID_CLUSTER_QUALITY_SCORE'),
                'POST45_GOOGLE_CLUSTER_QUALITY_SCORE': app.config.get('POST45_GOOGLE_CLUSTER_QUALITY_SCORE'),
                'POST45_OCLC_KEYS_SET_VIA_ENV': app.config.get('POST45_OCLC_KEYS_SET_VIA_ENV'),
                'POST45_OCLC_CLIENT_ID': app.config.get('POST45_OCLC_CLIENT_ID'),
                'POST45_OCLC_SECRET': app.config.get('POST45_OCLC_SECRET')
            }
        }

        if app.config.get('POST45_OCLC_KEYS_SET_VIA_ENV') == True:
            response['updated']['POST45_OCLC_CLIENT_ID'] = "<set via env var>"
            response['updated']['POST45_OCLC_SECRET'] = "<set via env var>"

            response['current_config']['POST45_OCLC_CLIENT_ID'] = "<set via env var>"
            response['current_config']['POST45_OCLC_SECRET'] = "<set via env var>"

        if invalid_configs:
            response["invalid"] = invalid_configs
        
        print("app.config",app.config,flush=True)
        
        return jsonify(response), 200
        
        

    except Exception as e:
        return jsonify({
            "error": f"Failed to update configuration: {str(e)}"
        }), 500

import shutil

# setup the cache directory
# try:
#     shutil.rmtree(f'{CACHE_DIR}')
# except:
#     print('error rm')
#     pass

try:
    pathlib.Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
except:
    print('error create')
    pass

if __name__ == '__main__':
    import webbrowser
    import threading
    import subprocess
    import socket

    # Check if running inside Electron (Electron sets this env var in main.js)
    running_in_electron = os.environ.get('ELECTRON_RUN_AS_NODE') is not None or os.environ.get('RUNNING_IN_ELECTRON') == 'true'

    # Only open browser if NOT running in Electron (Electron handles the UI)
    if not running_in_electron:
        webbrowser.open('http://127.0.0.1:5001/')

    # Check if port is already in use
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    if is_port_in_use(5001):
        # Port already in use, just show notification and exit
        if not running_in_electron:
            try:
                subprocess.run([
                    'osascript', '-e',
                    'display notification "BookReconciler is already running at http://127.0.0.1:5001" with title "BookReconciler"'
                ])
            except:
                pass
        print("BookReconciler is already running at http://127.0.0.1:5001")
    else:
        # Start the server
        def show_notification():
            if not running_in_electron:
                try:
                    subprocess.run([
                        'osascript', '-e',
                        'display notification "BookReconciler is running at http://127.0.0.1:5001" with title "BookReconciler Started"'
                    ])
                except:
                    pass

        timer = threading.Timer(1.5, show_notification)
        timer.daemon = True
        timer.start()

        print("BookReconciler is running at http://127.0.0.1:5001")
        if not running_in_electron:
            print("Press Ctrl+C to stop the server")
        app.run(host='0.0.0.0', port=5001, debug=False)

