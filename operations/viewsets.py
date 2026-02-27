"""
Operations app 的视图集
处理周菜单配置等运营相关的 API 请求
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import WeeklyMenu
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
        
        # 支持按公司筛选
        company = self.request.query_params.get('company', None)
        if company:
            queryset = queryset.filter(company=company)
        
        # 支持按餐食类型筛选
        diet_category = self.request.query_params.get('diet_category', None)
        if diet_category:
            queryset = queryset.filter(diet_category=diet_category)
        
        # 支持按星期筛选
        day_of_week = self.request.query_params.get('day_of_week', None)
        if day_of_week:
            queryset = queryset.filter(day_of_week=day_of_week)
        
        # 支持按用餐时间筛选
        meal_time = self.request.query_params.get('meal_time', None)
        if meal_time:
            queryset = queryset.filter(meal_time=meal_time)
        
        return queryset
    
    @action(detail=False, methods=['post'], url_path='batch')
    def batch_create(self, request):
        """
        批量创建或更新周菜单
        
        POST /api/weekly-menus/batch/
        请求体:
        {
            "menus": [
                {
                    "company": 1,
                    "diet_category": 1,
                    "day_of_week": 1,
                    "meal_time": "L",
                    "dishes": [1, 2, 3]
                },
                {
                    "company": 1,
                    "diet_category": 1,
                    "day_of_week": 2,
                    "meal_time": "L",
                    "dishes": [4, 5, 6]
                }
            ]
        }
        
        说明：
        - 如果指定的 company + diet_category + day_of_week + meal_time 组合已存在，
          则更新该配置的菜品列表
        - 如果不存在，则创建新的菜单配置
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
