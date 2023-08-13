# Just built-in packages
import sys
import os
import re
import http.client
import urllib.request
import urllib.parse
import json
import logging
import json
import subprocess
import shlex
from pathlib import Path

# Install steps:
# The script can run in windows and linux.
# 1. Set all variables in the section below.
# 2. Download mkvtoolnix in "https://mkvtoolnix.download/downloads.html". The download can be done in portable version or full instalation.
# 3. Mkvtoolnix will be used to read and write metadata.
# 4. Set Sonarr to use the respectives episodes formats:
# 4.1 Standard Episode Format: {Series Title} - S{season:00}E{episode:00} - {Episode CleanTitle} [{Preferred Words }{Quality Full}]{[MediaInfo VideoDynamicRange]}[{MediaInfo VideoBitDepth}bit]{[MediaInfo VideoCodec]}[{Mediainfo AudioCodec} { Mediainfo AudioChannels}]{MediaInfo AudioLanguages}{MediaInfo SubtitleLanguages:PT+BR+PT-BR+Portuguese+Brazilian+EN}{-Release Group}
# 4.2 Daily Episode Format: {Series Title} - {Air-Date} - {Episode CleanTitle} [{Preferred Words }{Quality Full}]{[MediaInfo VideoDynamicRange]}[{MediaInfo VideoBitDepth}bit]{[MediaInfo VideoCodec]}[{Mediainfo AudioCodec} { Mediainfo AudioChannels}]{MediaInfo AudioLanguages}{MediaInfo SubtitleLanguages:PT+BR+PT-BR+Portuguese+Brazilian+EN}{-Release Group}
# 4.3 Anime Episode Format: {Series Title} - S{season:00}E{episode:00} - {absolute:000} - {Episode CleanTitle} [{Preferred Words }{Quality Full}]{[MediaInfo VideoDynamicRange]}[{MediaInfo VideoBitDepth}bit]{[MediaInfo VideoCodec]}[{Mediainfo AudioCodec} { Mediainfo AudioChannels}]{MediaInfo AudioLanguages}{MediaInfo SubtitleLanguages:PT+BR+PT-BR+Portuguese+Brazilian+EN}{-Release Group}
# 5. Series Folder Format: {Series TitleYear} [tvdb-{TvdbId}]
# 6. Add the script in "Settins -> Connect" add a new connection as custom script
# 6.1 Notification Triggers: On Import, On Upgrade, On Episode File Delete
# 6.2 Recomendation: Add one tag to just call the script to some tags
# 6.3 Path: Call the .sh script, then .sh script will call python script

#############################################################################################################################################################################

# Values in this sections neet to be configurated to run the script properly

# Global Variables
API_KEY_TMDB = '12345678789' # API Key from TMDB when search for ID from tv shows
API_KEY_OPENSUBTITLES = '987654321' # API Key to download from opensubtitles.com
USERNAME_OPENSUBTITLES = 'TesteTeste' # Username to authenticate to opensubtitles.com (the same used in browser)
PASSWORD_OPENSUBTITLES = 'Teste123' # Password to authenticate to opensubtitle.coms (the same used in browser)
SCRIPT_PATH = os.path.realpath(__file__) # Script path to log
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH) # Script directory to log
SUBTITLE_LANGUAGE = 'pt-br' # Language to search in opensubtitles.com
SUBTITLE_KNOWN_NAMES = ['portuguese', 'portugues', 'pt-br', 'br'] # Known names from the language that is searched
SUBTITLE_END_FILEPATH_PATTERN = '.pt.srt' # End filepath name, for example 'subtitle_123.pt.srt', '.pt.srt' is the pattern
ALWAYS_DOWNLOAD_SUBTITLE = False  # If True then always will download subtitles in the language target, even if already exist one
WEBHOOK_DISCORD = "/api/webhooks/123/123456789" # If not filled or equal -1, will ignore Discord notifications, Just paste after https://discord.com/

# EMBED CONFIGURATION
# The configuration below is just to metadata usage in mkv files
EMBED_SUBTITLE_NAME = 'Portuguese (Brazil)' # The name of track
EMBED_SUBTITLE_CODE = 'pt-BR' # The international code of languages
MKVMERGE_PATH = 'mkvmerge' # Path/command to execute mkvmerge
EMBED_SUBTITLE_TRACKS = ["pt", "pt-br", "por", "portuguese", "brazilian", "ptbr", "pob", "portugues", "português", "br"] # Known names from the language that is searched in embed subtitles
EXECUTION_TYPE = 'remote' # 'remote' is to execute from Sonarr, 'local' is to execute locally without use sonarr the code

