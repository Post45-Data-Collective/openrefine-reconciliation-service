extend_values_LC_Work_Id = {
  "limit": 10,
  "type": "LC_Work_Id",
  "properties": [
    {
      "id": "URI",
      "name": "Work URI"
    },
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
    },
    {
      "id": "subjects",
      "name": "Subject Headings"
    },
    {
      "id": "genres",
      "name": "Genres"
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

extend_values_VIAF_Title = {
  "limit": 10,
  "type": "VIAF_Title",
  "properties": [
    
    # none

  ]
}

extend_values_Worldcat = {
  "limit": 10,
  "type": "OCLC_Record",
  "properties": [
    {
      "id": "isbn_cluster",
      "name": "ISBN Cluster"
    },
    {
      "id": "dewey",
      "name": "Dewey (DDC)"
    }    

  ]
}

extend_values_HathiTrust = {
  "limit": 10,
  "type": "HathiTrust",
  "properties": [
    {
      "id": "hdl",
      "name": "Volume Handles"
    },
    {
      "id": "OCLC",
      "name": "OCLC Numbers"
    },
    {
      "id": "ISBN",
      "name": "ISBN Numbers"
    },
    {
      "id": "LCCN",
      "name": "LCCN Numbers"
    },
    {
      "id": "thumbnail",
      "name": "Thumbnail URL"
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
    if query == 'VIAF_Title':
        return extend_values_VIAF_Title
    
    if query == 'OCLC_Record':
        return extend_values_Worldcat
    if query == 'HathiTrust':
        return extend_values_HathiTrust


    return None

