import json
from typing import List

import pytest

from domain.domain_service import AbstractRepository, AbstractUnitOfWork, ServiceFileProcessor, DjangoRepository, DjangoUOW
from domain.domain_model import FileBatch, JsonFileBatch

from file_helper import models as django_models
###################File######################
files_count_2 = {
        'text.txt': '{"text":"Hellow"}',
        'text2.txt': '{"text":"World"}',
    }

files_count_3 = {
        'text.txt': '{"text":"Hellow"}',
        'text2.txt': '{"text":"World"}',
        'text3.txt': '{"text":"!!!!"}'
    }

file_number_3 = {'text3.txt': '{"text":"!!!!"}'}

file_merge= '{"text": "HellowWorld!!!!"}'
###################Repository################

@pytest.mark.django_db
def test_repository_can_save_to_file_batch():

    file_batch = JsonFileBatch.create(files_count_3)

    repo = DjangoRepository()
    repo.add(file_batch)

    [django_file_batch] = django_models.FileBatch.objects.prefetch_related('file_set').all()

    for file in django_file_batch.file_set.all():
        if file.is_merge == 'f':
            assert files_count_3.get(file.file_name) == file.file_body


@pytest.mark.django_db
def test_repository_can_create_merge_file_in_file_batch():

    file_batch = JsonFileBatch.create(files_count_3)

    repo = DjangoRepository()
    repo.add(file_batch)

    get_repo_file_batch = repo.get(file_batch.id)
    get_repo_file_batch.merged_file_in_batch()

    repo.add(get_repo_file_batch)

    [django_file_batch] = django_models.FileBatch.objects.prefetch_related('file_set').all()

    for file in django_file_batch.file_set.all():
        if file.is_merge == 'm':
            assert file.file_body == file_merge

###################UOW######################
@pytest.mark.django_db
def test_uow_can_create_file_batch_and_merge():
    uow = DjangoUOW()
    file_batch = JsonFileBatch.create(files_count_3)

    with uow:
        uow.rep_file_batches.add(file_batch)
        uow.commit()

    with uow:
        file_batch = uow.rep_file_batches.get(file_batch.id)
        print(file_batch)
        print('T92',file_batch._files)
        file_batch.merged_file_in_batch()
        uow.commit()

    with uow:
        file_batch = uow.rep_file_batches.get(file_batch.id)
        print('!!!!!',file_batch.get_merge_files())
        assert file_batch.get_merge_files() != []

@pytest.mark.django_db
def test_uow_can_rollback():
    uow = DjangoUOW()
    file_batch = JsonFileBatch.create(files_count_3)

    with uow:
        uow.rep_file_batches.add(file_batch)
        uow.commit()

    with uow:
        file_batch = uow.rep_file_batches.get(file_batch.id)
        file_batch.merged_file_in_batch()
        uow.rollback()

    with uow:
        file_batch = uow.rep_file_batches.get(file_batch.id)
        assert file_batch.get_merge_files() == []

@pytest.mark.django_db
def test_uow_can_remove_file_from_batch():
    uow = DjangoUOW()
    file_batch = JsonFileBatch.create(files_count_3)

    with uow:
        uow.rep_file_batches.add(file_batch)
        uow.commit()

    with uow:
        file_batch = uow.rep_file_batches.get(file_batch.id)
        file = file_batch.get_all_files().pop()
        print('!!!!!!!!!!!!',file)
        file_batch.file(file.id).delete()
        uow.commit()


    with uow:
        file_batch = uow.rep_file_batches.get(file_batch.id)
        assert len(file_batch.get_all_files()) != 3

###################Service##################
class FakeFileStor(AbstractRepository):
    @property
    def list(self) -> List[FileBatch]:
        return list(self.set_file_batch)

    def _get(self, id):
        pass

    def get(self, id) -> FileBatch:
        return next(file for file in self.set_file_batch if file.id == id)


class FakeFileUOW(AbstractUnitOfWork):
    def __init__(self):
        self.rep_file_batches = FakeFileStor()
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

def test_add_batch():

    service = ServiceFileProcessor(FakeFileUOW())

    service.add_new_batch(files_count_3)

    id = service.uow.rep_file_batches.get_list_sorted_by_id()[0].id

    assert service.uow.rep_file_batches.get(id) is not None


def test_add_file_to_batch():

    service = ServiceFileProcessor(FakeFileUOW())

    service.add_new_batch(files_count_2)
    batchsi = service.uow.rep_file_batches.get_list_sorted_by_id()
    batch_id = batchsi[0].id
    service.add_file_to_batch(batch_id, file_number_3)

    batch = service.uow.rep_file_batches.get(batch_id)
    files = batch.get_all_files()
    assert len(files) == 3


def test_delete_file():

    service = ServiceFileProcessor(FakeFileUOW())
    service.add_new_batch(files_count_3)

    batch_id = service.uow.rep_file_batches.get_list_sorted_by_id()[0].id
    batch = service.uow.rep_file_batches.get_list_sorted_by_id()[0]
    id_file = batch.get_all_files()[0].id

    service.remove_file_from_batch(batch_id, id_file)

    assert service.uow.rep_file_batches.get(batch_id) is not None
    assert len(service.uow.rep_file_batches.get(batch_id).get_all_files()) == 2

def test_merged_file_in_batch():

    service = ServiceFileProcessor(FakeFileUOW())
    service.add_new_batch(files_count_3)

    batch_id = service.uow.rep_file_batches.get_list_sorted_by_id()[0].id

    service.merged_file_in_batch(batch_id)

    merge_file = service.uow.rep_file_batches.get(batch_id).get_merge_files()
    dict_body =  json.loads(merge_file[0].file_body)

    assert dict_body.get('text') == 'HellowWorld!!!!'

#todo логиррование
#todo сильно далеко: sql
