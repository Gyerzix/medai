# medai

`medai` — исследовательский пайплайн для обнаружения переломов тазобедренного сустава на рентгеновских снимках.


Система принимает DICOM-файл через веб-интерфейс, затем по шагам:
- извлекает и сохраняет метаданные исследования;
- ставит задачу в очередь Kafka;
- конвертирует DICOM в изображение и делит снимок на левый и правый сустав;
- классифицирует каждый сустав моделью ResNet18;
- сохраняет результат, превью и аннотированный DICOM для скачивания.

> **Важно:** проект предназначен только для образовательных и исследовательских целей и не является сертифицированным медицинским устройством.

КВМО-11-24: Гаджиев Шахин (shakhingadzhiev@yandex.ru), Дорошенко Глеб (dgleb02@mail.ru).

## Архитектура

Текущий основной runtime-контур:

1. `upload_study` (Django view)
2. `send_to_kafka` (Kafka producer)
3. `kafka_consumer` (management command)
4. `HipFractureDetector` (inference-слой)
5. `DicomStudy` (хранение результатов и UI)

Поток данных:

`DICOM upload -> DicomStudy (pending) -> Kafka message -> preprocessing + inference -> DicomStudy (completed) -> web UI / annotated DICOM download`

Параллельно существует offline ML-контур для обучения модели:

`raw images + YOLO labels -> split by hip -> normalization -> ImageFolder dataset -> training notebook -> .pth weights -> HipFractureDetector`

## Структура проекта

### `medai/`

Django-приложение и веб-сервис.

- [`medai/medai`](medai/medai)
  - настройки проекта (`settings.py`, `urls.py`, `wsgi.py`)
  - PostgreSQL, media/static, Kafka broker
  - entrypoint: `manage.py`

- [`medai/dicom_processor`](medai/dicom_processor)
  - основное Django-приложение
  - модель `DicomStudy`, формы, views, admin
  - шаблоны списка, загрузки и деталей исследования

- [`medai/dicom_processor/services`](medai/dicom_processor/services)
  - inference-слой
  - `HipFractureDetector` — загрузка ResNet18, препроцессинг DICOM, предсказание с confidence

- [`medai/dicom_processor/management/commands`](medai/dicom_processor/management/commands)
  - `kafka_consumer.py` — фоновый worker обработки исследований

- [`medai/dicom_processor/templates`](medai/dicom_processor/templates)
  - `study_list.html` — список исследований
  - `upload.html` — загрузка DICOM
  - `dicomstudy_detail.html` — результаты анализа, превью, скачивание

### `dataset/`

Скрипты подготовки обучающего датасета из размеченных изображений.

- [`dataset/main.py`](dataset/main.py)
  - разбивает исходные снимки на левый и правый тазобедренный сустав
  - использует YOLO-разметку (`images/` + `labels/`)
  - сохраняет кропы в `output/0`, `output/1`, `output/single`

- [`dataset/normalization.py`](dataset/normalization.py)
  - ресайз до `416×416`, grayscale, нормализация `0–1`
  - строит `normalized_fracture_dataset/{train,valid,test}/{fracture,normal}`

- [`dataset/dicom.py`](dataset/dicom.py)
  - утилита конвертации JPEG → DICOM (для тестовых данных)

### Корень репозитория

- [`hip_fracture_classification.ipynb`](hip_fracture_classification.ipynb)
  - обучение и оценка CNN-моделей
  - сравнение `resnet18`, `vgg16`, `densenet121`
  - метрики, ROC/PR, confusion matrix, сохранение весов

## Основные сущности

### DicomStudy

ORM-модель исследования. Хранит:

- `title`, `dicom_file`, `upload_date`
- `patient_id`, `patient_sex`, `patient_age`, `study_date`
- `study_instance_uid`, `accession_number`, `modality`, `body_part_examined`, `study_description`
- `processing_status` — `pending | processing | completed | failed`
- `result_left_hip`, `result_right_hip` — `True` = перелом, `False` = норма
- `confidence_left`, `confidence_right` — уверенность модели (0–100%)
- `dicom_preview`, `left_hip_image`, `right_hip_image`

Метод `get_annotated_dicom()` возвращает анонимизированный DICOM с заключением в `ImageComments`.

### HipFractureDetector

Inference-класс. Основные методы:

- `dicom_to_rgb(dicom_path)` — DICOM → grayscale → RGB
- `preprocess_dicom(dicom_path)` — деление снимка пополам (левый / правый сустав)
- `predict_with_confidence(image_pil)` — softmax + confidence
- `process_dicom(dicom_path)` — полный inference для обоих суставов

