from os import environ

use_endpoint_address = "http://127.0.0.1:5001"
if environ.get('OR_IP') is not None:
  use_endpoint_address = environ.get('OR_IP')


manifest = {
  "versions": ["0.2"],
  "defaultTypes": [
    {
      "id": "LC_Work_Id",
      "name": "Title -- id.loc.gov"
    },

    {
      "id": "Google_Books",
      "name": "Title -- Google Books"
    },  

    {
      "id": "OCLC_Record",
      "name": "Title -- Worldcat"
    },
    {
      "id": "HathiTrust",
      "name": "Title -- HathiTrust"
    },
    {
      "id": "VIAF_Title",
      "name": "Title -- VIAF Work"
    },
    {
      "id": "Wikidata_Title",
      "name": "Title -- Wikidata Work"
    }, 
    {
      "id": "VIAF_Personal",
      "name": "Name -- VIAF Personal"
    }
  ],
  "identifierSpace": "/doc/#identifierSpace",
  "schemaSpace": "/doc/#schemaSpace",

  "name": "BookReconciler Service",
  "batchSize": 1,
  "preview": {
    "height": 200,
    "url": use_endpoint_address + "/api/v1/preview?id={{id}}",
    "width": 500
  },

  "view": {
    "url": use_endpoint_address + "/api/v1/redirect?id={{id}}"
  },

  "suggest": {
    "property": {
      "service_url": use_endpoint_address + "/api/v1/reconcile",
      "service_path": "/suggest/property"
    },

  },
  "extend": {
    "propose_properties": {
      "service_url": use_endpoint_address + "/api/v1/reconcile",
      "service_path": "/extend_suggest"
    }
  }

}