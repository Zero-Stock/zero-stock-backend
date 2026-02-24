# operations/serializers.py
from rest_framework import serializers
from .models import ClientCompanyRegion, DailyCensus

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

class DailyCensusSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)
    diet_category_name = serializers.CharField(source="diet_category.name", read_only=True)

    class Meta:
        model = DailyCensus
        fields = [
            "id",
            "company",
            "date",
            "region",
            "region_name",
            "diet_category",
            "diet_category_name",
            "count",
        ]
        read_only_fields = ["id", "company"]


class DailyCensusBatchItemSerializer(serializers.Serializer):
    region_id = serializers.IntegerField()
    diet_category_id = serializers.IntegerField()
    count = serializers.IntegerField(min_value=0)


class DailyCensusBatchSerializer(serializers.Serializer):
    date = serializers.DateField()
    # 如果你们用户能从 token 推出 company，就不需要前端传 company_id
    company_id = serializers.IntegerField(required=False)
    items = DailyCensusBatchItemSerializer(many=True)

    def validate_items(self, items):
        # 避免同一个 (region_id, diet_category_id) 在同一批里重复
        seen = set()
        for it in items:
            key = (it["region_id"], it["diet_category_id"])
            if key in seen:
                raise serializers.ValidationError(
                    "Duplicate (region_id, diet_category_id) found in items."
                )
            seen.add(key)
        return items