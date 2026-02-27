# operations/migrations/0003_processingitem_nullable_processed_material.py
"""
Make ProcessingItem.processed_material nullable to support
ingredients that have no processing method.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0002_procurementitem_am_quantity_and_more'),
        ('core', '0002_dishingredient_raw_material_processing'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processingitem',
            name='processed_material',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='core.processedmaterial',
            ),
        ),
    ]
