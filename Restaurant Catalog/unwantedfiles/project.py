from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
app = Flask(__name__)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Restaurant, Base, MenuItem
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/')
@app.route('/restaurant/<int:restaurant_id>/')
def RestaurantDetail(restaurant_id):
	rest_1 = session.query(Restaurant).get(restaurant_id)
	menu = session.query(MenuItem).filter_by(restaurant_id = rest_1.id)
	return render_template('menu.html', restaurant=rest_1, items=menu)
	

# Task 1: Create route for newMenuItem function here


@app.route('/restaurant/<int:restaurant_id>/new/', methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
	if request.method == 'POST':
		newItem = MenuItem(name = request.form['name'], restaurant_id = restaurant_id)
		session.add(newItem)
		session.commit()
		flash("new menu item created!")
		return redirect(url_for('RestaurantDetail', restaurant_id=restaurant_id))

	else:
		return render_template('newMenuItem.html', restaurant_id=restaurant_id)

# Task 2: Create route for editMenuItem function here

@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/edit/', methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):
	editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
	if request.method == 'POST':
		if request.form['name']:
			editedItem.name = request.form['name']
		session.add(editedItem)
		session.commit()
		flash("menu item edited!")
		return redirect(url_for('RestaurantDetail', restaurant_id=restaurant_id))
	else:
		return render_template('editmenuitem.html', restaurant_id=restaurant_id, menu_id=menu_id, item=editedItem)

# Task 3: Create a route for deleteMenuItem function here

@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/delete/', methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
	deleteItem = session.query(MenuItem).filter_by(id=menu_id).one()
	if request.method == 'POST':
		session.query(MenuItem).filter(MenuItem.id == menu_id, MenuItem.restaurant_id == restaurant_id).delete(synchronize_session=False)
		session.commit()
		flash("menu item deleted!")
		return redirect(url_for('RestaurantDetail', restaurant_id=restaurant_id))
	else:
		return render_template('deletemenuitem.html', restaurant_id=restaurant_id, item=deleteItem)


@app.route('/restaurant/<int:restaurant_id>/menu/JSON', methods=['GET', 'POST'])
def restaurantMenuJSON(restaurant_id):
	restaurant = session.query(Restaurant).filter(Restaurant.id == restaurant_id)
	items = session.query(MenuItem).filter(MenuItem.restaurant_id == restaurant_id).all()
	return jsonify(MenuItems = [i.serialize for i in items])


@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/JSON', methods=['GET', 'POST'])
def restaurantIndividualMenuJSON(restaurant_id, menu_id):
	item = session.query(MenuItem).filter(MenuItem.id == menu_id, MenuItem.restaurant_id == restaurant_id).one()
	return jsonify(MenuItem = [item.serialize])



if __name__ == '__main__':
	app.secret_key = 'super_secret_key'
	app.debug = True
	app.run(host='0.0.0.0', port=5000)