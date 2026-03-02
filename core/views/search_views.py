# core/views/search_views.py
"""
POST /search/ endpoints for core models.
Each view inherits BaseSearchView and defines its own filter fields.
"""
from common.views import BaseSearchView
from core.models import RawMaterial, Dish, Supplier, DietCategory
from core.serializers import (
    RawMaterialSerializer, DishSerializer,
    SupplierSerializer, DietCategorySerializer,
)


class MaterialSearchView(BaseSearchView):
    """
    POST /api/materials/search/
    筛选: name(模糊), category(ID)
    排序: id, name, category__name
    """
    serializer_class = RawMaterialSerializer
    allowed_ordering = ['id', 'name', 'category__name']
    default_ordering = 'name'

    def get_base_queryset(self):
        return RawMaterial.objects.prefetch_related('specs')

    def apply_filters(self, qs, filters):
        if filters.get('name'):
            qs = qs.filter(name__icontains=filters['name'])
        if filters.get('category'):
            qs = qs.filter(category_id=filters['category'])
        return qs


class DishSearchView(BaseSearchView):
    """
    POST /api/dishes/search/
    筛选: name(模糊)
    排序: id, name
    """
    serializer_class = DishSerializer
    allowed_ordering = ['id', 'name']
    default_ordering = 'name'

    def get_base_queryset(self):
        return Dish.objects.prefetch_related(
            'allowed_diets', 'ingredients__raw_material', 'ingredients__processing'
        )

    def apply_filters(self, qs, filters):
        if filters.get('name'):
            qs = qs.filter(name__icontains=filters['name'])
        return qs


class SupplierSearchView(BaseSearchView):
    """
    POST /api/suppliers/search/
    筛选: name(模糊)
    排序: id, name
    """
    serializer_class = SupplierSerializer
    allowed_ordering = ['id', 'name']
    default_ordering = 'name'

    def get_base_queryset(self):
        return Supplier.objects.prefetch_related('materials__raw_material')

    def apply_filters(self, qs, filters):
        if filters.get('name'):
            qs = qs.filter(name__icontains=filters['name'])
        return qs


class DietSearchView(BaseSearchView):
    """
    POST /api/diets/search/
    筛选: name(模糊)
    排序: id, name
    """
    serializer_class = DietCategorySerializer
    allowed_ordering = ['id', 'name']
    default_ordering = 'name'

    def get_base_queryset(self):
        return DietCategory.objects.all()

    def apply_filters(self, qs, filters):
        if filters.get('name'):
            qs = qs.filter(name__icontains=filters['name'])
        return qs
