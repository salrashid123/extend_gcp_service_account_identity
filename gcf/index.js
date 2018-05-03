'use strict';
const {auth} = require('google-auth-library');
var google = require('googleapis');

var http = require('http');
var express = require('express')
var log4js = require("log4js");
var rp = require('request-promise');
var logger = log4js.getLogger();


const IMPERSONATED_SVC_ACCOUNT = 'impersonated-account@fabled-ray-104117.iam.gserviceaccount.com';
const EXTRA_SCOPES = 'https://www.googleapis.com/auth/books https://www.googleapis.com/auth/userinfo.email';

function getAccessToken(callback) {

  auth.getApplicationDefault(function(err, authClient) {
    if (err) {
      logger.error(err);
      callback(err, null);
      return;
    }
    if (authClient.createScopedRequired && authClient.createScopedRequired()) {
      const iam_scopes = ['https://www.googleapis.com/auth/iam https://www.googleapis.com/auth/cloud-platform']
      authClient = authClient.createScoped(iam_scopes);
    }      
    const iat = Math.floor(new Date().getTime() / 1000);
    const exp = iat + 3600;    
    var claims = {
      iss: IMPERSONATED_SVC_ACCOUNT,
      aud: "https://accounts.google.com/o/oauth2/token",
      exp: exp,
      iat: iat,
      scope: EXTRA_SCOPES
    };

    var data = { 'payload': JSON.stringify(claims) };
    var iam_path = 'projects/' + process.env.GCLOUD_PROJECT + '/serviceAccounts/' + IMPERSONATED_SVC_ACCOUNT;
    var signjwt_endpoint = 'https://iam.googleapis.com/v1/' + iam_path + ':signJwt';

    authClient.request( { 
        url: signjwt_endpoint, 
        method: 'POST', 
        headers: {
          'content-type': 'application/json',
        },        
        data } ).then(response => { 
          logger.info(response);
          var signed_jwt = response.data.signedJwt;
          var cdata = {
                  'grant_type' : 'assertion',
                  'assertion_type' : 'http://oauth.net/grant_type/jwt/1.0/bearer',
                  'assertion' : signed_jwt 
          };
          rp( {
              url: 'https://accounts.google.com/o/oauth2/token', 
              method: 'POST',            
              headers: { 'Content-Type': 'application/x-www-form-urlencoded'},
              formData: cdata
            })
            .then(function (rr) {
              var token_struct = JSON.parse(rr);
              logger.debug(token_struct);

              rp( {
                url: "https://www.googleapis.com/oauth2/v2/tokeninfo?access_token=" + token_struct.access_token,
                method:"GET"
              }).then(function (trresponse) {  
                callback(null, JSON.parse(trresponse));
              }).catch(function (trerror) {
                callback(trerror, null);
              });
            })
            .catch(function (err2) {
              logger.error(err2.message);
              callback(err2.message, null);
            });
        })
        .catch(error => {
            logger.error(error.message);
            callback(error.response.data, null);
        });      
  });
}


exports.imp = (req, res) => {

    var logger = log4js.getLogger();
    
    getAccessToken(function(err, result)  {
      if (err) {
        res.status(500).send(err);
      } else {
        res.status(200).send(result);
      }
    });


};
