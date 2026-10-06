from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from aiohoush.core.responses import APIResponse
from user.services.mentor import avatar_url, full_name

from .models import Project, ProjectFile, ProjectImage
from .services import projects as project_service


PAGE_SIZE = 12
SUMMARY_LENGTH = 220


def _failure(message):
    return APIResponse(
        success=False,
        called_by="webapp",
        message=message,
        status=status.HTTP_200_OK,
    )


def _ok(message, data=None, http_status=status.HTTP_200_OK):
    return APIResponse(
        success=True,
        called_by="webapp",
        message=message,
        data=data,
        status=http_status,
    )


def _int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _list_param(data, name):
    """multipart: چند مقدار با یک نام؛ JSON: آرایه."""
    if hasattr(data, "getlist"):
        return data.getlist(name)
    value = data.get(name)
    return value if isinstance(value, list) else []


def _project_data(request) -> dict:
    return {
        "title": request.data.get("title"),
        "description": request.data.get("description"),
        "course": request.data.get("course"),
        "technologies": _list_param(request.data, "technologies"),
        "github_url": request.data.get("github_url"),
        "demo_url": request.data.get("demo_url"),
    }


def _image_url(request, image: ProjectImage) -> str:
    return request.build_absolute_uri(image.image.url)


def _summary(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= SUMMARY_LENGTH:
        return text
    return text[:SUMMARY_LENGTH].rsplit(" ", 1)[0] + "…"


def _course(project: Project):
    if not project.course_id:
        return None
    return {"id": project.course_id, "title": project.course.title}


def _card(request, project: Project) -> dict:
    images = list(project.images.all())
    return {
        "id": project.pk,
        "kind": project.kind,
        "title": project.title,
        "summary": _summary(project.description),
        "cover": _image_url(request, images[0]) if images else None,
        "imageCount": len(images),
        "technologies": [item.title for item in project.technologies.all()],
        "course": _course(project),
        "author": (
            {"name": full_name(project.owner)}
            if project.owner_id
            else None
        ),
    }


def _with_relations(queryset):
    return queryset.select_related("owner", "course").prefetch_related(
        "technologies",
        Prefetch("images", queryset=ProjectImage.objects.order_by("id")),
    )


def _file_row(item: ProjectFile) -> dict:
    return {
        "id": item.pk,
        "name": item.original_name,
        "size": item.size,
        "url": f"/project/files/{item.pk}/",
    }


def _detail(request, project: Project) -> dict:
    is_mine = project.owner_id == request.user.pk

    data = {
        **_card(request, project),
        "description": project.description,
        "images": [
            {"id": image.pk, "url": _image_url(request, image)}
            for image in project.images.all()
        ],
        "technologies": [
            {"id": item.pk, "title": item.title}
            for item in project.technologies.all()
        ],
        "githubUrl": project.github_url or None,
        "demoUrl": project.demo_url or None,
        "isMine": is_mine,
        "createdAt": project.created_at.isoformat(),
        "files": (
            [_file_row(item) for item in project.files.all()]
            if project_service.can_download_files(request.user, project)
            else None
        ),
    }

    if project.owner_id:
        data["author"] = {
            "name": full_name(project.owner),
            "bio": project.owner.bio or "",
            "avatar": avatar_url(project.owner, request),
        }

    # وضعیت بررسی فقط برای خود دانشجو
    if is_mine:
        data.update({
            "status": project.status,
            "statusLabel": project.get_status_display(),
            "rejectionReason": project.rejection_reason or None,
        })

    return data


# --- گالری ------------------------------------------------------------------

class ProjectGalleryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        kind = request.query_params.get("kind") or Project.KIND.AIOHOUSH
        if kind not in Project.KIND.values:
            return _failure("نوع پروژه معتبر نیست.")

        query = (request.query_params.get("q") or "").strip()[:100]
        technology_id = _int(request.query_params.get("technology"))
        page = max(1, _int(request.query_params.get("page"), 1))

        projects = project_service.search_gallery(
            kind=kind,
            query=query,
            technology_id=technology_id,
        )

        total = projects.count()
        page_count = max(1, -(-total // PAGE_SIZE))
        page = min(page, page_count)
        start = (page - 1) * PAGE_SIZE

        rows = _with_relations(projects.order_by("-created_at", "-id"))[start:start + PAGE_SIZE]

        counts = (
            project_service.visible_projects()
            .aggregate(
                aiohoush=Count("pk", filter=Q(kind=Project.KIND.AIOHOUSH)),
                student=Count("pk", filter=Q(kind=Project.KIND.STUDENT)),
            )
        )

        return _ok(
            "پروژه‌ها دریافت شد.",
            {
                "projects": [_card(request, project) for project in rows],
                "counts": counts,
                "total": total,
                "page": page,
                "pageCount": page_count,
                "technologies": [
                    {"id": item.pk, "title": item.title}
                    for item in project_service.active_technologies()
                ],
            },
        )


class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def _get(self, request, project_id):
        project = (
            _with_relations(Project.objects.filter(pk=project_id))
            .prefetch_related("files")
            .first()
        )
        if project is None or not project_service.can_view(request.user, project):
            return None
        return project

    def get(self, request, project_id):
        project = self._get(request, project_id)
        if project is None:
            return _failure("پروژه پیدا نشد.")
        return _ok("پروژه دریافت شد.", _detail(request, project))

    def patch(self, request, project_id):
        try:
            project_service.update_student_project(
                student=request.user,
                project_id=project_id,
                data=_project_data(request),
            )
        except project_service.ProjectError as exc:
            return _failure(str(exc))

        project = self._get(request, project_id)
        return _ok(
            "تغییرات ذخیره شد و پروژه دوباره برای تأیید ارسال شد.",
            _detail(request, project),
        )

    def delete(self, request, project_id):
        try:
            project_service.delete_student_project(student=request.user, project_id=project_id)
        except project_service.ProjectError as exc:
            return _failure(str(exc))
        return _ok("پروژه حذف شد.")


# --- پروژه‌های من -------------------------------------------------------------

class MyProjectsView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        projects = _with_relations(
            Project.objects.filter(
                owner=request.user,
                kind=Project.KIND.STUDENT,
                is_deleted=False,
            ).order_by("-created_at")
        )

        return _ok(
            "پروژه‌های شما دریافت شد.",
            {
                "projects": [
                    {
                        **_card(request, project),
                        "status": project.status,
                        "statusLabel": project.get_status_display(),
                        "rejectionReason": project.rejection_reason or None,
                        "updatedAt": project.updated_at.isoformat(),
                    }
                    for project in projects
                ],
            },
        )

    def post(self, request):
        try:
            project = project_service.create_student_project(
                student=request.user,
                data=_project_data(request),
                images=request.FILES.getlist("images"),
                files=request.FILES.getlist("files"),
            )
        except project_service.ProjectError as exc:
            return _failure(str(exc))

        return _ok(
            "پروژه ثبت شد و بعد از تأیید نمایش داده می‌شود.",
            {"id": project.pk},
            status.HTTP_201_CREATED,
        )


class ProjectOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return _ok(
            "گزینه‌های پروژه دریافت شد.",
            {
                "technologies": [
                    {"id": item.pk, "title": item.title}
                    for item in project_service.active_technologies()
                ],
                "courses": [
                    {"id": course.pk, "title": course.title}
                    for course in project_service.purchased_courses(request.user)
                ],
            },
        )


class ProjectImageView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, project_id):
        image = request.FILES.get("image")
        if image is None:
            return _failure("عکسی انتخاب نشده است.")

        try:
            created = project_service.add_image(
                student=request.user, project_id=project_id, image=image,
            )
        except project_service.ProjectError as exc:
            return _failure(str(exc))

        return _ok(
            "عکس اضافه شد.",
            {"id": created.pk, "url": _image_url(request, created)},
            status.HTTP_201_CREATED,
        )

    def delete(self, request, project_id, image_id):
        try:
            project_service.remove_image(
                student=request.user, project_id=project_id, image_id=image_id,
            )
        except project_service.ProjectError as exc:
            return _failure(str(exc))
        return _ok("عکس حذف شد.")


class ProjectFileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, project_id):
        file = request.FILES.get("file")
        if file is None:
            return _failure("فایلی انتخاب نشده است.")

        try:
            created = project_service.add_file(
                student=request.user, project_id=project_id, file=file,
            )
        except project_service.ProjectError as exc:
            return _failure(str(exc))

        return _ok("فایل اضافه شد.", _file_row(created), status.HTTP_201_CREATED)

    def delete(self, request, project_id, file_id):
        try:
            project_service.remove_file(
                student=request.user, project_id=project_id, file_id=file_id,
            )
        except project_service.ProjectError as exc:
            return _failure(str(exc))
        return _ok("فایل حذف شد.")


def file_response(item: ProjectFile):
    try:
        handle = item.file.open("rb")
    except FileNotFoundError:
        raise Http404("فایل روی سرور پیدا نشد.")

    return FileResponse(handle, as_attachment=True, filename=item.original_name)


class ProjectFileDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        item = (
            ProjectFile.objects
            .select_related("project__course")
            .filter(pk=file_id)
            .first()
        )

        if item is None or not project_service.can_download_files(request.user, item.project):
            return _failure("فایل پیدا نشد.")

        return file_response(item)