#############################################################################################################################################################################

envs = {} # Do not change

# Set log format and file
log_file_path = f'{SCRIPT_DIR}/log.txt'

# Prefix of logs
formatter = logging.Formatter(
    fmt='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# If the logfile has more than 100MB will delete the log file to create a new one
if os.path.exists(log_file_path):
    file_size = os.path.getsize(log_file_path)
    if file_size > 100 * 1024 * 1024:  # 100MB in bytes
        os.remove(log_file_path)

# Append the log to a general log file
file_handler = logging.FileHandler(log_file_path, mode = 'a')
file_handler.setFormatter(formatter)

# Define that will use stdout to log
stream_handler = logging.StreamHandler(stream=sys.stdout)
stream_handler.setFormatter(formatter)

# Creating logger_ variable to use as log
logger_ = logging.getLogger('logfile')
logger_.setLevel(logging.DEBUG)
logger_.addHandler(file_handler)
logger_.addHandler(stream_handler)

# Starting script
logger_.info(f"*"*100)
logger_.info(f"Starting subtitles manager")
logger_.info(f"*"*100)

def read_arguments(type = 'local'):
    global envs

    # Sonarr execution
    if type == 'remote':
        ENV_FILE = f"{SCRIPT_DIR}/ARR_ENV.txt"
        
        logger_.info(f"Log path: {SCRIPT_DIR}")

        with open(ENV_FILE, 'r') as f:
            logger_.info(f"Environment variables: {os.environ}")
            for line in f:
                try:
                    env = line.rstrip().lower()
                    if env in os.environ:
                        envs[env] = os.environ[env]
                except Exception as e:
                    logger_.warning(f"Error parsing variable {line}. Exception: {e}")
                    continue
        
        if len(envs) == 0:
            logger_.error("No *arr Environment variables were found.")
            raise Exception('No *arr Environment variables were found.')
        
    # Local execute to test code
    elif type == 'local':
        envs['sonarr_eventtype'] = 'Download'
        envs['sonarr_series_title'] = 'The Angel Next Door Spoils Me Rotten'
        envs['sonarr_series_imdbid'] = ''
        envs['sonarr_series_type'] = 'Anime'
        envs['sonarr_episodefile_seasonnumber'] = '1'
        envs['sonarr_episodefile_episodenumbers'] = '11'
        envs['sonarr_isupgrade'] = 'False'
        envs['sonarr_series_path'] = f"X:\Anime\Shows\The Angel Next Door Spoils Me Rotten (2023) [tvdb-414221]\Season 01"
        envs['sonarr_episodefile_path'] = r"C:\Users\herik\OneDrive\Área de Trabalho\Subtitle_Manager\The Angel Next Door Spoils Me Rotten - S01E11 - 011 - The Angel Next Door Spoils Me Rotten [HDTV-1080p][8bit][x264][AAC 2.0][JA][PT+EN]-Erai-raws.mkv"
    else:
        logger_.error(f'Execution type not identified: {type}')
        raise Exception(f'Execution type not identified: {type}')

def consult_tmdb_id():
    tmdb_id = -1
    # Construct the request parameters and headers
    sonarr_series_title = envs['sonarr_series_title']
    url = f'/3/search/tv?api_key={API_KEY_TMDB}&query={sonarr_series_title}'
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Python HTTP Client',
    }

    try:
        # Establish a connection to the TMDb API server
        conn = http.client.HTTPSConnection('api.themoviedb.org')

        # Send the GET request
        conn.request('GET', url, headers=headers)

        # Get the response from the server
        response = conn.getresponse()

        # Check if the request was successful (status code 200)
        if response.status == 200:
            data = response.read().decode('utf-8')
            json_data = json.loads(data)
            
            # Check if the API responded with any TV show results
            if json_data['results']:
                for result in json_data['results']:
                    if TV_SHOW_YEAR in result['first_air_date']:
                        # Get result
                        tmdb_id = result['id']
                        logger_.info(f"TMDB ID for '{envs['sonarr_series_title']}' is: {tmdb_id}")
                        break
            else:
                logger_.warning("TV show not found.")
        else:
            logger_.error(f"Request failed with status code: {response.status}")
        # Close the connection
        conn.close()

    except Exception as e:
        logger_.error(f"An error occurred: {e}")
    
    return tmdb_id

