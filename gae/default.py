import logging
import os
import sys
import logging
import json
import time
import pprint
import traceback

from google.appengine.ext import webapp

from apiclient.discovery import build
import httplib2
from oauth2client.service_account import ServiceAccountCredentials
from oauth2client.client import AccessTokenCredentials
from oauth2client.client import GoogleCredentials

import urllib,urllib2, httplib
from urllib2 import URLError, HTTPError
import random

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

from google.auth import app_engine
from google.appengine.api import app_identity
from google.appengine.api import urlfetch

from datetime import datetime, timedelta

from flask import Flask, render_template, request, abort, Response

app = Flask(__name__)

EXTRA_SCOPES = 'https://www.googleapis.com/auth/books https://www.googleapis.com/auth/userinfo.email'
IMPERSONATED_SVC_ACCOUNT = 'impersonated-account@fabled-ray-104117.iam.gserviceaccount.com'

def getAccessToken():
  cc = GoogleCredentials.get_application_default()
  iam_scopes = 'https://www.googleapis.com/auth/iam https://www.googleapis.com/auth/cloud-platform'
  if cc.create_scoped_required():
    cc = cc.create_scoped(iam_scopes)
  http = cc.authorize(httplib2.Http())
  service = build(serviceName='iam', version= 'v1',http=http)
  resource = service.projects()   
  now = int(time.time())
  exptime = now + 3600
  claim =('{"iss":"%s",'
          '"scope":"%s",'
          '"aud":"https://accounts.google.com/o/oauth2/token",'
          '"exp":%s,'
          '"iat":%s}') %(IMPERSONATED_SVC_ACCOUNT,EXTRA_SCOPES,exptime,now)
  #      os.getenv('APPLICATION_ID')  return a prefix like s~ProjectID or w~ProjectID...so we'll remove that   
  slist = resource.serviceAccounts().signJwt(name='projects/' + os.getenv('APPLICATION_ID')[2:] + '/serviceAccounts/' + IMPERSONATED_SVC_ACCOUNT, body={'payload': claim })
  resp = slist.execute()   
  signed_jwt = resp['signedJwt'] 
  url = 'https://accounts.google.com/o/oauth2/token'
  data = {'grant_type' : 'assertion',
          'assertion_type' : 'http://oauth.net/grant_type/jwt/1.0/bearer',
          'assertion' : signed_jwt }
  headers = {"Content-type": "application/x-www-form-urlencoded"}
  
  data = urllib.urlencode(data)
  req = urllib2.Request(url, data, headers)

  try:
    resp = urllib2.urlopen(req).read()
    parsed = json.loads(resp)
    expires_in = parsed.get('expires_in')
    access_token = parsed.get('access_token')
    #logging.debug('access_token: ' + access_token)
    return access_token
  except HTTPError, e:
    logging.error('HTTPError on getting delegated access_token: ' + str(e.reason))
    logging.error(e.read())
    raise e
  except URLError, e:
    logging.error( 'URLError on getting delegated access_token: ' + str(e.reason))
    logging.error(e.read())
    raise e
  except Exception as e:
    logging.error(traceback.format_exc())    
    raise e



@app.route('/', methods=['GET'])   
def index():
  try:
    http = httplib2.Http()
    access_token = getAccessToken()
    credentials = AccessTokenCredentials(access_token,'my-user-agent/1.0')    
    http = httplib2.Http()
    http = credentials.authorize(http)
    service = build(serviceName='oauth2', version= 'v2',http=http)
    resp = service.userinfo().get().execute()
    email = resp['email']
    resp = service.tokeninfo(access_token=access_token).execute()    
    return Response(json.dumps(resp, sort_keys=True, indent=4), mimetype='application/json')
  except Exception as e:
    logging.error("Error: " + str(e))
    abort(500)


@app.errorhandler(500)
def server_error(e):
  logging.exception('An error occurred during a request.')
  return 'An internal error occurred.', 500
