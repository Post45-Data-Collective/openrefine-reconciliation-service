import gzip
import csv
import sqlite3
import os
import requests
import json
from datetime import datetime
import time
import pickle
import tempfile
import shutil

# all records: Processed 9400000 records. 18833795 lines read.
# BK only: Processed 8710000 records. 12351232 lines read.
# BK only has author: Processed 7300000 records. 10052756 lines read.

def search_records(db_path, author_query, title_query):
    """
    Searches the FTS5 table for author and title, then retrieves
    full records from the 'records' table using the rowid.
    """
    conn = None
    results = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Step 1: Search the FTS5 table
        fts_query = """
        SELECT rowid 
        FROM author_title 
        WHERE author MATCH ? AND title MATCH ? 
        ORDER BY rank;
        """
        cursor.execute(fts_query, (author_query, title_query))
        rowids = [row[0] for row in cursor.fetchall()]

        if not rowids:
            print("No matching records found in author_title FTS table.")
            return []

        # Step 2: Retrieve records from the 'records' table using the rowids
        # We can use a placeholder for a list of IDs
        placeholders = ','.join('?' for _ in rowids)
        records_query = f"SELECT * FROM records WHERE ht_bib_key IN ({placeholders});"
        
        cursor.execute(records_query, rowids)
        column_names = [description[0] for description in cursor.description]
        
        for row in cursor.fetchall():
            results.append(dict(zip(column_names, row)))

    except sqlite3.Error as e:
        print(f"Database error during search: {e}")
    finally:
        if conn:
            conn.close()
    return results

def example_search(db_path):
    """
    Example usage of the search_records function.
    """
    print("\n--- Example Search ---")
    author_to_search = 'Woolf Virginia 1882 1941'
    title_to_search = 'to the lighthouse'
    
    print(f"Searching for author: '{author_to_search}' AND title: '{title_to_search}'")
    
    matched_records = search_records(db_path, author_to_search, title_to_search)
    
    if matched_records:
        print(f"\nFound {len(matched_records)} matching record(s):")
        for i, record in enumerate(matched_records):
            print(f"\n--- Record {i+1} ---")
            for key, value in record.items():
                print(f"  {key}: {value}")
    else:
        print("No records found matching the criteria.")




fieldnames = ('htid',	'access',	'rights',	'ht_bib_key',	'description',	'source',	'source_bib_num',	'oclc_num',	'isbn',	'issn',	'lccn',	'title',	'imprint',	'rights_reason_code',	'rights_timestamp',	'us_gov_doc_flag',	'rights_date_used',	'pub_place',	'lang',	'bib_fmt',	'collection_code',	'content_provider_code',	'responsible_entity_code',	'digitization_agent_code',	'access_profile_code',	'author')
            

