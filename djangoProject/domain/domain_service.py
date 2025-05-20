import abc
from typing import Dict

from django.db import transaction

from .domain_model import FileBatch, FileName, FileBody, JsonFileBatch

from file_helper import models as django_models
################Repository###############
class AbstractRepository(abc.ABC):
    def __init__(self):
        self.set_file_batch = set() # type: Set[FileBatch]

    def add(self, file_batch: FileBatch):
        self.set_file_batch.add(file_batch)

    def get(self, id) -> FileBatch:
        fb = self._get(id)
        if fb:
            self.set_file_batch.add(fb)
        return fb

    @abc.abstractmethod
    def _get(self, id):
        raise NotImplementedError

    def get_list_sorted_by_id(self):
        return sorted(self.set_file_batch, key=lambda object: object.id)

class DjangoRepository(AbstractRepository):
    def add(self, file_batch: FileBatch ):
        super().add(file_batch)
        self.update(file_batch)

    def _get(self, id) -> FileBatch:
        return django_models.FileBatch.objects.get(domain_id=id).to_domain()

    @staticmethod
    def update(file_batch: FileBatch):
        django_models.FileBatch.update_from_domain(file_batch)

################UOW#######################
class AbstractUnitOfWork(abc.ABC):
    rep_file_batches: AbstractRepository

    def __enter__(self) -> 'AbstractUnitOfWork':
        return self

    def __exit__(self, *args):
        self.rollback()

    @abc.abstractmethod
    def commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError

class DjangoUOW(AbstractUnitOfWork):

    def __enter__(self):
        self.rep_file_batches = DjangoRepository()
        return super().__enter__()

    def __exit__(self, *args):
        return super().__exit__()

    def commit(self):
        for file_batch in self.rep_file_batches.set_file_batch:
            with transaction.atomic():
                self.rep_file_batches.update(file_batch)

    def rollback(self):
        pass

##############Service####################
class ServiceFileProcessor:
    """Класс службы для работы с пачками.

            Аттрибуты:
                uow: Конкретный реализованный UOW для управления транзакциями.
        """
    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    def add_new_batch(self, files: Dict[FileName,FileBody]):
        with self.uow:
            self.uow.rep_file_batches.add(
                JsonFileBatch.create(files)

            )
            self.uow.commit()

    def add_file_to_batch(self, batch_id, files: Dict[FileName,FileBody] ):
        with self.uow:
            batch = self.uow.rep_file_batches.get(batch_id)
            batch.add_files(files)
            self.uow.commit()

    def remove_file_from_batch(self, batch_id, remove_file_id):
        with self.uow:
            batch = self.uow.rep_file_batches.get(batch_id)
            batch.file(file_id=remove_file_id).delete()
            self.uow.commit()

    def merged_file_in_batch(self, batch_id):
        with self.uow:
            batch = self.uow.rep_file_batches.get(batch_id)
            batch.merged_file_in_batch()
            self.uow.commit()