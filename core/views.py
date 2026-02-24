# Create your views here.
# Company Views:
# core/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import ClientCompany
from .serializers import CompanySerializer

class CompanyListView(generics.ListAPIView):
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 你现在的结构：一个用户只有一个 company
        return ClientCompany.objects.filter(id=self.request.user.profile.company_id)