# ![](https://storage.googleapis.com/material-icons/external-assets/v4/icons/svg/ic_info_outline_black_24px.svg) Autonomia Device SDK for Python
Provides a simple wrapper around [Autonomia Device Side API](http://www.autonomia.io). Typical use would be to develop a connected application running on a vehicle on-board computer.

It allows to connect an on-board computer to the Autonomia Cloud infrastructure and handle remote interactions with the vehicle.

![](https://storage.googleapis.com/material-icons/external-assets/v4/icons/svg/ic_cloud_black_24px.svg) ![](https://storage.googleapis.com/material-icons/external-assets/v4/icons/svg/ic_arrow_forward_black_24px.svg) ![](https://storage.googleapis.com/material-icons/external-assets/v4/icons/svg/ic_directions_car_black_24px.svg) 
The Autonomia API enables you to send messages to the vehicle and get synchronous responses in the tpyical RPC pattern. This library provides a simple way to bind user-defined functions to JSON/RPC methods.

![](https://storage.googleapis.com/material-icons/external-assets/v4/icons/svg/ic_cloud_black_24px.svg) ![](https://storage.googleapis.com/material-icons/external-assets/v4/icons/svg/ic_arrow_back_black_24px.svg) ![](https://storage.googleapis.com/material-icons/external-assets/v4/icons/svg/ic_directions_car_black_24px.svg) 
The library is also used to send asynchronous event data messages upstream to the Autonomia server, telemetry for instance. The telemetry messages are propagated by the Autonomia cloud server to all open WebSockets endpoints and are relayed to the real-time analytics pipeline.


# ![](https://storage.googleapis.com/material-icons/external-assets/v4/icons/svg/ic_phonelink_setup_black_24px.svg) Setup `autonomialib` Python module
- `git clone https://github.com/Autonomia/Autonomia-Device-SDK-Python.git`
- `Autonomia-Device-SDK-Python` 
- `sudo python setup.py install`

# ![](https://storage.googleapis.com/material-icons/external-assets/v4/icons/svg/ic_code_black_24px.svg) Code Samples
- For a complete example check [**this**](https://github.com/Autonomia/Autonomia-Device-Sample-RPI). Get your API key [**@DeveloperPortal**](https://developer.autonomia.io)
- `export AUTONOMIA_APP_KEY="your-api-key"`
- Copy & Paste this code
```python
import time
import os
from autonomialib import AutonomiaClient

application_key = os.environ.get('AUTONOMIA_APP_KEY', None)

def applog(msg):
  systime = int(time.time())
  print ("[%d] %s" % (systime, msg))

car = AutonomiaClient(application_key, applog)

# RPC methods binding
rpc_methods = (  
    {'name':'video_start', 'function':_video_start},
    {'name':'video_stop' , 'function':_video_stop }
)

def _video_stop(params):
  car.video_stop()
  return {"success": True}  

def _video_start(params):
  _, url = car.video_start()
  # return the live stream URL
  return {"success": True, "url": url}  

# Connect the vehicle to the Autonomia Cloud and get the server response:
reply = car.attach(rpc_methods)

# The server returns an object like: {"msg":"200 OK","heartbeat":60,"timestamp":1441405206}
applog("Device \"%s\" attached to Autonomia. Server returned: %s" % (car.device_id, reply))
```

- At this point a client application can call JSON/RPC methods by sending to its WebSocket endpoint on the Autonomia Cloud server (api.autonomia.io) a message such as:
```javascript
{
    "jsonrpc":"2.0",
    "method":"video_start",
    "params":{},
    "id":7
}
```

- To send event data or telemetry upstream, the `send_data` method is used:
```python
car.send_data(msg)
```

# ![](https://storage.googleapis.com/material-icons/external-assets/v4/icons/svg/ic_verified_user_black_24px.svg) API
| Method          | Parameters                                                | Comments                |
| ----            |:----                                                      |:-----                   |
| AutonomiaClient | application_key, applog, use_ssl=True                     | class constructor       |
| attach          | rpc_methods, device_id=get_mac(), device_info="Autonomia" | vehicle connection      |
| send_data       | msg                                                       | send telemetry upstream |
| video_start     | timestamp=False                                           | start video streaming   |
| video_stop      | -                                                         | stop video streaming    |

Read more code examples and API references at [https://sdk.autonomia.io](https://sdk.autonomia.io)
