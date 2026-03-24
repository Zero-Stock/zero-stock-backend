from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny

from ..models import DietCategory
from ..serializers import DietCategorySerializer


class DietCategoryListView(generics.ListAPIView):
    """
    GET /api/diet-categories/
    """
    queryset = DietCategory.objects.all().order_by("name")
    serializer_class = DietCategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]