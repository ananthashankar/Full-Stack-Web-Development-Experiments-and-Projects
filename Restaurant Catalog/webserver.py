from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Restaurant, Base, MenuItem
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import cgi

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

class handlerClass(BaseHTTPRequestHandler):
	def do_GET(self):
		try:
			
			if(self.path.endswith("/restaurants")):
				list_restaurants = session.query(Restaurant).all()
				self.send_response(200)
				self.send_header('Content_type', 'text/html')
				self.end_headers()
				output = "<html><body>"
				output += "<a href='/restaurants/new'>Make a New Restaurant Here</a></br></br>"
				for r in list_restaurants :
					output += r.name + "</br>"
					output += "<a href='/restaurants/%s/edit' > Edit </a></br>"  % (r.id) + "<a href='/restaurants/%s/delete' > Delete </a></br></br></br>" % (r.id)

				output += "</body></html>"
				self.wfile.write(output)
				print(output)
				return

			if(self.path.endswith("/restaurants/new")):
				self.send_response(200)
				self.send_header('Content_type', 'text/html')
				self.end_headers()
				output = "<html><body>"
				output += "<h2>Make a New Restaurant</h2></br>"
				output += "<form method='POST' enctype='multipart/form-data' action='/restaurants/new'><input name='restName' type='text' /><input value='Create' type='submit' /> </form>"
				output += "</body></html>"
				self.wfile.write(output)
				print(output)
				return

			if(self.path.endswith('/edit')):
				tmp_path = self.path.split('/')
				id1 = tmp_path[2]
				rest = session.query(Restaurant).get(id1)
				self.send_response(200)
				self.send_header('Content_type', 'text/html')
				self.end_headers()
				output = "<html><body>"
				output += "<h2>%s</h2></br>" % rest.name
				output += "<form method='POST' enctype='multipart/form-data' action='/restaurants/%s/edit'><input name='newName' type='text' placeholder='%s'/><input value='Rename' type='submit' /> </form>" % (id1, rest.name)
				output += "</body></html>"
				self.wfile.write(output)
				print(output)
				return

			if(self.path.endswith('/delete')):
				id1 = self.path.split('/')[2]
				rest = session.query(Restaurant).get(id1)
				self.send_response(200)
				self.send_header('Content_type', 'text/html')
				self.end_headers()
				output = "<html><body>"
				output += "<h2>Are You Sure You Want To Delete %s ?</h2></br>" % rest.name
				output += "<form method='POST' enctype='multipart/form-data' action='/restaurants/%s/delete'><input value='Delete' type='submit' /></form>" % rest.id
				output += "</body></html>"
				self.wfile.write(output)
				return



		except IOError:
			self.send_error(404, "file not found error %s", self.path)
	
	
	def do_POST(self):
		try:
			if(self.path.endswith('/restaurants/new')):
				ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
				if (ctype == 'multipart/form-data'):
					fields = cgi.parse_multipart(self.rfile, pdict)
					nameRest = fields.get('restName')
					rest_new = Restaurant(name=nameRest[0])
					session.add(rest_new)
					session.commit()
				self.send_response(301)
				self.send_header('Content-type', 'text/html')
				self.send_header('Location', '/restaurants')
				self.end_headers()
				return

			if(self.path.endswith('/edit')):
				tmp_path = self.path.split('/')
				id1 = tmp_path[2]
				ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
				if (ctype == 'multipart/form-data'):
					fields = cgi.parse_multipart(self.rfile, pdict)
					newNm = fields.get('newName')
					nm = newNm[0]
					session.query(Restaurant).filter(Restaurant.id == id1).update({Restaurant.name: nm}, synchronize_session=False)
					session.commit()
				self.send_response(301)
				self.send_header('Content-type', 'text/html')
				self.send_header('Location', '/restaurants')
				self.end_headers()
				return

			if(self.path.endswith('/delete')):
				tmp_path = self.path.split('/')
				id1 = tmp_path[2]
				session.query(Restaurant).filter(Restaurant.id == id1).delete(synchronize_session=False)
				session.commit()
				self.send_response(301)
				self.send_header('Content-type', 'text/html')
				self.send_header('Location', '/restaurants')
				self.end_headers()
				return

				
		except:
			pass
		


def main():
	try:
		port = 8080
		server = HTTPServer(('', port), handlerClass)
		print("Server up and running on %s", port)
		server.serve_forever()

	except KeyboardInterrupt:
		print("Server successfully stopped")
		server.socket.close()
	


if __name__ == '__main__':
		main()