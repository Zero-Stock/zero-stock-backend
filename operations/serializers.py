# operations/serializers.py
from rest_framework import serializers
from .models import ClientCompanyRegion

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientCompanyRegion
        fields = ["id", "name", "company"]
        read_only_fields = ["id", "company"]
    def validate(self, attrs):
        """
        Prevent duplicate region name under the same company.
        """
        company_id = self.context.get("company_id")
        name = attrs.get("name")

        if company_id and name:
            exists = ClientCompanyRegion.objects.filter(company_id=company_id, name=name).exists()
            if exists:
                raise serializers.ValidationError({"name": "This region already exists in this company."})

        return attrs