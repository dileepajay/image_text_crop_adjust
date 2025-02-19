import pytest
from crop_adjust import CropAdjust

def test_fix_rect_simple():
    crop = CropAdjust()
    
    # Fake "image_data" with all zeroes (pure black).
    #  Let's make it 100x100 for a test:
    width, height = 100, 100
    image_data = [[0]*height for _ in range(width)]
    
    # If the image is all black, we might expect the rectangle won't change drastically.
    x, y, w, h = 10, 10, 30, 30
    result = crop.fix_rect(image_data, x, y, w, h)
    
    assert len(result) == 4
    # Just check it's within reason
    # (You can refine these checks or mock partial logic.)
    assert 0 <= result[0] <= 100
    assert 0 <= result[1] <= 100
