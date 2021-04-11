# RpiCameraDaemon

A python daemon that reads and provides access to the Raspberry Pi camera.

A base class based on example code from https://github.com/aigo9/python-daemon-example that
uses python-daemon to manage a Linux daemon.

The main class accesses the Raspbery Pi camera and provides images to requesting processes
via unix sockets. This allows multiple processes to access the camera at the same time.
