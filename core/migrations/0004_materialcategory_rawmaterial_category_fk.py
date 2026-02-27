# core/migrations/0004_materialcategory_rawmaterial_category_fk.py
"""
Convert RawMaterial.category from CharField to FK to MaterialCategory.

Steps:
1. Create MaterialCategory table
2. Add new FK field (category_fk) as nullable
3. Create initial categories from existing data + populate FK
4. Remove old CharField, rename FK
"""
from django.db import migrations, models
import django.db.models.deletion


def convert_category_to_fk(apps, schema_editor):
    """Create MaterialCategory records and populate FK."""
    MaterialCategory = apps.get_model('core', 'MaterialCategory')
    RawMaterial = apps.get_model('core', 'RawMaterial')

    # Get unique category names from existing data
    category_names = set(RawMaterial.objects.values_list('category_old', flat=True).distinct())

    # Ensure at least 鲜品 and 冻品 exist
    category_names.add('鲜品')
    category_names.add('冻品')
    category_names.discard('')
    category_names.discard(None)

    # Create MaterialCategory records
    cat_map = {}
    for name in category_names:
        cat, _ = MaterialCategory.objects.get_or_create(name=name)
        cat_map[name] = cat

    # Populate FK
    for mat in RawMaterial.objects.all():
        old_val = mat.category_old or '鲜品'
        mat.category = cat_map.get(old_val, cat_map['鲜品'])
        mat.save(update_fields=['category_id'])


def reverse_convert(apps, schema_editor):
    RawMaterial = apps.get_model('core', 'RawMaterial')
    for mat in RawMaterial.objects.select_related('category').all():
        mat.category_old = mat.category.name if mat.category else '鲜品'
        mat.save(update_fields=['category_old'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_alter_rawmaterial_category'),
    ]

    operations = [
        # 1. Create MaterialCategory table
        migrations.CreateModel(
            name='MaterialCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='分类名称')),
            ],
            options={
                'verbose_name': '原料分类',
                'verbose_name_plural': '原料分类',
            },
        ),

        # 2. Rename old category to category_old
        migrations.RenameField(
            model_name='rawmaterial',
            old_name='category',
            new_name='category_old',
        ),

        # 3. Add new FK field as nullable
        migrations.AddField(
            model_name='rawmaterial',
            name='category',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='core.materialcategory',
                verbose_name='Category',
            ),
        ),

        # 4. Populate FK from old data
        migrations.RunPython(convert_category_to_fk, reverse_convert),

        # 5. Make FK non-nullable
        migrations.AlterField(
            model_name='rawmaterial',
            name='category',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='core.materialcategory',
                verbose_name='Category',
            ),
        ),

        # 6. Remove old CharField
        migrations.RemoveField(
            model_name='rawmaterial',
            name='category_old',
        ),
    ]
