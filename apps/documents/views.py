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
        if template not in ['birthday', 'praise', 'certificate', 'welcome', 'employee_month']:
            return Response({'error': 'Template inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        generator = DocumentGenerator()
        result = generator.generate(template, data, request.user)
        if 'error' in result:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(result, status=status.HTTP_201_CREATED)

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
