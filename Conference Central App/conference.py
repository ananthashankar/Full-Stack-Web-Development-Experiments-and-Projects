#!/usr/bin/env python

"""
conference.py -- Udacity conference server-side Python App Engine API;
    uses Google Cloud Endpoints

$Id: conference.py,v 1.25 2014/05/24 23:42:19 wesc Exp wesc $

created by wesc on 2014 apr 21

"""

__author__ = 'wesc+api@google.com (Wesley Chun)'


from datetime import datetime
from time import localtime, strftime, mktime

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import StringMessage
from models import ConflictException
from models import Profile
from models import ProfileMiniForm
from models import ProfileForm
from models import BooleanMessage
from models import Conference
from models import ConferenceForm
from models import ConferenceForms
from models import ConferenceQueryForm
from models import ConferenceQueryForms
from models import TeeShirtSize
from models import TypeOfSession
from models import Session
from models import SessionForm
from models import SessionMiniForm
from models import SessionForms
from models import Speaker

from utils import getUserId

from settings import WEB_CLIENT_ID

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID
MEMCACHE_ANNOUNCEMENTS_KEY = "RECENT_ANNOUNCEMENTS"
MEMCACHE_FEATURED_SPEAKER_KEY = "FEATURED_SPEAKER"

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

DEFAULTS = {
    "city": "Default City",
    "maxAttendees": 0,
    "seatsAvailable": 0,
    "topics": [ "Default", "Topic" ],
}

DEFAULTS_SESSION = {
    "highlights": "No Highlights",
    "speaker": "Default Speaker",
    "duration": 1,
    "typeOfSession": TypeOfSession.NOT_SPECIFIED,
}

OPERATORS = {
            'EQ':   '=',
            'GT':   '>',
            'GTEQ': '>=',
            'LT':   '<',
            'LTEQ': '<=',
            'NE':   '!='
            }

FIELDS =    {
            'CITY': 'city',
            'TOPIC': 'topics',
            'MONTH': 'month',
            'MAX_ATTENDEES': 'maxAttendees',
            }

CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

CONF_POST_REQUEST = endpoints.ResourceContainer(
    ConferenceForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_POST_REQUEST = endpoints.ResourceContainer(
    SessionForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_GET_REQUEST_TYP = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
    typeOfSession=messages.StringField(2),
)

SESSION_GET_REQUEST_SPK = endpoints.ResourceContainer(
    message_types.VoidMessage,
    speaker=messages.StringField(1),
)

SESSION_ADD_WISHLIST_POST = endpoints.ResourceContainer(
    SessionForm,
    sessionKey=messages.StringField(1),
)

SESSION_GET_REQUEST_TYM = endpoints.ResourceContainer(
    message_types.VoidMessage,
    sessionTime=messages.StringField(1),
)

SESSION_GET_REQUEST_TYM_DUR = endpoints.ResourceContainer(
    message_types.VoidMessage,
    sessionTime=messages.StringField(1),
    duration=messages.IntegerField(2),
)

SESSION_DEL_WISHLIST_GET = endpoints.ResourceContainer(
    message_types.VoidMessage,
    sessionKey=messages.StringField(1),
)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


@endpoints.api(name='conference', version='v1', 
    allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID],
    scopes=[EMAIL_SCOPE])
class ConferenceApi(remote.Service):
    """Conference API v0.1"""

