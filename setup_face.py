import cv2
import os
import numpy as np
import time

def setup_face_recognition():
    print("====================================================")
    print("      J.A.R.V.I.S. Owner Face Registration          ")
    print("====================================================")
    
    # Create directories
    os.makedirs("faces/owner", exist_ok=True)
    os.makedirs("model", exist_ok=True)
    
    # Load OpenCV Haar Cascade face detector
    face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(face_cascade_path)
    
    if face_cascade.empty():
        print("[ERROR] Could not load face detector. Please verify OpenCV installation.")
        return False
        
    # Initialize webcam
    print("\nInitializing webcam...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("[ERROR] Could not open webcam. Make sure it is connected and not in use by another app.")
        return False
        
    print("\n--- INSTRUCTIONS ---")
    print("1. Look directly at the camera.")
    print("2. Slowly tilt and turn your head slightly during capture to get different angles.")
    print("3. Ensure you are in a well-lit room.")
    print("Press 'SPACE' to start capturing, or 'Q' to quit.")
    
    count = 0
    max_samples = 60
    started = False
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to grab frame.")
            break
            
        display_frame = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))
        
        for (x, y, w, h) in faces:
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            if started and count < max_samples:
                # Save the cropped face image
                count += 1
                face_img = gray[y:y+h, x:x+w]
                face_img = cv2.resize(face_img, (200, 200))
                cv2.imwrite(f"faces/owner/face_{count}.jpg", face_img)
                
                # Visual cue on the rectangle
                cv2.putText(display_frame, f"Saving {count}/{max_samples}", (x, y-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Small delay to capture different frames
                time.sleep(0.05)
                
        # UI overlays
        if not started:
            cv2.putText(display_frame, "Press SPACE to Start Capture", (30, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        elif count >= max_samples:
            cv2.putText(display_frame, "Capture Complete! Training starting...", (30, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(display_frame, f"Capturing: {count}/{max_samples} frames", (30, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
        cv2.imshow("JARVIS Face Registration", display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' ') and not started:
            started = True
            print("Capturing faces... Look at the camera and move your head slowly.")
        elif key == ord('q'):
            print("Registration cancelled.")
            cap.release()
            cv2.destroyAllWindows()
            return False
            
        if count >= max_samples:
            break
            
    cap.release()
    cv2.destroyAllWindows()
    
    print("\nProcessing captured faces...")
    # Train the face recognizer
    faces_data = []
    labels = []
    
    for filename in os.listdir("faces/owner"):
        if filename.endswith(".jpg"):
            img_path = os.path.join("faces/owner", filename)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                faces_data.append(img)
                labels.append(1)  # Label 1 is the Owner
                
    if len(faces_data) == 0:
        print("[ERROR] No face images found. Training failed.")
        return False
        
    print(f"Training J.A.R.V.I.S. on {len(faces_data)} samples...")
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces_data, np.array(labels))
        recognizer.write("model/trainer.yml")
        print("\n[SUCCESS] Model trained successfully! Saved to 'model/trainer.yml'.")
        print("Your face is now registered as the OWNER of this PC.")
        return True
    except AttributeError:
        print("[ERROR] OpenCV face module is missing. Please run: pip install opencv-contrib-python")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to train recognizer: {e}")
        return False

if __name__ == "__main__":
    setup_face_recognition()
