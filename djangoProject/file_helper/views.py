import io
import re

from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.http import HttpResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView

from domain.domain_service import ServiceFileProcessor,  DjangoUOW
from .forms import JsonUploadForm, UploadFile
# Create your views here.

from django.shortcuts import render
from .models import FileBatch, File

file_processor = ServiceFileProcessor(DjangoUOW())

def main_page(request):

    if request.POST:
        form = JsonUploadForm(request.POST, request.FILES)
        if form.is_valid():
            files = form.cleaned_data.get('files')
            for_domain_files = {file.name: file.read().decode('utf-8') for file in files}
            file_processor.add_new_batch(for_domain_files)
            return redirect('main')
    else:
        form = JsonUploadForm()

    batches = FileBatch.objects.order_by('-id')[:10].select_related('file_type').prefetch_related('file_set')
    return render(request, 'main.html', {'batches': batches, 'form': form})

def batch_detail(request, batch_id):
    batch = get_object_or_404(FileBatch.objects.select_related('file_type'), domain_id=batch_id)
    error_msg=None

    django_merged_files = Prefetch(
        'file_set',
        queryset=File.objects.filter(is_merge='m').order_by('-id'),
        to_attr='django_merged_files'
    )

    django_file_files = Prefetch(
        'file_set',
        queryset=File.objects.filter(is_merge='f').order_by('-id'),
        to_attr='django_file_files'
    )
#
    batch = FileBatch.objects.prefetch_related(django_merged_files, django_file_files).get(domain_id=batch_id)

    if request.POST and 'merge' in request.POST:
        file_processor.merged_file_in_batch(batch_id)
        return redirect('batch_detail', batch_id = batch_id)


    if request.POST and 'file' in request.FILES:
        form = UploadFile(request.POST, request.FILES)
        if form.is_valid():
            form_file = form.cleaned_data.get('file')
            file = {form_file.name: form_file.read().decode('utf-8')}
            try:
                file_processor.add_file_to_batch(batch_id, file)
                return redirect('batch_detail', batch_id=batch_id)
            except Exception as e:
                error_msg = f' Ошибка при загрузке файла в пачку: {e}'

    else:
        form = UploadFile()


    return render(
        request, 'batch_detail.html',{
            'batch':batch,
            'merged_files': batch.django_merged_files,
            'file_files' : batch.django_file_files,
            'error_msg': error_msg
        }

    )

def download_file(request, file_id):
    file = File.objects.get(domain_id=file_id)

    file_content = file.file_body.encode('utf-8')
    file_object = io.BytesIO(file_content)
    file_name_full = f'{file.file_name}.{re.match(r'^([A-Za-z]+)', 'JSON2').group(1).lower()}'

    response = FileResponse(file_object, as_attachment=True, filename=file_name_full)
    response['Content-Length'] = len(file_content)

    return response

def remove_file_from_batch(request, batch_id, remove_file_id):
    file_processor.remove_file_from_batch(batch_id, remove_file_id)
    return redirect('batch_detail', batch_id=batch_id)

class BatchListView(ListView):
    model = FileBatch
    template_name = 'all_batch.html'
    context_object_name = 'batches'
    paginate_by = 10
    ordering = ['-id']
