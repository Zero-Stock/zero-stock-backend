# core/migrations/0002_dishingredient_raw_material_processing.py
"""
Multi-step migration to replace DishIngredient.material (FK to ProcessedMaterial)
with raw_material (FK to RawMaterial) + processing (nullable FK to ProcessedMaterial).

Step 1: Add new fields as nullable
Step 2: Copy data from old material FK
Step 3: Remove old field, make raw_material non-nullable
"""
from django.db import migrations, models
import django.db.models.deletion


def populate_raw_material_and_processing(apps, schema_editor):
    """
    For each existing DishIngredient:
      - raw_material = material.raw_material
      - processing = material (the old ProcessedMaterial FK)
    """
    DishIngredient = apps.get_model('core', 'DishIngredient')
    for ing in DishIngredient.objects.select_related('material').all():
        if ing.material_id:
            ing.raw_material_id = ing.material.raw_material_id
            ing.processing_id = ing.material_id
            ing.save(update_fields=['raw_material_id', 'processing_id'])


def reverse_populate(apps, schema_editor):
    """
    Reverse: copy processing back to material.
    """
    DishIngredient = apps.get_model('core', 'DishIngredient')
    for ing in DishIngredient.objects.all():
        if ing.processing_id:
            ing.material_id = ing.processing_id
            ing.save(update_fields=['material_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        # Step 1: Add new fields as nullable
        migrations.AddField(
            model_name='dishingredient',
            name='raw_material',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='core.rawmaterial',
                verbose_name='原料',
            ),
        ),
        migrations.AddField(
            model_name='dishingredient',
            name='processing',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='core.processedmaterial',
                verbose_name='处理方法',
                help_text='可选。若选择了处理方法，系统会自动使用对应的出成率。',
            ),
        ),

        # Step 2: Populate new fields from old material FK
        migrations.RunPython(populate_raw_material_and_processing, reverse_populate),

        # Step 3: Remove old material field
        migrations.RemoveField(
            model_name='dishingredient',
            name='material',
        ),

        # Step 4: Make raw_material non-nullable
        migrations.AlterField(
            model_name='dishingredient',
            name='raw_material',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='core.rawmaterial',
                verbose_name='原料',
            ),
        ),

        # Step 5: Update net_quantity field metadata
        migrations.AlterField(
            model_name='dishingredient',
            name='net_quantity',
            field=models.DecimalField(
                decimal_places=3,
                help_text='每份用量，单位与原料一致（通常为 kg）。',
                max_digits=8,
                verbose_name='重量(每份)',
            ),
        ),
    ]
