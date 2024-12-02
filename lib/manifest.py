manifest = {
  "versions": ["0.2"],
  "defaultTypes": [
    {
      "id": "/agent_title_uncontrolled",
      "name": "Work -- Uncontrolled author and title search"
    },
    {
      "id": "/sdfsf",
      "name": "Work -- test"
    }            
  ],
  "identifierSpace": "/doc/#identifierSpace",
  "schemaSpace": "/doc/#schemaSpace",

  "name": "Post 45 Reconciliation Service",
  "batchSize": 20,
  "preview": {
    "height": 200,
    "url": "/api/v1/preview/?id={{id}}",
    "width": 350
  },

  "view": {
    "url": "/redirect/?id={{id}}"
  }
}