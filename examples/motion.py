# I believe this code is based on a tutorial at:
# https://www.pyimagesearch.com/2015/06/01/home-surveillance-and-motion-detection-with-the-raspberry-pi-python-and-opencv/

from picamera.array import PiRGBArray
import datetime
import imutils
import os
import socket

import cv2
import numpy as np

class TempClient():
    
    def __init__(self, basePath="/tmp/"):
        self.basePath = basePath

    def upload(self, frame, timestamp):
        # write the image to temporary file
        t = os.path.join(self.basePath, "motion.png")
        cv2.imwrite(t, frame)
        print( f"Wrote image to {t}" )

def getImage():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host ="127.0.0.1"
        port = 12346
        s.connect((host,port))
        s.sendall("image".encode()) 
# need to shutdown our write end of the socket so the server knows it's time to send the image
        s.shutdown(socket.SHUT_WR)
        sfile = s.makefile('rb')
        jpeg_byte_string = sfile.read() 
        sfile.close()
        s.close()
        return jpeg_byte_string
    except Exception as inst:
        raise

if __name__ == "__main__":

    conf = {
        "min_upload_seconds": 3.0,
        "min_motion_frames": 4,
        "delta_thresh": 5,
        "resolution": [640, 480],
        "min_area": 5000
        }

    client = TempClient()

    avg = None
    lastUploaded = datetime.datetime.now()
    motionCounter = 0

# Read images from the camera daemon
    while True:
        jpeg_byte_string = getImage()
        cv2_img_flag=cv2.IMREAD_COLOR
        img_array = np.asarray(bytearray(jpeg_byte_string), dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2_img_flag)

        # the timestamp and occupied/unoccupied text
        timestamp = datetime.datetime.now()
        text = "Unoccupied"
     
        # resize the frame, convert it to grayscale, and blur it
        frame = imutils.resize(frame, width=500)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
     
        # if the average frame is None, initialize it
        if avg is None:
            print("[INFO] starting background model...", flush=True)
            avg = gray.copy().astype("float")
            continue
     
        # accumulate the weighted average between the current frame and
        # previous frames, then compute the difference between the current
        # frame and running average
        cv2.accumulateWeighted(gray, avg, 0.5)
        frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

        # threshold the delta image, dilate the thresholded image to fill
        # in holes, then find contours on thresholded image
        thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if imutils.is_cv2() else cnts[1]
     
        # loop over the contours
        for c in cnts:
            # if the contour is too small, ignore it
            if cv2.contourArea(c) < conf["min_area"]:
                continue
    
            # compute the bounding box for the contour, draw it on the frame,
            # and update the text
            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            text = "Occupied"
     
        # draw the text and timestamp on the frame
        ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
        cv2.putText(frame, "Room Status: {}".format(text), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        # check to see if the room is occupied
        if text == "Occupied":
            # check to see if enough time has passed between uploads
            if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
                # increment the motion counter
                motionCounter += 1
     
                # check to see if the number of frames with consistent motion is
                # high enough
                if motionCounter >= conf["min_motion_frames"]:
                    client.upload(frame,ts)
     
                    # update the last uploaded timestamp and reset the motion
                    # counter
                    lastUploaded = timestamp
                    motionCounter = 0
     
        # otherwise, the room is not occupied
        else:
            motionCounter = 0
