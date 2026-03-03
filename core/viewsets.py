"""
ViewSets for handling API business logic and HTTP request/response.
"""
from rest_framework import viewsets, status, filters, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError

from common.views import success_response, error_response
from .models import (
    DietCategory, RawMaterial, ProcessedMaterial,
    Dish, Supplier, SupplierMaterial, MaterialCategory
)
from .serializers import (
    DietCategorySerializer, RawMaterialSerializer,
    ProcessedMaterialSerializer, DishSerializer, DishPrintSerializer,
    DietDishesSerializer, SupplierSerializer, SupplierMaterialSerializer,
    MaterialCategorySerializer
)


class DietCategoryViewSet(viewsets.ModelViewSet):
    """
    Diet category ViewSet - full CRUD + dishes sub-resource

    GET /api/diets/ - List all diet categories
    POST /api/diets/ - Create a diet category
    PUT/PATCH /api/diets/{id}/ - Update a diet category
    GET /api/diets/{id}/dishes/ - Get dishes assigned to this diet
    POST /api/diets/{id}/dishes/ - Batch-assign dishes to this diet
    """
    queryset = DietCategory.objects.all()
    serializer_class = DietCategorySerializer
    pagination_class = None

    @action(detail=True, methods=['get', 'post'], url_path='dishes')
    def dishes(self, request, pk=None):
        diet = self.get_object()
        if request.method == 'GET':
            dishes = Dish.objects.filter(allowed_diets=diet)
            serializer = DishSerializer(dishes, many=True)
            return success_response(results=serializer.data)
        else:
            serializer = DietDishesSerializer(data=request.data)
            if serializer.is_valid():
                dish_ids = serializer.validated_data['dish_ids']
                dishes = Dish.objects.filter(id__in=dish_ids)
                for dish in dishes:
                    dish.allowed_diets.add(diet)
                result = DishSerializer(dishes, many=True)
                return success_response(results=result.data, message="Dishes assigned")
            return error_response(error=serializer.errors, message="Validation failed")


class MaterialCategoryViewSet(viewsets.ModelViewSet):
    """
    原料分类 CRUD

    GET /api/material-categories/ - 获取所有分类
    POST /api/material-categories/ - 创建分类
    PUT/PATCH /api/material-categories/{id}/ - 更新分类
    DELETE /api/material-categories/{id}/ - 删除分类
    """
    queryset = MaterialCategory.objects.all().order_by('name')
    serializer_class = MaterialCategorySerializer
    pagination_class = None


class RawMaterialViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    """
    食材视图集
    
    GET /api/materials/ - 获取食材列表（支持搜索、排序、筛选、分组）
    GET /api/materials/{id}/ - 获取单个食材详情（含加工规格）
    DELETE /api/materials/{id}/ - 删除食材
    POST /api/materials/batch/ - 批量添加/修改（有id更新，无id新建）
    POST /api/materials/{id}/specs/ - 为食材添加加工规格
    """
    queryset = RawMaterial.objects.prefetch_related('specs')
    serializer_class = RawMaterialSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['id', 'name', 'category__name']
    ordering = ['name']
    
    def get_queryset(self):
        """自定义查询集，支持按类别筛选"""
        queryset = super().get_queryset()
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category_id=category)
        return queryset

    def list(self, request, *args, **kwargs):
        """
        获取食材列表，支持 group_by 参数

        GET /api/materials/?group_by=category  → 按分类分组返回
        GET /api/materials/?group_by=unit      → 按单位分组返回
        GET /api/materials/?ordering=category   → 按分类排序
        GET /api/materials/?ordering=-name      → 按名称倒序
        """
        group_by = request.query_params.get('group_by', None)

        if group_by and group_by in ('category', 'unit'):
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)

            # 按指定字段分组
            grouped = {}
            for item in serializer.data:
                key = item.get(group_by, '未分类')
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(item)

            return success_response(results=grouped)

        return super().list(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], url_path='specs')
    def add_spec(self, request, pk=None):
        """
        为指定食材添加加工规格

        POST /api/materials/{id}/specs/
        请求体:
        {
            "method_name": "去皮切块",
            "yield_rate": "0.80"
        }
        """
        material = self.get_object()
        serializer = ProcessedMaterialSerializer(data=request.data)

        if serializer.is_valid():
            # 检查是否已存在相同的加工方法
            if ProcessedMaterial.objects.filter(
                raw_material=material,
                method_name=serializer.validated_data['method_name']
            ).exists():
                return error_response(
                    error='该加工方法已存在',
                    message='该加工方法已存在',
                )

            serializer.save(raw_material=material)
            return success_response(
                results=serializer.data,
                message='Spec created',
                http_status=status.HTTP_201_CREATED,
            )

        return error_response(error=serializer.errors, message='Validation failed')

    @action(detail=False, methods=['post'], url_path='batch')
    def batch_save(self, request):
        """
        POST /api/materials/batch/
        Body: JSON array

        Atomic: if any item fails validation the entire batch is rejected.

        Rules:
        - If id provided -> update by id
        - Else if name matches existing -> update that record
        - Else -> create new
        """
        if not isinstance(request.data, list):
            return error_response(
                error="Request body must be a JSON array.",
                message="Request body must be a JSON array.",
            )

        # ---- Phase 1: validate all items (no DB writes) ----
        plans = []   # list of (action, serializer, index)
        errors = []

        for index, item in enumerate(request.data):
            if not isinstance(item, dict):
                errors.append({"index": index, "detail": "Each item must be an object."})
                continue

            item_id = item.get("id")
            name = (item.get("name") or "").strip()

            # 1) update by id
            if item_id:
                material = RawMaterial.objects.filter(id=item_id).first()
                if not material:
                    errors.append({"index": index, "id": item_id, "detail": "Material not found."})
                    continue
                serializer = RawMaterialSerializer(material, data=item, partial=True)
                if not serializer.is_valid():
                    errors.append({"index": index, "id": item_id, "detail": serializer.errors})
                    continue
                plans.append(("updated", serializer, index))
                continue

            # 2) update by name
            if name:
                material = RawMaterial.objects.filter(name=name).first()
                if material:
                    serializer = RawMaterialSerializer(material, data=item, partial=True)
                    if not serializer.is_valid():
                        errors.append({"index": index, "name": name, "detail": serializer.errors})
                        continue
                    plans.append(("updated", serializer, index))
                    continue

            # 3) create new
            serializer = RawMaterialSerializer(data=item)
            if not serializer.is_valid():
                errors.append({"index": index, "detail": serializer.errors})
                continue
            plans.append(("created", serializer, index))

        # If any errors, reject entire batch
        if errors:
            return error_response(
                error=errors,
                message=f"Validation failed for {len(errors)} item(s), no changes applied.",
            )

        # ---- Phase 2: execute inside transaction ----
        created, updated = [], []
        with transaction.atomic():
            for action_type, serializer, index in plans:
                serializer.save()
                if action_type == "created":
                    created.append(serializer.data)
                else:
                    updated.append(serializer.data)

        return success_response(
            results={"created": created, "updated": updated},
            message=f"Created {len(created)}, Updated {len(updated)}",
        )


