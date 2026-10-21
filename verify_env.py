#!/usr/bin/env python3
"""
Multimodal Attendance & Engagement Agent
Environment & Dependency Verification Script
"""

import sys
import platform
import importlib

def check_python_version():
    print("=" * 60)
    print("1. PYTHON ENVIRONMENT")
    print("=" * 60)
    v = sys.version_info
    print(f"Python Version: {v.major}.{v.minor}.{v.micro} ({platform.python_implementation()})")
    print(f"Executable:     {sys.executable}")
    print(f"Platform:       {platform.system()} {platform.machine()} ({platform.platform()})")
    
    if v.major == 3 and v.minor == 11:
        print("  [PASS] Target Python 3.11 detected.")
        return True
    elif v.major == 3 and v.minor >= 10:
        print(f"  [WARN] Python {v.major}.{v.minor} is compatible, but 3.11 is recommended.")
        return True
    else:
        print(f"  [FAIL] Python {v.major}.{v.minor} is not supported. Please use Python 3.11.")
        return False

def check_dependencies():
    print("\n" + "=" * 60)
    print("2. CORE DEPENDENCY VERIFICATION")
    print("=" * 60)

    modules = [
        ("OpenCV", "cv2", "__version__"),
        ("MediaPipe", "mediapipe", "__version__"),
        ("DeepFace", "deepface", "__version__"),
        ("DeepSort Realtime", "deep_sort_realtime", None),
        ("Librosa", "librosa", "__version__"),
        ("SoundFile", "soundfile", "__version__"),
        ("NumPy", "numpy", "__version__"),
        ("Pandas", "pandas", "__version__"),
        ("FastAPI", "fastapi", "__version__"),
        ("Uvicorn", "uvicorn", "__version__"),
        ("WebSockets", "websockets", "__version__"),
        ("SQLAlchemy", "sqlalchemy", "__version__"),
        ("Python DotEnv", "dotenv", "__version__"),
        ("Streamlit", "streamlit", "__version__"),
    ]

    all_passed = True
    for name, mod_name, ver_attr in modules:
        try:
            mod = importlib.import_module(mod_name)
            ver = getattr(mod, ver_attr, "installed") if ver_attr else "installed"
            print(f"  [PASS] {name:<20} : {ver}")
        except Exception as e:
            print(f"  [FAIL] {name:<20} : FAILED to import ({e})")
            all_passed = False

    return all_passed

def check_camera():
    print("\n" + "=" * 60)
    print("3. VIDEO CAPTURE (CAMERA) PROBE")
    print("=" * 60)
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                h, w, c = frame.shape
                print(f"  [PASS] Camera device 0 detected and accessible: {w}x{h} ({c} channels)")
                return True
            else:
                print("  [INFO] Camera device 0 opened, but no frame returned (permissions or in-use).")
                print("         Synthetic test video generator will be used for testing.")
                return True
        else:
            print("  [INFO] Camera device 0 could not be opened (no hardware webcam or permissions).")
            print("         Synthetic test video generator will be used for offline testing.")
            return True
    except Exception as e:
        print(f"  [WARN] Camera probe raised exception: {e}")
        return True

def main():
    py_ok = check_python_version()
    deps_ok = check_dependencies()
    check_camera()
    
    print("\n" + "=" * 60)
    if py_ok and deps_ok:
        print("RESULT: ALL REQUIRED DEPENDENCIES VERIFIED SUCCESSFULLY!")
        print("=" * 60)
        return 0
    else:
        print("RESULT: ENVIRONMENT VERIFICATION FAILED. Check errors above.")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