def get_subtitle_id(season, episode, imdb_id = -1, tmdb_id = -1):
    file_id = -1
    #imdb_id = imdb_id.replace('tt', '')
    # Construct the request parameters and headers
    if imdb_id == -1:
        url = f'/api/v1/subtitles?ai_translated=exclude&episode_number={episode}&tmdb_id={tmdb_id}&languages={SUBTITLE_LANGUAGE}&order_by=download_count&season_number={season}'
    else:
        url =f'/api/v1/subtitles?ai_translated=exclude&episode_number={episode}&imdb_id={imdb_id}&languages={SUBTITLE_LANGUAGE}&order_by=download_count&season_number={season}'
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Python HTTP Client',
        'Api-Key': API_KEY_OPENSUBTITLES
    }

    try:
        # Establish a connection to the Opensubtitles API server
        conn = http.client.HTTPSConnection('api.opensubtitles.com')

        # Send the GET request
        conn.request('GET', url, headers=headers)

        # Get the response from the server
        response = conn.getresponse()

        # Check if the request was successful (status code 200)
        if response.status == 200:
            data = response.read().decode('utf-8')
            json_data = json.loads(data)
            
            # Check if the API responded with any subtitle
            if json_data['data']:
                result = json_data['data'][0]
                file_id = result['attributes']['files'][0]['file_id']

            else:
                logger_.warning("Subtitle not found.")

        # Check if need to redirect the request
        elif response.status == 301:
            # Get new location and redirect a new request
            redirect_location = response.getheader('Location')
            conn.close()

            conn = http.client.HTTPSConnection('api.opensubtitles.com')
            conn.request('GET', redirect_location, headers=headers)
            response = conn.getresponse()

            data = response.read().decode('utf-8')
            json_data = json.loads(data)
            
            # Check if the API responded with any subtitle
            if json_data['data']:
                result = json_data['data'][0]
                file_id = result['attributes']['files'][0]['file_id']

            else:
                logger_.warning("Subtitle not found.")
        else:
            logger_.error(f"Request failed with status code: {response.status}")
        # Close the connection
        conn.close()

    except Exception as e:
        logger_.error(f"An error occurred: {e}")

    return file_id

def get_token_opensubtitles():
    token = -1

    # Construct the request parameters and headers
    url = f'/api/v1/login'
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Python HTTP Client',
        'Api-Key': API_KEY_OPENSUBTITLES
    }

    body = {
        "username": USERNAME_OPENSUBTITLES,
        "password": PASSWORD_OPENSUBTITLES
    }

    try:
        # Establish a connection to the OpenSubtitles API server
        conn = http.client.HTTPSConnection('api.opensubtitles.com')

        # Send the GET request
        conn.request('POST', url, body = json.dumps(body), headers=headers)

        # Get the response from the server
        response = conn.getresponse()

        # Check if the request was successful (status code 200)
        if response.status == 200:
            data = response.read().decode('utf-8')
            json_data = json.loads(data)
            
            # Get token
            token = json_data['token']

            logger_.info(f"Obtained token from opensubtitles.")

        # Check if need to redirect the request
        elif response.status == 301:
            # Get new location and redirect a new request
            redirect_location = response.getheader('Location')
            conn.close()

            conn = http.client.HTTPSConnection('api.opensubtitles.com')
            conn.request('POST', redirect_location, body = json.dumps(body), headers=headers)
            response = conn.getresponse()

            data = response.read().decode('utf-8')
            json_data = json.loads(data)
            
            # Get token
            token = json_data['token']

            logger_.info(f"Obtained token from opensubtitles.")
        else:
            logger_.error(f"Request failed with status code: {response.status}")
        # Close the connection
        conn.close()

    except Exception as e:
        logger_.error(f"An error occurred: {e}")

    return token    

def destroy_token_opensubtitles(token):
    # Construct the request parameters and headers
    url = f'/api/v1/logout'
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Python HTTP Client',
        'Api-Key': API_KEY_OPENSUBTITLES,
        'Authorization': f'Bearer {token}' 
    }

    try:
        # Establish a connection to the OpenSubtitles API server
        conn = http.client.HTTPSConnection('api.opensubtitles.com')

        # Send the GET request
        conn.request('DELETE', url, headers=headers)

        # Get the response from the server
        response = conn.getresponse()

        # Check if the request was successful (status code 200)
        if response.status == 200:
            logger_.info(f"Token from opensubtitles was destroied.")

        # Check if need to redirect the request
        elif response.status == 301:
            # Get new location and redirect a new request
            redirect_location = response.getheader('Location')
            conn.close()

            conn = http.client.HTTPSConnection('api.opensubtitles.com')
            conn.request('DELETE', redirect_location, headers=headers)
            response = conn.getresponse()
            
            if response.status == 200:
                logger_.info(f"Token from opensubtitles was destroied.")

            return
        else:
            logger_.error(f"Request failed with status code: {response.status}")
        # Close the connection
        conn.close()

    except Exception as e:
        logger_.error(f"An error occurred: {e}")

    return