# - - - Conference objects - - - - - - - - - - - - - - - - -

    def _copyConferenceToForm(self, conf, displayName):
        """Copy relevant fields from Conference to ConferenceForm."""
        cf = ConferenceForm()
        for field in cf.all_fields():
            if hasattr(conf, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('Date'):
                    setattr(cf, field.name, str(getattr(conf, field.name)))
                else:
                    setattr(cf, field.name, getattr(conf, field.name))
            elif field.name == "websafeKey":
                setattr(cf, field.name, conf.key.urlsafe())
        if displayName:
            setattr(cf, 'organizerDisplayName', displayName)
        cf.check_initialized()
        return cf


    def _createConferenceObject(self, request):
        """Create or update Conference object, returning ConferenceForm/request."""
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        if not request.name:
            raise endpoints.BadRequestException("Conference 'name' field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}
        del data['websafeKey']
        del data['organizerDisplayName']

        # add default values for those missing (both data model & outbound Message)
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])

        # convert dates from strings to Date objects; set month based on start_date
        if data['startDate']:
            data['startDate'] = datetime.strptime(data['startDate'][:10], "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(data['endDate'][:10], "%Y-%m-%d").date()

        # set seatsAvailable to be same as maxAttendees on creation
        if data["maxAttendees"] > 0:
            data["seatsAvailable"] = data["maxAttendees"]
        # generate Profile Key based on user ID and Conference
        # ID based on Profile key get Conference key from ID
        p_key = ndb.Key(Profile, user_id)
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]
        c_key = ndb.Key(Conference, c_id, parent=p_key)
        data['key'] = c_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # create Conference, send email to organizer confirming
        # creation of Conference & return (modified) ConferenceForm
        Conference(**data).put()

        taskqueue.add(params={'email': user.email(),
            'conferenceInfo': repr(request)},
            url='/tasks/send_confirmation_email')

        return request


    @ndb.transactional()
    def _updateConferenceObject(self, request):
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}

        # update existing conference
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the conference.')

        # Not getting all the fields, so don't create a new object; just
        # copy relevant fields from ConferenceForm to Conference object
        for field in request.all_fields():
            data = getattr(request, field.name)
            # only copy fields where we get data
            if data not in (None, []):
                # special handling for dates (convert string to Date)
                if field.name in ('startDate', 'endDate'):
                    data = datetime.strptime(data, "%Y-%m-%d").date()
                    if field.name == 'startDate':
                        conf.month = data.month
                # write to Conference object
                setattr(conf, field.name, data)
        conf.put()
        prof = ndb.Key(Profile, user_id).get()
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))


    @endpoints.method(ConferenceForm, ConferenceForm, path='conference',
            http_method='POST', name='createConference')
    def createConference(self, request):
        """Create new conference."""
        return self._createConferenceObject(request)


    @endpoints.method(CONF_POST_REQUEST, ConferenceForm,
            path='conference/{websafeConferenceKey}',
            http_method='PUT', name='updateConference')
    def updateConference(self, request):
        """Update conference w/provided fields & return w/updated info."""
        return self._updateConferenceObject(request)


    @endpoints.method(CONF_GET_REQUEST, ConferenceForm,
            path='conference/{websafeConferenceKey}',
            http_method='GET', name='getConference')
    def getConference(self, request):
        """Return requested conference (by websafeConferenceKey)."""
        # get Conference object from request; bail if not found
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)
        prof = conf.key.parent().get()
        # return ConferenceForm
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))


    @endpoints.method(message_types.VoidMessage, ConferenceForms,
            path='getConferencesCreated',
            http_method='POST', name='getConferencesCreated')
    def getConferencesCreated(self, request):
        """Return conferences created by user."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id =  getUserId(user)
        # create ancestor query for all key matches for this user
        confs = Conference.query(ancestor=ndb.Key(Profile, user_id))
        prof = ndb.Key(Profile, user_id).get()
        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, getattr(prof, 'displayName')) for conf in confs]
        )


    def _getQuery(self, request):
        """Return formatted query from the submitted filters."""
        q = Conference.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Conference.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Conference.name)

        for filtr in filters:
            if filtr["field"] in ["month", "maxAttendees"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(filtr["field"], filtr["operator"], filtr["value"])
            q = q.filter(formatted_query)
        return q


    def _formatFilters(self, filters):
        """Parse, check validity and format user supplied filters."""
        formatted_filters = []
        inequality_field = None

        for f in filters:
            filtr = {field.name: getattr(f, field.name) for field in f.all_fields()}

            try:
                filtr["field"] = FIELDS[filtr["field"]]
                filtr["operator"] = OPERATORS[filtr["operator"]]
            except KeyError:
                raise endpoints.BadRequestException("Filter contains invalid field or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                # check if inequality operation has been used in previous filters
                # disallow the filter if inequality was performed on a different field before
                # track the field on which the inequality operation is performed
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException("Inequality filter is allowed on only one field.")
                else:
                    inequality_field = filtr["field"]

            formatted_filters.append(filtr)
        return (inequality_field, formatted_filters)


    @endpoints.method(ConferenceQueryForms, ConferenceForms,
            path='queryConferences',
            http_method='POST',
            name='queryConferences')
    def queryConferences(self, request):
        """Query for conferences."""
        conferences = self._getQuery(request)

        # need to fetch organiser displayName from profiles
        # get all keys and use get_multi for speed
        organisers = [(ndb.Key(Profile, conf.organizerUserId)) for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return individual ConferenceForm object per Conference
        return ConferenceForms(
                items=[self._copyConferenceToForm(conf, names[conf.organizerUserId]) for conf in \
                conferences]
        )


# - - - Profile objects - - - - - - - - - - - - - - - - - - -

    def _copyProfileToForm(self, prof):
        """Copy relevant fields from Profile to ProfileForm."""
        # copy relevant fields from Profile to ProfileForm
        pf = ProfileForm()
        for field in pf.all_fields():
            if hasattr(prof, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr(pf, field.name, getattr(TeeShirtSize, getattr(prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf


    def _getProfileFromUser(self):
        """Return user Profile from datastore, creating new one if non-existent."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get Profile from datastore
        user_id = getUserId(user)
        p_key = ndb.Key(Profile, user_id)
        profile = p_key.get()
        # create new Profile if not there
        if not profile:
            profile = Profile(
                key = p_key,
                displayName = user.nickname(),
                mainEmail= user.email(),
                teeShirtSize = str(TeeShirtSize.NOT_SPECIFIED),
            )
            profile.put()

        return profile      # return Profile


    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        prof = self._getProfileFromUser()

        # if saveProfile(), process user-modifyable fields
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
                        #if field == 'teeShirtSize':
                        #    setattr(prof, field, str(val).upper())
                        #else:
                        #    setattr(prof, field, val)
            prof.put()

        # return ProfileForm
        return self._copyProfileToForm(prof)


    @endpoints.method(message_types.VoidMessage, ProfileForm,
            path='profile', http_method='GET', name='getProfile')
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()


    @endpoints.method(ProfileMiniForm, ProfileForm,
            path='profile', http_method='POST', name='saveProfile')
    def saveProfile(self, request):
        """Update & return user profile."""
        return self._doProfile(request)