def update_status(status, message, progress=None, total=None):
    """
    Updates the build status file
    """
    status_data = {
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    if progress is not None:
        status_data["progress"] = progress
    if total is not None:
        status_data["total"] = total
    
    status_file = "data/hathi/build_status.json"
    os.makedirs(os.path.dirname(status_file), exist_ok=True)
    
    with open(status_file, 'w') as f:
        json.dump(status_data, f)


def build_db(gzipped_file_path):
    """
    This script is used to build a database of HathiTrust records from a gzipped file.
    It reads the gzipped file, extracts the records, and stores them in a database.
    Records are batched to disk to avoid memory issues.
    """
    update_status("preparing", f"Building database from {gzipped_file_path}")
    
    # Create temp directory for batch files
    temp_dir = tempfile.mkdtemp(prefix="hathi_batch_", dir="data/hathi")
    print(f"Created temp directory for batches: {temp_dir}")
    batch_files = []



    db_path = "data/hathi/hathitrust.db"
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Existing database '{db_path}' removed.")
        update_status("preparing", "Removed existing database...")

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # SQL statement to create a table named 'records'
        # The schema is based on the structure of 'current_record' later in the script
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS records (
            ht_bib_key INTEGER PRIMARY KEY,
            htid TEXT,
            access TEXT,
            description TEXT,
            oclc_num TEXT,
            isbn TEXT,
            issn TEXT,
            lccn TEXT,
            title TEXT,
            rights_date_used TEXT,
            lang TEXT,
            author TEXT
        );
        """
        cursor.execute(create_table_sql)
        conn.commit()
        create_table_sql = """
            CREATE VIRTUAL TABLE author_title 
            USING fts5(author, title);
        """
        cursor.execute(create_table_sql)
        conn.commit()
        print("Created FTS5 index table for fast searching")
        update_status("preparing", "Created full-text search index")




        print(f"Database '{db_path}' and table 'records' initialized successfully.")
        update_status("preparing", "Database tables initialized successfully")
    except sqlite3.Error as e:
        print(f"Database error: {e}")


    records = []
    batch_size = 50000
    batch_count = 0
    total_records = 0
    
    print(f"Starting to read gzip file: {gzipped_file_path}")
    update_status("processing", f"Reading data from {gzipped_file_path}")
    try:
        with gzip.open(gzipped_file_path, 'rt') as f:
            previous_ht_bib_key = None
            previous_record = None
            current_record=None
            
            line_count = 0
            for line in f:
                try:

                    record = list(csv.DictReader([line],delimiter='\t', fieldnames=fieldnames))[0]
                    # field order: htid	access	rights	ht_bib_key	description	source	source_bib_num	oclc_num	isbn	issn	lccn	title	imprint	rights_reason_code	rights_timestamp	us_gov_doc_flag	rights_date_used	pub_place	lang	bib_fmt	collection_code	content_provider_code	responsible_entity_code	digitization_agent_code	access_profile_code	author
                    if record['bib_fmt'] != 'BK':
                        continue
                    if record['author'] == '':
                        continue
                    line_count += 1

                    # if '/' in record['title'] and ':' in record['title']:
                    #     print(record['title'])

                    # this is here to build the test database
                    # if len(records) > 10000:
                    #     if 'Woolf, Virginia, 1882' not in record['author']:
                    #         continue
                    #     # break
                        

                    if previous_ht_bib_key != record['ht_bib_key']:
                        
                        if current_record != None:
                            # print(current_record)
                            records.append(current_record)
                            total_records += 1
                            
                            if total_records % 10000 == 0:
                                print(f"Processed {total_records} records. {line_count} lines read.")
                                update_status("processing", f"Processed {total_records} records from {line_count} lines", total_records)
                            
                            # Write batch to disk when reaching batch_size
                            if len(records) >= batch_size:
                                batch_file = os.path.join(temp_dir, f"batch_{batch_count:04d}.pkl")
                                with open(batch_file, 'wb') as bf:
                                    pickle.dump(records, bf)
                                batch_files.append(batch_file)
                                print(f"Wrote batch {batch_count} with {len(records)} records to {batch_file}")
                                batch_count += 1
                                records = []  # Clear records list to free memory

                        previous_ht_bib_key = record['ht_bib_key']
                        current_record = {
                            'htid': [],
                            'access': 'deny',
                            # 'rights': previous_record['rights'],
                            'ht_bib_key': record['ht_bib_key'],
                            'description': record['description'],
                            # 'source': record['source'],
                            # 'source_bib_num': record['source_bib_num'],
                            'oclc_num': [],
                            'isbn': [],
                            'issn': [],
                            'lccn': [],
                            'title': record['title'],
                            # 'imprint': record['imprint'],
                            # 'rights_reason_code': record['rights_reason_code'],
                            # 'rights_timestamp': record['rights_timestamp'],
                            # 'us_gov_doc_flag': record['us_gov_doc_flag'],
                            'rights_date_used': record['rights_date_used'],
                            # 'pub_place': record['pub_place'],
                            'lang': [],
                            # 'bib_fmt': record['bib_fmt'],
                            # 'collection_code': record['collection_code'],
                            # 'content_provider_code': record['content_provider_code'],
                            # 'responsible_entity_code': record['responsible_entity_code'],
                            # 'digitization_agent_code': record['digitization_agent_code'],
                            # 'access_profile_code': record['access_profile_code']
                            'author': record['author']
                        }
                    
                    current_record['htid'].append(record['htid'])
                    if record['access'] != 'deny':
                        current_record['access'] = record['access']

                    if record['oclc_num'] not in current_record['oclc_num'] and record['oclc_num'] != '' and record['oclc_num'] != None:
                        current_record['oclc_num'].append(record['oclc_num'])
                    if record['isbn'] not in current_record['isbn']and record['isbn'] != '' and record['isbn'] != None:
                        current_record['isbn'].append(record['isbn'])
                    if record['issn'] not in current_record['issn']and record['issn'] != '' and record['issn'] != None:
                        current_record['issn'].append(record['issn'])
                    if record['lccn'] not in current_record['lccn']and record['lccn'] != '' and record['lccn'] != None:
                        current_record['lccn'].append(record['lccn'])
                    if record['lang'] not in current_record['lang']and record['lang'] != '' and record['lang'] != None:
                        current_record['lang'].append(record['lang'])



                except csv.Error as e:
                    print(f"Error processing line: {line}")
                    print(f"CSV error: {e}")
 
            # Don't forget the last record still in progress
            if current_record is not None:
                records.append(current_record)
                total_records += 1
                
            # Write final batch if there are remaining records
            if records:
                batch_file = os.path.join(temp_dir, f"batch_{batch_count:04d}.pkl")
                with open(batch_file, 'wb') as bf:
                    pickle.dump(records, bf)
                batch_files.append(batch_file)
                print(f"Wrote final batch {batch_count} with {len(records)} records to {batch_file}")
                records = []  # Clear records list
                
    except FileNotFoundError:
        print(f"Error: File not found: {gzipped_file_path}")
        update_status("error", f"File not found: {gzipped_file_path}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return
    except gzip.BadGzipFile:
        print(f"Error: Invalid gzip file: {gzipped_file_path}")
        update_status("error", f"Invalid gzip file: {gzipped_file_path}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return


    print(f"Starting to insert {total_records} records into database from {len(batch_files)} batch files")
    update_status("processing", f"Inserting {total_records} records into database", 0, total_records)
    rec_count = 0
    
    # Process each batch file
    for batch_idx, batch_file in enumerate(batch_files):
        print(f"Processing batch {batch_idx + 1}/{len(batch_files)}: {batch_file}")
        
        # Load batch from disk
        with open(batch_file, 'rb') as bf:
            batch_records = pickle.load(bf)
        
        # Process records in this batch
        for record in batch_records:
            rec_count += 1
            # Prepare data for SQLite insertion
            # The current_record is guaranteed to be initialized and non-None at this point
            # if at least one line has passed the initial filters.
            data_tuple_for_db = (
                int(record['ht_bib_key']),
                "|".join(record['htid']),
                record['access'],
                record['description'],
                "|".join(record['oclc_num']),
                "|".join(record['isbn']),
                "|".join(record['issn']),
                "|".join(record['lccn']),
                record['title'],
                record['rights_date_used'],
                "|".join(record['lang']),
                record['author']
            )

            sql_insert_replace_stmt = """INSERT OR REPLACE INTO records 
                                        (ht_bib_key, htid, access, description, oclc_num, isbn, issn, lccn, title, rights_date_used, lang, author)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            try:
                cursor.execute(sql_insert_replace_stmt, data_tuple_for_db)

                # fts5_insert_stmt = """INSERT INTO author_title (rowid, author, title) VALUES (?, ?, ?)"""
                # fts5_insert_stmt_tuple = (int(record['ht_bib_key']),record['author'], record['title'])
                # print(fts5_insert_stmt_tuple)
                # cursor.execute(fts5_insert_stmt, fts5_insert_stmt_tuple)


                # Insert into FTS5 table
                # The FTS5 table uses the rowid from the main 'records' table.
                # We use ht_bib_key as the rowid.
                fts5_insert_stmt = """INSERT INTO author_title (rowid, author, title) VALUES (?, ?, ?)"""
                fts5_data_tuple = (
                    int(record['ht_bib_key']),
                    record['author'],
                    record['title']
                )
                cursor.execute(fts5_insert_stmt, fts5_data_tuple)


                # Periodic commit based on rec_count (lines processed after initial filters)
                # Adjust batch size (e.g., 10000) as needed for performance.
                if rec_count % 10000 == 0:
                    conn.commit()
                    print(f"Database commit triggered at rec_count {rec_count}.") # Optional: for debugging
                    update_status("processing", f"Inserted {rec_count} records into database", rec_count)
            except sqlite3.Error as e:
                # Log error or handle as appropriate for the application
                print(f"SQLite error during insert/replace for ht_bib_key {int(record['ht_bib_key'])}: {e}")
                print(f"Record data: {data_tuple_for_db}")
        
        # Delete batch file after processing to free disk space
        try:
            os.remove(batch_file)
            print(f"Deleted processed batch file: {batch_file}")
        except Exception as e:
            print(f"Warning: Could not delete batch file {batch_file}: {e}")
    
    conn.commit()  # Final commit after all records are processed
    print(f"Final database commit. Total records: {rec_count}")
    update_status("finalizing", f"Finalizing database with {rec_count} total records", rec_count)
    
    # Clean up temp directory
    try:
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temp directory: {temp_dir}")
    except Exception as e:
        print(f"Warning: Could not remove temp directory {temp_dir}: {e}")
    
    # Close connection and mark as complete
    if conn:
        conn.close()
    print(f"Database build complete! Created {db_path} with {rec_count} records")
    update_status("complete", f"Database successfully created with {rec_count} records", rec_count, rec_count)
    
    # Clean up: delete the downloaded gzip file to save disk space
    try:
        if os.path.exists(gzipped_file_path):
            os.remove(gzipped_file_path)
            print(f"Cleaned up: Deleted {gzipped_file_path}")
            update_status("complete", f"Database created with {rec_count} records. Cleaned up temporary files.", rec_count, rec_count)
    except Exception as e:
        print(f"Warning: Could not delete {gzipped_file_path}: {e}")
        # Don't fail the whole process for cleanup issues

def download_file(url):
    """Download file from URL with progress tracking"""
    local_filename = os.path.join('data/hathi', url.split('/')[-1])
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(local_filename), exist_ok=True)
    
    print(f"Starting download of {url}")
    update_status("downloading", f"Downloading {url.split('/')[-1]}...")
    
    # NOTE the stream=True parameter below
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress every 10MB
                        if downloaded % (10 * 1024 * 1024) == 0 or downloaded == total_size:
                            if total_size > 0:
                                progress_percent = (downloaded / total_size) * 100
                                print(f"Downloaded {downloaded:,} / {total_size:,} bytes ({progress_percent:.1f}%)")
                                update_status("downloading", f"Downloaded {progress_percent:.1f}% of {url.split('/')[-1]}", downloaded, total_size)
            
            print(f"Download completed: {local_filename}")
            update_status("download_complete", f"Downloaded {local_filename}")
            return local_filename
    
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")
        update_status("error", f"Download failed: {str(e)}")
        raise

