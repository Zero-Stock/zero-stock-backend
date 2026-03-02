"""
Operations app 的视图集
处理周菜单配置等运营相关的 API 请求
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import WeeklyMenu, WeeklyMenuDish
from .serializers import WeeklyMenuSerializer, WeeklyMenuBatchSerializer


class WeeklyMenuViewSet(viewsets.ModelViewSet):
    """
    周菜单视图集 - 管理标准化的周菜单循环

    GET /api/weekly-menus/ - 获取周菜单列表（支持按公司和餐食类型筛选）
    POST /api/weekly-menus/ - 创建单个菜单配置
    GET /api/weekly-menus/{id}/ - 获取单个菜单详情
    PUT/PATCH /api/weekly-menus/{id}/ - 更新菜单配置
    DELETE /api/weekly-menus/{id}/ - 删除菜单配置
    POST /api/weekly-menus/batch/ - 批量创建/更新一周的菜单

    dishes 字段支持两种格式：
    - 纯 ID 列表 [1, 2, 3]（向后兼容，quantity=1）
    - 对象列表 [{"dish_id": 1, "quantity": 2}, {"dish_id": 2, "quantity": 3}]
    """
    queryset = WeeklyMenu.objects.select_related(
        'company', 'diet_category'
    ).prefetch_related('dishes').order_by('day_of_week', 'meal_time')

    serializer_class = WeeklyMenuSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['day_of_week', 'meal_time']
    ordering = ['day_of_week', 'meal_time']

    def get_queryset(self):
        """自定义查询集，支持多条件筛选"""
        queryset = super().get_queryset()

        company = self.request.query_params.get('company', None)
        if company:
            queryset = queryset.filter(company=company)

        diet_category = self.request.query_params.get('diet_category', None)
        if diet_category:
            queryset = queryset.filter(diet_category=diet_category)

        day_of_week = self.request.query_params.get('day_of_week', None)
        if day_of_week:
            queryset = queryset.filter(day_of_week=day_of_week)

        meal_time = self.request.query_params.get('meal_time', None)
        if meal_time:
            queryset = queryset.filter(meal_time=meal_time)

        return queryset

    def _set_dishes(self, menu, dishes_data):
        """
        Helper to set dishes on a menu via the through table.
        Supports both plain ID list [1,2,3] and object list [{"dish_id":1,"quantity":2}].
        """
        WeeklyMenuDish.objects.filter(menu=menu).delete()
        if dishes_data is None:
            return
        for d in dishes_data:
            if isinstance(d, dict):
                dish_id = d.get('dish_id') or d.get('id')
                quantity = d.get('quantity', 1)
            else:
                dish_id = int(d)
                quantity = 1
            WeeklyMenuDish.objects.create(
                menu=menu, dish_id=dish_id, quantity=quantity
            )

    def perform_create(self, serializer):
        menu = serializer.save()
        dishes_data = self.request.data.get('dishes')
        if dishes_data:
            self._set_dishes(menu, dishes_data)

    def perform_update(self, serializer):
        menu = serializer.save()
        dishes_data = self.request.data.get('dishes')
        if dishes_data is not None:
            self._set_dishes(menu, dishes_data)

    @action(detail=False, methods=['post'], url_path='batch')
    def batch_create(self, request):
        """
        批量创建或更新周菜单

        POST /api/weekly-menus/batch/
        请求体 (JSON 数组):
        [
            {
                "company": 1, "diet_category": 1,
                "day_of_week": 1, "meal_time": "L",
                "dishes": [1, 2, 3]
            },
            {
                "company": 1, "diet_category": 1,
                "day_of_week": 5, "meal_time": "L",
                "dishes": [{"dish_id": 4, "quantity": 2}, {"dish_id": 5, "quantity": 3}]
            }
        ]

        说明：
        - 如果指定的 company + diet_category + day_of_week + meal_time 组合已存在，
          则更新该配置的菜品列表
        - 如果不存在，则创建新的菜单配置
        - dishes 支持纯ID列表（quantity默认1）和对象列表（可指定quantity）
        """
        serializer = WeeklyMenuBatchSerializer(data={'menus': request.data})

        if serializer.is_valid():
            menus = serializer.save()
            result_serializer = WeeklyMenuSerializer(menus, many=True)
            return Response(
                {
                    'message': f'成功处理 {len(menus)} 条菜单配置',
                    'data': result_serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