# - - - Registration - - - - - - - - - - - - - - - - - - - -

    @ndb.transactional(xg=True)
    def _conferenceRegistration(self, request, reg=True):
        """Register or unregister user for selected conference."""
        retval = None
        prof = self._getProfileFromUser() # get user Profile

        # check if conf exists given websafeConfKey
        # get conference; check that it exists
        wsck = request.websafeConferenceKey
        conf = ndb.Key(urlsafe=wsck).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)

        # register
        if reg:
            # check if user already registered otherwise add
            if wsck in prof.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            # check if seats avail
            if conf.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

            # register user, take away one seat
            prof.conferenceKeysToAttend.append(wsck)
            conf.seatsAvailable -= 1
            retval = True

        # unregister
        else:
            # check if user already registered
            if wsck in prof.conferenceKeysToAttend:

                # unregister user, add back one seat
                prof.conferenceKeysToAttend.remove(wsck)
                conf.seatsAvailable += 1
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()
        conf.put()
        return BooleanMessage(data=retval)


    @endpoints.method(message_types.VoidMessage, ConferenceForms,
            path='conferences/attending',
            http_method='GET', name='getConferencesToAttend')
    def getConferencesToAttend(self, request):
        """Get list of conferences that user has registered for."""
        prof = self._getProfileFromUser() # get user Profile
        conf_keys = [ndb.Key(urlsafe=wsck) for wsck in prof.conferenceKeysToAttend]
        conferences = ndb.get_multi(conf_keys)

        # get organizers
        organisers = [ndb.Key(Profile, conf.organizerUserId) for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(items=[self._copyConferenceToForm(conf, names[conf.organizerUserId])\
         for conf in conferences]
        )


    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
            path='conference/{websafeConferenceKey}',
            http_method='POST', name='registerForConference')
    def registerForConference(self, request):
        """Register user for selected conference."""
        return self._conferenceRegistration(request)


    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
            path='conference/{websafeConferenceKey}',
            http_method='DELETE', name='unregisterFromConference')
    def unregisterFromConference(self, request):
        """Unregister user for selected conference."""
        return self._conferenceRegistration(request, reg=False)


