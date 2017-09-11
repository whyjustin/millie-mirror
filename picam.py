"""Raspberry Pi Face Recognition Treasure Box
Pi Camera OpenCV Capture Device
Copyright 2013 Tony DiCola
Pi camera device capture class for OpenCV.  This class allows you to capture a
single image from the pi camera as an OpenCV image.
"""
import threading

import picamera
import picamera.array


class OpenCVCapture:
    def __init__(self):
        self._capture_frame = None
        self._camera = picamera.PiCamera(sensor_mode=5)
        self._rawCapture = picamera.array.PiRGBArray(self._camera)

        self._capture_thread = threading.Thread(target=self._grab_frames)
        self._capture_thread.daemon = True
        self._capture_thread.start()

    def _grab_frames(self):
        for f in self._camera.capture_continuous(self._rawCapture, format="bgr", use_video_port=True):
            self._capture_frame = f.array
            self._rawCapture.truncate(0)

    def read(self):
        return self._capture_frame
