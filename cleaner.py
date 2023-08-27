import os
import asyncio
import logging
import requests
from requests.exceptions import RequestException
import json

# Set up logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s]: %(message)s', 
    level=logging.INFO, 
    handlers=[logging.StreamHandler()]
)

# Sonarr and Radarr API endpoints
SONARR_API_URL = (os.environ['SONARR_URL']) + "/api/v3"
RADARR_API_URL = (os.environ['RADARR_URL']) + "/api/v3"

# API key for Sonarr and Radarr
SONARR_API_KEY = (os.environ['SONARR_API_KEY'])
RADARR_API_KEY = (os.environ['RADARR_API_KEY'])

# Timeout for API requests in seconds
API_TIMEOUT = int(os.environ['API_TIMEOUT']) 

# Function to make API requests with error handling
async def make_api_request(method, url, api_key, data=None):
    try:
        if method == "GET":
            request_function = requests.get
        elif method == "POST":
            request_function = requests.post
        elif method == "DELETE":
            request_function = requests.delete
        headers = {'X-Api-Key': api_key, 'Content-Type': 'application/json'}
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: request_function(url, data=json.dumps(data), headers=headers))
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logging.error(f'Error making API request to {url}: {e}')
        return None
    except ValueError as e:
        logging.error(f'Error parsing JSON response from {url}: {e}')
        return None

# Function to remove stalled Sonarr downloads
async def remove_stalled_sonarr_downloads():
    logging.info('Checking Sonarr queue...')
    sonarr_url = f'{SONARR_API_URL}/queue'
    sonarr_queue = await make_api_request("GET", sonarr_url, SONARR_API_KEY, {'page': '1', 'pageSize': await count_records(SONARR_API_URL,SONARR_API_KEY)})
    if sonarr_queue is not None and 'records' in sonarr_queue:
        logging.info('Processing Sonarr queue...')
        for item in sonarr_queue['records']:
            if 'title' in item and 'status' in item and 'trackedDownloadStatus' in item:
                logging.info(f'Checking the status of {item["title"]}')
                if item['status'] == 'warning' and item['errorMessage'] == 'The download is stalled with no connections':
                    logging.info(f'Removing stalled Sonarr download: {item["title"]}')
                    await make_api_request("DELETE", f'{SONARR_API_URL}/queue/{item["id"]}', SONARR_API_KEY, {'removeFromClient': 'true', 'blocklist': 'true'})
            else:
                logging.warning('Skipping item in Sonarr queue due to missing or invalid keys')
    else:
        logging.warning('Sonarr queue is None or missing "records" key')

# Function to remove stalled Radarr downloads
async def remove_stalled_radarr_downloads():
    logging.info('Checking radarr queue...')
    radarr_url = f'{RADARR_API_URL}/queue'
    radarr_queue = await make_api_request("GET", radarr_url, RADARR_API_KEY, {'page': '1', 'pageSize': await count_records(RADARR_API_URL,RADARR_API_KEY)})
    if radarr_queue is not None and 'records' in radarr_queue:
        logging.info('Processing Radarr queue...')
        for item in radarr_queue['records']:
            if 'title' in item and 'status' in item and 'trackedDownloadStatus' in item:
                logging.info(f'Checking the status of {item["title"]}')
                if item['status'] == 'warning' and item['errorMessage'] == 'The download is stalled with no connections':
                    logging.info(f'Removing stalled Radarr download: {item["title"]}')
                    await make_api_request("DELETE", f'{RADARR_API_URL}/queue/{item["id"]}', RADARR_API_KEY, {'removeFromClient': 'true', 'blocklist': 'true'})
            else:
                logging.warning('Skipping item in Radarr queue due to missing or invalid keys')
    else:
        logging.warning('Radarr queue is None or missing "records" key')

#Function to import the sync lists on Sonarr
async def import_sonarr_list():
    logging.info('Importing Sonarr sync list...')
    sonarr_url = f'{SONARR_API_URL}/command'
    sonarr_queue = await make_api_request("POST", sonarr_url, SONARR_API_KEY, {'name': 'ImportListSync'})
    if sonarr_queue is not None:
        logging.info('Imported Sonarr sync list')
    else:
        logging.warning('Sonarr queue is None or missing "records" key')

#Function to import the sync lists on Radarr
async def import_radarr_list():
    logging.info('Importing Radarr sync list...')
    radarr_url = f'{RADARR_API_URL}/command'
    radarr_queue = await make_api_request("POST", radarr_url, RADARR_API_KEY, {'name': 'ImportListSync'})
    if radarr_queue is not None:
        logging.info('Imported Radarr sync list')
    else:
        logging.warning('Radarr queue is None or missing "records" key')

#Function to import the refresh missing episodes on Sonarr
async def refresh_sonarr_missing_episodes():
    logging.info('Refreshing Sonarr missing episodes on monitored series...')
    sonarr_url = f'{SONARR_API_URL}/command'
    sonarr_queue = await make_api_request("POST", sonarr_url, SONARR_API_KEY, {'name': 'missingEpisodeSearch'})
    if sonarr_queue is not None:
        logging.info('Refreshed Sonarr missing episodes on monitored series')
    else:
        logging.warning('Sonarr queue is None or missing "records" key')
    
    logging.info('Refreshed Sonarr missing episodes on monitored series...')


# Make a request to view and count items in queue and return the number.
async def count_records(API_URL, API_Key):
    the_url = f'{API_URL}/queue'
    the_queue = await make_api_request("GET", the_url, API_Key)
    if the_queue is not None and 'records' in the_queue:
        return the_queue['totalRecords']

# Main function
async def main():
    while True:
        logging.info('Running media-tools script')
        await remove_stalled_sonarr_downloads()
        await remove_stalled_radarr_downloads()
        await import_sonarr_list()
        await import_radarr_list()
        await refresh_sonarr_missing_episodes()
        logging.info(f'Finished running media-tools script. Sleeping for {API_TIMEOUT/60} minutes.')
        await asyncio.sleep(API_TIMEOUT)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
