"""Full pipeline test with a real image."""
import sys, os, struct, zlib, base64, tempfile, shutil
sys.path.insert(0, "D:/codex/V18")

# Create a test image with actual text-like content
def make_test_image():
    width, height = 200, 50
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'
        for x in range(width):
            if 10 < x < 190 and 10 < y < 40:
                raw_data += b'\x00\x00\x00'  # black area (simulates text)
            else:
                raw_data += b'\xff\xff\xff'  # white background
    compressed = zlib.compress(raw_data)
    def chunk(ctype, data):
        c = ctype + data
        crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        return struct.pack('>I', len(data)) + c + crc
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', ihdr)
    png += chunk(b'IDAT', compressed)
    png += chunk(b'IEND', b'')
    return png

# Create temp directory with test image
tmpdir = tempfile.mkdtemp(prefix="v18_test_")
img_path = os.path.join(tmpdir, "test_evidence.png")
with open(img_path, "wb") as f:
    f.write(make_test_image())
print(f"Created test image: {img_path} ({os.path.getsize(img_path)} bytes)")

# Test OCR
from core.intake import ocr_images_via_api
print("\n--- Testing OCR ---")
result = ocr_images_via_api([img_path])
print(f"OCR result: {result}")

# Test full intake
from core.fact_card import PipelineContext
ctx = PipelineContext(
    input_dir=tmpdir,
    output_dir=os.path.join(tmpdir, "output"),
    identity="起诉方（原告）",
    goal="提起起诉",
    file_list=[img_path],
    task_id="test",
    task_status="进行中",
)
ctx.file_list = [img_path]

print("\n--- Testing run_intake ---")
from core.intake import run_intake
run_intake(ctx)
print(f"raw_texts count: {len(ctx.raw_texts)}")
for i, t in enumerate(ctx.raw_texts):
    print(f"  [{i}]: {t[:100] if t else '(empty)'}")

# Check if placeholders were replaced
has_real_text = any(not t.startswith("[") for t in ctx.raw_texts)
print(f"\nHas real text (not placeholder): {has_real_text}")

# Cleanup
shutil.rmtree(tmpdir, ignore_errors=True)
print("\nDone!")