def get_subtitle_download_link(file_id, token):
    subtitle_link = -1
    # Construct the request parameters and headers
    url = f'/api/v1/download?file_id={file_id}'

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Api-Key': API_KEY_OPENSUBTITLES,
        'Authorization': f'Bearer {token}'
    }

    try:
        # Establish a connection to the Opensubtitles API server
        conn = http.client.HTTPSConnection('api.opensubtitles.com')

        # Send the POST request
        conn.request('POST', url, headers=headers)

        # Get the response from the server
        response = conn.getresponse()

        # Check if the request was successful (status code 200)
        if response.status == 200:
            data = response.read().decode('utf-8')
            json_data = json.loads(data)

            # Get subtitle link
            subtitle_link = json_data['link']

        # Check if need to redirect the request
        elif response.status == 301:
            # Get new location and redirect a new request
            redirect_location = response.getheader('Location')
            conn.close()

            conn = http.client.HTTPSConnection('api.opensubtitles.com')
            conn.request('GET', redirect_location, headers=headers)
            response = conn.getresponse()

            data = response.read().decode('utf-8')
            json_data = json.loads(data)
            
            # Get subtitle link
            subtitle_link = json_data['link']
        else:
            logger_.error(f"Request failed with status code: {response.status}")
        # Close the connection
        conn.close()

    except Exception as e:
        logger_.error(f"An error occurred: {e}")

    return subtitle_link

def download_content_from_url(url, output_file):
    try:
        # Set a custom user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

        # Create a request with the custom user agent
        request = urllib.request.Request(url, headers=headers)

        # Fetch the content from the URL
        with urllib.request.urlopen(request) as response:
            data = response.read()

        # Save the content to a local file
        with open(output_file, 'wb') as file:
            file.write(data)

        logger_.info(f"Subtitle downloaded and saved to '{output_file}' successfully.")
    except urllib.error.URLError as e:
        logger_.info(f"Error: Unable to download subtitle from the URL. {e}")
    except IOError as e:
        logger_.info(f"Error: Unable to save the subtitle to '{output_file}'. {e}")

def embed_subtitle(video_path, subtitle_path = '', delete_old_subtitle = True):

    # If does not has any subtitle_path, with check if found
    if subtitle_path == '':
        folderpath = os.path.dirname(video_path)
        folderpath = Path(folderpath)
        filelist = list(folderpath.glob(f"*.srt"))

        # Check all subtitles and if match with the episode and language
        for subtitle in filelist:
            if os.path.basename(video_path.replace(".mkv", "")) in os.path.basename(str(subtitle)):
                if any(name.lower() in str(subtitle).lower() for name in EMBED_SUBTITLE_TRACKS):
                    subtitle_path = str(subtitle)
                    break
        
        if subtitle_path == '':
            return

    output_path = video_path.replace('.mkv', '_temp.mkv')

    # Command to embed subtitle
    cmd = [
        MKVMERGE_PATH,
        "-o", output_path,
        video_path,
        "--language", f"0:{EMBED_SUBTITLE_CODE}",  # Language code
        "--track-name", f"0:{EMBED_SUBTITLE_NAME}",  # Track name
        '--default-track-flag', '0:yes',   # Set track as default subtitle
        '--forced-display-flag', '0:no',   # Set track as not forced subtitle
        "--sub-charset", "0:UTF-8",
        subtitle_path
    ]

    try:
        # Embed Subtitle
        subprocess.run(cmd, check = True)
        logger_.info("Subtitle embedded successfully!")

        if delete_old_subtitle:
            # Deleting old subtitle
            os.remove(subtitle_path)

        # Delete old video file and rename the new to old name
        os.remove(video_path)
        os.rename(output_path, video_path)

        delete_external_subtitles(video_path)
    except subprocess.CalledProcessError as e:
        logger_.error(f"Error occurred while embedding subtitle: {e}")

