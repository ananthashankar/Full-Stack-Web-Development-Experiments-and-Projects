import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

#creating User class
class User(Base):

	#creating user table
	__tablename__ = 'user'
	#creating required columns for table user
	name = Column(String(80), nullable=False)
	id = Column(Integer, primary_key=True)
	email = Column(String(80), nullable=False)
	picture = Column(String(250))



#creating Restaurant class
class Restaurant(Base):
	
	#creating restaurant table
	__tablename__ = 'restaurant'
	#creating required columns for table restaurant
	name = Column(String(80), nullable=False)
	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User)
	picture = Column(String(1000))

	@property
	def serialize(self):
		return {
			'id' : self.id,
			'name' : self.name,
			'picture' : self.picture,
		}


#creating MenuItem class
class MenuItem(Base):

	#creating menu_item table
	__tablename__ = 'menu_item'
	#creating required columns for table menu_item
	name = Column(String(80), nullable=False)
	id = Column(Integer, primary_key=True)
	course = Column(String(250))
	description = Column(String(250))
	price = Column(String(8))
	restaurant_id = Column(Integer, ForeignKey('restaurant.id'))
	restaurant = relationship(Restaurant)
	user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"))
	user = relationship(User)
	picture = Column(String(1000))

	@property
	def serialize(self):
		return {
			'course' : self.course,
			'description' : self.description,
			'id' : self.id,
			'name' : self.name,
			'price' : self.price,
			'picture' : self.picture,
		}


engine = create_engine('sqlite:///restaurant.db')
Base.metadata.create_all(engine)