def find_dump_url():
    """Find the latest HathiTrust dump file URL"""
    print("Looking for latest HathiTrust dump file...")
    update_status("finding_dump", "Searching for latest HathiTrust dump file...")
    
    url = "https://www.hathitrust.org/files/hathifiles/hathi_file_list.json"
    newest_full_dump = None
    latest_date = None

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        
        print(f"Found {len(data)} files in HathiTrust file list")
        update_status("finding_dump", f"Checking {len(data)} files for latest dump...")

        for item in data:
            if item.get("full") is True:
                # Assuming 'updated' field stores the date
                item_date_str = item.get("modified")
                if item_date_str:
                    try:
                        current_item_date = datetime.strptime(item_date_str, "%Y-%m-%d %H:%M:%S %z")
                        if latest_date is None or current_item_date > latest_date:
                            latest_date = current_item_date
                            newest_full_dump = item
                    except ValueError:
                        print(f"Warning: Could not parse date '{item_date_str}' for an item.")
                        continue
        
        if newest_full_dump:
            filename = newest_full_dump.get('filename')
            file_url = newest_full_dump.get('url')
            file_size = newest_full_dump.get('size', 'unknown')
            print("Found newest full dump:")
            print(f"  Filename: {filename}")
            print(f"  URL: {file_url}")
            print(f"  Updated: {newest_full_dump.get('updated')}")
            print(f"  Size: {file_size}")
            update_status("found_dump", f"Found latest dump: {filename} (Size: {file_size})")
            return file_url
        else:
            print("No full dump found in the list.")
            update_status("error", "No full dump found in HathiTrust file list")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        update_status("error", f"Error fetching HathiTrust file list: {str(e)}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response.")
        update_status("error", "Error parsing HathiTrust file list JSON")
        return None



def main():
    """Main function that orchestrates the entire database build process"""
    update_status("starting", "Initializing HathiTrust database build process...")
    
    # Clean up any existing database before starting
    db_path = "data/hathi/hathitrust.db"
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Removed existing database: {db_path}")
            update_status("starting", "Removed existing database, starting fresh build...")
    except Exception as e:
        print(f"Warning: Could not remove existing database {db_path}: {e}")
        update_status("starting", f"Warning: Could not remove existing database, continuing...")
    
    try:
        # Step 1: Find the latest dump URL
        url = find_dump_url()
        if url is None:
            update_status("error", "Could not find HathiTrust dump file URL")
            return
        
        # Step 2: Download the file
        gzipped_file_path = download_file(url)
        
        # Step 3: Build the database
        build_db(gzipped_file_path)
        
    except Exception as e:
        print(f"Fatal error in main process: {e}")
        try:
            update_status("error", f"Fatal error: {str(e)}")
        except:
            pass
        raise


if __name__ == "__main__":
    main()

