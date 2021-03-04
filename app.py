###############################################################################
# IBM Cloud Discovery service Knowledge Graph visualizer
# -----------------------------------------------------------------------------
# This app parses and generattes knowledge graphs from enriched data
# (currently "entities") from Discovery service query responses.
#
# /keyword request should follow format:
#   http:localhost:8000/keyword?keyword=Dennis J. Reimer&sessionId=coolcat&team=pink
###############################################################################

import requests
import sys
import os
from os.path import join, dirname
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, json, jsonify
from dotenv import load_dotenv
from datetime import datetime
import random
from urllib3.exceptions import InsecureRequestWarning
from waitress import serve


# Suppress only the single warning from urllib3 needed.
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


app = Flask(__name__)
app.secret_key = "wabbits wuv carrots"


try:
    env_file = open(join(dirname(__file__), '.env')) # Check for .env file
    if not env_file:
        raise FileNotFoundError
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)
except FileNotFoundError:
    print('missing .env file. Program will NOT be able to communicate with IBM Watson Discovery service. Stopping execution. Please see README.md')
    exit()


# Default environmental variables
APIKEY = os.getenv('APIKEY')
URL = os.getenv('URL')
COLLECTION_ID = os.getenv('COLLECTION_ID')
ENVIRONMENT_ID = os.getenv('ENVIRONMENT_ID')
VERSION = '2019-04-30'


WCP_URL = ''
if 'VCAP_APPLICATION' in os.environ:
    WCP_URL = 'https://169.62.25.66:8081/api/top_entities' # prod
else:
    WCP_URL = 'http://localhost:8081/api/top_entities' # dev


colorsTheme = ['#4076AF', '#E08445', '#669E40', '#9675BE', '#CC584E'] # WCP UI theme colors
# colors = list(colorsTheme)
entTypes = [{"name": "Person"}, {"name": "Organization"}, {"name": "Location"}] # Entity types able to filter via the dropdown


# Create a user session
def createSession(data, dev):

    global APIKEY, COLLECTION_ID, ENVIRONMENT_ID, URL, VERSION, WCP_URL

    session['created'] = True
    session['date'] = str(datetime.utcnow()) + ' UTC'


    # Set defaults
    session['APIKEY'] = APIKEY
    session['COLLECTION_ID'] = COLLECTION_ID
    session['ENVIRONMENT_ID'] = ENVIRONMENT_ID
    session['URL'] = URL
    session['WCP_URL'] = WCP_URL
    session['VERSION'] = VERSION


    if data.get('APIKEY'):
        session['APIKEY'] = data['APIKEY']
    if data.get('COLLECTION_ID'):
        session['COLLECTION_ID'] = data['COLLECTION_ID']
    if data.get('ENVIRONMENT_ID'):
        session['ENVIRONMENT_ID'] = data['ENVIRONMENT_ID']
    # if data.get('URL'):
    #     session['URL'] = data['URL']


    session['about'] = {} # Bundle session info
    session['about']['date'] = session['date']

    # For dev
    if dev is True:
        session['sessionId'] = 'dev'
        session['team'] = 'team dev'
        # session['COLLECTION_ID'] = COLLECTION_ID
        # session['ENVIRONMENT_ID'] = ENVIRONMENT_ID
        session['about']['sessionId'] = 'dev'
        session['about']['team'] = 'team dev'
        session['about']['COLLECTION_ID'] = session['COLLECTION_ID']
    # For prod
    else:
        session['sessionId'] = data['sessionId']
        session['team'] = data['team']
        session['about']['sessionId'] = data['sessionId']
        session['about']['team'] = data['team']
        session['about']['COLLECTION_ID'] = session['COLLECTION_ID']

    return

