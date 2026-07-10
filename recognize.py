import cv2
import json
import os
import sys
import csv
import time
from datetime import datetime
from database import get_connection

# ==========================
# EXPECTED REGISTER NUMBER (passed from dashboard, optional)
# ==========================
# If a register number is passed in, we only mark attendance when the
# recognized face matches this register number (verification mode).
expected_register_number = sys.argv[1] if len(sys.argv) > 1 else None

# ==========================
# DATABASE CONNECTION
# ==========================

db = get_connection()
cursor = db.cursor()

# ==========================
# LOAD TRAINED MODEL
# ==========================

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("trainer/trainer.yml")

# ==========================
# LOAD LABEL MAP
# ==========================

with open("trainer/label_map.json", "r") as file:
    label_map = json.load(file)

# ==========================
# FACE DETECTOR
# ==========================

face_detector = cv2.CascadeClassifier(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "haarcascade_frontalface_default.xml"
    )
)

if face_detector.empty():
    print("Face Detector Not Loaded")
    sys.exit()

# ==========================
# OPEN CAMERA
# ==========================

camera = cv2.VideoCapture(0)

time.sleep(2)

if not camera.isOpened():
    print("Cannot Open Camera")
    sys.exit()

print("===================================")
print(" AI FACE ATTENDANCE SYSTEM ")
print("===================================")
if expected_register_number:
    print(f"Verifying Register Number : {expected_register_number}")
print("Camera Started Successfully")
print("Press Q to Exit")
print("===================================")


def mark_attendance(register_number):
    """Insert attendance row (if not already marked today) + append to CSV."""

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M:%S")

    cursor.execute("""
        SELECT * FROM attendance
        WHERE register_number=%s
        AND attendance_date=%s
    """, (register_number, today))

    result = cursor.fetchone()

    if result is None:
        cursor.execute("""
            INSERT INTO attendance
            (register_number, attendance_date, attendance_time)
            VALUES (%s,%s,%s)
        """, (register_number, today, now))

        db.commit()

        print(f"✅ Attendance Marked for {register_number}")
    else:
        print(f"ℹ️ Attendance already marked today for {register_number}")

    csv_file = "Attendance.csv"
    file_exists = os.path.isfile(csv_file)

    with open(csv_file, "a", newline="") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(["Name", "Date", "Time"])

        writer.writerow([register_number, today, now])

    print("✅ Attendance Saved to CSV")


# ==========================
# START RECOGNITION
# ==========================

attendance_done = False

while True:

    ret, frame = camera.read()

    if not ret:
        print("Camera Error")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5,
        minSize=(100, 100)
    )

    for (x, y, w, h) in faces:

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

        face = gray[y:y+h, x:x+w]

        # Predict Face
        label, confidence = recognizer.predict(face)

        # Convert label to Register Number
        recognized_register_number = label_map.get(str(label), "Unknown")

        # Confidence percentage
        confidence_percent = round(100 - confidence)

        if confidence_percent >= 60:

            if expected_register_number:
                # ---- VERIFICATION MODE ----
                if recognized_register_number == expected_register_number:

                    cv2.putText(
                        frame,
                        f"Verified: {recognized_register_number}",
                        (x, y - 35),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 0),
                        2
                    )
                    cv2.putText(
                        frame,
                        f"Confidence: {confidence_percent}%",
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2
                    )

                    if not attendance_done:
                        mark_attendance(recognized_register_number)
                        attendance_done = True

                else:
                    cv2.putText(
                        frame,
                        "Face does not match entered ID",
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2
                    )

            else:
                # ---- OLD GENERIC MODE (no reg number passed in) ----
                cv2.putText(
                    frame,
                    f"ID: {recognized_register_number}",
                    (x, y - 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )
                cv2.putText(
                    frame,
                    f"Confidence: {confidence_percent}%",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

                if not attendance_done:
                    mark_attendance(recognized_register_number)
                    attendance_done = True

        else:
            cv2.putText(
                frame,
                "Unknown Face",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

    cv2.imshow("AI Face Recognition", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    # Auto-close a couple seconds after a successful, verified match
    if attendance_done:
        cv2.waitKey(1500)
        break

camera.release()
cv2.destroyAllWindows()
cursor.close()
db.close()