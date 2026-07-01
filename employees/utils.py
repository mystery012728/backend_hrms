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


from PIL import Image, ImageOps
import io
from django.core.files.uploadedfile import InMemoryUploadedFile

def resize_uploaded_image(uploaded_file, max_size=600):
    if not uploaded_file:
        return uploaded_file
    try:
        # Seek back to start of file in case it has been read before
        uploaded_file.seek(0)
        
        # Read the file into PIL
        img = Image.open(uploaded_file)
        
        # Check if the image has EXIF orientation tag
        has_exif = False
        try:
            exif = img._getexif()
            if exif and 274 in exif:
                has_exif = True
        except Exception:
            pass
            
        # Transpose if it has EXIF orientation tag
        transposed_img = ImageOps.exif_transpose(img)
        
        # We process/save the image if:
        # 1. It exceeds the max_size (needs resizing)
        # 2. It was transposed (orientation changed)
        # 3. Or it's not a JPEG (to standardize to JPEG)
        needs_processing = (
            img.width > max_size or 
            img.height > max_size or 
            has_exif or 
            img.format != 'JPEG'
        )
        
        if needs_processing:
            if transposed_img.width > max_size or transposed_img.height > max_size:
                transposed_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Save back to an in-memory buffer
            buffer = io.BytesIO()
            # Convert to RGB (to drop alpha channel if any) and save as JPEG
            transposed_img.convert("RGB").save(buffer, format="JPEG", quality=85)
            buffer.seek(0)
            
            # Construct a new InMemoryUploadedFile
            new_file = InMemoryUploadedFile(
                file=buffer,
                field_name=uploaded_file.field_name,
                name=uploaded_file.name,
                content_type="image/jpeg",
                size=buffer.getbuffer().nbytes,
                charset=None
            )
            return new_file
    except Exception:
        pass
    
    # Seek back to start so other readers can use the file
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
        
    return uploaded_file

