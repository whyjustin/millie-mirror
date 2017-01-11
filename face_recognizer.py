import os
import shutil

import cv2
import numpy


class FaceRecognizer:
    def __init__(self, settings):
        self.training_file_name = 'training.xml'
        self.cascade_file_name = 'haarcascade_frontalface_alt.xml'
        self.training_image_directory = 'training_images'
        self.training_user = None
        self.training_user_iteration = None
        self.settings = settings

        self.model = None
        if os.path.isfile(self.training_file_name):
            self.model = cv2.createLBPHFaceRecognizer(threshold=self.settings.recognition_threshold)
            self.model.load(self.training_file_name)

        self.cascade_classifier = cv2.CascadeClassifier(self.cascade_file_name)

    def detect_faces(self, image):
        image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        faces = self.cascade_classifier.detectMultiScale(image, scaleFactor=1.2, minNeighbors=3, minSize=(50, 50),
                                                        flags=cv2.cv.CV_HAAR_SCALE_IMAGE)

        detected_faces = []
        for face in faces:
            x, y, w, h = face
            image_face = numpy.copy(image)
            image_face = image_face[y:y + h, x:x + w]

            label = -1
            if self.model is not None:
                try:
                    label, confidence = self.model.predict(image_face)
                except:
                    label = -1

            detected_faces.append(type('obj', (object,), {'user': str(label), 'x': x, 'y': y, 'w': w, 'h': h}))

        return detected_faces

    def init_new_face(self):
        if not os.path.exists(self.training_image_directory):
            os.makedirs(self.training_image_directory)

        i = 0
        while True:
            i += 1
            potential_directory = os.path.join(self.training_image_directory, '%03d' % i)
            if not os.path.exists(potential_directory):
                os.makedirs(potential_directory)
                self.training_user = i
                self.training_user_iteration = 0
                break

    def add_new_face(self, image):
        if self.training_user is None or self.training_user_iteration is None:
            return False, "Face training was not initiated."

        faces = self.detect_faces(image)
        if len(faces) == 0:
            return False, "No face detected."
        elif len(faces) > 1:
            return False, "More than one face detected."

        face = faces[0]
        cropped = image[face.y:face.y + face.h, face.x:face.x + face.w]
        filename = os.path.join(self.training_image_directory, '%03d' % self.training_user,
                                '%03d.pgm' % self.training_user_iteration)
        cv2.imwrite(filename, cropped)
        self.training_user_iteration += 1
        return True, ""

    def train_faces(self):
        self.training_user = None
        self.training_user_iteration = None

        training_model = cv2.createLBPHFaceRecognizer()
        images = []
        labels = []
        for directory in os.listdir(self.training_image_directory):
            joined_directory = os.path.join(self.training_image_directory, directory)
            if os.path.isdir(joined_directory):
                for image_file in os.listdir(joined_directory):
                    joined_file = os.path.join(joined_directory, image_file)
                    image = cv2.imread(joined_file, cv2.IMREAD_GRAYSCALE)
                    images.append(image)
                    labels.append(int(directory))
        training_model.train(numpy.asarray(images), numpy.asarray(labels))
        training_model.save(self.training_file_name)
        self.model = training_model

    def delete_training(self):
        if os.path.isdir(self.training_image_directory):
            shutil.rmtree(self.training_image_directory)
        if os.path.isfile(self.training_file_name):
            os.remove(self.training_file_name)
        self.model = None
