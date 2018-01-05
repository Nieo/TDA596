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
import json
#------------------------------------------------------------------------------------------------------

# Global variables for HTML templates
byzantine_template = 'server/byzantine_template.html'
vote_result_template = 'server/vote_result_template.html'

#------------------------------------------------------------------------------------------------------
# Static variables definitions
PORT_NUMBER = 80
#------------------------------------------------------------------------------------------------------

#Compute byzantine votes for round 1, by trying to create
#a split decision.
#input: 
#   number of loyal nodes,
#   number of total nodes,
#   Decision on a tie: True or False 
#output:
#   A list with votes to send to the loyal nodes
#   in the form [True,False,True,.....]

def compute_byzantine_vote_round1(no_loyal,no_total,on_tie):

    result_vote = {}
    for i in range(1,no_loyal+1):
        if i%2==0:
            result_vote[str(i)] = not on_tie
        else:
            result_vote[str(i)] = on_tie
    return result_vote

#Compute byzantine votes for round 2, trying to swing the decision
#on different directions for different nodes.
#input: 
#   number of loyal nodes,
#   number of total nodes,
#   Decision on a tie: True or False
#output:
#   A list where every element is a the vector that the 
#   byzantine node will send to every one of the loyal ones
#   in the form [[True,...],[False,...],...]
def compute_byzantine_vote_round2(no_loyal,no_total,on_tie):
  
    result_vectors={}
    for i in range(1,no_loyal+1):
        if i%2==0:
            obj = {}
            for a in range(1, no_total+1):
                obj[str(a)] = on_tie
            result_vectors[str(i)] = obj
        else:
            obj = {}
            for a in range(1, no_total+1):
                obj[str(a)] = not on_tie
            result_vectors[str(i)] = obj
    return result_vectors


#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
class BlackboardServer(HTTPServer):
#------------------------------------------------------------------------------------------------------
    def __init__(self, server_address, handler, node_id, vessel_list):
    # We call the super init
        HTTPServer.__init__(self,server_address, handler)
        # our own ID (IP is 10.1.0.ID)
        self.vessel_id = vessel_id
        # The list of other vessels
        self.vessels = vessel_list

        self.round = 0
        self.votes = [[],{},{}]
        self.byzantine = False
        self.result = 'In progress...'

#------------------------------------------------------------------------------------------------------
# Contact a specific vessel with a set of variables to transmit to it
    def contact_vessel(self, vessel, path, iteration, votes):
        # the Boolean variable we will return
        success = False
        # The variables must be encoded in the URL format, through urllib.urlencode
        print("contacting vessel %s" % vessel)
        post_content = json.dumps({'iteration':iteration, 'votes':votes, 'source': self.vessel_id})
        print ("With content %s " % post_content)
        # the HTTP header must contain the type of data we are transmitting, here URL encoded
        headers = {"Content-type": "application/json"}
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
    def propagate_value_to_vessels(self, path, iteration, votes):
        # We iterate through the vessel list
        for vessel in self.vessels:
            # We should not send it to our own IP, or we would create an infinite loop of updates
            if vessel != ("10.1.0.%s" % self.vessel_id):
                # A good practice would be to try again if the request failed
                # Here, we do it only once
                self.contact_vessel(vessel, path, iteration, votes)       

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
        post_data = json.loads(self.rfile.read(length))
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
        elif self.path == '/vote/result':
            self.do_GET_Result()
        else:
             self.wfile.write('error')
#------------------------------------------------------------------------------------------------------
# GET logic - specific path
#------------------------------------------------------------------------------------------------------
    
    #Sends the html code of the first page back to the reqester upon request
    def do_GET_Index(self):
        self.set_HTTP_headers(200)
        self.wfile.write(open(byzantine_template).read()) 

    #Sends the board upon request  
    def do_GET_Result(self):
        self.set_HTTP_headers(200)
        self.wfile.write(self.server.result)

#------------------------------------------------------------------------------------------------------
    # we might want some other functions
#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# Request handling - POST
#------------------------------------------------------------------------------------------------------
    #Handles all post actions
    def do_POST(self):
        print("Receiving a POST on %s" % self.path)
        if self.path == '/vote/attack':
            self.sendVote(True)
        elif self.path == '/vote/retreat':
            self.sendVote(False)
        elif self.path == '/vote/byzantine':
            self.server.byzantine = True
            self.byzantine(1)
            self.server.result = "I'm byza"
        elif self.path == '/propagate':
            data = self.parse_POST_request()
            iteration = int(data['iteration'])
            
            if self.server.byzantine:
                #Act byzantine
                self.server.votes[iteration][str(data['source'])] = []
                if iteration == 1 and len(self.server.votes[iteration]) >= len(self.server.vessels)-1:
                    self.byzantine(2)
            else:    
                #Act correctly    
                self.server.votes[iteration][str(data['source'])] = data['votes']
                print("iteration:%d, current votes %d"%(iteration, len(self.server.votes[iteration])))
                print(self.server.votes[iteration])
                if iteration == 1 and len(self.server.votes[iteration]) >= len(self.server.vessels):
                    print("Starting round 2")
                    #Send round 2 messages
                    thread = Thread(target=self.server.propagate_value_to_vessels, args=("/propagate", 2, self.server.votes[1]))
                    thread.daemon = True
                    thread.start()

                elif iteration == 2 and len(self.server.votes[iteration]) >= len(self.server.vessels)-1:
                    print("Computing result" + json.dumps(self.server.votes[2]))
                    #Compute result
                    result = []
                    print(json.dumps(self.server.votes[2][self.server.votes[2].keys()[0]]))
                    for i in self.server.votes[2][self.server.votes[2].keys()[0]]:
                        false = 0
                        true = 0
                        for j in self.server.votes[2].keys():
                            print("Keys %s, %s"%(j,i))
                            if self.server.votes[2][j][i]:
                                true += 1
                            else:
                                false += 1
                        result.append(false < true)
                    false = 0
                    true = 0
                    for i in result:
                        if i:
                            true += 1
                        else:
                            false += 1
                    self.server.result = ("Attack! " if true > false else "Retreat! ") + ',' + json.dumps(self.server.votes) + json.dumps(result)

        self.set_HTTP_headers(200)
        self.wfile.write("ok")
#------------------------------------------------------------------------------------------------------
# POST Logic
#------------------------------------------------------------------------------------------------------
    # We might want some functions here as well
#------------------------------------------------------------------------------------------------------

    def sendVote(self,attack):
        print("Sending vote command")
        self.server.votes[1][str(self.server.vessel_id)] = attack        
        thread = Thread(target=self.server.propagate_value_to_vessels, args=("/propagate", 1, attack))
        thread.daemon = True
        thread.start()
        if len(self.server.votes[1]) == len(self.server.vessels):
            print("starting round 2;")
            thread2 = Thread(target=self.server.propagate_value_to_vessels, args=("/propagate", 2, self.server.votes[1]))
            thread2.daemon = True
            thread2.start()


    def byzantine(self, iteration):
        #Number of loyal nodes is total-1 for our tasks
        if iteration == 1:
            byzantine_votes = compute_byzantine_vote_round1(len(self.server.vessels)-1, len(self.server.vessels), False)
        else:
            byzantine_votes = compute_byzantine_vote_round2(len(self.server.vessels)-1, len(self.server.vessels), False)
        i = 1
        for vessel in self.server.vessels:
            if vessel != ("10.1.0.%s" % self.server.vessel_id):
                thread = Thread(target=self.server.contact_vessel, args=(vessel, "/propagate", iteration, byzantine_votes[str(i)]))
                thread.daemon = True
                thread.start()
                i += 1




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

