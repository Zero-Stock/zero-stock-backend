"""
BaseSearchView — 通用搜索基类
所有 POST /search/ 接口继承此类，只需实现 get_queryset(filters) 定义筛选逻辑。

统一功能：
- ordering: 白名单校验的排序
- page / page_size: 分页（默认 page=1, page_size=20, 最大 100）

统一响应格式：
{
    "total": 42,
    "page": 1,
    "page_size": 20,
    "results": [...]
}
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class BaseSearchView(APIView):
    """
    通用搜索基类。子类需设置：
    - serializer_class: 序列化器
    - allowed_ordering: list[str]，允许排序的字段名
    - default_ordering: str，默认排序字段

    子类需实现：
    - get_base_queryset(): 返回基础 queryset（不含筛选）
    - apply_filters(queryset, filters): 根据 filters dict 应用筛选条件
    """
    serializer_class = None
    allowed_ordering = []
    default_ordering = 'id'

    def get_base_queryset(self):
        raise NotImplementedError

    def apply_filters(self, queryset, filters):
        raise NotImplementedError

    def post(self, request):
        filters = request.data or {}

        # 1) 筛选
        qs = self.get_base_queryset()
        qs = self.apply_filters(qs, filters)

        # 2) 排序
        ordering = filters.get('ordering', self.default_ordering)
        field = ordering.lstrip('-')
        if field in self.allowed_ordering:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by(self.default_ordering)

        # 3) 分页
        total = qs.count()
        page = max(int(filters.get('page', 1)), 1)
        page_size = min(max(int(filters.get('page_size', 20)), 1), 100)
        start = (page - 1) * page_size
        qs = qs[start:start + page_size]

        # 4) 序列化
        serializer = self.serializer_class(qs, many=True)

        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'results': serializer.data,
        })
