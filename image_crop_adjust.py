import sys
from PIL import Image

class ImageCropAdjust:
    """
    Python version of the Java "ImageCropAdjust" logic.
    Dynamically sets skipRows = rect.width // 40 (at least 1) per rectangle.
    """

    def __init__(self, threshold=0.0, search_range=20, tolerance=20, expand_ratio=0.1):
        """
        :param threshold: (float) threshold ratio to decide dark vs. light row/col
        :param search_range: (int) how far above/below we search for boundary
        :param tolerance: (int) +/- range around darkest color to be considered "dark"
        :param expand_ratio: (float) how much to expand the final rectangle, e.g. 0.1 => 10%
        """
        self.threshold = threshold
        self.search_range = search_range
        self.tolerance = tolerance
        self.expand_ratio = expand_ratio

    def process_image_file(self, image_path, txt_path):
        """
        Reads one image (JPG/PNG/etc.) and a .txt file with rectangle data.
        For each line "x,y,w,h", it applies 'fix_rect' logic.
        """
        try:
            # Load the image (convert to RGB to ensure we have R,G,B channels)
            image = Image.open(image_path).convert('RGB')

            # Convert entire image to a 2D grayscale array
            image_data = self.image_to_byte_array(image)

            # Read the text file lines
            with open(txt_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line in lines:
                parts = line.strip().split(',')
                if len(parts) >= 4:
                    x = int(parts[0])
                    y = int(parts[1])
                    w = int(parts[2])
                    h = int(parts[3])

                    print(f"GIVEN:\t{x},{y},{w},{h}")
                    # Perform the rectangle fix
                    fixed = self.fix_rect(image_data, x, y, w, h)
                    print(f"FIXED:\t{fixed[0]},{fixed[1]},{fixed[2]},{fixed[3]}")

            print("Processing Completed.")

        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)

    def image_to_byte_array(self, image):
        """
        Convert a PIL Image (RGB) to a 2D grayscale array:
            image_data[x][y] in range 0..255.
        The array dimensions will be [width][height].
        """
        width, height = image.size
        # Create a 2D list: image_data[x][y]
        image_data = [[0]*height for _ in range(width)]

        for y in range(height):
            for x in range(width):
                r, g, b = image.getpixel((x, y))
                # Convert to grayscale (luminance)
                gray = int(0.299*r + 0.587*g + 0.114*b)
                image_data[x][y] = gray

        return image_data

    def fix_rect(self, image_data, x, y, w, h):
        """
        Adjusts (x, y, w, h) based on dark/light boundaries in image_data.
        skipRows is computed as w//40 (at least 1). 
        Returns a tuple (new_x, new_y, new_w, new_h).
        """
        # Dynamically compute skipRows
        skip_rows = max(1, w // 40)

        # We'll find the boundary in sub-method:
        new_rect = self.find_change_layer(image_data, x, y, w, h, skip_rows)
        return tuple(new_rect)

    def find_change_layer(self, image_data, x, y, w, h, skip_rows):
        """
        Core logic that tries to shrink/expand the rectangle around dark text/objects.
        Returns [x, y, w, h].
        """
        dark_color = self.get_darkest_average_color(image_data, x, y, w, h)

        # Keep results in fixed_rect = [x, y, w, h]
        fixed_rect = [x, y, w, h]

        # ------------------------------------------------
        # A) Adjust Y direction
        # ------------------------------------------------
        start_x = fixed_rect[0]
        end_x = fixed_rect[0] + fixed_rect[2]

        # Look at the row at rect.y
        row_rate = self.find_row_dark_rate(image_data, direction=0,
                                           index=fixed_rect[1],
                                           start=start_x, end=end_x,
                                           dark=dark_color,
                                           tol=self.tolerance)
        if row_rate <= self.threshold:
            # move downward to find the first dark row
            for yy in range(fixed_rect[1], fixed_rect[1] + fixed_rect[3]):
                row_rate = self.find_row_dark_rate(image_data, 0, yy,
                                                   start_x, end_x,
                                                   dark_color, self.tolerance)
                if row_rate > self.threshold:
                    fixed_rect[1] = yy
                    break
        else:
            # move upward to find the transition from light to dark
            start_y = fixed_rect[1]
            for yy in range(start_y, start_y - self.search_range, -1):
                if yy < 0:
                    break
                row_rate = self.find_row_dark_rate(image_data, 0, yy,
                                                   start_x, end_x,
                                                   dark_color, self.tolerance)
                if row_rate <= self.threshold:
                    fixed_rect[1] = yy
                    break

        # Now find where it goes light again
        for yy in range(fixed_rect[1] + 1, fixed_rect[1] + h):
            row_rate = self.find_row_dark_rate(image_data, 0, yy,
                                               start_x, end_x,
                                               dark_color, self.tolerance)
            if row_rate <= self.threshold:
                fixed_rect[3] = yy
                break

        # ------------------------------------------------
        # B) Adjust X direction
        # ------------------------------------------------
        start_y = fixed_rect[1]
        end_y = fixed_rect[1] + fixed_rect[3]

        col_rate = self.find_row_dark_rate(image_data, 1, x,
                                           start_y, end_y,
                                           dark_color, self.tolerance)
        if col_rate <= self.threshold:
            # move right
            skipping = skip_rows
            for xx in range(x, x + w):
                col_rate = self.find_row_dark_rate(image_data, 1, xx,
                                                   start_y, end_y,
                                                   dark_color, self.tolerance)
                if col_rate > self.threshold:
                    fixed_rect[0] = xx
                    skipping -= 1
                    if skipping == 0:
                        break
        else:
            # move left
            skipping = skip_rows
            for xx in range(x, x - self.search_range, -1):
                if xx < 0:
                    break
                col_rate = self.find_row_dark_rate(image_data, 1, xx,
                                                   start_y, end_y,
                                                   dark_color, self.tolerance)
                if col_rate <= self.threshold:
                    fixed_rect[0] = xx
                    skipping -= 1
                    if skipping == 0:
                        break

        # find where it becomes light again
        skipping = skip_rows
        for xx in range(fixed_rect[0] + 1, fixed_rect[0] + w):
            col_rate = self.find_row_dark_rate(image_data, 1, xx,
                                               start_y, end_y,
                                               dark_color, self.tolerance)
            if col_rate <= self.threshold:
                fixed_rect[2] = xx
                skipping -= 1
                if skipping == 0:
                    break

        # Convert from [x, y, x2, y2] => [x, y, width, height]
        fixed_rect[2] -= fixed_rect[0]
        fixed_rect[3] -= fixed_rect[1]

        # ------------------------------------------------
        # C) Expand final rectangle by expand_ratio
        # ------------------------------------------------
        expand_x = int(fixed_rect[2] * self.expand_ratio)
        expand_y = int(fixed_rect[3] * self.expand_ratio)

        fixed_rect[0] -= expand_x
        fixed_rect[1] -= expand_y
        fixed_rect[2] += expand_x * 2
        fixed_rect[3] += expand_y * 2

        return fixed_rect

    def get_darkest_average_color(self, image_data, x, y, w, h):
        """
        Finds the darkest average color in the sub-rectangle.
        Returns an int in [0..255].
        """
        width  = len(image_data)
        height = len(image_data[0])

        total = 0
        count = 0
        min_gray = 255

        # Loop through the requested rect
        for yy in range(y, y + h):
            if yy < 0 or yy >= height:
                continue
            for xx in range(x, x + w):
                if xx < 0 or xx >= width:
                    continue
                val = image_data[xx][yy]
                total += val
                count += 1
                if val < min_gray:
                    min_gray = val

        avg = (total // count) if count > 0 else 0
        # return the darker of the min or the average
        return min(avg, min_gray)

    def find_row_dark_rate(self, image_data, direction, index,
                           start, end, dark, tol):
        """
        direction = 0 => row mode (index is y, we iterate x)
        direction = 1 => column mode (index is x, we iterate y)
        Returns ratio of "dark" pixels in [start..end].
        """
        width  = len(image_data)
        height = len(image_data[0])

        lower_bound = max(0, dark - abs(tol))
        upper_bound = min(255, dark + abs(tol))

        dark_pixels  = 0
        total_pixels = 0

        if direction == 0:
            # row mode: index => y
            y = index
            if 0 <= y < height:
                for x in range(start, end):
                    if 0 <= x < width:
                        val = image_data[x][y]
                        if lower_bound <= val <= upper_bound:
                            dark_pixels += 1
                        total_pixels += 1

        else:
            # column mode: index => x
            x = index
            if 0 <= x < width:
                for y in range(start, end):
                    if 0 <= y < height:
                        val = image_data[x][y]
                        if lower_bound <= val <= upper_bound:
                            dark_pixels += 1
                        total_pixels += 1

        if total_pixels == 0:
            return 0.0
        return float(dark_pixels) / float(total_pixels)


if __name__ == '__main__':
    """
    Example usage. Update IMAGE_PATH and TXT_PATH to point to your files.
    """
    IMAGE_PATH = r"samples\\03.jpg"
    TXT_PATH   = r"samples\\03.txt"

    # Create with default config; optionally override
    # e.g. threshold=0.0, search_range=20, tolerance=20, expand_ratio=0.1
    crop_adjust = ImageCropAdjust()

    # Run the main process
    crop_adjust.process_image_file(IMAGE_PATH, TXT_PATH)
