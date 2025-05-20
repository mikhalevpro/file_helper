from django.urls import path

from . import views

urlpatterns = [
    path('', views.main_page, name='main'),
    path('batch/<uuid:batch_id>/', views.batch_detail, name='batch_detail'),
    path('download/<uuid:file_id>/', views.download_file, name='download_file'),
    path('remove/<uuid:batch_id>/<uuid:remove_file_id>/', views.remove_file_from_batch, name='remove_file'),
    path('batches/', views.BatchListView.as_view(), name ='all_batch'),
]