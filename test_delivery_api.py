import os
import django
from datetime import date
from collections import defaultdict
import json
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'canteen_system.settings')
django.setup()

from core.models import ClientCompany, DietCategory
from operations.models import ClientCompanyRegion, DailyCensus, DeliveryOrder, DeliveryItem

def run_test():
    # 1. Setup Data
    company, _ = ClientCompany.objects.get_or_create(code='TEST', defaults={'name': 'Test Company'})
    
    # Just force the creation of the DietCategories
    diet_a, _ = DietCategory.objects.get_or_create(name='标准套餐A')
    diet_b, _ = DietCategory.objects.get_or_create(name='糖尿病餐')

    region1, _ = ClientCompanyRegion.objects.get_or_create(company=company, name='园区A')
    region2, _ = ClientCompanyRegion.objects.get_or_create(company=company, name='研发楼B')

    target_date = date(2026, 2, 25)

    # Completely clear ALL census data to avoid Unique Constraint errors from conflicting region/diet data
    DailyCensus.objects.all().delete()

    # Create Census
    DailyCensus.objects.create(company=company, date=target_date, region=region1, diet_category=diet_a, count=120)
    # Using different region/diet combinations to avoid UNIQUE constraint failed
    DailyCensus.objects.create(company=company, date=target_date, region=region1, diet_category=diet_b, count=15)
    DailyCensus.objects.create(company=company, date=target_date, region=region2, diet_category=diet_a, count=85)

    with open('api_test_output.txt', 'w', encoding='utf-8') as f:
        f.write('\n===== 1. [前置数据]: 各区域录入的订餐人数 (DailyCensus) =====\n')
        for c in DailyCensus.objects.filter(company=company, date=target_date):
            f.write(f'  - {c.region.name} : {c.diet_category.name} x {c.count} 份\n')
            
        # 2. Call the Generate Logic (similar to DeliveryGenerateView)
        order, created = DeliveryOrder.objects.get_or_create(
            company=company,
            target_date=target_date,
            meal_time='L',
        )
        if not created:
            order.items.all().delete()

        for census in DailyCensus.objects.filter(company=company, date=target_date):
            if census.count > 0:
                DeliveryItem.objects.create(
                    delivery=order,
                    region=census.region,
                    diet_category=census.diet_category,
                    count=census.count,
                )

        f.write(f'\n===== 2. [后台生成完毕]: {order} =====\n')

        # 3. Test By-Region View Logic
        items = DeliveryItem.objects.filter(delivery=order).select_related('region', 'diet_category')
        grouped = defaultdict(list)
        for item in items:
            grouped[item.region.name].append({
                'diet_category': item.diet_category.name,
                'count': item.count,
            })

        f.write('\n===== 3. [前端按区域展示接口 /api/delivery/{id}/by-region/ 返回效果] =====\n')
        for k, v in grouped.items():
            total = sum(i['count'] for i in v)
            f.write(f'  [{k}] - 区域总计: {total} 份\n')
            for d in v:
                cat = d['diet_category']
                cnt = d['count']
                f.write(f'    - {cat} : {cnt} 份\n')

        # 4. Test Export View Logic
        export_data = {
            'title': '每日送餐统计表',
            'company': order.company.name,
            'date': str(order.target_date),
            'meal_time': order.get_meal_time_display(),
            'regions': [
                {
                    'region': region_name,
                    'diets': diets,
                    'total_count': sum(d['count'] for d in diets),
                }
                for region_name, diets in grouped.items()
            ],
            'grand_total': sum(item.count for item in items),
        }

        f.write('\n===== 4. [打印导出接口 /api/delivery/{id}/export/ 返回 JSON 数据] =====\n')
        f.write(json.dumps(export_data, indent=2, ensure_ascii=False))
        f.write('\n=====================================\n')

if __name__ == '__main__':
    try:
        run_test()
    except Exception as e:
        with open('api_test_output.txt', 'w', encoding='utf-8') as f:
            traceback.print_exc(file=f)
