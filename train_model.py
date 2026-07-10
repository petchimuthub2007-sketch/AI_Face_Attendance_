import cv2
import os
import numpy as np
import json

# Face Recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()

dataset_path = "dataset"

faces = []
labels = []

label_map = {}
current_label = 0

for student_folder in os.listdir(dataset_path):

    folder_path = os.path.join(dataset_path, student_folder)

    if not os.path.isdir(folder_path):
        continue

    label_map[current_label] = student_folder

    for image_name in os.listdir(folder_path):

        image_path = os.path.join(folder_path, image_name)

        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        if image is None:
            continue

        faces.append(image)
        labels.append(current_label)

    current_label += 1

labels = np.array(labels)

recognizer.train(faces, labels)

if not os.path.exists("trainer"):
    os.makedirs("trainer")

recognizer.save("trainer/trainer.yml")
with open("trainer/label_map.json", "w") as file:
    json.dump(label_map, file)

print(" AI Model Trained Successfully!")
print("Total Students :", len(label_map))
print("Total Images   :", len(faces))