"""Test OCR function with a real image."""
import sys
sys.path.insert(0, "D:/codex/V18")

from core.intake import ocr_images_via_api

# Find a test image
import glob
images = glob.glob("D:/codex/V18/**/*.jpg", recursive=True) + glob.glob("D:/codex/V18/**/*.png", recursive=True)
print(f"Found {len(images)} images in project")

if images:
    test_img = images[0]
    print(f"Testing OCR on: {test_img}")
    result = ocr_images_via_api([test_img])
    print(f"OCR result keys: {list(result.keys())}")
    for k, v in result.items():
        print(f"  {k}: {v[:200] if v else '(empty)'}")
else:
    print("No test images found")

# Also test with a non-existent image to check error handling
print("\nTesting error handling...")
result2 = ocr_images_via_api(["nonexistent.jpg"])
print(f"Error result: {result2}")
