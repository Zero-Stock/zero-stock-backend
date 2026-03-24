# operations/views/search_views.py
"""
POST /search/ endpoints for operations models.
Each view inherits BaseSearchView and defines its own filter fields.
"""
from common.views import BaseSearchView
from operations.models import WeeklyMenu, DailyCensus, ProcurementRequest, ReceivingRecord, ProcessingOrder, DeliveryOrder
from operations.serializers import (
    WeeklyMenuSerializer, DailyCensusSerializer, ProcurementRequestSerializer, ReceivingRecordSerializer, ProcessingOrderSerializer, DeliveryOrderSerializer)
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication


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

    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get_base_queryset(self):
        # Hardcoded company_id=1 for local development/integration
        company_id = 1
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

    def post(self, request):
        filters = request.data or {}
        date_param = filters.get('date')
        start_param = filters.get('start')
        end_param = filters.get('end')

        if not (date_param or start_param or end_param):
            return super().post(request)

        import datetime
        from common.views import success_response
        from core.models import DietCategory
        from operations.models import ClientCompanyRegion

        company_id = 1

        # Determine target dates safely
        target_dates = []
        if date_param:
            try:
                dt = datetime.datetime.strptime(date_param, "%Y-%m-%d").date()
                target_dates.append(dt)
            except ValueError:
                return super().post(request)
        else:
            try:
                start_dt = datetime.datetime.strptime(start_param, "%Y-%m-%d").date() if start_param else datetime.date.today() - datetime.timedelta(days=7)
                end_dt = datetime.datetime.strptime(end_param, "%Y-%m-%d").date() if end_param else datetime.date.today() + datetime.timedelta(days=7)
                if (end_dt - start_dt).days > 31: # Cap to 31 days to prevent massive memory loops
                    end_dt = start_dt + datetime.timedelta(days=31)
                
                curr = start_dt
                while curr <= end_dt:
                    target_dates.append(curr)
                    curr += datetime.timedelta(days=1)
            except ValueError:
                return super().post(request)

        qs = self.get_base_queryset()
        qs = self.apply_filters(qs, filters)

        regions_qs = ClientCompanyRegion.objects.filter(company_id=company_id).order_by('id')
        if filters.get('region_id'):
            regions_qs = regions_qs.filter(id=filters['region_id'])

        diets_qs = DietCategory.objects.all().order_by('id')
        if filters.get('diet_category_id'):
            diets_qs = diets_qs.filter(id=filters['diet_category_id'])

        regions = list(regions_qs)
        diets = list(diets_qs)
        
        # Bulk serialize existing records once to prevent O(N) serializer instantiation overhead
        qs_data = self.serializer_class(qs, many=True).data
        existing_records_data = {
            (r['date'], r['region'], r['diet_category']): r
            for r in qs_data
        }

        padded_results = []
        for dt in target_dates:
            dt_str = str(dt)
            for region in regions:
                for diet in diets:
                    key = (dt_str, region.id, diet.id)
                    if key in existing_records_data:
                        padded_results.append(existing_records_data[key])
                    else:
                        padded_results.append({
                            "id": None,
                            "company": company_id,
                            "date": dt_str,
                            "region": region.id,
                            "region_name": region.name,
                            "diet_category": diet.id,
                            "diet_category_name": diet.name,
                            "count": 0
                        })

        # Apply custom sorting
        ordering = filters.get('ordering', self.default_ordering)
        field = ordering.lstrip('-')
        reverse = ordering.startswith('-')
        
        # Map Django ORM field names to serialized JSON dictionary keys
        field_map = {
            'region_id': 'region',
            'diet_category_id': 'diet_category',
            'date': 'date'
        }
        dict_key = field_map.get(field, field)

        if field in self.allowed_ordering:
            padded_results.sort(key=lambda x: x.get(dict_key) if x.get(dict_key) is not None else 0, reverse=reverse)

        # Pagination
        total = len(padded_results)
        page = max(int(filters.get('page', 1)), 1)
        page_size = min(max(int(filters.get('page_size', 20)), 1), 100)
        start_idx = (page - 1) * page_size
        paginated_results = padded_results[start_idx:start_idx + page_size]

        return success_response(
            results={
                'total': total,
                'page': page,
                'page_size': page_size,
                'results': paginated_results,
            }
        )



class ProcurementSearchView(BaseSearchView):
    """
    POST /api/procurement/search/
    筛选: status(精确), date(精确), start(>=), end(<=)
    排序: target_date, id
    """
    serializer_class = ProcurementRequestSerializer
    allowed_ordering = ['target_date', 'id']
    default_ordering = '-target_date'

    def get_base_queryset(self):
        company_id = 1
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

class ReceivingSearchView(BaseSearchView):
    """
    POST /api/receiving/search/
    Filters: status(exact), date(exact), start(>=), end(<=)
    Ordering: received_date, id
    """
    serializer_class = ReceivingRecordSerializer
    allowed_ordering = ['received_date', 'id']
    default_ordering = '-received_date'

    def get_base_queryset(self):
        company_id = 1

        return ReceivingRecord.objects.filter(
            company_id=company_id
        ).select_related('procurement', 'company').prefetch_related('items__raw_material')

    def apply_filters(self, qs, filters):
        if filters.get('status'):
            qs = qs.filter(status=filters['status'])

        if filters.get('date'):
            qs = qs.filter(procurement__target_date=filters['date'])
        else:
            if filters.get('start'):
                qs = qs.filter(procurement__target_date__gte=filters['start'])
            if filters.get('end'):
                qs = qs.filter(procurement__target_date__lte=filters['end'])

        return qs
    
class ProcessingSearchView(BaseSearchView):
    """
    POST /api/processing/search/
    Filters: status(exact), date(exact), start(>=), end(<=)
    Ordering: target_date, id
    """
    serializer_class = ProcessingOrderSerializer
    allowed_ordering = ['target_date', 'id']
    default_ordering = '-target_date'

    def get_base_queryset(self):
        company_id = 1

        return ProcessingOrder.objects.filter(
            company_id=company_id
        ).select_related('company').prefetch_related(
            'items__raw_material', 'items__processed_material', 'items__dish'
        )

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
    
class DeliverySearchView(BaseSearchView):
    """
    POST /api/delivery/search/
    Filters: meal_time(exact), date(exact), start(>=), end(<=)
    Ordering: target_date, meal_time, id
    """
    serializer_class = DeliveryOrderSerializer
    allowed_ordering = ['target_date', 'meal_time', 'id']
    default_ordering = '-target_date'

    def get_base_queryset(self):
        company_id = 1

        return DeliveryOrder.objects.filter(
            company_id=company_id
        ).select_related('company').prefetch_related('items__region', 'items__diet_category')

    def apply_filters(self, qs, filters):
        if filters.get('meal_time'):
            qs = qs.filter(meal_time=filters['meal_time'])

        if filters.get('date'):
            qs = qs.filter(target_date=filters['date'])
        else:
            if filters.get('start'):
                qs = qs.filter(target_date__gte=filters['start'])
            if filters.get('end'):
                qs = qs.filter(target_date__lte=filters['end'])

        return qs