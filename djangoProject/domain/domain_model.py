import abc
import json
import uuid
from abc import abstractmethod
from dataclasses import dataclass, field
import time
from typing import Dict, List, Set
from uuid import uuid1

#--custom Exception
class DomainException(Exception):
    message = "Произошла ошибка при выполнении операции"
    code = "domain_error"

class FileNotFoundInBatchError(DomainException):
    """Фаил по айди не найден в пачке"""

class FileEmptyError(DomainException):
    """У файла отсутствует имя или содержание"""


class InvalidJsonFormatError(DomainException):
    """Некорректный формат JSON"""


class InvalidDataTypeError(DomainException):
    """Некорректный тип данных"""


#--custom type
FileName = str
FileBody = str
#--

class CheckCorrectFile:
    """
    Базовый класс валидации файла.
        Метод:
            check: должен в результате вернуть True или вызвать исключение
    """
    def __init__(self, file_attribute_for_check):
        self.file_attribute_for_check = file_attribute_for_check

    def check(self) -> bool:
        return True

class CheckJsonCorrect(CheckCorrectFile):
    """
    Конкретный класс для проверки корректности загрузки JSON
        переопределен check
    """
    def check(self):
        try:
            json.loads(self.file_attribute_for_check)

        except json.JSONDecodeError as e:
            msg = f"Строка {e.lineno}, колонка {e.colno}: {e.msg}"
            raise InvalidJsonFormatError(msg, e) from e

        except TypeError as e:
            raise InvalidDataTypeError(str(e), e) from e

        except Exception as e:
            raise DomainException(f"Обработка json пошла не по плану : {e}", e) from e

        return True

class MergeProcessor:
    """
    Базовый класс процессора слияния файлов.

    Атрибуты:
        process_files (Dict[str, str]): Словарь с именами объединенных файлов и их содержимым
        files (List[File]): Список файлов для обработки
        generate_name (str): Имя объединенного файла, генерируемое автоматически

    Методы:
        by_merge: Выполняет слияние файлов
        get_result_file_body: Возвращает результат слияния
        generate_name: Статический метод генерации имени файла

    Переопределить:
        by_merge: вся логика обработки словаря Dict[FileName:FileBody]
    """
    def __init__(self):
        self.process_files: Dict[FileName:FileBody] = {}
        self.files = []
        self.generate_name = f"merged_{time.strftime('%Y%m%d%H%M%S')}"

    def by_merge(self, files: List['File']):
        self.files = files
        for file in self.files:
           self.process_files[self.generate_name] += file.file_body

    def get_result_file_body(self) -> 'Dict[FileName:FileBody]':
        return self.process_files

class MergeJsonProcessor(MergeProcessor):
    """
    Конкретный класс для слияния JSON файлов
        переопределён by_merge, в качестве демонстрации работы.
    """
    def by_merge(self, files: List['File']):
        self.files = files
        dict_file_body = self.process_files.setdefault(self.generate_name, {})

        for file in self.files:

            data = json.loads(file.file_body)
            for key, value in data.items():

                ##############################################
                # В реальной эксплуатации в этот раздел,
                # будут подключены уже имеющиеся скрипты,
                # которые ожидают на вход пачку файлов.
                ##############################################
                if key in dict_file_body:
                    dict_file_body[key] += value  # Конкатенация строк
                else:
                    dict_file_body[key] = value
                ##############################################

        self.process_files[self.generate_name] = json.dumps(dict_file_body, ensure_ascii=False)


@dataclass
class File:
    """
    Базовый класс, описывающий сущность файла.

    Атрибуты:
        file_name (str): Имя файла
        file_body (str): Содержимое файла
        batch (FileBatch): Ссылка на пачку
        id (UUID): Уникальный идентификатор файла (генерируется автоматически)

    Методы:
        delete: Удаляет файл из пачки
        check_correct_file: Проверяет корректность содержимого файла
        create_set: фабрика создания сущностей файлов и размещение их в пачке.
    """

    file_name: str
    file_body: str
    batch: 'FileBatch'
    id:uuid.UUID = field(default_factory=lambda: uuid1())

    def __post_init__(self):
        pass
        #print('108', [self.id,self.file_name, self.file_body, self.batch.id])
        #todo добавить ЛОГ отладочный ?!

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other,File):
            return self.id == other.id
        else:
            return False

    def delete(self):
        self.batch.remove_file(self)

    @staticmethod
    def check_correct_file(file_attribute_for_check) -> bool:
        concrete_check = CheckCorrectFile(file_attribute_for_check)
        return concrete_check.check()

    @classmethod
    def create_set(
            cls,
            batch:'FileBatch',
            files: Dict[FileName, FileBody]
    ):
        file_set = set()
        for file_name, file_body in files.items():

            if file_name is None:
                raise FileEmptyError('FileName empty')
            if file_body is None:
                raise FileEmptyError('FileBody empty')

            if cls.check_correct_file(file_body):
                file = cls(
                    file_name,
                    file_body,
                    batch
                )
                file_set.add(file)

        return file_set


