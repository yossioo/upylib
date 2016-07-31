from http.connection import *

try:
    import usocket as socket
except:
    import socket

try: # mpy/cpython compat in main loop
    BlockingIOError
except:
    class BlockingIOError(Exception):
        pass


class HttpServer():

    def __init__(self,
                 http_handler = HttpConnection,
                 websocket_handler = None,
                 addr = ("0.0.0.0", 80),
                 backlog = 3
                ):
        self.http_handler = http_handler
        self.websocket_handler = websocket_handler
        self.connections = []
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setblocking(False)
        self.s.bind( socket.getaddrinfo(addr[0], addr[1])[0][-1] )
        self.s.listen(backlog)
    
    def serve(self):
        while True:
            # accept new connections
            self.accept()
            # service established connections
            self.service_queue()
    
    def accept(self):
        # TODO: process first request
        # TODO: normal http request, close on complete (despite Connection: Keep-Alive)
        # TODO: websocket request, negotiate, add to websockets list
        try:
            connection = self.http_handler( self.s.accept() )
            if connection.service_requests():
                # connection is to be kept-alive
                self.connections.append( connection )
            # else discarded
        except (OSError, BlockingIOError):
            pass
    
    def service_queue(self):
        # TODO: replace by websocket handler
        for idx,connection in enumerate( self.connections ):
            # drop connections that aren't to be kept-alive
            if not connection.service_requests():
                del( self.connections[idx] )