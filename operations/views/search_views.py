# operations/views/search_views.py
"""
POST /search/ endpoints for operations models.
Each view inherits BaseSearchView and defines its own filter fields.
"""
from common.views import BaseSearchView
from operations.models import WeeklyMenu, DailyCensus, ProcurementRequest
from operations.serializers import (
    WeeklyMenuSerializer, DailyCensusSerializer, ProcurementRequestSerializer,
)


class WeeklyMenuSearchView(BaseSearchView):
    """
    POST /api/weekly-menus/search/
    筛选: company(ID), diet_category(ID), day_of_week(1-7), meal_time(B/L/D)
    排序: day_of_week, meal_time
    """
    serializer_class = WeeklyMenuSerializer
    allowed_ordering = ['day_of_week', 'meal_time']
    default_ordering = 'day_of_week'

    def get_base_queryset(self):
        return WeeklyMenu.objects.select_related(
            'company', 'diet_category'
        ).prefetch_related('dishes')

    def apply_filters(self, qs, filters):
        if filters.get('company'):
            qs = qs.filter(company_id=filters['company'])
        if filters.get('diet_category'):
            qs = qs.filter(diet_category_id=filters['diet_category'])
        if filters.get('day_of_week'):
            qs = qs.filter(day_of_week=filters['day_of_week'])
        if filters.get('meal_time'):
            qs = qs.filter(meal_time=filters['meal_time'])
        return qs


class CensusSearchView(BaseSearchView):
    """
    POST /api/census/search/
    筛选: date(精确), start(>=), end(<=), region_id(ID), diet_category_id(ID)
    排序: date, region_id, diet_category_id
    """
    serializer_class = DailyCensusSerializer
    allowed_ordering = ['date', 'region_id', 'diet_category_id']
    default_ordering = 'date'
    permission_classes = []  # Will use IsAuthenticated from parent

    def get_base_queryset(self):
        company_id = self.request.user.profile.company_id
        return DailyCensus.objects.filter(company_id=company_id)

    def apply_filters(self, qs, filters):
        if filters.get('date'):
            qs = qs.filter(date=filters['date'])
        else:
            if filters.get('start'):
                qs = qs.filter(date__gte=filters['start'])
            if filters.get('end'):
                qs = qs.filter(date__lte=filters['end'])
        if filters.get('region_id'):
            qs = qs.filter(region_id=filters['region_id'])
        if filters.get('diet_category_id'):
            qs = qs.filter(diet_category_id=filters['diet_category_id'])
        return qs


class ProcurementSearchView(BaseSearchView):
    """
    POST /api/procurement/search/
    筛选: status(精确), date(精确), start(>=), end(<=)
    排序: target_date, id
    """
    serializer_class = ProcurementRequestSerializer
    allowed_ordering = ['target_date', 'id']
    default_ordering = '-target_date'
    permission_classes = []

    def get_base_queryset(self):
        company_id = self.request.user.profile.company_id
        return ProcurementRequest.objects.filter(company_id=company_id)

    def apply_filters(self, qs, filters):
        if filters.get('status'):
            qs = qs.filter(status=filters['status'])
        if filters.get('date'):
            qs = qs.filter(target_date=filters['date'])
        else:
            if filters.get('start'):
                qs = qs.filter(target_date__gte=filters['start'])
            if filters.get('end'):
                qs = qs.filter(target_date__lte=filters['end'])
        return qs
