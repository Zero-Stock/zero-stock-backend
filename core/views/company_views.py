from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from ..models import ClientCompany
from ..serializers import CompanySerializer

class CompanyListView(generics.ListAPIView):
    serializer_class = CompanySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get_queryset(self):
        # 你现在的结构：一个用户只有一个 company
        return ClientCompany.objects.filter(id=1)
