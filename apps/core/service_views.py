"""Endpoints técnicos mantidos para integração com o Portal SSO."""

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsServiceClient


class ServiceEmployeeOfMonthView(APIView):
    """Devolve ao SSO o cartão atual de funcionário do mês."""

    permission_classes = [IsServiceClient]
    authentication_classes = []

    def get(self, request):
        from apps.documents.models import Document

        restaurant_id = request.query_params.get("restaurant_id")
        if not restaurant_id:
            return Response(
                {"detail": "O restaurante é obrigatório."},
                status=400,
            )
        try:
            restaurant_id = int(restaurant_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "O restaurante indicado é inválido."},
                status=400,
            )

        now = timezone.now()
        document = (
            Document.objects.filter(
                document_type="employee_month",
                restaurant_id=restaurant_id,
                created_at__year=now.year,
                created_at__month=now.month,
                status="generated",
            )
            .select_related("employee")
            .order_by("-created_at")
            .first()
        )

        if document is None:
            return Response({"employee_of_month": None})

        person = document.worker or document.employee
        name = (
            getattr(person, "name", None)
            or document.title.split("—")[-1].strip()
        )
        image_url = (
            request.build_absolute_uri(
                f"/media/documents/generated/{document.filename}"
            )
            if document.filename
            else None
        )

        return Response({
            "employee_of_month": {
                "name": name,
                "month": now.strftime("%Y-%m"),
                "restaurant_id": restaurant_id,
                "image_url": image_url,
            }
        })
