# operations/views/__init__.py
from .region_views import CompanyRegionListCreateView
from .census_views import (
    DailyCensusListView,
    DailyCensusBatchView,
    DailyCensusSummaryView,
)
from .procurement_views import (
    ProcurementListView,
    ProcurementDetailView,
    ProcurementItemsView,
    ProcurementSubmitView,
    ProcurementGenerateView,
    ProcurementSheetView,
    ProcurementTemplateView,
    ProcurementAssignSuppliersView,
)
from .receiving_views import (
    ReceivingTemplateView,
    ReceivingCreateView,
    ReceivingDetailView,
)
from .processing_views import (
    ProcessingGenerateView,
    ProcessingSearchView,
)
from .cooking_views import (
    CookingTodayView,
    CookingRecipeView,
)
from .delivery_views import (
    DeliveryGenerateView,
    DeliveryDetailView,
    DeliveryByRegionView,
    DeliveryExportView,
)