# 1st step - Initialization of KG from WCP
# @app.route('/setConnection', methods=['POST'])
def setConnection(data):

    # { sessionId: '5d851071271334c18d4889ee', team: 'blue' }

    # global APIKEY, COLLECTION_ID, ENVIRONMENT_ID, URL, WCP_URL

    output = {}
    output['api'] = '/setConnection'
    session['created'] = False

    try:
        # data = request.get_json(force=True)
        # print("data in setConnection is", data)

        if not 'sessionId' in data:
            print('sessionId not in data')
        if not 'team' in data:
            print('team not in data')

        # If params are completely missing from request
        # if not 'sessionId' in data or not 'team' in data or not 'collection' in data:
        if not 'sessionId' in data or not 'team' in data:
            raise KeyError

        # If params are included in request but have no values
        # if not data['sessionId'] or not data['team'] or not data['collection']:
        if not data['sessionId'] or not data['team']:
            raise ValueError

        # params = {}
        # params['sessionId'] = data['sessionId']
        # params['team'] = data['team']
        # createSession(params, False)

        createSession(data, False)
        print("createSession() session = ", session) # dev
        session['created'] = True

        # (Optional) set collection_id, etc. Otherwise, set defaults.
        # colData = data.get('collection')
        if data.get('APIKEY'):
            session['APIKEY'] = data['APIKEY']
            #print(data['APIKEY'])
        if data.get('COLLECTION_ID'):
            session['COLLECTION_ID'] = data['COLLECTION_ID']
            #print(data['COLLECTION_ID'])
        if data.get('ENVIRONMENT_ID'):
            session['ENVIRONMENT_ID'] = data['ENVIRONMENT_ID']
            #print(data['ENVIRONMENT_ID'])
        if data.get('URL'):
            session['URL'] = data['URL']
            #print(data['URL'])

        output['date'] = str(datetime.utcnow()) + ' UTC'
        output['status'] = 'OK'
        output['message'] = 'Session created and collection information updated'
        print('setConnection() output = ' + json.dumps(output, indent=2)) # dev
        return

    except KeyError:
        output['date'] = str(datetime.utcnow()) + ' UTC'
        output['status'] = 'Error'
        output['message'] = 'ensure your request body is formatted like { sessionId: YOUR_SESSION_ID, team: YOUR_TEAM_NAME, collection: COLLECTION }'
        # return jsonify(output)
        print('setConnection() output = ' + json.dumps(output, indent=2)) # dev
        # return output

    except ValueError:
        output['date'] = str(datetime.utcnow()) + ' UTC'
        output['status'] = 'Error'
        output['message'] = '1 or more of your values is blank'
        print('setConnection() output = ' + json.dumps(output, indent=2)) # dev

    except Exception as e: # Catch all other errors
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        output['date'] = str(datetime.utcnow()) + ' UTC'
        output['error'] = str(exc_type)+' '+str(fname)+' '+str(exc_tb.tb_lineno)
        output['message'] = 'error setting collection'
        output['status'] = 'Error'
        print('setConnection() output = ' + json.dumps(output, indent=2)) # dev


    # return jsonify(output)
    return


