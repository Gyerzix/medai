import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import generate_uid, ExplicitVRLittleEndian
from PIL import Image
import numpy as np
import datetime

# Пути к файлам
jpg_path = "images/ft027_jpg.rf.9cbda95939b98f43ecfc19aab35c4a50.jpg"
dicom_path = "ft027.dcm"

# Открытие изображения и преобразование
img = Image.open(jpg_path).convert('L')  # Градации серого
pixel_array = np.array(img)

# Мета-информация
file_meta = pydicom.Dataset()
file_meta.MediaStorageSOPClassUID = pydicom.uid.SecondaryCaptureImageStorage
file_meta.MediaStorageSOPInstanceUID = generate_uid()
file_meta.ImplementationClassUID = generate_uid()  # Уникальный идентификатор реализации
file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

# Создание DICOM Dataset
ds = FileDataset(dicom_path, {}, file_meta=file_meta, preamble=b"\0" * 128)
dt = datetime.datetime.now()
ds.ContentDate = dt.strftime('%Y%m%d')
ds.ContentTime = dt.strftime('%H%M%S.%f')

# Основная информация о пациенте
ds.PatientName = "Vyacheslav Ivanov"
ds.PatientID = "123456"
ds.PatientBirthDate = "19700101"  # Пример даты рождения
ds.PatientSex = "O"  # M/F/O (male/female/other)
ds.PatientAge = "050Y"  # Формат: nnnD, nnnW, nnnM, nnnY

# Исследование и серия
ds.StudyDate = dt.strftime('%Y%m%d')
ds.StudyTime = dt.strftime('%H%M%S.%f')
ds.StudyDescription = "Secondary capture"  # Описание исследования
ds.StudyID = "1"
ds.StudyInstanceUID = generate_uid()
ds.SeriesInstanceUID = generate_uid()
ds.SeriesNumber = "1"  # Номер серии
ds.SeriesDescription = "Converted from JPEG"  # Описание серии
ds.InstanceNumber = "1"  # Номер инстанса

# Информация об оборудовании
ds.Modality = "OT"  # Other
ds.Manufacturer = "Custom DICOM Converter"
ds.InstitutionName = "Your Institution"
ds.InstitutionAddress = "Your Address"
ds.StationName = "WORKSTATION1"  # Имя рабочей станции

# Технические параметры изображения
ds.SamplesPerPixel = 1
ds.PhotometricInterpretation = "MONOCHROME2"
ds.Rows, ds.Columns = pixel_array.shape
ds.BitsAllocated = 8
ds.BitsStored = 8
ds.HighBit = 7
ds.PixelRepresentation = 0
ds.PixelSpacing = [1.0, 1.0]  # Размер пикселя в мм (горизонталь, вертикаль)
ds.SliceThickness = 1.0  # Толщина среза в мм (если применимо)
ds.SpacingBetweenSlices = 1.0  # Расстояние между срезами
ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]  # Ориентация изображения
ds.ImagePositionPatient = [0, 0, 0]  # Позиция изображения в пространстве
ds.PixelData = pixel_array.tobytes()

# Дополнительные описательные теги
ds.ImageComments = "Converted from JPEG image"
ds.LossyImageCompression = "00"  # 00 - без потерь, 01 - с потерями
ds.LossyImageCompressionRatio = 1.0  # Коэффициент сжатия
ds.RequestingPhysician = "Dr. Smith"  # Направляющий врач
ds.PerformingPhysicianName = "Dr. Jones"  # Выполняющий врач
ds.OperatorName = "Technician"  # Оператор

# Уникальные идентификаторы
ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
ds.FrameOfReferenceUID = generate_uid()  # UID системы координат

# Сохранение
ds.save_as(dicom_path)
print(f"DICOM сохранён: {dicom_path}")