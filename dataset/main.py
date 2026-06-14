import os
import cv2
import numpy as np

# Пути к папкам
images_path = 'images'
labels_path = 'labels'
output_path_0 = 'output/0'  # Здоровый сустав
output_path_1 = 'output/1'  # Поврежденный сустав
output_single = 'output/single'  # Если в изображении только один сустав

# Создаем папки для вывода, если они не существуют
os.makedirs(output_path_0, exist_ok=True)
os.makedirs(output_path_1, exist_ok=True)
os.makedirs(output_single, exist_ok=True)

# Проходим по всем изображениям
for image_name in os.listdir(images_path):
    if image_name.endswith('.jpg') or image_name.endswith('.png'):
        # Читаем изображение
        image = cv2.imread(os.path.join(images_path, image_name))
        height, width, _ = image.shape

        # Читаем метки из txt файла
        label_path = os.path.join(labels_path, image_name.replace('.jpg', '.txt').replace('.png', '.txt'))

        with open(label_path, 'r') as file:
            labels = file.readlines()

        # Если в файле только одна строка, сохраняем изображение целиком в output/single
        if len(labels) == 1:
            class_id, _, _, _, _ = map(float, labels[0].split())
            output_dir = output_path_1 if class_id == 1 else output_path_0
            cv2.imwrite(os.path.join(output_single, image_name), image)
            continue

        # Разделяем изображение на две половины
        left_image = image[:, :width // 2]
        right_image = image[:, width // 2:]

        left_has_fracture = False
        right_has_fracture = False

        # Проверяем, есть ли повреждение на каждой половине
        for label in labels:
            class_id, x_center, _, _, _ = map(float, label.split())

            if x_center < 0.5:  # Левая половина
                if class_id == 1:
                    left_has_fracture = True
            else:  # Правая половина
                if class_id == 1:
                    right_has_fracture = True

        # Сохраняем изображения в соответствующие папки
        cv2.imwrite(os.path.join(output_path_1 if left_has_fracture else output_path_0, f'left_{image_name}'),
                    left_image)
        cv2.imwrite(os.path.join(output_path_1 if right_has_fracture else output_path_0, f'right_{image_name}'),
                    right_image)