# Upon Discovery service query response, call WCP new top entity IDs, etc.
# def topEntities(url, payload):
def topEntities(data):

    global WCP_URL

    # print("top_entities session collection_id", session['COLLECTION_ID'])
    # print("top_entities session session_id", session['sessionId'])

    # Extract top query response IDs
    i = 0
    numTop = 3 # Number of top scored entities to POST
    payload = {}
    payload['passages'] = []

    try:
        if data.get('passages'):
            while i < numTop:
                passage = {}
                passage['document_id'] = data['passages'][i]['document_id']
                passage['passage_text'] = data['passages'][i]['passage_text']
                payload['passages'].append(passage)
                i += 1

        payload['COLLECTION_ID'] = session['COLLECTION_ID']
        payload['entities'] = session['entities']
        payload['ENVIRONMENT_ID'] = session['ENVIRONMENT_ID']
        payload['entityTypes'] = session['entityTypes']
        payload['SESSION_ID'] = session['sessionId']
        payload['TEAM'] = session['team']

        # print('topEntities() payload = ' + json.dumps(payload, indent=2)) # dev

        # Todo: send message to front-end
        try:
            results = requests.post(url=WCP_URL, json=payload, verify=False)
            response = results.json()
            # print('topEntities() response = ' + json.dumps(response, indent=2)) # dev
        except requests.exceptions.RequestException as e:
            print(e)
            # output['message'] = 'Unable to send top entities. Is receipient server offline?'



        # except KeyError:
        # output['date'] = str(datetime.utcnow()) + ' UTC'
        # output['status'] = 'Error'
        # output['message'] = 'ensure your request body is formatted like { sessionId: YOUR_SESSION_ID, team: YOUR_TEAM_NAME, collection: COLLECTION }'
        # # return jsonify(output)
        # print('setConnection() output = ' + json.dumps(output, indent=2)) # dev
        # # return output


        # /keyword session['created'] = True
        # /keyword session['about'] = {"date": "2019-10-04 16:27:25.588914 UTC", "sessionId": "5d8916ba1994e6e5d23033f7", "team": "blue"}
        # <class 'requests.exceptions.ConnectionError'> app.py 206
        # <class 'UnboundLocalError'> app.py 736
        # <class 'KeyError'> app.py 743


        # 2019-10-03T15:00:08.72-0400 [APP/PROC/WEB/2] ERR /home/vcap/deps/0/python/lib/python3.5/site-packages/urllib3/connectionpool.py:1004: InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
        # 2019-10-03T15:00:08.72-0400 [APP/PROC/WEB/2] ERR   InsecureRequestWarning,
        # 2019-10-03T15:00:08.76-0400 [APP/PROC/WEB/2] OUT <class 'json.decoder.JSONDecodeError'> app.py 203
        # 2019-10-03T15:00:08.76-0400 [APP/PROC/WEB/2] OUT <class 'UnboundLocalError'> app.py 492

    except Exception as e:
        # print("Exception = ", e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

    return response



# Interacts with dropdown menu
@app.route('/setType', methods=['POST'])
def setType():

    # data = request.get_json(force=True)
    output = {}
    output['api'] = '/setType'


    # print("setType session collection_id", session['COLLECTION_ID'])
    # print("setType session session_id", session['sessionId'])
    # Must check if session exists
    # if not session['session']:
    # if session['session'] is False:
    if not 'created' in session or session['created'] is False:
        output['status'] = 'Error'
        output['message'] = 'Session does not exists. Please visit API /setConnection to create session.'
        return jsonify(output)

    try:
        data = request.get_json(force=True)
        entityTypes = []
        session['entityFilter'] = ''
        session['entityTypes'] = entityTypes

        if data.get('entityTypes'):
            entityFilter = ''

            entityTypes = data['entityTypes']
            session['entityTypes'] = entityTypes

            # Assemble "filter"
            # Filter should have the following form: ".filter(enriched_text.entities.type:"Person",enriched_text.entities.type:"Organization")"
            # condition = ',' # The query "is" all of the entitie type(s)
            condition = '|' # The query "contains" any of the entitie type(s)
            # entityFilter = ''
            filters = ''
            operator = ':' # The rule must "contain" the entity value
            uiMsg = '' # Message to the UI
            for idx, entityType in enumerate(entityTypes):
                filters += 'enriched_text.entities.text'+operator+'"'+entityType+'"'
                uiMsg += entityType
                if idx < len(entityTypes) - 1:
                    filters += condition
                    uiMsg += ', '
            # print('filters = ' + filters) # dev

            if filters:
                entityFilter = '.filter('+filters+')'
                session['entityFilter'] = entityFilter

            # print("/setType entityFilter  = " + entityFilter) # dev


        # print("/setType request entityTypes = " + ', '.join(entityTypes)) # dev

        output['status'] = 'OK'
        if not entityTypes:
            # clientMsg['message'] = 'entityTypes cleared'
            output['message'] = 'entityTypes cleared'
            output['uiMsg'] = 'Entity types cleared'
        else:
            # clientMsg['message'] = 'entityTypes set'
            output['message'] = 'entityTypes set'
            output['uiMsg'] = 'Entity types set to ' + uiMsg

        output['entities'] = session['entities'] # dev
        output['entityTypes'] = session['entityTypes'] # dev
        output['session'] = session['about'] # dev


    except Exception as e:
        # print("Exception = ", e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        # clientMsg['message'] = 'error in /setType API'
        # clientMsg['status'] = 'failure'
        output['error'] = str(exc_type)+' '+str(fname)+' '+str(exc_tb.tb_lineno)
        output['message'] = 'error in /setType API'
        output['status'] = 'Error'

    # print("/setType response output  = " + json.dumps(output)) # dev

    return jsonify(output)