class DishViewSet(viewsets.ModelViewSet):
    """
    Dish ViewSet - full CRUD with nested recipe ingredients

    GET /api/dishes/ - List dishes (searchable by name)
    POST /api/dishes/ - Create dish with recipe
    GET /api/dishes/{id}/ - Get dish detail with full recipe
    PUT/PATCH /api/dishes/{id}/ - Update dish and recipe
    DELETE /api/dishes/{id}/ - Delete dish
    """
    queryset = Dish.objects.prefetch_related('allowed_diets', 'ingredients__raw_material', 'ingredients__processing')
    serializer_class = DishSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']

    @action(detail=False, methods=['get'], url_path='print')
    def print_all(self, request):
        """
        GET /api/dishes/print/
        Returns all dishes in print-friendly format:
        name, ingredients (formatted), seasonings, cooking_method
        """
        dishes = Dish.objects.prefetch_related(
            'ingredients__raw_material', 'ingredients__processing'
        ).all().order_by('name')
        serializer = DishPrintSerializer(dishes, many=True)
        return success_response(results=serializer.data)


class SupplierViewSet(viewsets.ModelViewSet):
    """
    Supplier ViewSet - full CRUD with materials sub-resource

    GET /api/suppliers/ - List suppliers
    POST /api/suppliers/ - Create supplier
    PUT/PATCH /api/suppliers/{id}/ - Update supplier
    GET /api/suppliers/{id}/materials/ - List materials this supplier provides
    POST /api/suppliers/{id}/materials/ - Add a material to this supplier
    """
    queryset = Supplier.objects.prefetch_related('materials__raw_material')
    serializer_class = SupplierSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

class SupplierMaterialViewSet(viewsets.ModelViewSet):
    """
    SupplierMaterial CRUD

    GET  /api/supplier-materials/?supplier=1&search=tomato&ordering=-price
    POST /api/supplier-materials/
    PATCH/PUT/DELETE /api/supplier-materials/{id}/
    """
    queryset = SupplierMaterial.objects.select_related("supplier", "raw_material")
    serializer_class = SupplierMaterialSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["supplier__name", "raw_material__name"]
    ordering_fields = ["id", "supplier__name", "raw_material__name", "unit_name", "kg_per_unit", "price"]
    ordering = ["supplier__name", "raw_material__name"]

    def get_queryset(self):
        qs = super().get_queryset()
        supplier_id = self.request.query_params.get("supplier")
        raw_material_id = self.request.query_params.get("raw_material")

        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        if raw_material_id:
            qs = qs.filter(raw_material_id=raw_material_id)

        return qs

    def create(self, request, *args, **kwargs):
        """
        Handle unique_together (supplier, raw_material) nicely.
        """
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            raise ValidationError({"detail": "This supplier already has this raw material."})

