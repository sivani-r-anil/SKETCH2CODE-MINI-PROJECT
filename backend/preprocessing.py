import cv2


def preprocess_image(image_path):
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError('Cannot decode this image. Upload a PNG or JPEG.')
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresholded = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    # Preserve dimensions so all stages use the same coordinates.
    return thresholded