def check_track_name(track_name=str):
    subtitles = ["full", "dialog", "subtitles", ""]

    for s in subtitles:
        if s in track_name.lower():
            return True

    return False

def set_default_tracks(video_path):
    logger_.info("Starting to set default audio and subtitle track")

    # Set variavles
    default_tracks_id = []
    remove_forced_tracks_id = []
    remove_default_tracks_id = []
    is_audio_set = False
    is_subtitle_set = False

    anime = Path(video_path)

    # Get metadata from video file
    get_tracks_flags = [str(MKVMERGE_PATH), "-J", str(anime)]
    out = subprocess.check_output(get_tracks_flags, shell=False)
    out = json.loads(str(out, "utf-8").strip())

    # Loop all tracks and match with audio and subtitle types
    for item in out["tracks"]:
        properties = item["properties"]

        # Check if this track is audio, then set default if it is Japanese audio
        if item["type"] == "audio":
            if properties["language"] in ["jpn", "jp", "ja"] and not is_audio_set:
                itemId = item['id']
                logger_.info(f"Audio track identified with id: {itemId}")
                default_tracks_id.append(itemId)
                is_audio_set = True
            else:
                remove_default_tracks_id.append(item["id"])
        # If the track is subtitle check if it is the target language and set as default
        elif item["type"] == "subtitles":
            remove_forced_tracks_id.append(item["id"])
            if properties["language"] in EMBED_SUBTITLE_TRACKS:               
                track_name = (
                    properties["track_name"]
                    if "track_name" in properties.keys()
                    else ""
                )
                if check_track_name(track_name) and not is_subtitle_set:
                    itemId = item['id']
                    logger_.info(f"Subtitle track identified with id: {itemId}")
                    default_tracks_id.append(itemId)
                    is_subtitle_set = True
                else:
                    remove_default_tracks_id.append(item["id"])
            else:
                remove_default_tracks_id.append(item["id"])

    # Build default track variable
    default_tracks = " ".join(
        [f"--default-track-flag {x}:yes" for x in default_tracks_id]
    )
    logger_.info(f"Add default tracks: {default_tracks}")
    default_tracks = shlex.split(default_tracks)

    # Build forced track variable
    forced_tracks = " ".join(
        [f"--forced-display-flag {x}:no" for x in remove_forced_tracks_id]
    )
    logger_.info(f"Remove forced tracks: {forced_tracks}")
    forced_tracks = shlex.split(forced_tracks)

    # Build not default track variable
    remove_default_tracks = " ".join(
        [f"--default-track-flag {x}:no" for x in remove_default_tracks_id]
    )
    logger_.info(f"Remove default tracks: {remove_default_tracks}")
    remove_default_tracks = shlex.split(remove_default_tracks)

    # Concatenate the command
    set_tracks_flags = [
        str(MKVMERGE_PATH),
        "-o",
        str(anime).replace(".mkv", "_temp.mkv")
    ] + default_tracks + remove_default_tracks + forced_tracks
    logger_.info(f"Full command to mkvmerge: {set_tracks_flags}")
    set_tracks_flags.append(str(anime))

    # Run script to set default tracks
    proc = subprocess.run(set_tracks_flags, check=True, shell=False)
    name = anime.name.replace(".mkv", "_temp.mkv")
    parent = anime.parent

    # Delete old file and rename new file
    anime.unlink()
    anime = Path(parent/name)
    name = name.replace("_temp.mkv", ".mkv")

    anime.replace(parent / name)
    logger_.info("Tracks was organized with successful!")

def delete_external_subtitles(video_path):
    logger_.info("Deleting external subtitles with the target language")
    folderpath = os.path.dirname(video_path)
    folderpath = Path(folderpath)
    filelist = list(folderpath.glob(f"*.srt"))

    # Check all subtitles and if match with the episode and language, then delete
    for subtitle in filelist:
        if os.path.basename(video_path.replace(".mkv", "")) in os.path.basename(str(subtitle)):
            if any(name.lower() in str(subtitle).lower() for name in EMBED_SUBTITLE_TRACKS):
                strSubtitle = str(subtitle)
                logger_.info(f'Deleting external subtitle: {strSubtitle}')
                os.remove(strSubtitle)

