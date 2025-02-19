from PIL import Image

class CropAdjust:
    """
    A reusable Python class for adjusting a rectangle around dark text/objects in an image.

    Main Usage:
        from crop_adjust import CropAdjust
        from PIL import Image

        # 1) Create the CropAdjust object (optional config overrides)
        crop = CropAdjust(threshold=0.0, search_range=20, tolerance=20, expand_ratio=0.1)

        # 2) Convert an image to a 2D grayscale array
        img = Image.open("example.jpg").convert('RGB')
        image_data = crop.image_to_byte_array(img)

        # 3) Provide an initial rectangle (x, y, w, h)
        adjusted_rect = crop.fix_rect(image_data, x=190, y=125, w=172, h=31)
        print("Adjusted rectangle:", adjusted_rect)
    """

    def __init__(self,
                 threshold=0.0,
                 search_range=20,
                 tolerance=20,
                 expand_ratio=0.1):
        """
        :param threshold: (float) ratio threshold to decide dark vs. light row/col
        :param search_range: (int) how far above/below we search for boundary
        :param tolerance: (int) +/- range around darkest color to be considered "dark"
        :param expand_ratio: (float) how much to expand the final rectangle, e.g. 0.1 => 10%
        """
        self.threshold = threshold
        self.search_range = search_range
        self.tolerance = tolerance
        self.expand_ratio = expand_ratio

    # ----------------------------------------------------------------
    # Configuration Setters
    # ----------------------------------------------------------------
    def set_threshold(self, threshold):
        """Override the default threshold (float)."""
        self.threshold = threshold

    def set_search_range(self, search_range):
        """Override the default search range (int)."""
        self.search_range = search_range

    def set_tolerance(self, tolerance):
        """Override the default tolerance (int)."""
        self.tolerance = tolerance

    def set_expand_ratio(self, expand_ratio):
        """Override the default expand ratio (float)."""
        self.expand_ratio = expand_ratio

    # ----------------------------------------------------------------
    # Convert a Pillow Image to a 2D grayscale array
    # ----------------------------------------------------------------
    def image_to_byte_array(self, image):
        """
        Convert a PIL Image (RGB) to a 2D grayscale array: image_data[x][y] in [0..255].
        :param image: PIL Image object in RGB mode
        :return: 2D list of ints, dimensions [width][height]
        """
        width, height = image.size
        image_data = [[0]*height for _ in range(width)]

        for y in range(height):
            for x in range(width):
                r, g, b = image.getpixel((x, y))
                gray = int(0.299*r + 0.587*g + 0.114*b)
                image_data[x][y] = gray

        return image_data

    # ----------------------------------------------------------------
    # Public API: fix_rect
    # ----------------------------------------------------------------
    def fix_rect(self, image_data, x, y, w, h):
        """
        Given an image_data 2D array (grayscale) and an initial rectangle (x, y, w, h),
        returns an adjusted rectangle [x, y, width, height].

        skipRows is computed from w//40 (at least 1).
        """
        skip_rows = max(1, w // 40)
        adjusted = self._find_change_layer(image_data, x, y, w, h, skip_rows)
        return adjusted

    # ----------------------------------------------------------------
    # Internal logic: find_change_layer
    # ----------------------------------------------------------------
    def _find_change_layer(self, image_data, x, y, w, h, skip_rows):
        """
        Finds the bounding rectangle around dark text/objects by searching
        row/col boundaries and adjusting. Returns [x, y, width, height].
        """
        dark_color = self._get_darkest_average_color(image_data, x, y, w, h)

        # We'll store the rect in [x, y, w, h] form
        rect = [x, y, w, h]

        # ------------------------------------------------------------
        # A) Adjust Y direction
        # ------------------------------------------------------------
        start_x = rect[0]
        end_x   = rect[0] + rect[2]

        row_rate = self._find_row_dark_rate(image_data, direction=0,
                                            index=rect[1],
                                            start=start_x,
                                            end=end_x,
                                            dark=dark_color,
                                            tol=self.tolerance)
        if row_rate <= self.threshold:
            # move downward
            for yy in range(rect[1], rect[1] + rect[3]):
                row_rate = self._find_row_dark_rate(image_data, 0, yy,
                                                    start_x, end_x,
                                                    dark_color, self.tolerance)
                if row_rate > self.threshold:
                    rect[1] = yy
                    break
        else:
            # move upward
            start_y = rect[1]
            for yy in range(start_y, start_y - self.search_range, -1):
                if yy < 0:
                    break
                row_rate = self._find_row_dark_rate(image_data, 0, yy,
                                                    start_x, end_x,
                                                    dark_color, self.tolerance)
                if row_rate <= self.threshold:
                    rect[1] = yy
                    break

        # find where it goes light again
        for yy in range(rect[1] + 1, rect[1] + h):
            row_rate = self._find_row_dark_rate(image_data, 0, yy,
                                                start_x, end_x,
                                                dark_color, self.tolerance)
            if row_rate <= self.threshold:
                rect[3] = yy
                break

        # ------------------------------------------------------------
        # B) Adjust X direction
        # ------------------------------------------------------------
        start_y = rect[1]
        end_y   = rect[1] + rect[3]

        col_rate = self._find_row_dark_rate(image_data, direction=1,
                                            index=x,
                                            start=start_y,
                                            end=end_y,
                                            dark=dark_color,
                                            tol=self.tolerance)
        if col_rate <= self.threshold:
            # move right
            skipping = skip_rows
            for xx in range(x, x + w):
                col_rate = self._find_row_dark_rate(image_data, 1, xx,
                                                    start_y, end_y,
                                                    dark_color, self.tolerance)
                if col_rate > self.threshold:
                    rect[0] = xx
                    skipping -= 1
                    if skipping == 0:
                        break
                    else:
                        skipping = skip_rows
        else:
            # move left
            skipping = skip_rows
            for xx in range(x, x - self.search_range, -1):
                if xx < 0:
                    break
                col_rate = self._find_row_dark_rate(image_data, 1, xx,
                                                    start_y, end_y,
                                                    dark_color, self.tolerance)
                if col_rate <= self.threshold:
                    rect[0] = xx
                    skipping -= 1
                    if skipping == 0:
                        break
                    else:
                        skipping = skip_rows

        # find where it becomes light
        skipping = skip_rows
        for xx in range(rect[0] + 1, rect[0] + w):
            col_rate = self._find_row_dark_rate(image_data, 1, xx,
                                                start_y, end_y,
                                                dark_color, self.tolerance)
            if col_rate <= self.threshold:
                rect[2] = xx
                skipping -= 1
                if skipping == 0:
                    break
                else:
                        skipping = skip_rows

        # Convert (x, y, x2, y2) => (x, y, width, height)
        rect[2] -= rect[0]
        rect[3] -= rect[1]

        # ------------------------------------------------------------
        # C) Expand final rectangle by expand_ratio
        # ------------------------------------------------------------
        expand_x = int(rect[2] * self.expand_ratio)
        expand_y = int(rect[3] * self.expand_ratio)

        rect[0] -= expand_x
        rect[1] -= expand_y
        rect[2] += expand_x * 2
        rect[3] += expand_y * 2

        return rect

    # ----------------------------------------------------------------
    # Internal helper: darkest average color
    # ----------------------------------------------------------------
    def _get_darkest_average_color(self, image_data, x, y, w, h):
        """
        Returns an int in [0..255], the darkest average color in [x, y, w, h].
        """
        width  = len(image_data)
        height = len(image_data[0])

        total = 0
        count = 0
        min_gray = 255

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

        if count == 0:
            return 0
        avg_gray = total // count
        return min(avg_gray, min_gray)

    # ----------------------------------------------------------------
    # Internal helper: row or column dark rate
    # ----------------------------------------------------------------
    def _find_row_dark_rate(self, image_data, direction, index,
                            start, end, dark, tol):
        """
        direction=0 => row mode (index is y), direction=1 => column mode (index is x).
        Returns ratio = dark_pixels / total_pixels in [start..end].
        """
        width  = len(image_data)
        height = len(image_data[0])

        lower = max(0, dark - abs(tol))
        upper = min(255, dark + abs(tol))

        dark_pixels = 0
        total_pixels = 0

        if direction == 0:
            # row mode => index is y
            y = index
            if 0 <= y < height:
                for x in range(start, end):
                    if 0 <= x < width:
                        val = image_data[x][y]
                        if lower <= val <= upper:
                            dark_pixels += 1
                        total_pixels += 1
        else:
            # column mode => index is x
            x = index
            if 0 <= x < width:
                for y in range(start, end):
                    if 0 <= y < height:
                        val = image_data[x][y]
                        if lower <= val <= upper:
                            dark_pixels += 1
                        total_pixels += 1

        if total_pixels == 0:
            return 0.0
        return dark_pixels / float(total_pixels)