# - - - Session Objects - - - - - - - - - - - - - - - - - - - -
    
    def _copySessionToForm(self, session):
        """Copy relevant fields from Session to SessionMiniForm."""
        sf = SessionForm()
        for field in sf.all_fields():
            if hasattr(session, field.name):
                # convert date and time fields to string;
                if field.name in ('date', 'startTime'):
                    setattr(sf, field.name, str(getattr(session, field.name)))
                # convert string fields to typeOfSession;
                elif field.name == 'typeOfSession':
                    setattr(sf, field.name, TypeOfSession(getattr(session, field.name)))
                else:
                    setattr(sf, field.name, getattr(session, field.name))

            elif field.name == 'websafeSessionKey':
                setattr(sf, field.name, session.key.urlsafe())
                
            
        
        sf.check_initialized()
        return sf

    def _getSessionObjects(self, request):
        """ Get Session Objects for given conference key """
        conf = ndb.Key(urlsafe=request.websafeConferenceKey)
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)

        sessions = Session.query(Session.websafeConferenceKey == request.websafeConferenceKey)

        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )


    def _getConferenceSessionsByType(self, request):
        """ Get Session Objects for a given conference by type """
        conf = ndb.Key(urlsafe=request.websafeConferenceKey)
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)

        # retrieving the sessions by type using query by kind
        sessions = Session.query(Session.websafeConferenceKey == request.websafeConferenceKey, \
         Session.typeOfSession == request.typeOfSession).order(Session.sessionName)

        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )


    def _getConferenceSessionsBySpeaker(self, request):
        """ Get Session Objects for a given speaker """
        # retrieving the sessions by speaker using query by kind

        spkr = Speaker.query(Speaker.speaker == request.speaker).get()
        print spkr.sessions
        sessions = spkr.sessions

        return SessionForms(
            items=[self._copySessionToForm(Session.query(Session.key == ndb.Key(urlsafe=session)).get()) for session in sessions]
        )

    def _addSessionToWishlist(self, request):
        """ Add Session objects to a given user's wishlist """
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        profile = self._getProfileFromUser()

        #retrieve exisitng wishlist

        existingWishList = profile.sessionWishList

        session = request.sessionKey

        retval = False

        #no need to add if already added
        if session in existingWishList:
            raise ConflictException(
                    "You have already added this session")
        else:
            profile.sessionWishList.append(session)
            retval = True

        profile.put()

        return BooleanMessage(data=retval)


    def _delSessionFromWishlist(self, request):
        """ Delete Session objects to a given user's wishlist """

        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        profile = self._getProfileFromUser()

        retval = False

        if request.sessionKey in profile.sessionWishList:
            profile.sessionWishList.remove(request.sessionKey)
            retval = True
        else:
            raise ConflictException(
                    "Session is not available in wishList")

        profile.put()

        return BooleanMessage(data=retval)


    #@ndb.transactional(xg=True)
    def _createSessionObject(self, request):
        """ Create Session for a given conference """
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # copy SessionForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}
        del data['websafeSessionKey']

        # retrieve conference
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner of the conference create a session.')


        if data['sessionName']:
            data['sessionName'] = data['sessionName']
        else:
            raise endpoints.BadRequestException("Session 'name' field required")

        # add default values for those missing (both data model & outbound Message)
        for df in DEFAULTS_SESSION:
            if data[df] in (None, []):
                data[df] = DEFAULTS_SESSION[df]
                setattr(request, df, DEFAULTS_SESSION[df])

        # convert dates from strings to Date objects;
        if data['date']:
            data['date'] = datetime.strptime(data['date'], "%Y-%m-%d").date()
        else:
            data['date'] = datetime.strptime("2015-12-25", "%Y-%m-%d").date()

        # convert time from strings to time objects;
        if data['startTime']:
            data['startTime'] = datetime.strptime(data['startTime'][:5], "%H:%M").time()
        else:
            data['startTime'] = datetime.strptime("12:00", "%H:%M").time()

        data['typeOfSession'] = str(data['typeOfSession'])

        if data['websafeConferenceKey']:
            data['websafeConferenceKey'] = request.websafeConferenceKey


        # generate Conference Key based on webSafeConferenceKey and Conference
        # ID based on Conference key get Conference key from ID
        c_key = ndb.Key(Conference, request.websafeConferenceKey).get()
        s_id = Session.allocate_ids(size=1, parent=c_key)[0]
        s_key = ndb.Key(Session, s_id, parent=c_key)

        data['key'] = s_key

        print str(s_key)

        request.websafeSessionKey = str(s_key)

        Session(**data).put()

        
        spkr= data['speaker']

        # retrieve existind speakers and check whether the current speaker is in Speaker
        spks = Speaker.query(Speaker.name == data['speaker']).get()

        print " here value spks ",spks

        if not spks:
            del data['key']
            del data['date']
            del data['startTime']
            del data['typeOfSession']
            del data['duration']
            del data['highlights']
            del data['websafeConferenceKey']
            del data['sessionName']
            keys = [s_key.urlsafe()]
            data['sessions'] = keys
            data['name'] = data['speaker']
            del data['speaker']
            print ("here speaker creation", data)
            Speaker(**data).put()

        else:
            print (" here append spks ", s_key.urlsafe())
            spks.sessions.append(s_key.urlsafe())
            spks.put()

        #send email confirmation
        
        taskqueue.add(params={'email': user.email(),
            'sessionInfo': repr(request)},
            url='/tasks/send_confirmation_session_email')

        # set featured speaker
        # retireve speaker's total number of session details
        speaker = {}

        res = Session.query(Session.speaker == spkr)
        count = 0
        for session in res:
            count += 1

        speaker[spkr] = count

        taskqueue.add(params={'speaker': speaker},
            url='/tasks/set_featured_speaker')        

        return request

    
    @endpoints.method(SessionForm, SessionForm, 
            path='conference/session/{websafeConferenceKey}',
            http_method='POST', name='createSession')
    def createSession(self, request):
        """Create new Session for a given conferencekey"""
        return self._createSessionObject(request)


    @endpoints.method(SESSION_GET_REQUEST, SessionForms, 
            path='conference/getSessions/{websafeConferenceKey}',
            http_method='GET', name='getConferenceSessions')
    def getConferenceSessions(self, request):
        """Get Sessions created for a given conferencekey"""
        return self._getSessionObjects(request)


    @endpoints.method(SESSION_GET_REQUEST_TYP, SessionForms, 
            path='conference/getSessionsByType/{websafeConferenceKey}',
            http_method='GET', name='getConferenceSessionByType')
    def getConferenceSessionByType(self, request):
        """Get Sessions created for a given typeOfSession in a conference"""
        return self._getConferenceSessionsByType(request)


    @endpoints.method(SESSION_GET_REQUEST_SPK, SessionForms, 
            path='conference/getSessionsBySpeaker',
            http_method='GET', name='getConferenceSessionBySpeaker')
    def getConferenceSessionBySpeaker(self, request):
        """Get Sessions created for a given speaker"""
        return self._getConferenceSessionsBySpeaker(request)


    @endpoints.method(SESSION_ADD_WISHLIST_POST, BooleanMessage, 
            path='session/addWishList',
            http_method='POST', name='addSessionToWishList')
    def addSessionToWishList(self, request):
        """Add Sessions to the wishList"""
        return self._addSessionToWishlist(request)


    @endpoints.method(SESSION_DEL_WISHLIST_GET, BooleanMessage, 
            path='session/delWishList',
            http_method='POST', name='delSessionFromWishList')
    def delSessionFromWWishList(self, request):
        """Del Sessions from wishList"""
        return self._delSessionFromWishlist(request)


    @endpoints.method(message_types.VoidMessage, SessionForms, 
            path='session/getWishList',
            http_method='GET', name='getSessionWishList')
    def getSessionWishList(self, request):
        """Get Sessions that are in wishlist"""

        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        profile = self._getProfileFromUser()

        keys = profile.sessionWishList

        return SessionForms(
            items=[self._copySessionToForm(ndb.Key(urlsafe=key).get()) for key in keys]
        )

    @endpoints.method(SESSION_GET_REQUEST_TYM, SessionForms, 
            path='session/getSessionByTime',
            http_method='GET', name='getSessionByTime')
    def getSessionByTimeQuery(self, request):
        """Get Sessions that are have start time greater than given time in the input"""

        start_Time = datetime.strptime(request.sessionTime[:5], "%H:%M").time()

        sessions = Session.query().filter(Session.startTime > start_Time)\
                    .order(Session.startTime).order(Session.sessionName)

        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )


    @endpoints.method(SESSION_GET_REQUEST_TYM_DUR, SessionForms, 
            path='session/getSessionByTimeAndDuration',
            http_method='GET', name='getSessionByTimeAndDuration')
    def getSessionByTimeAndDurationQuery(self, request):
        """Get Sessions that are have start time greater than given time in the input
        and equal to given duration"""

        start_Time = datetime.strptime(request.sessionTime[:5], "%H:%M").time()

        sessions = Session.query().filter(Session.startTime > start_Time)\
                    .filter(Session.duration == request.duration).order(Session.startTime)\
                    .order(Session.duration).order(Session.sessionName)

        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )


    @endpoints.method(message_types.VoidMessage, SessionForms, 
            path='session/getSessionBefore7NoWorkshop',
            http_method='GET', name='getSessionBefore7NoWorkshop')
    def getSessionBefore7NoWorkshop(self, request):
        """Get Sessions that are not Worksops and are before 7 PM"""

        start_Time = datetime.strptime("19:00:00", "%H:%M:%S").time()

        #filtering all other session types except for WORKSHOP and filtering again for time < 7 PM
        #Can also use ndb.OR in this case or can use ~Session.typeOfSession.IN("WORKSHOP")
        sessions = Session.query().filter(Session.typeOfSession.IN([str(TypeOfSession("NOT_SPECIFIED")), \
                        str(TypeOfSession("LECTURE")), \
                        str(TypeOfSession("KEYNOTE"))]))\
                    .filter(Session.startTime < start_Time)\
                    .order(Session.startTime).order(Session.typeOfSession)\
                    .order(Session.sessionName)

        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )


