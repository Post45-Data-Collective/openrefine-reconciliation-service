extend_values_LC_Work_Id = {
  "limit": 10,
  "type": "LC_Work_Id",
  "properties": [
    {
      "id": "ISBN",
      "name": "ISBN"
    },
    {
      "id": "LCCN",
      "name": "LCCN"
    },
    {
      "id": "OCLC",
      "name": "OCLC"
    }
  ]
}


extend_values_Google_Books = {
  "limit": 10,
  "type": "Google_Books",
  "properties": [
    {
      "id": "ISBN",
      "name": "ISBN"
    },
    {
      "id": "description",
      "name": "Description"
    },   
    {
      "id": "pageCount",
      "name": "Page Count"
    },   
    {
      "id": "language",
      "name": "Language"
    },

  ]
}


extend_values_VIAF = {
  "limit": 10,
  "type": "VIAF_Personal",
  "properties": [
    {
      "id": "wikidata",
      "name": "Wikidata"
    }

  ]
}



def suggest_extend(query):

    if query == 'LC_Work_Id':
        return extend_values_LC_Work_Id
    if query == 'Google_Books':
        return extend_values_Google_Books
    if query == 'VIAF_Personal':
        return extend_values_VIAF


    return None

