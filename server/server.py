# coding=utf-8
#------------------------------------------------------------------------------------------------------
# TDA596 Labs - Server Skeleton
# server/server.py
# Input: Node_ID total_number_of_ID
# Student Group:
# Student names: John Doe & John Doe
#------------------------------------------------------------------------------------------------------
# We import various libraries
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler # Socket specifically designed to handle HTTP requests
import sys # Retrieve arguments
from urlparse import parse_qs # Parse POST data
from httplib import HTTPConnection # Create a HTTP connection, as a client (for POST requests to the other vessels)
from urllib import urlencode # Encode POST content into the HTTP header
from codecs import open # Open a file
from threading import  Thread # Thread Management
import random
import time
#------------------------------------------------------------------------------------------------------

# Global variables for HTML templates
board_frontpage_footer_template = "server/board_frontpage_footer_template.html"
board_frontpage_header_template = "server/board_frontpage_header_template.html"
boardcontents_template = "server/boardcontents_template.html"
entry_template = "server/entry_template.html"

#------------------------------------------------------------------------------------------------------
# Static variables definitions
PORT_NUMBER = 80
#------------------------------------------------------------------------------------------------------




#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
class BlackboardServer(HTTPServer):
#------------------------------------------------------------------------------------------------------
	def __init__(self, server_address, handler, node_id, vessel_list):
	# We call the super init
		HTTPServer.__init__(self,server_address, handler)
		# we create the dictionary of values
		self.store = {}
		# We keep a variable of the next id to insert
		self.current_key = -1
		# our own ID (IP is 10.1.0.ID)
		self.vessel_id = vessel_id
		# The list of other vessels
		self.vessels = vessel_list

		self.id = random.randint(1,10000)
		self.leader = 0
		self.leader_id = 0
		thread = Thread(target=self.start_leader_election)
		thread.daemon = True
		thread.start()
#------------------------------------------------------------------------------------------------------
	# We add a value received to the store
	def add_value_to_store(self, value):
		self.current_key += 1
		self.store[self.current_key] = value
		return self.current_key

#------------------------------------------------------------------------------------------------------
	# We modify a value received in the store
	def modify_value_in_store(self,key,value):
		self.store[int(key)] = value
		return key

#------------------------------------------------------------------------------------------------------
	# We delete a value received from the store
	def delete_value_in_store(self,key):
		del self.store[int(key)]
		return key
#------------------------------------------------------------------------------------------------------
# Contact a specific vessel with a set of variables to transmit to it
	def contact_vessel(self, vessel, path, action, key, value):
		# the Boolean variable we will return
		success = False
		# The variables must be encoded in the URL format, through urllib.urlencode
		post_content = urlencode({'action': action, 'key': key, 'value': value})
		# the HTTP header must contain the type of data we are transmitting, here URL encoded
		headers = {"Content-type": "application/x-www-form-urlencoded"}
		# We should try to catch errors when contacting the vessel
		try:
			# We contact vessel:PORT_NUMBER since we all use the same port
			# We can set a timeout, after which the connection fails if nothing happened
			connection = HTTPConnection("%s:%d" % (vessel, PORT_NUMBER), timeout = 30)
			# We only use POST to send data (PUT and DELETE not supported)
			action_type = "POST"
			# We send the HTTP request
			connection.request(action_type, path, post_content, headers)
			# We retrieve the response
			response = connection.getresponse()
			# We want to check the status, the body should be empty
			status = response.status
			# If we receive a HTTP 200 - OK
			if status == 200:
				success = True
		# We catch every possible exceptions
		except Exception as e:
			print "Error while contacting %s" % vessel
			# printing the error given by Python
			print(e)

		# we return if we succeeded or not
		return success
#------------------------------------------------------------------------------------------------------
	# We send a received value to all the other vessels of the system
	def propagate_value_to_vessels(self, path, action, key, value):
		# We iterate through the vessel list
		for vessel in self.vessels:
			# We should not send it to our own IP, or we would create an infinite loop of updates
			if vessel != ("10.1.0.%s" % self.vessel_id):
				# A good practice would be to try again if the request failed
				# Here, we do it only once
				self.contact_vessel(vessel, path, action, key, value)		
#------------------------------------------------------------------------------------------------------

	def start_leader_election(self):
		time.sleep(1)
		vessel = "10.1.0.%s" % ((self.vessel_id % 10) + 1)
		#Key is used for message source and value is the largest id found
		self.contact_vessel(vessel, '/election', self.vessel_id, self.id, self.vessel_id)


#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# This class implements the logic when a server receives a GET or POST request
# It can access to the server data through self.server.*
# i.e. the store is accessible through self.server.store
# Attributes of the server are SHARED accross all request hqndling/ threads!
class BlackboardRequestHandler(BaseHTTPRequestHandler):
#------------------------------------------------------------------------------------------------------
	# We fill the HTTP headers
	def set_HTTP_headers(self, status_code = 200):
		 # We set the response status code (200 if OK, something else otherwise)
		self.send_response(status_code)
		# We set the content type to HTML
		self.send_header("Content-type","text/html")
		# No more important headers, we can close them
		self.end_headers()