class UploadedJsonFile(File):
    """
    Конкретный клас файла JSON
        переопределен метод: check_correct_file
    """
    @staticmethod
    def check_correct_file(file_attribute_for_check):
        concrete_check = CheckJsonCorrect(file_attribute_for_check)
        return concrete_check.check()

class FileBatch:
    """
    Корневой базовый класс, описывающий сущность "Пачка файлов".

    Аттрибуты:
        uploaded_file (Type[File]): Множество файлов
        choice_merge_processor (Type[MergeProcessor]): Класс процессора слияния файлов
        id (UUID): Уникальный идентификатор пакета
        _files (Set[File]): Набор обычных файлов
        _merge_files (Set[File]): Набор объединенных файлов

    Методы:
        file: Получает файл по ID
        add_files: Добавляет файлы в пачку, c предварительным созданием через фабрику File.create_set
        remove_file: Удаляет файл из пачки
        get_all_files: Возвращает все файлы для слияния
        get_merge_files: Возвращает все слитые файлы
        merged_file_in_batch: Сливает файлы в соответствии с переопределённым choice_merge_processor
            и сохраняет результат
        create: Фабрика создания пачки
    """
    uploaded_file = File
    choice_merge_processor = MergeProcessor

    def __init__(self, id: uuid.UUID):
        self.id: uuid.UUID = id
        self._files: Set[File] = set()
        self._merge_files: Set[File] = set()

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, FileBatch):
            return self.id == other.id
        else:
            return False

    def file(self, file_id = None) -> uploaded_file:
        try:
            file = next(f for f in self._files if f.id == file_id)
        except StopIteration:
            file = next(f for f in self._merge_files if f.id == file_id)
        except StopIteration:
            raise FileNotFoundInBatchError(f'File id = {file_id} not found in the batch( id_batch = {self.id})')

        return file

    def add_files(self, files: Dict[FileName,FileBody]):
        """
        На вход принимает словарь с файлами Dict[FileName,FileBody]
        Вызывает фабрику File.create_set, результат фабрики - множество файлов, кладет в текущую пачку
        """
        file_set = self.uploaded_file.create_set(self,files)
        #print('185',files)
        #todo вставить лог сюда как минимум
        self._files.update(file_set)

    def remove_file(self,file: uploaded_file):
        if file in self._files:
            self._files.remove(file)
            return True
        elif file in self._merge_files:
            self._merge_files.remove(file)
            return True
        else:
            return False

    def get_all_files(self) -> List[uploaded_file]:
        return sorted(self._files, key=lambda file: file.id)

    def get_merge_files(self)-> List[uploaded_file]:
        return list(self._merge_files)

    def merged_file_in_batch(self):
        merge_instance = self.choice_merge_processor()
        merge_instance.by_merge(self.get_all_files())

        self._merge_files.update(
            self.uploaded_file.create_set(
                self,
                merge_instance.get_result_file_body()
            )
        )
        #print('213',merge_instance.get_result_file_body())
        # todo вставить лог сюда как минимум

    @classmethod
    def create(cls, files: Dict[str,str]):
        batch_id = uuid1()
        batch = cls(batch_id)
        batch.add_files(files)

        return batch

class JsonFileBatch(FileBatch):
    """
    Конкретный класс пачки с JSON файлами
        Класс файлов: UploadedJsonFile
        класс процесса слияния: MergeJsonProcessor
    """
    uploaded_file = UploadedJsonFile
    choice_merge_processor = MergeJsonProcessor