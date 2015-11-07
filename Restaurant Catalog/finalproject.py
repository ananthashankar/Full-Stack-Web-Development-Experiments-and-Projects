# importing flask and supporting functionaities
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask import send_from_directory
from flask.ext.seasurf import SeaSurf
from werkzeug import secure_filename
import os
from functools import wraps

UPLOAD_FOLDER = 'static/images/uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
csrf = SeaSurf(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


from flask import session as login_session

# importing pyhton libraries
import random, string
import json
import httplib2
import requests

# importing oauth2client and supporting functionaities
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

# importing sqlalchemy and db to access

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Restaurant, Base, MenuItem, User
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
engine = create_engine('sqlite:///restaurant.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            return redirect(url_for('showlogin'))
        return f(*args, **kwargs)
    return decorated_function


# Verifying file format
def allowed_file(filename):
	return '.' in filename and \
			filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# copying file to upload folder
@csrf.exempt
@app.route('/uploads')
def upload_file(request):
	file = request.files['image']
	if file and allowed_file(file.filename):
		filename = secure_filename(file.filename)
		file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
		return 1
	else:
		print("here uploads")
		flash("Image not saved. File type not supported. Please try \
			again with supported image formats ('png', 'jpg', 'jpeg', 'gif')")
		return None


# serving file to required page
@app.route('/uploads/<filename>')
def uploaded_file(filename):
	print("here" + send_from_directory(app.config['UPLOAD_FOLDER'], filename))
	return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# "routing and method to google and facebook login feature"
@app.route('/login')
def showLogin():
	state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
	login_session['state'] = state
	return render_template('login.html', STATE=state)

# "routing and method to redirect to home page after google login"
@csrf.exempt
@app.route('/gconnect', methods=['POST'])
def gconnect():
	# Validate state tokens
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid State Parameter'))
		response.headers['Content-Type'] = 'application/json'
		return response

	# Obtain authorization code
	code = request.data
	try:
		# Upgrade the authorization code into a credentials object
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)
	except FlowExchangeError:
		response = make_response(json.dumps('Fail to Upgrade the Authorization Code'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Check that the access token is valid.
	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' %access_token)
	h = httplib2.Http()
	result = json.loads(h.request(url, 'GET')[1])


	# If there was an error in the access token info, abort.
	if result.get('error') is not None:
		response = make_response(json.dumps(result.get('error')), 500)
		response.headers['Content-Type'] = 'application/json'
		

    # Verify that the access token is used for the intended user.
	gplus_id = credentials.id_token['sub']
	if result['user_id'] != gplus_id:
		response = make_response(json.dumps("Token's user ID doesn't match given user ID."), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

    # Verify that the access token is valid for this app.
	if result['issued_to'] != CLIENT_ID:
		response = make_response(json.dumps("Token's client ID does not match app's."), 401)
		print "Token's client ID does not match app's."
		response.headers['Content-Type'] = 'application/json'
		return response

	stored_credentials = login_session.get('credentials')
	stored_gplus_id = login_session.get('gplus_id')
	if stored_credentials is not None and gplus_id == stored_gplus_id:
		response = make_response(json.dumps('Current user is already connected.'),200)
		response.headers['Content-Type'] = 'application/json'
		return response

    # Store the access token in the session for later use.
	login_session['credentials'] = access_token
	#credentials.access_token
	login_session['gplus_id'] = gplus_id

    # Get user info
	userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
	params = {'access_token': credentials.access_token, 'alt': 'json'}
	answer = requests.get(userinfo_url, params=params)

	data = answer.json()
	login_session['provider'] = 'google'
	login_session['username'] = data['name']
	login_session['picture'] = data['picture']
	login_session['email'] = data['email']

	# check if user details already exists in db else create the user and add in db
	user_id = getUserId(login_session['email'])
	if not user_id:
		user_id = createUser(login_session)
	login_session['user_id'] = user_id

	output = ''
	output += '<h1>Welcome, '
	output += login_session['username']
	output += '!</h1>'
	output += '<img src="'
	output += login_session['picture']
	output += ' " style = "width: 300px; height: 300px;border-radius: 150px;\
	-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
	flash("You are now logged in as %s" % login_session['username'])
	print "done!"
	return output


#facebook login
@csrf.exempt
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
	print("here fb login")
	# Validate state tokens
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid State Parameter'))
		response.headers['Content-Type'] = 'application/json'
		return response

	# Obtain authorization code
	access_token = request.data

	#Exchange short lived to long lived server side token
	app_id = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_id']
	app_secret = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_secret']
	url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s'\
	 % (app_id, app_secret, access_token)
	h = httplib2.Http()
	result = h.request(url, 'GET')[1]

	#get user info from api
	userinfo_url = "https://graph.facebook.com/v2.4/me"
	#strip expire tag from access token
	token = result.split("&")[0]

	url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token

	h = httplib2.Http()
	result = h.request(url, 'GET')[1]

	data = json.loads(result)
	#populate login session
	login_session['provider'] = 'facebook'
	login_session['username'] = data['name']
	login_session['facebook_id'] = data['id']
	login_session['email'] = data['email']


	# The token must be stored in the login_session in order to properly logout, 
	#let's strip out the information before the equals sign in our token
	#stored_token = token.split("=")[1]
	#login_session['access_token'] = stored_token

	#Get Picture
	url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
	h = httplib2.Http()
	result = h.request(url, 'GET')[1]
	data = json.loads(result)

	login_session['picture'] = data["data"]["url"]

	# check if user details already exists in db else create the user and add in db
	user_id = getUserId(login_session['email'])
	if not user_id:
		user_id = createUser(login_session)
	login_session['user_id'] = user_id

	output = ''
	output += '<h1>Welcome, '
	output += login_session['username']
	output += '!</h1>'
	output += '<img src="'
	output += login_session['picture']
	output += ' " style = "width: 100px; height: 100px;border-radius: 150px;\
	-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
	flash("You are now logged in as %s" % login_session['username'])
	print "done!"
	return output





# user related methods
def createUser(login_session):
	newUser = User(name=login_session['username'], email=login_session['email'],\
	 picture=login_session['picture'])
	session.add(newUser)
	session.commit()
	user = session.query(User).filter_by(email=login_session['email']).one()
	return user.id


def getUserInfo(user_id):
	try:
		user = session.query(User).filter_by(id=user_id).one()
		return user
	except:
		return None



def getUserId(email):
	try:
		user = session.query(User).filter_by(email=email).one()
		return user.id
	except:
		return None



# "routing and method to disconnect the google login session"
@app.route('/gdisconnect')
def gdisconnect():
	credentials = login_session.get('credentials')
	if credentials is None:
		response = make_response(json.dumps('Current user not conected'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	
	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % credentials
	h = httplib2.Http()
	result = h.request(url, 'GET')[0]
	print (result)

	if result['status'] == '200':
		# Reset the user's session.
		del login_session['credentials']
		del login_session['username']
		del login_session['email']
		del login_session['picture']
		del login_session['gplus_id']
		del login_session['provider']

		response = make_response(json.dumps('Successfully disconnected.'), 200)
		response.headers['Content-Type'] = 'application/json'
		return response
    
	else:
    	# For whatever reason, the given token was invalid.
		response = make_response(json.dumps('Failed to revoke token for given user.', 400))
		response.headers['Content-Type'] = 'application/json'
		return response


# "routing and method to disconnect the google login session"
@app.route('/fbdisconnect')
def fbdisconnect():
	facebook_id = login_session['facebook_id']

	# The access token must me included to successfully logout
	#access_token = login_session['access_token']

	url = 'https://graph.facebook.com/%s/permissions' % facebook_id
	#?access_token=%s' % facebook_id

	h = httplib2.Http()
	result = h.request(url, 'DELETE')[1]
	del login_session['user_id']
	del login_session['facebook_id']
	del login_session['username']
	del login_session['email']
	del login_session['picture']
	del login_session['provider']
	return "You've been logged out" 


@app.route('/disconnect')
def disconnect():
	if 'provider' in login_session:
		if login_session['provider'] == 'google':
			gdisconnect()
		elif login_session['provider'] == 'facebook':
			fbdisconnect()
		flash("You've Successfully logged out")
		return redirect(url_for('allRestaurants'))
	else:
		flash("You were not logged in to log out")
		return redirect(url_for('allRestaurants'))


# "routing and method to display all restaurants lists with link to their individual page"
@app.route('/')
@app.route('/restaurants')
def allRestaurants():
	restaurants = session.query(Restaurant).all()
	if 'username' not in login_session:
		return render_template('publicrestaurants.html', restaurants=restaurants)
	else:
		return render_template("restaurants.html", restaurants = restaurants,\
		 picture=login_session['picture'])



# "routing and method to create new restaurants"
@login_required
@app.route('/restaurant/new', methods=['GET', 'POST'])
def createNewRestaurant():
	#if 'username' not in login_session:
	#	return redirect ('/login')
	if request.method == 'POST':
		if request.form['name']:
			path = ""
			if upload_file(request) != None:
				file = request.files['image']
				path = os.path.join('/', app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
			restaurant = Restaurant(name = request.form['name'], user_id=login_session['user_id'], \
				picture=path)
			session.add(restaurant)
			session.commit()
			flash("New Restaurant Created!")
		return redirect(url_for('allRestaurants'))

	else:
		return render_template("newrestaurant.html")



# "routing and method to edit the restaurant details"
@login_required
@app.route('/restaurant/<int:restaurant_id>/edit', methods=['GET', 'POST'])
def editRestaurant(restaurant_id):
	#if 'username' not in login_session:
	#	return redirect ('/login')
	restaurant = session.query(Restaurant).get(restaurant_id)
	if restaurant.user_id != login_session['user_id']:
		redirect(url_for('allRestaurants'))
		return "<script>function myFunction() {var a = alert('You are not authorized \
			to edit this restaurant. Please create your own restaurant in order to \
			edit.');}</script><body onload='myFunction()''>"


	if request.method == 'POST':
		if request.form['name']:
			restaurant.name = request.form['name']

		if upload_file(request) != None:
			file = request.files['image']
			path = os.path.join('/', app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
			restaurant.picture = path

		session.add(restaurant)
		session.commit()
		flash("Restaurant Successfully Edited!")
		return redirect(url_for('allRestaurants'))

	else:
		return render_template("editrestaurant.html", restaurant = restaurant,\
		 restaurant_id = restaurant_id)



# "routing and method to delete the restaurant details"
@login_required
@app.route('/restaurant/<int:restaurant_id>/delete', methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
	#if 'username' not in login_session:
	#	return redirect ('/login')
	restaurant = session.query(Restaurant).get(restaurant_id)
	if restaurant.user_id != login_session['user_id']:
		return "<script>function myFunction() {alert('You are not authorized to \
			delete this restaurant. Please create your own restaurant in order to \
			delete.');}</script><body onload='myFunction()''>"

	if request.method == 'POST':
		session.query(Restaurant).filter_by(id=restaurant_id).delete(synchronize_session=False)
		session.commit()
		flash("Restaurant Successfully Deleted!")
		return redirect(url_for('allRestaurants'))

	else:
		return render_template("deleterestaurant.html", restaurant = restaurant,\
		 restaurant_id = restaurant_id)



# "routing and method to display the restaurant details with list of menu"
@app.route('/restaurant/<int:restaurant_id>')
@app.route('/restaurant/<int:restaurant_id>/menu')
def showMenu(restaurant_id):
	restaurant = session.query(Restaurant).get(restaurant_id)
	creator = getUserInfo(restaurant.user_id)
	items = session.query(MenuItem).filter_by(restaurant_id = restaurant.id)
	if 'username' not in login_session or creator.id != login_session['user_id']:
		return render_template("publicmenu.html", restaurant = restaurant, items = items)
	else:
		return render_template("menu.html", restaurant = restaurant, items = items)
	


# "routing and method to create menuitem for a restaurant"
@login_required
@app.route('/restaurant/<int:restaurant_id>/menu/new', methods=['GET', 'POST'])
def createMenuItem(restaurant_id):
	#if 'username' not in login_session:
	#	return redirect ('/login')

	restaurant = session.query(Restaurant).get(restaurant_id)
	creator = getUserInfo(restaurant.user_id)

	if creator.id != login_session['user_id']:
		return "<script>function myFunction() {alert('You are not authorized \
			to add menu to this restaurant. Please create your own restaurant \
			in order to create menu.');}</script><body onload='myFunction()''>"


	if request.method == 'POST':
		if request.form['name']:

			path = ""
			if upload_file(request) != None:
				file = request.files['image']
				path = os.path.join('/', app.config['UPLOAD_FOLDER'], secure_filename(file.filename)) 
			item = MenuItem(name=request.form['name'], restaurant_id=restaurant_id, \
				course=request.form['course'], description=request.form['description'], \
				price=request.form['price'], user_id=login_session['user_id'],\
			  picture=path)
			session.add(item)
			session.commit()
			flash("New Menu Created!")
			return redirect(url_for('showMenu', restaurant_id=restaurant_id))

	else:
		return render_template("newmenuitem.html", restaurant_id = restaurant_id)
	


# "routing and method to edit menuitem of a restaurant"
@login_required
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit', methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):
	#if 'username' not in login_session:
	#	return redirect ('/login')

	restaurant = session.query(Restaurant).get(restaurant_id)
	creator = getUserInfo(restaurant.user_id)

	if creator.id != login_session['user_id']:
		return "<script>function myFunction() {var a = alert('You are not authorized \
			to edit menu to this restaurant. \
		 Please create your own restaurant in order to edit menu.');}\
		</script><body onload='myFunction()''>"



	menu_item = session.query(MenuItem).filter_by(id=menu_id, restaurant_id=restaurant_id).one()
	if request.method == 'POST':
		if upload_file(request) != None:
			file = request.files['image']
			path = os.path.join('/', app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
			menu_item.picture = path
		menu_item.name = request.form['name']
		menu_item.course = request.form['course']
		menu_item.description = request.form['description']
		menu_item.price = request.form['price']

		session.add(menu_item)
		session.commit()
		flash("Menu Successfully Edited!")
		return redirect(url_for('showMenu', restaurant_id=restaurant_id))

	else:
		return render_template("editmenuitem.html", restaurant_id = restaurant_id, \
			menu_id=menu_id, menu_item=menu_item)



# "routing and method to delete menuitem of a restaurant"
@login_required
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete', methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
	#if 'username' not in login_session:
	#	return redirect ('/login')

	restaurant = session.query(Restaurant).get(restaurant_id)
	creator = getUserInfo(restaurant.user_id)

	if creator.id != login_session['user_id']:
		return "<script>function myFunction() {alert('You are not authorized to \
			delete menu to this restaurant. \
		 Please create your own restaurant in order to delete menu.');}\
		</script><body onload='myFunction()''>"


	restaurant = session.query(Restaurant).get(restaurant_id)
	menu_item = session.query(MenuItem).filter_by(id=menu_id, restaurant_id=restaurant_id).one()
	if request.method == 'POST':
		session.query(MenuItem).filter_by(id=menu_id).delete(synchronize_session=False)
		session.commit()
		flash("Menu Successfully Deleted!")
		return redirect(url_for('showMenu', restaurant_id=restaurant_id))

	else:
		return render_template("deletemenuitem.html", restaurant = restaurant, \
			menu_id=menu_id, menu_item=menu_item)



# "routing and method for restaurants list api"
@app.route('/restaurants/JSON')
def restaurantJSON():
	restaurants = session.query(Restaurant).all()
	return jsonify(Restaurants = [i.serialize for i in restaurants])


# "routing and method for restaurants menu list api"
@app.route('/restaurants/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
	restaurant = session.query(Restaurant).filter(Restaurant.id == restaurant_id)
	items = session.query(MenuItem).filter(MenuItem.restaurant_id == restaurant_id).all()
	return jsonify(MenuItems = [i.serialize for i in items])



# "routing and method for single menu api"
@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def restaurantOneMenuJSON(restaurant_id, menu_id):
	item = session.query(MenuItem).filter(MenuItem.id == menu_id,\
	 MenuItem.restaurant_id == restaurant_id).one()
	return jsonify(MenuItem = [item.serialize])

# "routing and method for restaurants xml"
@app.route('/restaurants/XML')
def restaurantsXML():
    restaurants = session.query(Restaurant).all()
    return render_template('restaurants.xml', restaurants=restaurants)

# "routing and method for restaurants menu xml"
@app.route('/restaurants/<int:restaurant_id>/menu/XML')
def restaurantsMenuXML(restaurant_id):
    restaurant  = session.query(Restaurant).filter(Restaurant.id == restaurant_id)
    items = session.query(MenuItem).filter(MenuItem.restaurant_id == restaurant_id).all()
    return render_template('restaurantMenu.xml', restaurant=restaurant, items=items)


# "routing and method for restaurants single menu xml"
@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/XML')
def restaurantsSingleMenuXML(restaurant_id, menu_id):
    item = session.query(MenuItem).filter(MenuItem.id == menu_id,\
     MenuItem.restaurant_id == restaurant_id).one()
    return render_template('restaurantSingleMenu.xml', item=item)


if __name__ == '__main__':
	app.secret_key = 'super_secret_key'
	app.debug = True
	app.run(host='0.0.0.0', port=5000)
