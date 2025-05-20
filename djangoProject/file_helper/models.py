from django.db import models
from django.db.models import ForeignKey, CASCADE
from domain import domain_model


DOMAIN_CLASS_TO_FILETYPE_BATCH = {'JSON1': domain_model.JsonFileBatch}
DOMAIN_CLASS_TO_FILETYPE_FILE = {'JSON1': domain_model.UploadedJsonFile}
DOMAIN_CLASS_DESC = {
    'JSON1': 'Совмещаем джейсон, тип: любой - "склеивание ключа, добавление ключа"'
}

# Create your models here.
class FileType(models.Model):
    type_name = models.CharField(max_length=10)
    desc = models.CharField()

class FileBatch(models.Model):
    """
    Пачка с файлами django
        Методы:
            update_from_domain - Для обновления данных в базе из доменной модели
            to_domain - Для получения доменной модели из базы
    """
    domain_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    file_type = models.ForeignKey(FileType,on_delete=CASCADE, null=True)

    @staticmethod
    def update_from_domain(file_batch: domain_model.FileBatch):
        """
        Метод обновления данных в базе по пачке из модели.
        Через fb.file_set.set() обновляет связи по файлам,
            удалённые файлы забывают пачку
        """
        try:
            fb = FileBatch.objects.get(domain_id=file_batch.id)
        except FileBatch.DoesNotExist:
            fb = FileBatch(domain_id=file_batch.id)

        django_file_type=None
        for const_type, cls in DOMAIN_CLASS_TO_FILETYPE_BATCH.items():
            if isinstance(file_batch, cls):
                django_file_type, _ = FileType.objects.get_or_create(
                type_name = const_type,
                desc = DOMAIN_CLASS_DESC.get(const_type)
                )
                break

        if django_file_type is not None:
            fb.file_type = django_file_type

        fb.save()

        all_file =[File.from_domain('f',file, fb, django_file_type) for file in file_batch.get_all_files() ]
        all_file += [File.from_domain('m', file, fb, django_file_type) for file in file_batch.get_merge_files()]

        fb.file_set.set(all_file)

    def to_domain(self):
        """
        Метод восстановления пачки с файлами в модель.
        Для восстановления используется маппинг:
            DOMAIN_CLASS_TO_FILETYPE_BATCH - классы пачек
            DOMAIN_CLASS_TO_FILETYPE_FILE - классы файлов
                {тип файла в базе: класс для работы с этим типом}

            DOMAIN_CLASS_DESC - описывает тип файла в базе.

        Возвращает экземпляр пачки django
        """
        file_type_name = self.file_type.type_name

        domain_class_batch = DOMAIN_CLASS_TO_FILETYPE_BATCH.get(file_type_name)
        domain_class_file = DOMAIN_CLASS_TO_FILETYPE_FILE.get(file_type_name)

        file_batch = domain_class_batch(id=self.domain_id)

        files_set = set(
            domain_class_file(
                id=django_file.domain_id,
                file_name=django_file.file_name,
                file_body=django_file.file_body,
                batch=file_batch
            )
            for django_file in File.objects.filter(batch_id=self.id, is_merge='f')
        )

        files_merge_set = set(
            domain_class_file(
                id=django_file.domain_id,
                file_name=django_file.file_name,
                file_body=django_file.file_body,
                batch=file_batch
                )
            for django_file in File.objects.filter(batch_id= self.id, is_merge='m')
            )

        file_batch._files = files_set
        file_batch._merge_files = files_merge_set

        return file_batch

class File(models.Model):
    """
    Файлы в пачке django
        Метод:
            from_domain - обновляет или создаёт File в базе из модели и возвращает экземпляр файла django
    """
    domain_id = models.UUIDField()
    file_name = models.CharField()
    file_body = models.CharField()
    batch_id = models.ForeignKey(FileBatch,on_delete=CASCADE, null=True)
    file_type = models.ForeignKey(FileType,on_delete=CASCADE, null=True)
    is_merge = models.CharField(max_length=1)

    @staticmethod
    def from_domain(
            is_merge,
            domain_model_file: domain_model.File,
            django_file_batch: FileBatch,
            django_file_type: FileType
    ):

        file, _ = File.objects.update_or_create(
            domain_id = domain_model_file.id,
            file_name = domain_model_file.file_name,
            file_body = domain_model_file.file_body,
            batch_id = django_file_batch,
            file_type = django_file_type,
            is_merge = is_merge
        )
        return file