Возвращает:

```python
{
    'left_pred': bool,
    'left_confidence': float,   # 0–100
    'right_pred': bool,
    'right_confidence': float,
    'status': 'completed' | 'failed',
}
```

### Kafka message

Producer отправляет в топик `dicom_studies`:

```python
{'study_id': <int>}
```

Consumer читает сообщение, блокирует запись в БД, обновляет статус и сохраняет результаты inference.

### ML training notebook

Обучающий контур в `hip_fracture_classification.ipynb`:

- датасет: `normalized_fracture_dataset` (`ImageFolder`, классы `fracture` / `normal`)
- аугментации: flip, rotation, crop, color jitter
- `CrossEntropyLoss` с весами классов
- оптимизатор: `Adam(lr=1e-4)`
- архитектуры: ResNet18, VGG16, DenseNet121
- production-модель: **ResNet18** → `hip_fracture_model_resnet18.pth`

На тестовой выборке (VGG16, 155 снимков): accuracy ≈ 0.94, AUC ≈ 0.93.

## Данные и артефакты

Ожидаемые директории и файлы:

### Подготовка датасета

- `images/` — исходные JPG/PNG
- `labels/` — YOLO `.txt` разметка
- `output/0`, `output/1`, `output/single` — кропы по суставам
- `hip_fracture_dataset/{train,valid,test}/{fracture,normal}`
- `normalized_fracture_dataset/{train,valid,test}/{fracture,normal}`

### Runtime Django

- `medai/models/hip_fracture_model_resnet18.pth` — веса модели (путь по умолчанию в consumer)
- `medai/media/dicom_files/` — загруженные DICOM
- `medai/media/dicom_previews/` — превью снимков
- `medai/media/processed/` — кропы левого и правого сустава

## Быстрый старт

### 1. Подготовка датасета

```powershell
# Разбиение снимков на левый/правый сустав по YOLO-разметке
python.exe .\dataset\main.py

# Нормализация и ресайз
python.exe .\dataset\normalization.py
```

### 2. Обучение модели

Откройте [`hip_fracture_classification.ipynb`](hip_fracture_classification.ipynb), распакуйте `normalized_resized_fracture_dataset.zip` (или используйте `normalized_fracture_dataset`) и обучите модель. Сохраните веса как `hip_fracture_model_resnet18.pth`.

### 3. Запуск веб-сервиса

```powershell
cd medai

# Миграции и запуск Django
python.exe manage.py migrate
python.exe manage.py runserver
```

Откройте `http://127.0.0.1:8000/` — список исследований, загрузка DICOM на `/upload/`.

### 4. Запуск Kafka consumer

В отдельном терминале (нужны Kafka на `localhost:9092` и файл весов):

```powershell
cd medai
python.exe manage.py kafka_consumer --model-path models/hip_fracture_model_resnet18.pth
```

После загрузки DICOM через UI consumer асинхронно обработает исследование и обновит статус на `completed`.

## Зависимости
По коду используются:

| Компонент | Пакеты |
|-----------|--------|
| ML / inference | `torch`, `torchvision`, `numpy`, `opencv-python`, `Pillow`, `scikit-learn`, `matplotlib` |
| Django app | `django`, `psycopg2` (PostgreSQL) |
| DICOM | `pydicom` |
| Очередь | `kafka-python` |
| Dataset scripts | `opencv-python`, `tqdm` |

## Инфраструктура

| Сервис | Назначение | Конфигурация |
|--------|------------|--------------|
| PostgreSQL | хранение `DicomStudy` | `medai/settings.py` → `DATABASES` |
| Kafka | асинхронная обработка | `localhost:9092`, топик `dicom_studies` |
| Django media | файлы DICOM и превью | `MEDIA_ROOT = medai/media` |

## Web routes

| URL | Описание |
|-----|----------|
| `/` | список исследований |
| `/upload/` | загрузка DICOM |
| `/study/<id>/` | детали и результаты анализа |
| `/study/<id>/download/` | скачивание аннотированного DICOM |
| `/admin/` | Django admin |

## Типовая цепочка подготовки данных

1. `dataset/main.py` — split по суставам из YOLO-разметки
2. `dataset/normalization.py` — нормализация и ресайз
3. `hip_fracture_classification.ipynb` — обучение и экспорт весов
4. размещение `hip_fracture_model_resnet18.pth` в `medai/models/`
5. `manage.py runserver` + `manage.py kafka_consumer` — production-like inference
