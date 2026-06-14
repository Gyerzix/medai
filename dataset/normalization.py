import os
import cv2
import numpy as np
from tqdm import tqdm

# Пути к исходному и новому датасету
input_dir = "hip_fracture_dataset"
output_dir = "normalized_fracture_dataset"
target_size = (416, 416)


# Функция для загрузки и нормализации изображений
def process_and_save_images(input_path, output_path):
    os.makedirs(output_path, exist_ok=True)
    images = os.listdir(input_path)

    for img_name in tqdm(images, desc=f"Processing {input_path}"):
        img_path = os.path.join(input_path, img_name)
        output_img_path = os.path.join(output_path, img_name)

        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)  # Грузим в градациях серого
        if img is None:
            continue

        # Изменение размера
        resized_img = cv2.resize(img, target_size, interpolation=cv2.INTER_LINEAR)

        # Нормализация (0-1)
        normalized_img = resized_img.astype(np.float32) / 255.0

        # Z-score
        # mean, std = resized_img.mean(), resized_img.std()
        # normalized_img = (resized_img - mean) / std

        # Сохранение
        cv2.imwrite(output_img_path, (normalized_img * 255).astype(np.uint8))


# Обход всех папок в датасете
for split in ["train", "valid", "test"]:
    for category in ["fracture", "normal"]:
        input_path = os.path.join(input_dir, split, category)
        output_path = os.path.join(output_dir, split, category)
        process_and_save_images(input_path, output_path)

print("Все изображения обработаны и сохранены!")