def has_targe_subtitles(video_path, method = 'title'):

    if ALWAYS_DOWNLOAD_SUBTITLE:
        logger_.info("The subtitle will be downloaded because ALWAYS_DOWNLOAD_SUBTITLE is True.")
        return False

    logger_.info(f"Check subtitles with {method} method.")

    try:
        if method == 'title':
            subtitles = envs['sonarr_episodefile_path'].split('[')[-1].split(']')[0]

            logger_.info(f"Identified subtitles: {subtitles}")

            # Check if has minimum one subtitle
            if len(subtitles) >= 2:
                # Check if some of the subtitle is portuguese
                if 'pt' in subtitles.lower() or 'br' in subtitles.lower():
                    return True
                else:
                    return False
            else:
                logger_.info("The title does not have any subtitles, will be checked again with media header.")
                return has_targe_subtitles(video_path, 'header')
        elif method == 'header':
            # Open media header
            with open(video_path, "rb") as f:
                # Read the first 10 MB of the file header
                header_data = f.read(10 * 1024 * 1024)

                # Check for the presence of portuguese terms
                if any(name.lower() in header_data.lower() for name in SUBTITLE_KNOWN_NAMES):
                    return True

                return False
        elif method == 'mkv':
            try:
                get_tracks_flags = [str(MKVMERGE_PATH), "-J", str(video_path)]
                out = subprocess.check_output(get_tracks_flags, shell=False)
                out = json.loads(str(out, "utf-8").strip())

                # Loop all tracks
                for item in out["tracks"]:
                    properties = item["properties"]

                    # if the track is subtitle
                    if item["type"] == "subtitles":
                        # Chech if the language is the target
                        if properties["language"] in EMBED_SUBTITLE_TRACKS:
                            return True
                
                return False

            except Exception as e:
                logger_.error(f"An error occurred: {e}")
                logger_.warning("Trying again, but with title method.")
                return has_targe_subtitles(video_path, 'title')
        else:
            logger_.error(f"The '{method}' is invalid to read subtitles.")

    except Exception as e:
        logger_.error(f"An error occurred: {e}")
        return False

def has_external_target_subtitles(video_path):
    logger_.info("Checking if has external subtitles")
    folderpath = os.path.dirname(video_path)
    folderpath = Path(folderpath)
    filelist = list(folderpath.glob(f"*.srt"))

    # Check all subtitles and if match with the episode and language
    for subtitle in filelist:
        if os.path.basename(video_path.replace(".mkv", "")) in os.path.basename(str(subtitle)):
            if any(name.lower() in str(subtitle).lower() for name in EMBED_SUBTITLE_TRACKS):
                logger_.info(f"External subtitles identified: {subtitle}")
                return True

    logger_.info("Does not has any external subtitle with target language")
    return False