# - - - Announcements - - - - - - - - - - - - - - - - - - - -

    @staticmethod
    def _cacheSpeaker(speaker):
        """ Add Featured Speaker """
        
        # Set featured speaker with session count

        if not speaker:
            featuredSpeaker = "Empty"
            memcache.delete(MEMCACHE_FEATURED_SPEAKER_KEY)
        else:
            # delete if no speaker
            featuredSpeaker = {}
            sessions = Session.query(Session.speaker == speaker).fetch()
            featuredSpeaker[speaker] = sessions
            memcache.set(MEMCACHE_FEATURED_SPEAKER_KEY, value=featuredSpeaker)

        return featuredSpeaker


    @endpoints.method(message_types.VoidMessage, StringMessage,
            path='session/featuredSpeaker/get',
            http_method='GET', name='getFeaturedSpeaker')
    def getFeaturedSpeaker(self, request):
        """Return Featured Speaker from memcache."""
        
        speaker = memcache.get(MEMCACHE_FEATURED_SPEAKER_KEY)
        if not speaker:
            speaker = ""
        return StringMessage(data=speaker)


    @staticmethod
    def _cacheAnnouncement():
        """Create Announcement & assign to memcache; used by
        memcache cron job & putAnnouncement().
        """
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        if confs:
            # If there are almost sold out conferences,
            # format announcement and set it in memcache
            announcement = '%s %s' % (
                'Last chance to attend! The following conferences '
                'are nearly sold out:',
                ', '.join(conf.name for conf in confs))
            memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
            # If there are no sold out conferences,
            # delete the memcache announcements entry
            announcement = ""
            memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

        return announcement


    @endpoints.method(message_types.VoidMessage, StringMessage,
            path='conference/announcement/get',
            http_method='GET', name='getAnnouncement')
    def getAnnouncement(self, request):
        """Return Announcement from memcache."""
        # TODO 1
        # return an existing announcement from Memcache or an empty string.
        announcement = memcache.get(MEMCACHE_ANNOUNCEMENTS_KEY)
        if not announcement:
            announcement = ""
        return StringMessage(data=announcement)



# TODO 1

api = endpoints.api_server([ConferenceApi]) # register API