# Assemble 1 or more entity types for query filter
# Unused
def assembleFilter(data):

    try:
        # Assemble "filter"
        condition = ',' # The query "is" all of the entities
        filters = ''
        operator = ':' # The rule must "contain" the entity value
        for idx, entityType in enumerate(data):
          filters += 'enriched_text.entities.text'+operator+'"'+entityType+'"'
          if idx < len(entityTypes) - 1:
            filters += condition
        print('filters = ' + filters) # dev

    except Exception as e:
        # print("Exception = ", e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

    return filters


@app.route('/setCollection', methods=['POST'])
def setCollection():
    output = {}
    output['status'] = 'Error'
    output['message'] = '/setCollection is deprecated'
    return jsonify(output)


# Unused for WCP
@app.route('/viewvHeadline', methods=['POST'])
def viewvHeadline():
    id = request.json['id']
    version = '2018-12-03'

    try:
        query_url = URL+'/v1/environments/'+ENVIRONMENT_ID+'/collections/'+COLLECTION_ID+'/query?query=id::'+id+'&version='+version
        # results = requests.get(url=query_url, auth=(username, password))
        results = requests.get(url=query_url, auth=('apikey', APIKEY))
        response = results.json()
        # print(json.dumps(response, indent=2)) # dev

    except Exception as e:
        print("Exception = ",e)

    output = { 'response': response }
    return jsonify(output)


# Unused for WCP
@app.route('/newHeadlines', methods=['POST'])
def newHeadlines():
    combo = request.json['combo']
    comboWords=combo.replace("\"","").split('|')

    combos=[]
    headlines={}
    version = '2018-12-03'

    try:
        query_url = URL+'/v1/environments/'+ENVIRONMENT_ID+'/collections/'+COLLECTION_ID+'/query?deduplicate=false&highlight=true&passages=true&passages.count=5&query=enriched_text.entities.text:'+combo+'&return=text&version='+version
        # results = requests.get(url=query_url, auth=(username, password))
        results = requests.get(url=query_url, auth=('apikey', APIKEY))
        response = results.json()
        # print(json.dumps(response, indent=2)) # dev

        for article in response['results']:
            text_full=article['text']
            # text_clip=text_full[:80]
            text_clip=text_full[:160]
            combos[:]=[]
            for word in comboWords:
                if word.upper() in article['text'].upper():
                    combos.append(word)
            comboStr = ''.join(sorted(combos))
            comboLen = len(combos)
            if comboLen not in headlines:
                headlines[comboLen]={}
            if comboStr not in headlines[comboLen]:
                headlines[comboLen][comboStr]={}
            headlines[comboLen][comboStr][text_clip]=article['id']

    except Exception as e:
        print("Exception = ",e)

    output = { 'headlines': headlines }
    return jsonify(output)



