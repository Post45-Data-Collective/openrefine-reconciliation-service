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
      "id": "VIAF_Personal",
      "name": "Name -- VIAF Personal"
    }, 



  ],
  "identifierSpace": "/doc/#identifierSpace",
  "schemaSpace": "/doc/#schemaSpace",

  "name": "Post 45 Reconciliation Service",
  "batchSize": 1,
  "preview": {
    "height": 200,
    "url": "http://127.0.0.1:5000/api/v1/preview?id={{id}}",
    "width": 500
  },

  "view": {
    "url": "http://127.0.0.1:5000/api/v1/redirect?id={{id}}"
  },

  "suggest": {
    "property": {
      "service_url": "http://127.0.0.1:5000/api/v1/reconcile",
      "service_path": "/suggest/property"
    },

  },
  "extend": {
    "propose_properties": {
      "service_url": "http://127.0.0.1:5000/api/v1/reconcile",
      "service_path": "/extend_suggest"
    }
  }

}