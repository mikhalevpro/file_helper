# forms.py
from tabnanny import check

from django import forms
from django.core.exceptions import ValidationError
from django.db.models.expressions import result
from django.utils.safestring import mark_safe

import domain.domain_model


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultiFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultiFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if isinstance(data, (list,tuple)):
            result = [super().clean(d, initial) for d in data]
            return result
        return super().clean(data, initial)

class JsonUploadForm(forms.Form):
    files = MultiFileField(label='Выберите JSON файл')

    def clean_files(self):
        files = self.cleaned_data.get('files')
        if not files:
            raise ValidationError('File not selected')

        for file in files:
            try:
                file_content = file.read().decode('utf-8')
                curr_chek = domain.domain_model.CheckJsonCorrect(file_content)
                curr_chek.check()
            except Exception as e:
                raise ValidationError(f'Ошибка в домене при проверке файла: {file.name}: {str(e)}')
            finally:
                file.seek(0)
        return files

class UploadFile(forms.Form):
    file = forms.FileField()