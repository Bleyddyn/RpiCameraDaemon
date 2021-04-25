import os
import socket

import cv2
import numpy as np

class TempClient():
    
    def __init__(self, basePath="/tmp/"):
        self.basePath = basePath

    def upload(self, frame):
        # write the image to temporary file
        t = os.path.join(self.basePath, "image.png")
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

    client = TempClient()

# Read an image from the camera daemon
    jpeg_byte_string = getImage()
    img_array = np.asarray(bytearray(jpeg_byte_string), dtype=np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    client.upload(frame)
