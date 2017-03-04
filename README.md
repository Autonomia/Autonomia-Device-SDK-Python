# Autonomia Python Client SDK
## Overview
This Python library provides a simple wrapper around our device and video management [API](http://www.autonomia.io). Typical use would be to develop a connected application running on a vehicle on-board computer. 


The library is providing the `AutonomiaClient` class and methods used to connect an on-board computer to the Autonomia Cloud infrastructure and to handle remote interactions with the vehicle.
#### Cloud to vehicle
The Autonomia API allows to send messages to vehicle messages and to receive synchronous responses in the tpyical RPC pattern. This library provides a simple way to bind user-defined functions to JSON/RPC methods.


After instantiating an AutonomiaClient object the `attach` method connects the vehicle to the Autonomia Cloud. Once a vehicle is attached, an application uses the vehicle's WebSockets endpoint or the HTTPS API to invoke remote methods with JSON/RPC.
>The library implements also the receive loop and the heartbeat function as a separate threads.

#### Vechicle to cloud
The library is also used to send asynchronous event data messages upstream to the Autonomia server, telemetry for instance. The telemetry messages are propagated by the Autonomia cloud server to all open WebSockets endpoints and are relayed to the real-time analytics pipeline.
## Installation
To install the `autonomialib` Python module, clone or download and unzip this repo, and from the Autonomia-SDK-Python directory run:


|:----                      
| `python setup.py install` |



## Setup

Use of the library in a vehicle application require an `APPLICATION_KEY` to authenticate a vehicle connecting to the Autonomia Cloud and to associate it with the Application.

You can create an Application and obtain the `APPLICATION_KEY` from [http://developer.autonomia.io](http://developer.autonomia.io)

To use the library is required to set the environmental variable `AUTONOMIA_APP_KEY` to a valid Application Key.
>An established Internet connection and a video camera are also required in the vehicle.

## Getting Started

Create a simple logger, get the `APPLICATION_KEY` and instatiate an `AutonomiaClient` object:
```
import time
import os
from autonomialib import AutonomiaClient

application_key = os.environ.get('AUTONOMIA_APP_KEY', None)

def applog(msg):
  """Simple system logger."""
  systime = int(time.time())
  print ("[%d] %s" % (systime, msg))
  
car = AutonomiaClient(application_key, applog)  
```

Once the `AutonomiaClient` object has been instantiated, define the RPC methods and the `rpc_methods` tuple: 
```
# RPC methods binding
rpc_methods = (  
    {'name':'video_start','function':_video_start}, 
    {'name':'video_stop','function':_video_stop}, 
)

def _video_stop(params):
  car.video_stop()
  return {"success": True}  

def _video_start(params):
  _, url = car.video_start()
  # return the live stream URL
  return {"success": True, "url": url}  
```
Connect the vehicle to the Autonomia Cloud and get the server response:

```
reply = car.attach(rpc_methods)

# The server returns an object like: {"msg":"200 OK","heartbeat":60,"timestamp":1441405206}
applog("Device \"%s\" attached to Autonomia. Server returned: %s" % (car.device_id, reply))
```
>The vehicle ID obtained in the library is available as object property `device_id`

Once the vehicle is connected JSON/RPC methods can be remotely invoked by sending to its WebSocket endpoint on the Autonomia Cloud server (api.autonomia.io) a message such as:
```
{"jsonrpc":"2.0","method":"video_start","params":{},"id":7}
```
To send event data or telemetry upstream, the `send_data` method is used:
```
car.send_data(msg)
```
As with video, telemetry data for each vehicle is both processed in the analytics pipeline and saved for later retrival.

## Documentation
Summary of methods expoerted:

| Method        | Parameters           | Comments  |
| ------------- |:-------------:| -----:|
| AutonomiaClient | application_key, applog, use_ssl=True | class constructor |
| attach | rpc_methods, device_id=get_mac(), device_info="Autonomia"  | vehicle connection |
| send_data | msg   | send telemetry upstream |
| video_start | timestamp=False   | start video streaming |
| video_stop | -   | stop video streaming |

Read more code examples and API references at [https://sdk.autonomia.io](https://sdk.autonomia.io)
