from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from ..models import DietCategory
from ..serializers import DietCategorySerializer


class DietCategoryListView(generics.ListAPIView):
    """
    GET /api/diet-categories/
    """
    queryset = DietCategory.objects.all().order_by("name")
    serializer_class = DietCategorySerializer
    permission_classes = [IsAuthenticated]