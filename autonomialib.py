"""
Author:  Emile Camus
"""
__license__ = """
Copyright 2015 Visible Energy Inc. All Rights Reserved.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
__all__ = ["AutonomiaClient"]

import socket
import select
import time
import threading
import ssl
import fcntl
import struct
import array
import sys
import os
import json

# From http-parser (0.8.3)
# pip install http-parser
from http_parser.parser import HttpParser
import streamer

#------------------ TODO: move to autonomia.io
AUTONOMIA_SERVER='cometa.vederly.com'

def message_handler(msg, msg_len):
  """
  The generic JSON-RPC message handler for Autonomia receive callback.
  Invoked every time the Autonomia object receives a JSON-RPC message for this device.
  It returns the JSON-RPC result object to send back to the application that sent the request.
  The rpc_methods tuple contains the mapping of names into functions.
  """
  try:
    req = json.loads(msg)
  except Exception as e:
    # the message is not a json object
    # print("Received JSON-RPC invalid message (parse error): %s" % msg)
    return JSONError.JSON_RPC_PARSE_ERROR

  # check the message is a proper JSON-RPC message
  ret,id = check_rpc_msg(req)
  if not ret:
    if id and isanumber(id):
      return JSONError.JSON_RPC_INVALID_PARAMS_FMT_NUM % id
    if id and isinstance(id, str):
      return JSONError.JSON_RPC_INVALID_PARAMS_FMT_STR % id
    else:
      return JSONError.JSON_RPC_PARSE_ERROR

  # print("JSON-RPC: %s" % msg)

  method = req['method']
  func = None
  # check if the method is in the registered list
  for m in AutonomiaClient._rpc_methods:
    if m['name'] == method:
        func = m['function']
        break

  if func == None:
    return JSONError.JSON_RPC_INVALID_REQUEST

  # call the method
  try:
    result = func(req['params'])
  except Exception as e:
    print e
    return JSONError.JSON_RPC_INTERNAL_ERROR_FMT_STR % str(id)

  # build the response object
  reply = {}
  reply['jsonrpc'] = "2.0"
  reply['result'] = result
  reply['id'] = req['id']

  return json.dumps(reply)

def check_rpc_msg(req):
    ret = False
    id = None
    k = req.keys()
    # check presence of required id attribute
    if 'id' in k:
        id = req['id']
    else:
        return ret, id
    # check object length
    if (len(k) != 4):
        return ret, id
    # check presence of required attributes
    if (not 'jsonrpc' in k) or (not 'method' in k) or (not 'params' in k):
        return ret, id
    # check for version
    if req['jsonrpc'] != "2.0":
        return ret, id
    # valid request
    return True,id

def isanumber(x):
    try:
        int(x)
    except ValueError:
        try:
            float(x)
        except ValueError:
            return False
    return True

class AutonomiaClient(object):
  """
  Connect a device to the Autonomia infrastructure.
  Methods exported:
    AutonomiaClient(application_key, logger, use_ssl=True) -- Object constructor
    attach(rpc_methods, device_id=get_mac(), device_info="Automomia-Vehicle") -- Attach the device to the Autonomia cloud server
    send_data(msg) -- Send a data event message upstream to the Autonomia cloud server
    start_video(timestamp=False) -- Start video streaming to Autonomia cloud
    stop_video() -- Stop video streaming
  """

  errors = {0:'ok', 1:'timeout', 2:'network error', 3:'protocol error', 4:'authorization error', 5:'wrong parameters', 9:'internal error'} 
  _rpc_methods = None
  
  def __init__(self, application_key, logger, use_ssl=True):
    """
    The Autonomia instance constructor.

    server: the Autonomia server FQDN
    port: the Autonomia server port
    application_id: the Autonomia application ID
    """
    self.error = 9
    self.debug = False
    self.device_id = ""
    self.log = logger

    self._server = AUTONOMIA_SERVER
    self._port =  443 if use_ssl else 80
    self._app_key = application_key
    self._use_ssl = use_ssl
    self._message_cb = message_handler # default message handlerNone

    self._platform = ""
    self._hparser = None
    self._sock = None #socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self._heartbeat_rate = 60
    self._trecv = None
    self._thbeat = None
    self._hb_lock = threading.Lock()
    self._reconnecting = False
    return

  def get_mac():
    """
    Get the device MAC address. Linux host.
    """
    if 'linux' not in sys.platform:
      from uuid import getnode
      return getnode()
    # proper MAC on Linux
    # try Ethrnet first
    try:
      ifname = 'eth0'
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', ifname[:15]))
    except Exception, e:
      # try WiFi
      ifname = 'wlan0'
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', ifname[:15]))

    return ''.join(['%02X' % ord(char) for char in info[18:24]])

  def attach(self, rpc_methods, device_id=get_mac(), device_info="ROV"):
    """
    Attach the specified device to the Autonomia cloud server. 
    Authentication is done using only the application_id (one-way authentication).

    rpc_methods: tuple with RPC method callbacks
    device_id: the device unique identifier -- default is device's MAC address
    device_info: a description of the platform or the device (used only as a comment)
    """
    self.device_id = device_id
    self._platform = device_info
    self._hparser = HttpParser()
    AutonomiaClient._rpc_methods = rpc_methods
    print '-----------in attach'
    print AutonomiaClient._rpc_methods

    tsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if self._use_ssl:
      self._sock = ssl.wrap_socket(tsock, ssl_version=ssl.PROTOCOL_SSLv23,  ciphers="AES256-GCM-SHA384")
    else:
      self._sock = tsock
    try:
      self._sock.connect((self._server, self._port))
      sendBuf="POST /v1/applications/%s/devices/%s HTTP/1.1\r\nHost: api.autonomia.io\r\nContent-Length:%d\r\n\r\n%s" % (self._app_key,device_id,len(device_info),device_info)
      self._sock.send(sendBuf)
      recvBuf = ""
      while True:
        data = self._sock.recv(1024)
        if not data:
          break

        dataLen = len(data)
        nparsed = self._hparser.execute(data, dataLen)
        assert nparsed == dataLen

        if self._hparser.is_headers_complete():
          if self.debug:
            print "connection for device %s headers received" % (device_id)
            print self._hparser.get_headers()

        if self._hparser.is_partial_body():
          recvBuf = self._hparser.recv_body()
          if self.debug:
            print "connection for device %s body received" % (device_id)
            print recvBuf         
          #TODO: check for error in connecting, i.e. 403 already connected

          # reading the attach complete message from the server  
          # i.e. {"msg":"200 OK","heartbeat":60,"timestamp":1441382935}
          if len(recvBuf) < 16 or recvBuf[1:12] != '"msg":"200"':
            self.error = 5
            print "Error in string from server; %s" % recvBuf
            return recvBuf

          # reset error
          self.error = 0

          # set the socket non blocking
          self._sock.setblocking(0) 

          # do not (re)start the threads during a reconnection
          if self._reconnecting:
            self._reconnecting = False
            return recvBuf

          if self.debug:
            print "connection for device %s completed" % (device_id)
                      # start the hearbeat thread
          self._thbeat = threading.Thread(target=self._heartbeat)
          self._thbeat.daemon = True
          self._thbeat.start()
            
          # start the receive thread
          #time.sleep(2)
          self._trecv = threading.Thread(target=self._receive)
          self._trecv.daemon = True # force to exit on SIGINT
          self._trecv.start()
          return recvBuf
    except Exception, e:
      print e
      self.error = 2
      return

  def send_data(self, msg):
    """
    Send a data event message upstream to the Autonomia cloud server.
    The Autonomia server propagates the message to all open devices Websockets. 
    """
    sendBuf = "%x\r\n%c%s\r\n" % (len(msg) + 1,'\07',msg)
    if self._reconnecting:
      if self.debug:
        print "Error in Autonomia.send_data(): device is reconnecting."
      return -1
    try:
      self._hb_lock.acquire()
      self._sock.send(sendBuf)
      self._hb_lock.release()     
    except Exception, e:
      if self.debug:
        print "Error in Autonomia.send_data(): socket write failed."
      return -1
    return 0

  def bind_cb(self, message_cb):
    """
    Binds the specified user callback to the Autonomia instance.
    """
    self._message_cb = message_cb
    return

  def perror(self):
    """
    Return a string for the current error.
    """
    return AutonomiaClient.errors[self.error]

  def _heartbeat(self):
    """
    The heartbeat thread.
    The hearbeat message is a chunk of length 3 with the MSG_HEARBEAT byte and closed with CRLF.
    This thread detects a server disconnection and attempts to reconnect to the Autonomia server.
    """
    if self.debug:
      print "Hearbeat thread started.\r"
        
    while True:
      time.sleep(self._heartbeat_rate)
      if self._reconnecting:
        print "--- heartbeat while reconnecting"
        continue  
      sendBuf = "1\r\n%c\r\n" % '\06'
      self.log("sending heartbeat")
      try:
        self._hb_lock.acquire()
        self._sock.send(sendBuf)
        self._hb_lock.release()
      except Exception, e:
        print "--- error sending heartbeat"
        return

  def _receive(self):
    """
    The receive and user callback dispatch loop thread.
    """
    if self.debug:
      print "Receive thread started.\r"
    while True:
      ready_to_read, ready_to_write, in_error = select.select([self._sock.fileno()],[],[self._sock.fileno()], 15)

      # check for timeout
      if not (ready_to_read or ready_to_write or in_error):
        continue

      for i in in_error:
        # handle errors as disconnections and try to reconnect to the server
        print "Network error in receive loop (error). Reconnecting..."
        self._sock.close()
        # self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._reconnecting = True
        ret = self.attach(self.rpc_methods, self.device_id, self._platform)
        if self.error != 0:
          print "Error in attaching to Autonomia.", self.perror()
          time.sleep(15)
          continue
        else:
          print "Device attached to Autonomia.", ret
        continue

      data = None
      for i in ready_to_read:
        try:
          data = self._sock.recv(1024)
        except Exception, e:
          print e
          pass

      if not data:
        if self._use_ssl:
          # ssl read may return no data
          continue
          
        # handle errors as disconnections and try to reconnect to the server
        print "Network error in receive loop (no data). Reconnecting..."
        try:
          self._sock.close()
        except Exception, e:
          print "--- exception in close socket."
          pass
        
        # self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._reconnecting = True
        ret = self.attach(self.rpc_methods, self.device_id, self._platform)
        if self.error != 0:
          print "Error in attaching to Autonomia.", self.perror()
          time.sleep(15) 
          continue
        else:
          print "Device attached to Autonomia.", ret       
        continue

      if self.debug:
        print "** received: %s (%d)" % (data, len(data))      
      self._hparser.execute(data, len(data))
      if self._hparser.is_partial_body():
        to_send = self._hparser.recv_body()
        # the payload contains a HTTP chunk
        if self._message_cb:
          # invoke the user callback 
          reply = self._message_cb(to_send, len(to_send))
        else:
          reply = ""
        if self.debug:
          print "After callback."
      else:
        continue

      if self.debug:
        print "Returning result."
      sendBuf = "%x\r\n%s\r\n" % (len(reply),reply)
      try:
        self._hb_lock.acquire()
        self._sock.send(sendBuf)
        self._hb_lock.release()
      except Exception, e:
        print "--- error sending reply"
        pass
      msg = ""     

  def video_start(self, timestamp=False):
    return streamer.video_start(self.device_id, self._app_key, timestamp)

  def video_stop(self):
    return streamer.video_stop()

class JSONError:
  # JSON-RPC errors
  #
  JSON_RPC_PARSE_ERROR = '{"jsonrpc": "2.0","error":{"code":-32700,"message":"Parse error"},"id": null}'
  JSON_RPC_INVALID_REQUEST = '{"jsonrpc": "2.0","error":{"code":-32600,"message":"Invalid Request"},"id":null}'

  JSON_RPC_METHOD_NOTFOUND_FMT_STR = '{"jsonrpc":"2.0","error":{"code": -32601,"message":"Method not found"},"id": %s}'
  JSON_RPC_METHOD_NOTFOUND_FMT_NUM = '{"jsonrpc":"2.0","error":{"code": -32601,"message":"Method not found"},"id": %d}'
  JSON_RPC_INVALID_PARAMS_FMT_STR = '{"jsonrpc":"2.0","error":{"code": -32602,"message":"Method not found"},"id": %s}'
  JSON_RPC_INVALID_PARAMS_FMT_NUM = '{"jsonrpc":"2.0","error":{"code": -32602,"message":"Method not found"},"id": %d}'
  JSON_RPC_INTERNAL_ERROR_FMT_STR = '{"jsonrpc":"2.0","error":{"code": -32603,"message":"Method not found"},"id": %s}'
  JSON_RPC_INTERNAL_ERROR_FMT_NUM = '{"jsonrpc":"2.0","error":{"code": -32602,"message":"Method not found"},"id": %d}'

