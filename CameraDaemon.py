#!/usr/bin/python

# To start the Camera Daemon:
#   python3 CameraDaemon.py start
#
# PiCamera documentation: http://picamera.readthedocs.io/en/release-1.10/api_camera.html

import logging
import time
import socket
import threading
import os
import datetime
import io
import atexit
import argparse

from picamera import PiCamera

import daemon
from daemon import pidfile
from DaemonBase import DaemonBase

class RpiCameraDaemon(DaemonBase):
    
    def __init__(self, port, *args, extra2=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.port = port
        self.recording = False
        self.camera = None

    def setup_logging(self):
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.INFO)

        fh = logging.FileHandler(self.log_file)
        fh.setLevel(logging.INFO)

        formatstr = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(formatstr)

        fh.setFormatter(formatter)

        self.logger.addHandler(fh)

    def run(self):
        self.setup_logging()
        self.camera = PiCamera()

        server = socket.socket()
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1",self.port))
        server.listen(5)
        self.logger.info("Starting up")
        self.logger.info(f"Listenting to port {self.port}")
        atexit.register(self.stopCamera)

        while True:
            conn, address = server.accept()
            thread = threading.Thread(target=self.handle_client, args=[conn])
            thread.daemon = True
            thread.start()

    def handle_client(self, sock):
        for line in sock.makefile('r'):
            self.logger.info(line)
            if line.startswith( 'video_start', 0, len('video_start') ):
                self.startVideo( line[len('video_start '):] )
            elif line.startswith( 'video_stop', 0, len('video_stop') ):
                self.endVideo( line[len('video_stop '):] )
            elif line.startswith( 'set ', 0, len('set ') ):
                self.adjust( line[len('set '):] )
            else:
                jpeg_byte_string = self.getImage2()
                sock.sendall( jpeg_byte_string )
                sock.close()
                #self.logger.info( "Writing camera image" )

    def stopCamera(self):
        if self.camera:
            if self.camera.recording:
                self.camera.stop_recording()
            self.camera.close()
        self.logger.info("Shutting down")

    def getImage2(self):
        my_stream = io.BytesIO()
        self.camera.capture(my_stream, 'jpeg')
        my_stream.seek(0)
        image_string = my_stream.read(-1)
        return image_string

    def adjust(self, args):
        try:
            attr, value = args.split(' ')
            if attr == 'brightness':
                value = int(value)
                if value > 0 and value <= 100:
                    print( "setting brightness: " + str(value) )
                    self.camera.brightness = value
            elif attr == 'shutter_speed':
                value = int(value)
                self.camera.shutter_speed = value
                print( "setting shutter speed: " + str(value) )
            elif attr == 'iso':
                value = int(value)
                self.camera.iso = value
                print( "setting iso: " + str(value) )
            elif attr == 'framerate':
                value = int(value)
                self.camera.framerate = value
                print( "setting framerate: " + str(value) )
        except Exception as ex:
            print( "Exception: {}".format( ex ) )

    def startVideo(self, filename):
        if self.camera.recording:
            self.camera.stop_recording()

        filename = os.path.basename(filename)
        if not filename:
            filename = "malpi.h264"
        if not filename.endswith(".h264"):
            filename += ".h264"
        filename = os.path.join("/var/ramdrive", filename)

        #Other possible options
        #camera.annotate_text = "Hello world!"
        #camera.brightness = 50 #0-100
        #camera.contrast = 50 #0-100

        self.camera.resolution = (640, 480)
        self.camera.framerate = 15
        self.camera.start_recording(filename)
        self.recording = True

    def endVideo(self, filename):
        if self.camera.recording:
            self.camera.stop_recording()

if __name__ == "__main__":

    test = RpiCameraDaemon( 12346, "RpiCameraDaemon", verbose=False)
    parser = test.createArgsParser(description="RPi Camera Daemon")
    # add any extra command line arguments here
    #    the results can be accessed via self.args after handleArgs is called
    test.handleArgs()