def clean_subtitle(subtitle_path, clean_html_tags = True, clean_special_tags = True):
    logger_.info("Cleaning subtitle")

    # Read subtitles
    with open(subtitle_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # If True remove html tags from subtitles
    if clean_html_tags:
        logger_.info("Removing HTML tags from subtitle")
        pattern = r'<.*?>'
        content = re.sub(pattern, '', content)
    
    # If True remove special tags like {*} from subtitles
    if clean_special_tags:
        logger_.info("Removing special tags from subtitle")
        pattern = r'\{.*?\}'
        content = re.sub(pattern, '', content)

    # Write clear subtitles
    with open(subtitle_path, 'w', encoding='utf-8') as file:
        file.write(content)

def download_subtitle(action_type):
    logger_.info(f'{action_type} action.')
    
    if '.mkv' in envs['sonarr_episodefile_path']:
        check_subtitles_method = 'mkv'
    else:
        check_subtitles_method = 'title'

    # Check if already has subtitles'
    if not has_targe_subtitles(envs['sonarr_episodefile_path'], check_subtitles_method):
        if not has_external_target_subtitles(envs['sonarr_episodefile_path']): 
            logger_.info(f'It will be necessary to download portuguese subtitle from opensubtitles')
            tmdb_id = -1
            imdbID = envs['sonarr_series_imdbid']

            # Check if has IMBDB ID, if not will get TMDB ID
            if imdbID == -1 or imdbID == "":
                logger_.info(f'IMDB_ID is invalid: {imdbID}')
                logger_.info(f'It will be required to use tmdb_id, imdb_id is invalid.')

                tmdb_id = consult_tmdb_id()
                imdbID = -1
            else:
                logger_.info(f'IMDB ID: {imdbID}')
            
            # Search for subtitle using season and episode
            sonarr_episodefile_seasonnumber = envs['sonarr_episodefile_seasonnumber']
            logger_.info(f'Trying to download subtitle with season and episode number S{sonarr_episodefile_seasonnumber}:E{RELEASE_ABSOLUTE_EPISODE_NUMBERS}')
            subtitle_id = get_subtitle_id(envs['sonarr_episodefile_seasonnumber'], envs['sonarr_episodefile_episodenumbers'], imdbID, tmdb_id)
            logger_.info(f'Subtitle ID: {subtitle_id}')

            # Search for subtitle using absolute episode number
            if subtitle_id == -1 and RELEASE_ABSOLUTE_EPISODE_NUMBERS != -1:
                logger_.info(f'Download with season and episode number failed')
                logger_.info(f'Trying to download subtitle with absolute episode number: {RELEASE_ABSOLUTE_EPISODE_NUMBERS}')
                subtitle_id = get_subtitle_id('1', RELEASE_ABSOLUTE_EPISODE_NUMBERS, imdbID, tmdb_id)
                logger_.info(f'Subtitle ID: {subtitle_id}')

            # If found subtitle, then download
            if subtitle_id != -1:
                # Authenticate to opensubtitles
                token_opensubtitles = get_token_opensubtitles()

                if token_opensubtitles != -1:
                    subtitle_download_link = get_subtitle_download_link(subtitle_id, token_opensubtitles)
                    logger_.info(f'Authenticate with successful to opensubtitles')               

                    # Check if found download link to subtitle, if yes save the subtitle
                    if subtitle_download_link != -1:
                        logger_.info(f'Link to download subtitle {subtitle_download_link}')
                        
                        _, file_extension = os.path.splitext(envs['sonarr_episodefile_path'])
                        subtitle_filepath = envs['sonarr_episodefile_path'].replace(file_extension, SUBTITLE_END_FILEPATH_PATTERN)

                        # Check if subtitle already exist, if yes delete
                        if os.path.exists(subtitle_filepath):
                            os.remove(subtitle_filepath)

                        # Download subtitle
                        download_content_from_url(subtitle_download_link, subtitle_filepath)

                        # Clean subtitle
                        clean_subtitle(subtitle_filepath)

                        # Embed subtitle
                        embed_subtitle(envs['sonarr_episodefile_path'], subtitle_filepath)

                        # Notify discord about subtitle download
                        notify_download_subtitle_discord(envs['sonarr_episodefile_path'], envs['sonarr_episodefile_seasonnumber'], envs['sonarr_episodefile_episodenumbers'], RELEASE_ABSOLUTE_EPISODE_NUMBERS)
                    else:
                        logger_.error(f'Failed to get subtitle download link')

                    # Logout from opensubtitles
                    destroy_token_opensubtitles(token_opensubtitles)
                else:
                    logger_.error(f'Failed to authenticate with opensubtitles')
            else:
                logger_.error(f'Failed to download subtitles')
        else:
            sonarr_episodefile_path = envs['sonarr_episodefile_path']
            logger_.warning(f'The \'{sonarr_episodefile_path}\' already has external subtitles')
            embed_subtitle(sonarr_episodefile_path)
          
    else:
        sonarr_episodefile_path = envs['sonarr_episodefile_path']
        logger_.warning(f'The \'{sonarr_episodefile_path}\' already has embed subtitles')
        delete_external_subtitles(sonarr_episodefile_path)

    if check_subtitles_method== 'mkv':
        sonarr_episodefile_path = envs['sonarr_episodefile_path']
        set_default_tracks(sonarr_episodefile_path)
        delete_external_subtitles(sonarr_episodefile_path)

def delete_subtitle():
    logger_.info(f'EpisodeFileDelete action.')

    # Get subtitles
    _, file_extension = os.path.splitext(envs['sonarr_episodefile_path'])
    subtitle_filepath = envs['sonarr_episodefile_path'].replace(file_extension, SUBTITLE_END_FILEPATH_PATTERN)

    # Check if subtitle exist, if yes delete
    if os.path.exists(subtitle_filepath):
        os.remove(subtitle_filepath)
        logger_.info(f'Subtitle deleted: {subtitle_filepath}.')
    
def upgrade_subtitle():
    logger_.info(f'Upgrade action.')
    delete_subtitle()
    download_subtitle('Upgrade')

def notify_download_subtitle_discord(sonarr_episodefile_path, sonarr_episodefile_seasonnumber, sonarr_episodefile_episodenumbers, release_absolute_episode_numbers):
    if WEBHOOK_DISCORD == "" or WEBHOOK_DISCORD == -1:
        return
    
    # Construct the request parameters and headers
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Python HTTP Client',
    }

    body = {
        "username": "Subtitle-Manager",
        "embeds": [
            {
                "title": "**Subtitle Grabbed**",
                "color": 65280,
                "fields": [
                    {
                        "name": "Title",
                        "value": sonarr_episodefile_path.split('/')[-1].split('[')[0].strip(),
                        "inline": False
                    },
                    {
                        "name": "Season",
                        "value": sonarr_episodefile_seasonnumber,
                        "inline": True
                    },   
                    {
                        "name": "Episode",
                        "value": sonarr_episodefile_episodenumbers,
                        "inline": True
                    },                                                
                    {
                        "name": "Absolute Episode",
                        "value": release_absolute_episode_numbers,
                        "inline": False
                    }          
                ]
            }
        ]
    }

    try:
        # Establish a connection to the OpenSubtitles API server
        conn = http.client.HTTPSConnection('discord.com')

        # Send the GET request
        conn.request('POST', WEBHOOK_DISCORD, body = json.dumps(body), headers=headers)

        # Get the response from the server
        response = conn.getresponse()

        # Check if the request was successful (status code 200)
        if response.status == 200 or response.status == 204:
            return
        
        # Check if need to redirect the request
        elif response.status == 301:
            # Get new location and redirect a new request
            redirect_location = response.getheader('Location')
            conn.close()

            conn = http.client.HTTPSConnection('api.opensubtitles.com')
            conn.request('POST', redirect_location, headers=headers)
        else:
            logger_.error(f"Notify Discord, request failed with status code: {response.status}")
        # Close the connection
        conn.close()

    except Exception as e:
        logger_.error(f"An error occurred: {e}")

    return   

