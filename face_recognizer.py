import cv2
import numpy
import os


class FaceRecognizer:
    def __init__(self):
        self.training_file_name = 'training.xml'
        self.cascade_file_name = 'haarcascade_frontalface_alt'

        self.model = None
        if os.path.isfile(self.training_file_name):
            self.model = cv2.createLBPHFaceRecognizer()
            self.model.load(self.training_file_name)

        self.cascade_classifier = cv2.CascadeClassifier(self.cascade_file_name)

    def update_threshold(self, threshold):
        if os.path.isfile(self.training_file_name):
            self.model = cv2.createLBPHFaceRecognizer(threshold)
            self.model.load(self.training_file_name)

    def detect_faces(self, image):
        image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        faces = self.cascade_classifier.detectMultiScale(image, scaleFactor=1.3, minNeighbors=4, minSize=(30, 30),
                                                        flags=cv2.CASCADE_SCALE_IMAGE)

        detected_faces = []
        for face in faces:
            x, y, w, h = face
            image_face = numpy.copy(image)
            image_face = image_face[y:y + h, x:x + w]
            label, confidence = self.model.predict(image_face)
            detected_faces.append(type('obj', (object,), {'user': label, 'x': x, 'y': y, 'w': w, 'h': h}))

        return detected_faces