@app.route('/click', methods=['GET', 'POST'])
def click():

    clientMsg = {}
    clientMsg['api'] = '/click'
    output = {}
    # Must check if session exists
    # if session['session'] is False:
    if not 'created' in session or session['created'] is False:
        output['status'] = 'Error'
        output['message'] = 'Session does not exists. Please visit API /setConnection to create session.'
        return jsonify(output)

    nodes=request.json['nodes']
    links=request.json['links']
    bigWords=request.json['bigWords']
    index=request.json['current']

    # print('/click nodes request = ' + json.dumps(nodes, indent=2)) # dev
    # print('/click links request = ' + json.dumps(links, indent=2)) # dev
    # print('/click bigWords request = ' + json.dumps(bigWords, indent=2)) # dev
    # print('/click index/click request = ' + json.dumps(index, indent=2)) # dev

    x = nodes[index]['x']
    y = nodes[index]['y']
    text = nodes[index]['text']
    # print('/click text = ' + text) # dev
    entities = session['entities']

    entities.append(text)
    # session['entities'].append(text)
    # print('/click updated entities = ' + json.dumps(entities, indent=2)) # dev

    # previousEntities = [text]
    # entities.append(text)

    numRelations = 2 # Show relationships between the last 'n' # of entities
    while len(entities) > numRelations:
        entities.reverse();
        entities.pop();
        entities.reverse();
    # print("entities after trim = " + json.dumps(entities, indent=2)) # dev

    session['entities'] = entities
    clientMsg['entities'] = entities

    # print('/click final entities = ' + json.dumps(session['entities'], indent=2)) # dev

    length = len(nodes)
    words={}
    headlines={}
    combo=""
    comboWords=[]
    combos=[]
    for node in nodes:
        words[node['text']] = node['index']
        if node['expand'] == 1:
            comboWords.append(node['text'])
    for word in comboWords:
        combo+="\""+word+"\"|"
    combo=combo[:-1]

    # print('combo = ' + json.dumps(combo, indent=2)) # dev
    # print('comboWords = ' + json.dumps(comboWords, indent=2)) # dev

    # Assemble "query"
    # entityType = 'Person' # dev
    # condition = ',' # The query "is" all of the entities # dev
    condition = '|' # The query "contains" any of the entities # prod
    operator = ':' # The rule must "contain" the entity value
    # operator = '::' # The rule "is" the entity value
    query = ''
    for idx, word in enumerate(comboWords):
      # query += 'enriched_text.entities.text::"'+word+'"'
      query += 'enriched_text.entities.text'+operator+'"'+word+'"'
      if idx < len(comboWords) - 1:
        # query += '|'
        query += condition
    # print('/click query = ' + query) # dev


    try:
        # version = '2018-12-03'
        # query_url = URL+'/v1/environments/'+ENVIRONMENT_ID+'/collections/'+COLLECTION_ID+'/query?deduplicate=false&highlight=true&passages=true&passages.count=5&query=enriched_text.entities.text:'+combo+'&return=text&version='+version

        # Filter on 1 or more entity types
        query_url = session['URL']+'/v1/environments/'+session['ENVIRONMENT_ID']+'/collections/'+session['COLLECTION_ID']+'/query?version='+session['VERSION']+'&aggregation=nested(enriched_text.entities)'+session['entityFilter']+'.term(enriched_text.entities.text,count:10)&deduplicate=false&highlight=true&passages=true&passages.count=5&query='+query
        # print('/click query_url = ' + json.dumps(query_url, indent=2)) # dev

        # results = requests.get(url=query_url, auth=(username, password))
        results = requests.get(url=query_url, auth=('apikey', session['APIKEY']))
        response = results.json()
        # print('/click response = ' + json.dumps(response, indent=2)) # dev

        try:
            wcpResponse = topEntities(response) # Make call to WCP with top query response IDs
            # print('/click topEntities() wcpResponse = ' + json.dumps(wcpResponse, indent=2)) # dev
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)


        for article in response['results']:
            text_full=article['text']
            # text_clip=text_full[:80]
            text_clip=text_full[:160]
            combos[:]=[]
            for word in comboWords:
                if word.upper() in article['text'].upper():
                    combos.append(word)
            comboStr = ''.join(sorted(combos))
            comboLen = len(combos)
            if comboLen not in headlines:
                headlines[comboLen]={}
            if comboStr not in headlines[comboLen]:
                headlines[comboLen][comboStr]={}
            headlines[comboLen][comboStr][text_clip]=article['id']

    except Exception as e:
        # print("Exception = ", e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        clientMsg['error'] = str(exc_type)+' '+str(fname)+' '+str(exc_tb.tb_lineno)
        clientMsg['message'] = 'error in /click API'
        clientMsg['status'] = 'failure'

    output = { 'results': { 'nodes': [], 'links': [], 'headlines': headlines, 'combo': combo } }

    try:

        # Add to bigWords
        wordList = []
        # for kword in response['aggregations'][0]['results']:
        if session['entityFilter']:
            # Check if query returned sub-entities
            # print("/click session['entityFilter'] = " + json.dumps(session['entityFilter'], indent=2)) # dev

            if not response['aggregations'][0]['aggregations'][0]['aggregations'][0]['results']:
                # print('query returned no sub-entities') # dev
                # resultsMsg['message'] = 'Query returned no related sub-entities. Try clicking another entity'
                clientMsg['uiMsg'] = 'Query returned no related sub-entities. Try clicking another entity'

            for kword in response['aggregations'][0]['aggregations'][0]['aggregations'][0]['results']:
                wordList.append(kword['key'])
            # print('/click wordList = ' + json.dumps(wordList, indent=2)) # dev
        else:
            # Check if query returned sub-entities
            if not response['aggregations'][0]['aggregations'][0]['results']:
                # print('query returned no sub-entities') # dev
                # resultsMsg['message'] = 'Query returned no related sub-entities. Try clicking another entity'
                clientMsg['uiMsg'] = 'Query returned no related sub-entities. Try clicking another entity'
            for kword in response['aggregations'][0]['aggregations'][0]['results']:
                wordList.append(kword['key'])
            # print('/click wordList = ' + json.dumps(wordList, indent=2)) # dev
        bigWords[text]={'wordList':wordList,'expand':1}
        output['results']['bigWords']=bigWords
        count1=0
        count2=0

        # print('/click wordList = ' + json.dumps(wordList, indent=2)) # dev

        # print('Beginning loop /click') # dev
        for newWord in bigWords[text]['wordList']:
            if newWord in words:
                output['results']['links'].append({'source':index,'target':words[newWord]})
                # print('if newWord in words') # dev
                # print("output['results']['links'] = " + json.dumps(output['results']['links'], indent=2)) # dev
                continue
                # print('/click output["results"]["links"] if newWord in words = ' + json.dumps(output['results']['links'], indent=2)) # dev
            if count2 < 5:
                for bigWord in bigWords:
                    if bigWords[bigWord]['expand']==0:
                        # print("if bigWords[bigWord]['expand']==0") # dev
                        continue
                    if bigWord == text:
                        # print("if bigWord == text") # dev
                        continue
                    if newWord in bigWords[bigWord]['wordList']:
                        if newWord not in words:

                            # print("newWord = " + json.dumps(newWord, indent=2)) # dev
                            # print("words = " + json.dumps(words, indent=2)) # dev

                            # output['results']['nodes'].append({'x': x, 'y': y, 'text': newWord, 'size': 1.5, 'color': 'white', 'expand': 0})
                            # output['results']['nodes'].append({'x': x, 'y': y, 'text': newWord, 'size': 1.5, 'color': '#212121', 'expand': 0})
                            output['results']['nodes'].append({'x': x, 'y': y, 'text': newWord, 'size': 0.75, 'color': '#212121', 'expand': 0})
                            # print("if newWord not in words") # dev
                            # print("output['results']['nodes'] = " + json.dumps(output['results']['nodes'], indent=2)) # dev
                            words[newWord]=length
                            length+=1
                            count2+=1
                        # print("newWord in bigWords[bigWord]['wordList']") # dev
                        output['results']['links'].append({'source':words[newWord],'target':words[bigWord]})
                        # print("output['results']['links'] = " + json.dumps(output['results']['links'], indent=2)) # dev
                        output['results']['links'].append({'source':words[newWord],'target':index})
                        # print("output['results']['links'] = " + json.dumps(output['results']['links'], indent=2)) # dev

                # print('/click output["results"]["links"] for bigWord in bigWords = ' + json.dumps(output['results']['links'], indent=2)) # dev

            if newWord not in words and count1 < 5:
                # output['results']['nodes'].append({'x': x, 'y': y, 'text': newWord, 'size': 1.5, 'color': 'white', 'expand': 0})
                # output['results']['nodes'].append({'x': x, 'y': y, 'text': newWord, 'size': 1.5, 'color': '#212121', 'expand': 0})
                output['results']['nodes'].append({'x': x, 'y': y, 'text': newWord, 'size': 0.75, 'color': '#212121', 'expand': 0})
                output['results']['links'].append({'source':length,'target':index})
                # print("output['results']['links'] = " + json.dumps(output['results']['links'], indent=2)) # dev
                length+=1
                count1+=1


        clientMsg['message'] = 'all good in the hood'
        clientMsg['status'] = 'OK'

    except Exception as e:
        # print("Exception = ", e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        clientMsg['error'] = str(exc_type)+' '+str(fname)+' '+str(exc_tb.tb_lineno)
        clientMsg['message'] = 'error in /click API'
        clientMsg['status'] = 'Error'

    clientMsg['session'] = session['about']
    # clientMsg['entityFilter'] = session['entityFilter']
    clientMsg['entityTypes'] = session['entityTypes']

    # print('/click output = ' + json.dumps(output, indent=2)) # dev
    # print('/click entities = ' + json.dumps(entities, indent=2)) # dev

    output['clientMsg'] = clientMsg

    return jsonify(output)




