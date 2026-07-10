import cv2
import os

# Load Face Detector (using a local copy of the cascade file to avoid
# OneDrive/cloud-sync issues with files inside the venv's site-packages)
CASCADE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "haarcascade_frontalface_default.xml"
)
face_detector = cv2.CascadeClassifier(CASCADE_PATH)

# Check if XML loaded successfully
if face_detector.empty():
    print(f"❌ Error: Could not load cascade file at {CASCADE_PATH}")
    exit()

# Open Webcam
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("❌ Error: Cannot open webcam.")
    exit()

while True:

    ret, frame = camera.read()

    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5,
        minSize=(100, 100)
    )

    # Draw Rectangle
    for (x, y, w, h) in faces:

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            "Face Detected",
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

    cv2.imshow("AI Face Attendance System", frame)

    # Press Q to Exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()