"""
  Cloud connected autonomous RC car.

  Copyright 2016 Visible Energy Inc. All Rights Reserved.
"""
__license__ = """
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

import os
import time
import subprocess
import hashlib
import hmac

# set resolution and encoding (Logitech C920)
# v4l2-ctl --device=/dev/video0 --set-fmt-video=width=960,height=720,pixelformat=1
# v4l2-ctl --list-formats

def buildKey(mac, secret):
    """Return the camera streaming key."""
    h = hmac.new(secret, mac, digestmod=hashlib.sha256).hexdigest()
    return mac + ':' + h[0:32]

def isRPIcamera():
  ret = False
  # Detect if running on RPI
  platform = 'rpi' if 'raspberrypi' in os.uname() else 'linux'
  print 'Platform: ' + platform

  # import the RPI streamer
  if platform == 'rpi':
    try:
      import picamera
      camera = picamera.PiCamera()
      resolution = camera.resolution
      camera.close()
      print 'Detected RPI camera. Resolution: ' + str(resolution)
      ret = True
    except Exception, e:
      # import the Linux streamer
      print 'Using USB camera.'
  else:
    # import the Linux streamer
    import streamer
    print 'Using USB camera.'      
  return ret

def video_stop():
  """ Stop running video capture streamer """
  pname = 'ffmpeg' 
  s = 'killall ' + pname
  FNULL = open(os.devnull, 'w')
  try:
    # execute and wait for completion
    subprocess.check_call(s, shell=True, stderr=FNULL) 
  except Exception, e:
      pass
  return

def rpi_cam_start(device_id, application_key, timestamp):
  FNULL = open(os.devnull, 'w')

  if not timestamp:
    # raspivid 
    params = ['raspivid', '-o', '-', '-t', '0',  '-vf', '-w', '1280', '-h', '720', '-fps', '30', '-b', '1000000', '-t', '5000']
    # params = ['raspivid', '-o', '-', '-t', '0', '-vf', '-hf', '-w', '1920', '-h', '1080', '-fps', '30', '-b', '2000000', '-t', '5000']
    raspivid_pid = subprocess.Popen(params, stdout=subprocess.PIPE)
    params = ['ffmpeg', '-r','30', '-use_wallclock_as_timestamps', '1', '-thread_queue_size', '512', '-f', 'h264', '-i', '-', '-vcodec', 'copy', '-g', '30', '-strict', 'experimental']
    server = 'stream.autonomia.io:12345'
    key = buildKey(device_id, application_key)
    url = 'rtmp://' + server + '/src/' + key + ':1'
    params = params + ['-threads', '4', '-f', 'flv', url]

    process = subprocess.Popen(params, stdin=raspivid_pid.stdout, stderr=FNULL)
    raspivid_pid.stdout.close()  
  else:
    # raspivid 
    #params = ['raspivid', '-o', '-', '-t', '0', '-vf', '-hf', '-w', '1280', '-h', '720', '-fps', '30', '-b', '2000000', '-t', '5000']
    params = ['raspivid', '-o', '-', '-t', '0', '-vf', '-w', '1280', '-h', '720', '-fps', '30', '-b', '2000000', '-t', '5000']
    raspivid_pid = subprocess.Popen(params, stdout=subprocess.PIPE)
    params = ['ffmpeg', '-r','30', '-use_wallclock_as_timestamps', '1', '-thread_queue_size', '512', '-f', 'h264', '-i', '-', '-vcodec', 'h264', '-g', '30', '-strict', 'experimental']
    server = 'stream.autonomia.io:12345'
    key = buildKey(device_id, application_key)
    url = 'rtmp://' + server + '/src/' + key + ':1'
    format = "drawtext=fontfile=/usr/share/fonts/truetype/freefont/FreeSans.ttf: text='%{localtime}':x=0:y=(h-th-2): fontsize=24: fontcolor=white: box=1: boxcolor=black@0.9"
    params = params + ['-vf', format, '-threads', '4', '-f', 'flv', url]

    process = subprocess.Popen(params, stdin=raspivid_pid.stdout, stderr=FNULL)
    raspivid_pid.stdout.close()
  return raspivid_pid, url     
  #raspivid -o - -t 0 -vf -hf -fps 30 -w 1280 -h 720 -b 2000000 | ffmpeg -r 30 -use_wallclock_as_timestamps 1 -f h264 -i - -vcodec copy -g 30 -strict experimental -f flv rtmp://stream.autonomia.io:12345/src/7777

def video_start(serial, app_key, timestamp=True):
  """ Start a video streamer """ 

  # insure streamer is not already running
  video_stop()
  time.sleep(0.5)

  if isRPIcamera():
    return rpi_cam_start(serial, app_key, timestamp)

  videodevs = ["/dev/" + x for x in os.listdir("/dev/") if x.startswith("video") ]
  if len(videodevs) == 0:
    print "Fatal error. Cannot proceed without cameras connected."
    return None, None

  # use the first camera
  camera=videodevs[0]
  print 'start video from: ' + camera

  pname = 'ffmpeg'
  vcodec = 'h264'
  server = 'stream.autonomia.io:12345'
  key = buildKey(serial, app_key)
  # to suppress output when running the streamer
  FNULL = open(os.devnull, 'w')

  if timestamp:
    # streaming video with timestamp -- to increase actual fps increase or remove maxrate and bufsize
    params = [pname, '-r','30', '-use_wallclock_as_timestamps', '1', '-thread_queue_size', '512', '-f', 'v4l2', '-i', camera,'-maxrate', '768k', '-bufsize', '960k']
    format = "drawtext=fontfile=/usr/share/fonts/truetype/freefont/FreeSans.ttf: text='%{localtime}':x=0:y=(h-th-2): fontsize=24: fontcolor=white: box=1: boxcolor=black@0.9"
    url = 'rtmp://' + server + '/src/' + key + ':1'
    params = params + ['-vf', format, '-threads', '4', '-r', '30', '-g', '60', '-f', 'flv', url]
    # spawn a process and do not wait
    pid = subprocess.Popen(params, stderr=FNULL)
  else:
    # streaming video 
    params = [pname, '-r','30', '-use_wallclock_as_timestamps', '1', '-thread_queue_size', '512', '-f', 'v4l2', '-i', camera, '-maxrate', '768k', '-bufsize', '960k']
    url = 'rtmp://' + server + '/src/' + key + ':1'
    params = params + ['-threads', '4', '-r', '30', '-g', '60', '-f', 'flv', url]
    # spawn a process and do not wait
    pid = subprocess.Popen(params, stderr=FNULL)
  return pid, url
  # ffmpeg -r 30 -use_wallclock_as_timestamps 1 -thread_queue_size 512 -f v4l2 -i  /dev/video0 -vb 2000k -vf "drawtext=fontfile=/usr/share/fonts/truetype/freefont/FreeSans.ttf:text='%{localtime}': x=0: y=(h-th-2): fontsize=24: fontcolor=white: box=1: boxcolor=black"  -threads 4 -r 30 -g 30 -f flv rtmp://stream.vederly.com:12345/src/B8AEED7340ED-6e0d2b1002b502ca1cac3c7862a9040f^C
