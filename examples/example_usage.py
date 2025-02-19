import os
from PIL import Image

from crop_adjust import CropAdjust

def main():
    # Path to your test image
    img_path = os.path.join("samples", "03.jpg")

    # Create a CropAdjust object
    crop = CropAdjust(threshold=0.0, search_range=20, tolerance=20, expand_ratio=0.1)

    # Load image and convert to 2D grayscale
    img = Image.open(img_path).convert('RGB')
    image_data = crop.image_to_byte_array(img)

    # Provide a rectangle (x, y, w, h)
    x, y, w, h = 190, 125, 172, 31

    # Get the adjusted rectangle
    result = crop.fix_rect(image_data, x, y, w, h)
    print("Adjusted rectangle:", result)

if __name__ == "__main__":
    main()
