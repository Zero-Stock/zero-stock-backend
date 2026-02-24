# core/serializers.py
from rest_framework import serializers
from .models import ClientCompany, DietCategory

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientCompany
        fields = ["id", "name", "code"]

class DietCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DietCategory
        fields = ["id", "name"]