if __name__ == "__main__":
    try:
        read_arguments(EXECUTION_TYPE)

        if envs['sonarr_eventtype'] == 'Download':

            # Dependent variables
            try:
                # If has absolute episode number
                RELEASE_ABSOLUTE_EPISODE_NUMBERS = int(re.search(r'- (\d{3}) -', envs['sonarr_episodefile_path']).group(1).replace('-', '').strip())
            except Exception as e:
                 # If does not has absolute episode number
                 RELEASE_ABSOLUTE_EPISODE_NUMBERS = -1

            TV_SHOW_YEAR = re.search(r'\((\d{4})\)', envs['sonarr_series_path']).group(1)
            envs['sonarr_series_title'] = urllib.parse.quote(envs['sonarr_series_title'])

            logger_.info(f"*"*100)
            logger_.info(f"Variables from sonarr:")
            logger_.info(f"envs['sonarr_eventtype']: {envs['sonarr_eventtype']}")
            logger_.info(f"envs['sonarr_series_imdbid']: {envs['sonarr_series_imdbid']}")
            logger_.info(f"envs['sonarr_series_type']: {envs['sonarr_series_type']}")
            logger_.info(f"envs['sonarr_episodefile_seasonnumber']: {envs['sonarr_episodefile_seasonnumber']}")
            logger_.info(f"envs['sonarr_episodefile_episodenumbers']: {envs['sonarr_episodefile_episodenumbers']}")
            logger_.info(f"envs['SONARR_RELEASE_ABSOLUTE_EPISODE_NUMBERS']: {RELEASE_ABSOLUTE_EPISODE_NUMBERS}")
            logger_.info(f"envs['sonarr_isupgrade']: {envs['sonarr_isupgrade']}")
            logger_.info(f"envs['sonarr_series_path']: {envs['sonarr_series_path']}")
            logger_.info(f"envs['sonarr_episodefile_path']: {envs['sonarr_episodefile_path']}")
            logger_.info(f"TV_SHOW_YEAR: {TV_SHOW_YEAR}")
            logger_.info(f"envs['sonarr_series_title']: {envs['sonarr_series_title']}")
            logger_.info(f"*"*100)

        # Just will execute if the event is Download
        if envs['sonarr_eventtype'] == 'Download' and envs['sonarr_isupgrade'] == 'False':
            download_subtitle('Download')
        elif envs['sonarr_eventtype'] == 'Download' and envs['sonarr_isupgrade'] == 'True':
            upgrade_subtitle()
        elif envs['sonarr_eventtype'] == 'EpisodeFileDelete':
            delete_subtitle()    
        elif envs['sonarr_eventtype'] == 'Test':
            logger_.info(f'Subtitle manager script recognized!')

    except Exception as e:
        logger_.error(f"An general error occurred: {e}")