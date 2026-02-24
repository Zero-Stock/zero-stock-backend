# core/serializers.py
from rest_framework import serializers
from .models import ClientCompany

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientCompany
        fields = ["id", "name", "code"]