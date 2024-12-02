from flask import Flask
from flask_cors import CORS
from flask import request
from lib.manifest import manifest

import json



app = Flask(__name__)
CORS(app)
print(manifest)



@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"



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

                print(query)



        except:
            pass




        # if has_body == True:
        #     print(post_data)
        # else:
        #     print("No json!")
        #     print(request.data)

        
        return manifest


