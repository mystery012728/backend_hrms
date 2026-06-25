import cv2
import numpy as np

def has_face(image_file):
    if not image_file:
        return False
    try:
        # Read file bytes
        file_bytes = np.frombuffer(image_file.read(), dtype=np.uint8)
        # Seek back to start of file so it can be saved/read by Django
        image_file.seek(0)
        
        # Decode the image using OpenCV
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            return False
            
        # Convert image to grayscale for face detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Load the default frontal face Haar Cascade XML from OpenCV
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if face_cascade.empty():
            return False
            
        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        return len(faces) > 0
    except Exception:
        return False
