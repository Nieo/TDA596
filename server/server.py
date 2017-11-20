# coding=utf-8
#------------------------------------------------------------------------------------------------------
# TDA596 Labs - Server Skeleton
# server/server.py
# Input: Node_ID total_number_of_ID
# Student Group: 8
# Student names: Erik Pihl, Alex Tao
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
		#IP of leader
		self.leader = 0
		self.leader_id = self.id
		thread = Thread(target=self.start_leader_election)
		thread.daemon = True
		thread.start()


	def get_next_key(self):
		self.current_key +=1
		return self.current_key	
#------------------------------------------------------------------------------------------------------
	# We add a value received to the store
	def add_value_to_store(self, key, value):
		self.store[int(key)] = value
		return key

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
	# Waits for 1 second to let all nodes start correctly then start the leaderelection 
	def start_leader_election(self):
		time.sleep(1)
		vessel = "10.1.0.%s" % ((self.vessel_id % 10) + 1)
		#Action is the vessel id to determine when the message have returned to is origin
		#Key is current larges random id
		#Value is the id (from the same node as key) used to get the ip of a node
		self.contact_vessel(vessel, '/election', self.vessel_id, self.id, self.vessel_id)

	# Send a request to the leader to get the next unique id
	def request_next_id(self):
		try:
			connection = HTTPConnection("%s:%d" % (self.leader, PORT_NUMBER), timeout=30)
			connection.request("GET", "/nextid")
			response = connection.getresponse()
			return response.read()
		except Exception as e:
			print "Error while contacting %s" % self.leader
			# printing the error given by Python
			print(e)
		return -1

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
		# print("Receiving a GET on path %s" % self.path)
		if self.path == '/':
			self.do_GET_Index()
		elif self.path == '/board':
			self.do_GET_Board()
		elif self.path == '/nextid':
			self.do_GET_Next_id()
		else:
			 self.wfile.write('error')
#------------------------------------------------------------------------------------------------------
# GET logic - specific path
#------------------------------------------------------------------------------------------------------
	
	#Sends the html code of the first page back to the reqester upon request
	def do_GET_Index(self):
		self.set_HTTP_headers(200)
		header = open(board_frontpage_header_template).read()
		footer = open(board_frontpage_footer_template).read()
		
		self.wfile.write(header + self.render_board() + footer % ('', self.server.leader, self.server.leader_id)) 

  	#Sends the board upon request  
	def do_GET_Board(self):
		self.set_HTTP_headers(200)
		self.wfile.write(self.render_board())

    
  	#Creates and combines and then returns
  	#all the elements of the the board section of the website
	def render_board(self):
		boardcontents = open(boardcontents_template).read()
		entry_t = open(entry_template).read()
		
		entires = []
		for key, value in self.server.store.items():
			entires.append(entry_t % ('entries/'+str(key), key, value))

		return boardcontents % ("title", "".join(entires))

	#Returns the next unique id
	def do_GET_Next_id(self):
		print("GET /nextid")
		self.set_HTTP_headers(200)
		self.wfile.write(self.server.get_next_key())


#------------------------------------------------------------------------------------------------------
	# we might want some other functions
#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# Request handling - POST
#------------------------------------------------------------------------------------------------------
	#Handles all post actions
  	def do_POST(self):
		print("Receiving a POST on %s" % self.path)
		data = parse_qs(self.rfile.read(int(self.headers['Content-Length'])))
		print data
		self.set_HTTP_headers(200)

    	#If the post path is /propagate, we retrieve and store the data
    	#/propagate is used when the POST request was invoked from another vessel
		if self.path == '/propagate':
			value = data['value'][0] if 'value' in data.keys() else ''
			self.update_store(data['action'][0],data['key'][0],value)
		elif self.path == '/election':
			self.propagate_leader(data['action'][0],data['key'][0],data['value'][0])
    	#Otherwise it was called from a client. In that case we handle the separate
    	#cases on our own and propagate the request, along with the affected entry
    	#to all other vessels
		else:
			action = ""
			key = ""
			value = ""
			
			if self.path == '/board': #Add new entry
				action = 'add'
				value = data['entry'][0]
				# If this is leader get the key locally
				if int(self.server.leader_id) == self.server.id:
					key = self.server.get_next_key()
				# If not leader request the key from the leader
				else: 
					key = self.server.request_next_id()
				self.server.add_value_to_store(key, value)
			elif self.path.startswith('/entries/'):
				key = data['id'][0]
				#If delete is set: delete value
				if data['delete'][0] == '1':
					action = 'delete'
					self.server.delete_value_in_store(key)
				#If delete is not set: update value
				else:
					action = 'modify'
					value = data['entry'][0]
					self.server.modify_value_in_store(key, value)
			else:
				self.send_error(404)

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
		
  	#Updates the store variable (which contains the values of all entries)  
	def update_store(self, action, key, value):
		# print("%s,%s,%s,%d,%d", (action, key, value, self.server.leader_id, self.server.id))
		if action == 'add':
			return self.server.add_value_to_store(key, value)
		elif action == 'modify':
			return self.server.modify_value_in_store(key, value)
		elif action == 'delete':
			return self.server.delete_value_in_store(key)

	#Sets the leader or continue sending election messages
	def propagate_leader(self, action, key, value):
		# action is used to store the vessel id of the origin of the message.
		# If This server was the origin use message to set the leader
		if int(action) == int(self.server.vessel_id):
			self.server.leader_id = key
			self.server.leader = "10.1.0.%s" % value
			print("Elected %s as leader" % self.server.leader)
		else:
			#If this nodes id is greater than the id in the message
			# update the message before sending it to the next node 
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