#------------------------------------------------------------------------------------------------------
	# a POST request must be parsed through urlparse.parse_QS, since the content is URL encoded
	def parse_POST_request(self):
		post_data = ""
		# We need to parse the response, so we must know the length of the content
		length = int(self.headers['Content-Length'])
		# we can now parse the content using parse_qs
		post_data = parse_qs(self.rfile.read(length), keep_blank_values=1)
		# we return the data
		return post_data
#------------------------------------------------------------------------------------------------------	
#------------------------------------------------------------------------------------------------------
# Request handling - GET
#------------------------------------------------------------------------------------------------------
	# This function contains the logic executed when this server receives a GET request
	# This function is called AUTOMATICALLY upon reception and is executed as a thread!
	def do_GET(self):
		print("Receiving a GET on path %s" % self.path)
		# Here, we should check which path was requested and call the right logic based on it
		if self.path == '/':
			self.do_GET_Index()
		elif self.path == '/board':
			self.do_GET_Board()
		else:
			 self.wfile.write('error')
#------------------------------------------------------------------------------------------------------
# GET logic - specific path
#------------------------------------------------------------------------------------------------------
	def do_GET_Index(self):
		# We set the response status code to 200 (OK)
		self.set_HTTP_headers(200)
		header = open(board_frontpage_header_template).read()
		footer = open(board_frontpage_footer_template).read()
		
		self.wfile.write(header + self.render_board() + footer % ('', self.server.leader, self.server.leader_id)) 

	def do_GET_Board(self):
		self.set_HTTP_headers(200)
		self.wfile.write(self.render_board())


	def render_board(self):
		boardcontents = open(boardcontents_template).read()
		entry_t = open(entry_template).read()
		
		entires = []
		for key, value in self.server.store.items():
			entires.append(entry_t % ('entries/'+str(key), key, value))

		return boardcontents % ("title", "".join(entires))
#------------------------------------------------------------------------------------------------------
	# we might want some other functions
#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# Request handling - POST
#------------------------------------------------------------------------------------------------------
	def do_POST(self):
		print("Receiving a POST on %s" % self.path)
		data = parse_qs(self.rfile.read(int(self.headers['Content-Length'])))
		print data
		self.set_HTTP_headers(200)
		if self.path == '/propagate':
			value = data['value'][0] if 'value' in data.keys() else ''
			self.update_store(data['action'][0],data['key'][0],value)
		elif self.path == '/election':
			self.propagate_leader(data['action'][0],data['key'][0],data['value'][0])
		else:
			action = ""
			key = ""
			value = ""
			
			if self.path == '/board':
				action = 'add'
				value = data['entry'][0]
			elif self.path.startswith('/entries/'):
				key = data['id'][0]
				if data['delete'][0] == '1':
					action = 'delete'
				else:
					action = 'modify'
					value = data['entry'][0]	
			else:
				self.send_error(404)

			key = self.update_store(action, key, value)

			thread = Thread(target=self.server.propagate_value_to_vessels,args=("/propagate",action, key, value))
			# We kill the process if we kill the server
			thread.daemon = True
			# We start the thread
			thread.start()

#------------------------------------------------------------------------------------------------------
# POST Logic
#------------------------------------------------------------------------------------------------------
	# We might want some functions here as well
#------------------------------------------------------------------------------------------------------
		
	def update_store(self, action, key, value):
		if action == 'add':
			return self.server.add_value_to_store(value)
		elif action == 'modify':
			return self.server.modify_value_in_store(key, value)
		elif action == 'delete':
			return self.server.delete_value_in_store(key)

	def propagate_leader(self, action, key, value):
		#This server was the source use the value as leader
		print(action)
		print(self.server.vessel_id) 
		if int(action) == int(self.server.vessel_id):
			self.server.leader_id = key
			self.server.leader = "10.1.0.%s" % value
			print("Elected %s as leader" % self.server.leader)
		else:
			if int(key) < int(self.server.id):
				key = self.server.id
				value = self.server.vessel_id
			vessel = "10.1.0.%s" % ((self.server.vessel_id % 10) + 1)
			thread = Thread(target=self.server.contact_vessel, args=(vessel, '/election', action, key, value))
			thread.daemon = True
			thread.start()





#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# Execute the code
if __name__ == '__main__':

	## read the templates from the corresponding html files
	# .....

	vessel_list = []
	vessel_id = 0
	# Checking the arguments
	if len(sys.argv) != 3: # 2 args, the script and the vessel name
		print("Arguments: vessel_ID number_of_vessels")
	else:
		# We need to know the vessel IP
		vessel_id = int(sys.argv[1])
		# We need to write the other vessels IP, based on the knowledge of their number
		for i in range(1, int(sys.argv[2])+1):
			vessel_list.append("10.1.0.%d" % i) # We can add ourselves, we have a test in the propagation

	# We launch a server
	server = BlackboardServer(('', PORT_NUMBER), BlackboardRequestHandler, vessel_id, vessel_list)
	print("Starting the server on port %d" % PORT_NUMBER)

	try:
		server.serve_forever()
	except KeyboardInterrupt:
		server.server_close()
		print("Stopping Server")
#------------------------------------------------------------------------------------------------------
