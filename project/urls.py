from django.urls import path

from .views import (
    MyProjectsView,
    ProjectDetailView,
    ProjectFileDownloadView,
    ProjectFileUploadView,
    ProjectGalleryView,
    ProjectImageView,
    ProjectOptionsView,
)


urlpatterns = [
    path("", ProjectGalleryView.as_view(), name="project-gallery"),
    path("options/", ProjectOptionsView.as_view(), name="project-options"),
    path("mine/", MyProjectsView.as_view(), name="my-projects"),
    path("<int:project_id>/", ProjectDetailView.as_view(), name="project-detail"),
    path("<int:project_id>/images/", ProjectImageView.as_view(), name="project-images"),
    path("<int:project_id>/images/<int:image_id>/", ProjectImageView.as_view(), name="project-image"),
    path("<int:project_id>/files/", ProjectFileUploadView.as_view(), name="project-files"),
    path("<int:project_id>/files/<int:file_id>/", ProjectFileUploadView.as_view(), name="project-file"),
    path("files/<int:file_id>/", ProjectFileDownloadView.as_view(), name="project-file-download"),
]
