# Author: Aaron Topping

import requests
import re

from dotenv import load_dotenv
import os

load_dotenv('Client.env')   #Keeping my ID and Secret off public

CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')

my_region = 'us'            # This authorization will work for all except CN

# Locales
locales = [ "en_US" , "ko_KR" , "fr_FR" , "de_DE" , "zh_CN" , "es_ES" , "zh_TW" , "es_MX" , "ru_RU" , "pt_BR" , "it_IT" ]
regions = [ "us" , "eu" , "kr" , "tw" ]                                     # China not included due to problem with battle.net API end points
namespaces = [ "dynamic-" , "dynamic-classic-" , "dynamic-classic1x-" ]     # Normal , Progression Classic , Classic (SOD, HD, Era)
currentNamespace = namespaces[0]
count = 0       #totalRealmsCounter

# Request OAuth token
def get_oauth_token(client_id, client_secret , regionID):
    url = ''

    if regionID != 'cn':
        url = f'https://{regionID}.battle.net/oauth/token'
    else:
        url = 'https://www.battlenet.com.cn/oauth/token'

    auth = ( client_id , client_secret )
    data = { 'grant_type': 'client_credentials' }
    response = requests.post( url , auth=auth , data=data )
    response.raise_for_status()
    token = response.json()

    return token[ 'access_token' ]

# Request the list of realms
def fetch_realms( access_token , regionID , locale ):
    global currentNamespace
    url = ""

    if regionID != "cn":
        url = f'https://{regionID}.api.blizzard.com/data/wow/realm/index'
    else:
        url = "https://gateway.battlenet.com.cn/data/wow/realm/index"

    headers = {'Authorization': f'Bearer {access_token}'}
    params = { 'namespace': f'{currentNamespace}{regionID}' , 'locale': locale }
    response = requests.get ( url , headers=headers, params=params )
    response.raise_for_status()

    return response.json()['realms']

# Get the realm names parsed out and in an array
def getRealmNames ( listOfRealms ):
    global count
    result = []
    count += len(listOfRealms)

    print(f"TOTAL REALMS SO FAR: {count}" , end="\r")
    for realmData in listOfRealms:
        if realmIsValid ( realmData['name'] ):                                                  # No Warcraft Realm is > 2 words
            result.append("\"" + re.sub(r'\s*\(.*?\)', '', realmData['name']).strip()  + "\"")  # Need to surround as a string

    return result

# Validate the name
def realmIsValid ( realmName ):
    if not realmName:
        return False

    names = realmName.split()
    for i in range ( len ( names ) ):
        if len( names[i] ) > 2 and names[i].isupper() and names[i].isalpha():
            return False
    return True

# Build arrays with the names of all realms per region and per locale.
def build_realms_locale ( region ):
    localeRealms = []
    global token

    for i in range ( len(locales) ):
        realms = fetch_realms ( token , region , locales[i] )
        allRealms = getRealmNames ( realms )
        allRealms.sort()
        localeRealms.append ( allRealms )
        if i == len(locales)-1:
            print()

    return localeRealms

# Build the string to export to file
# Note, using 4 spaces instead of \t as python defaults to 8 spaces, which I don't like, on print.
def build_export_text():
    global currentNamespace
    global namespaces
    global regions
    global locales

    # Start with live retail servers
    export = '\nlocal Realms = {};\n'.format('{}')
    export += 'local initialized = false\n\n'
    export += '\n-- Only Initialize if ever needed. No need to pull into memory otherwise.'
    export += '\nlocal InitializeRealms = function()\n    initialized = true\n\n'

    for k in range ( len ( namespaces ) ):

        currentNamespace = namespaces[k]
        build = ""
        if k == 0:
            build = "RETAIL"
        elif k == 1:
            build = "CATA"
        elif k == 2:
            build = "CLASSICERA"
        print("Next Namespace: " , build )

        modifier = ""
        if k > 0:
            modifier = "else"

        export += f"    {modifier}if GRM.GameVersion() == \"{build}\" then\n\n"

        #Add the Regions
        for i in range( len( regions ) ):
            print(f'Region: {regions[i]}')
            export += f'        Realms.{ regions[i] } = {{}}\n'
            regionRealms = build_realms_locale ( regions[i] )
            # Add the locales to regions.
            for j in range ( len ( locales ) ):
                export += f'        Realms.{ regions[i] }.{ locales[j].replace ( "_" , "" ) } = {{\n            { ", ".join( regionRealms[j] ) }\n        }}\n'
            if i == len( regions ) -1:
                print()

        if k == len ( namespaces ) - 1:
            export += '    end\n\n'

    export += 'end\n\n'

    # Add a function in Lua format
    export += '-- Get List of all Realm Names\n'
    export += 'GRM.GetRealmNames = function()\n'
    export += '    if not initialized then\n        InitializeRealms()\n    end\n\n'
    export += '    local region = string.lower(GetCurrentRegionName())\n    if region == \"cn\" then\n        region = \"us\"\n    end\n\n'
    export += '    return Realms[region][GetLocale()]\nend'

    create_file ( "GRM_Realms.lua" , export )   # Let's create the file. This will overwrite any older ones

def create_file ( nameOfFile , output ):
    from datetime import datetime , timezone
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    with open ( nameOfFile , "w" , encoding="utf-8" ) as file:
        file.write ( f'-- Realms updated on: {timestamp} UTC\n')
        file.write ( f'-- Author: Aaron Topping (GenomeWhisperer) - Using custom written program WarcraftRealms.py\n\n')
        file.write(output)
        print(f'{nameOfFile} has been created. Please check folder.\n')

token = get_oauth_token ( CLIENT_ID , CLIENT_SECRET , my_region )    # Default authorization will be US Region




build_export_text()