# @app.route('/keyword', methods=['GET'])
# @app.route('/keyword', methods=['GET', 'POST'])
# def news_page():
    # keyword = request.args.get('keyword')
# @app.route('/<keyword>')
# def news_page(keyword):
# @app.route('/keyword', methods=['POST', 'GET'])
@app.route('/keyword', methods=['GET'])
# @app.route('/keyword')
# def news_page():
def keyword_page():

    # Joyce E. Morrow
    # Malcolm Turnbull
    # Dennis J. Reimer

    global colorsTheme, entTypes

    # data = request.get_json(force=True)
    data = request.args.to_dict()
    keyword = data.get('keyword')
    print("data!: ",data)
    # print("/keyword request.args = ", request.args) # dev
    # print("/keyword request.args.keyword = ", request.args.get('keyword')) # dev
    print("/keyword data = " + json.dumps(data)) # dev

    setConnection(data) # Establish "session" and set collection for current user

    # For debugging to avoid /setCollection POST API
    # Including the work "dev" in a querystring will set sessionId, etc.
    # dev = request.args.get('dev')
    # if 'dev' in request.args:
    if not 'created' in session or session['created'] is False:
        print('session set to dev mode')
        # createSession({}, True)
        createSession({}, True)

    print("/keyword session['created'] = " + str(session['created'])) # dev
    print("/keyword session['about'] = " + json.dumps(session['about'])) # dev


    clientMsg = {}
    clientMsg['api'] = '/keyword'
    output = {}
    session['entityTypes'] = []

    colors = list(colorsTheme)
    color = random.choice(colors) # Color for initial entity
    index = colors.index(color)
    del colors[index]



    # Must check if session exists
    # if session['session'] is False:
    # if not 'created' in session or session['created'] is False:
    #     output['status'] = 'Error'
    #     output['message'] = 'Session does not exists. Please visit API /setConnection to create session.'
    #     return jsonify(output)


    bigWords={}
    index=0
    headlines={}
    headlines[1]={}
    headlines[1][keyword]={}
    links=[]
    nodes=[]

    session['entities'] = []
    session['entities'].append(keyword)
    clientMsg['entities'] = session['entities']
    clientMsg['entityTypes'] = []
    clientMsg['session'] = session['about']

    # print("/keyword session['entities'] = " + json.dumps(session['entities'])) # dev

    # Query options
    queryOperator = ':' # The rule must contain the entity value
    # queryOperator = '::' # The rule is the entity value

    try:
        # version = '2018-12-03'
        query_url = session['URL']+'/v1/environments/'+session['ENVIRONMENT_ID']+'/collections/'+session['COLLECTION_ID']+'/query?version='+session['VERSION']+'&aggregation=term(enriched_text.entities.text,count:10)&deduplicate=false&highlight=true&passages=true&passages.count=5&query=enriched_text.entities.text:"'+keyword+'"'

        # Prod
        results = requests.get(url=query_url, auth=('apikey', session['APIKEY'])) # prod
        response = results.json() # prod

        # Dev
        # with open('response_keyword.json') as json_file: # dev
        #     response = json.load(json_file)

        try:
            wcpResponse = topEntities(response) # Make call to WCP with top query response IDs
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

        # Check if query returned sub-entities
        if not response['aggregations'][0]['results']:
            print('/keyword query returned no sub-entities') # dev
            clientMsg['uiMsg'] = 'Query returned no entities. Try querying another entity'

        # Original
        # for article in response['results']:
        #     text_full=article['text']
        #     # text_clip=text_full[:80]
        #     text_clip=text_full[:160]
        #     headlines[1][keyword][text_clip]=article['id']

        # New
        for article in response['results']:
            text_full=article['highlight']['text'][0]
            # print('text_full 1 = ' + json.dumps(text_full, indent=2)) # dev
            # text_clip=text_full[:80]
            text_clip=text_full[:160]
            # print('text_clip 1 = ' + json.dumps(text_clip, indent=2)) # dev
            headlines[1][keyword][text_clip]=article['id']

        wordList = []
        # for kword in response['aggregations'][0]['aggregations'][0]['aggregations'][0]['results']:
        for kword in response['aggregations'][0]['results']:
            # print("/keyword kword['key'] = " + json.dumps(kword['key'], indent=2)) # dev
            wordList.append(kword['key'])
        bigWords[keyword]={'wordList':wordList,'expand':1}

        # print("/keyword wordList = " + json.dumps(wordList, indent=2)) # dev
        # print("/keyword bigWords = " + json.dumps(bigWords, indent=2)) # dev

        count=0
        # The keyword entity
        # nodes.insert(0, {'x': 300, 'y': 200, 'text': keyword, 'size': 3, 'fixed': 1, 'color': '#0066FF', 'expand': 1})
        nodes.insert(0, {'x': 100, 'y': 100, 'text': keyword, 'size': 1.5, 'fixed': 1, 'color': color, 'expand': 1})
        # print("/keyword bigWords[keyword]['wordList'] = " + bigWords[keyword]['wordList']) # dev
        for word in bigWords[keyword]['wordList']:
            if count > 9:
                break
            if word == keyword:
                continue
            else:
                # The child nodes
                # nodes.append({'x': 300, 'y': 200, 'text': word, 'size': 1.5, 'color': 'white', 'expand': 0})
                nodes.append({'x': 100, 'y': 100, 'text': word, 'size': 0.75, 'color': '#212121', 'expand': 0})
                links.append({'source':count + 1,'target':0})
                count+=1

    except Exception as e:
        # print("Exception = ", e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        clientMsg['error'] = str(exc_type)+' '+str(fname)+' '+str(exc_tb.tb_lineno)
        clientMsg['message'] = 'error in /setType API'
        clientMsg['status'] = 'Error'

    # print("/keyword nodes = " + json.dumps(nodes, indent=2)) # dev
    # print("/keyword links = " + json.dumps(links, indent=2)) # dev
    # print("/keyword bigWords = " + json.dumps(bigWords, indent=2)) # dev
    # print("/keyword headlines = " + json.dumps(headlines, indent=2)) # dev
    # print("/keyword clientMsg = " + json.dumps(clientMsg, indent=2)) # dev

    return render_template('cloud.html', nodes=json.dumps(nodes), links=json.dumps(links), bigWords=json.dumps(bigWords), headlines=json.dumps(headlines), colors=colors, entTypes=entTypes, clientMsg=clientMsg)
    # return render_template('layout.html', nodes=json.dumps(nodes), links=json.dumps(links), bigWords=json.dumps(bigWords), headlines=json.dumps(headlines), colors=colors, entTypes=entTypes, clientMsg=clientMsg)




@app.route('/favicon.ico')
def favicon():
   return ""


@app.route('/')
def home():

    # font-family: "Roboto", "Helvetica", "Arial", sans-serif;


    # return "Enter a search term above to explore related entities using Watson Discovery" # prod
    return """
        <div style="font-family: 'Roboto', 'Helvetica', 'Arial', sans-serif; color: #212121;">Enter a search term above to explore related entities using Watson Discovery</div>
    """
    # return render_template('layout.html')




port = os.getenv('VCAP_APP_PORT', '8000')

if __name__ == '__main__':
  #  app.run(host='0.0.0.0', port=int(port), debug=True)
   serve(app, host='0.0.0.0', port=int(port))
	# app.run(host='0.0.0.0', port=int(port), debug=True, ssl_context=('certificate.pem', 'key.pem'))
