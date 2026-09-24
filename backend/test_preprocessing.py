import cv2
from preprocessing import preprocess_image

input_path = "uploads/exapmle.png"
output_path = "uploads/example_processed.png"

processed_image = preprocess_image(input_path)

cv2.imwrite(output_path, processed_image)

print("Image preprocessing completed!")
print("Saved to:", output_path)