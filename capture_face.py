import cv2
import os
import sys

student_id = sys.argv[1]
path = os.path.join("dataset", student_id)

if not os.path.exists(path):
    os.makedirs(path)

# Load Face Detector (using a local copy of the cascade file to avoid
# OneDrive/cloud-sync issues with files inside the venv's site-packages)
CASCADE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "haarcascade_frontalface_default.xml"
)
detector = cv2.CascadeClassifier(CASCADE_PATH)

if detector.empty():
    print(f"❌ Error: Could not load cascade file at {CASCADE_PATH}")
    sys.exit()

camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

count = 0

while True:

    ret, frame = camera.read()

    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = detector.detectMultiScale(
        gray,
        1.3,
        5
    )

    for (x, y, w, h) in faces:

        count += 1

        face = gray[y:y+h, x:x+w]

        file_name = os.path.join(path, f"{count}.jpg")

        cv2.imwrite(file_name, face)

        cv2.rectangle(
            frame,
            (x, y),
            (x+w, y+h),
            (0,255,0),
            2
        )

        cv2.putText(
            frame,
            f"Images : {count}/100",
            (20,40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0,255,0),
            2
        )

    cv2.imshow("Capture Face", frame)

    if cv2.waitKey(1) == ord("q") or count >= 100:
        break

camera.release()
cv2.destroyAllWindows()

print("✅ Face Images Captured Successfully!")