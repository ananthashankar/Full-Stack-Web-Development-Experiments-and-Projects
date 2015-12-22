This project consists of a enhanced backend code to add a Session feature to the pre-designed Conference Central app that has been deployed to Google App Engine cloud  platform.

Technical Details: 

- Python Version: 2.7.10

Installation Help Link - https://docs.python.org/3/install/

- Google App Engine

- Google App Engine Datastore - https://developers.google.com/appengine/docs/python/endpoints/


SetUp:

 - Download Google App Engine Launcher, install it

 - Then open the launcher and go to File==> Add Existing Application

 - Select the downloaded project folder and set the Application ID as “conference-org-app”



- With app running in your browser you can go to the link http//localhost:portnumber to go to the home page

To test the app locally without login to google

- Go to link http//localhost:portnumber/_ah/api/explorer

- In the resulting console the api list will be displayed and by entering relevant values needed to test the api methods the results can be obtained.

To use the application with your own google account

 - Register to https://console.developers.google.com/
 - Create a application Id
 - Create a web client Id for the application 
 - Update the application Id in app.yaml
 - Update the client Ids to settings.py and static/js/app.js

Run your application locally once and then click on deploy in GAE launcher then goto below link to test the API methods in google cloud

https://apis-explorer.appspot.com/_ah/api/explorer

To review the logs and other information on the application check the developer console where the application was registered

========================================================

Project tasks related:

- Task 1:
 - Session and SessionForm has been implemented
 - All the date field has been set as ndb.dateProperty(), time field has been set as ndb.timeProperty() and enum fields have been set as enum field property
 - Speakers name are added as a String in Session’s speaker field and every speaker is added to its entity Speaker with saving name
 - Since we’re not using speaker’s details explicitly on any methods in the mentioned tasks only name has been added as a property to Session entity
 - webSafeSession is added only in sessionForm as it is only used in retrieving the Session
 - webConferenceKey has been added as a reference to each session with their respective conference
 - profile has been with wishList property to save all wishlist sessions with string property set to true to save only webSafeKey of the session

- Task 3:
 - The two additional queries that have been created are getSessionByTimeQuery and getSessionByTimeAndDurationQuery
  - getSessionByTimeQuery returns Sessions with greater startTime than given time
  - getSessionByTimeAndDurationQuery returns Sessions with greater startTime than given time and equal to given duration
  - Inequality parameters have been ordered first according to the Datastore rule
  - Corresponding indexes have been added to the index.yam file. Below are the indexes
————————————————————————
#index for session to filter based on typeOfSession and speaker

- kind: Session
  properties:
  - name: typeOfSession
  - name: speaker


#index for session to filter based on startTime and sessionName

- kind: Session
  properties:
  - name: startTime
  - name: sessionName 


#index for session to filter based on typeOfSession and startTime

- kind: Session
  properties:
  - name: typeOfSession
  - name: startTime
  - name: sessionName 

#index for session to filter based on duration, startTime and sessionName

- kind: Session
  properties:
  - name: duration
  - name: startTime
  - name: sessionName   
————————————————————

- Task 4:
 - For query problem task the problem is that the Session has to be filtered for less than 7 P.M condition and for non Workshop session condition which is not possible with standard approach as inequality filters cannot be applied for two fields
 - To resolve this there many ways few them are to use nab.OR option to choose non workshop sessions or using Session.IN to filter non workshop sessions or by retrieving the sessions first by applying filter on typeOfSession and then loop through the query result to eliminate the ones that has startTime greater than 7 P.M. One of these approaches has been implemented in the actual code in the project

