import os
import time
import zipfile
import io
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.models import ActivityLog
from .models import Document
from .serializers import DocumentSerializer
from .generators import DocumentGenerator
from .generation.config import get_template_definition, public_template_catalog


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params

        if user.role in settings.SUPER_ROLES:
            qs = Document.objects.all()
            restaurant_id = params.get('restaurant_id')
            if restaurant_id:
                qs = qs.filter(restaurant_id=restaurant_id)
        else:
            qs = Document.objects.filter(restaurant_id=user.restaurant_id)

        doc_type = params.get('type')
        if doc_type:
            qs = qs.filter(document_type=doc_type)

        search = params.get('search')
        if search:
            qs = qs.filter(title__icontains=search)

        # 'worker' is on the sso DB — select_related would attempt a cross-DB JOIN.
        # Use prefetch_related instead: it issues a separate batched query that
        # the SSORouter correctly routes to the sso connection.
        return (
            qs.select_related('restaurant', 'created_by', 'employee')
              .prefetch_related('worker')
              .order_by('-created_at')
        )

    def perform_create(self, serializer):
        user = self.request.user
        uploaded_file = self.request.FILES.get('file')

        filename = ''
        file_path = ''
        file_size = None
        file_ext = ''

        if uploaded_file:
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            filename = f"doc_{user.id}_{int(time.time())}{ext}"
            upload_dir = settings.MEDIA_ROOT / 'documents'
            upload_dir.mkdir(parents=True, exist_ok=True)
            full_path = upload_dir / filename
            with open(full_path, 'wb+') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
            file_path = str(full_path)
            file_size = uploaded_file.size
            file_ext = ext

        doc = serializer.save(
            created_by=user,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_extension=file_ext,
            status='uploaded' if uploaded_file else 'draft',
        )
        ActivityLog.log('document_created', f'Documento "{doc.title}" criado', user, restaurant=doc.restaurant)

    def perform_destroy(self, instance):
        """Remove também o ficheiro local, mas apenas dentro da pasta MEDIA_ROOT."""
        file_path = None
        if instance.file_path:
            candidate = Path(instance.file_path).resolve()
            media_root = Path(settings.MEDIA_ROOT).resolve()
            try:
                candidate.relative_to(media_root)
            except ValueError:
                pass
            else:
                file_path = candidate

        document_id = instance.pk
        title = instance.title
        restaurant = instance.restaurant

        if file_path and file_path.is_file():
            file_path.unlink()

        instance.delete()

        ActivityLog.log(
            'delete',
            f'Documento "{title}" eliminado',
            self.request.user,
            restaurant=restaurant,
            target_id=document_id,
            target_type='document',
        )

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        doc = self.get_object()
        if not doc.file_path or not Path(doc.file_path).exists():
            return Response({'error': 'Ficheiro não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(open(doc.file_path, 'rb'), as_attachment=True, filename=doc.filename)

    @action(detail=False, methods=['get'], url_path='bulk-download')
    def bulk_download(self, request):
        ids = request.query_params.getlist('ids')
        docs = self.get_queryset().filter(id__in=ids)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for doc in docs:
                if doc.file_path and Path(doc.file_path).exists():
                    zf.write(doc.file_path, doc.filename)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="documentos.zip"'
        return response

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        data = request.data
        template = data.get('template')
        if get_template_definition(template) is None:
            return Response({'error': 'O modelo selecionado não existe.'}, status=status.HTTP_400_BAD_REQUEST)

        generator = DocumentGenerator()
        result = generator.generate(template, data, request.user)
        if 'error' in result:
            user_error_codes = {
                'invalid_template',
                'person_required',
                'person_not_found',
                'restaurant_required',
                'template_file_missing',
                'photo_unavailable',
            }
            response_status = (
                status.HTTP_422_UNPROCESSABLE_ENTITY
                if result.get('code') in user_error_codes
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            return Response(result, status=response_status)
        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='templates')
    def templates(self, request):
        """Catálogo central dos modelos disponíveis na interface."""
        return Response({
            'idioma': 'pt-PT',
            'modelos': public_template_catalog(),
        })

    @action(detail=False, methods=['get'], url_path='photo-status')
    def photo_status(self, request):
        """Informa se a fotografia selecionada existe no ambiente local."""
        data = {
            'employee_id': request.query_params.get('employee_id'),
            'worker_id': request.query_params.get('worker_id'),
        }
        result = DocumentGenerator().photo_status(data)
        if result.get('error'):
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        return Response(result)

    @action(detail=True, methods=['get'], url_path='view')
    def view_file(self, request, pk=None):
        doc = self.get_object()
        if not doc.file_path or not Path(doc.file_path).exists():
            return Response({'error': 'Ficheiro não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        content_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
        }
        ct = content_types.get(doc.file_extension, 'application/octet-stream')
        return FileResponse(open(doc.file_path, 'rb'), content_type=ct)
