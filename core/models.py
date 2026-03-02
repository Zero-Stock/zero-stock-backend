from django.db import models
from django.contrib.auth.models import User

# User Data
class ClientCompany(models.Model):
    """
    Represents the tenant entity (e.g., Hospital A, Rehab Center B).
    System users are grouped by company to ensure data isolation.
    """
    name = models.CharField(max_length=100, verbose_name="Company Name",
                            help_text="Official name of the client company.")
    code = models.CharField(max_length=20, unique=True, verbose_name="Company Code",
                            help_text="Unique identifier, e.g., 'HOSP01'.")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Client Company"
        verbose_name_plural = "Client Companies"


class UserProfile(models.Model):
    """
    Extends the standard Django User model to include company association and role-based access control.
    """
    ROLE_CHOICES = (
        ('RW', 'Read/Write (Manager)'),
        ('RO', 'Read Only (Viewer)'),
    )

    # Link to the built-in Django User model
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # The company this user belongs to
    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE, related_name='users',
                                verbose_name="Affiliated Company")

    # The permission level
    role = models.CharField(max_length=2, choices=ROLE_CHOICES, default='RO', verbose_name="Role Permission")

    def __str__(self):
        return f"{self.user.username} - {self.company.code} ({self.get_role_display()})"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

# Diet Data
class DietCategory(models.Model):
    """
    Classifies the type of set meal (e.g., Standard A, Diabetic, Soft Food).
    This matches your requirement: 'First classified by Diet Type'.
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="Diet Category Name")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Diet Categories"


class MaterialCategory(models.Model):
    """原料分类（如 鲜品、冻品）"""
    name = models.CharField(max_length=50, unique=True, verbose_name="分类名称")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "原料分类"
        verbose_name_plural = "原料分类"


class RawMaterial(models.Model):
    """
    The base ingredient purchased from suppliers (Gross Material).
    Internal unit is always kg.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Material Name")
    category = models.ForeignKey(MaterialCategory, on_delete=models.PROTECT, verbose_name="Category")

    def __str__(self):
        return self.name

class RawMaterialYieldRate(models.Model):
    """
    Yield rate is tied ONLY to RawMaterial and affects PROCUREMENT only.
    Each record is a version effective from `effective_date` (inclusive).
    """
    raw_material = models.ForeignKey(
        "RawMaterial", on_delete=models.CASCADE, related_name="yield_rates"
    )
    yield_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.00,
        help_text="1.00 = 100%, 0.80 = 80%. Procurement gross = net / yield."
    )
    effective_date = models.DateField(help_text="Effective from this date (inclusive).")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("raw_material", "effective_date")
        ordering = ["-effective_date", "-id"]

    def __str__(self):
        return f"{self.raw_material.name} yield={self.yield_rate} from {self.effective_date}"

class ProcessedMaterial(models.Model):
    """
    [KEY LOGIC] Defines a specific processing method and its Yield Rate.
    Example: Raw 'Potato' -> Process 'Peeled & Diced' -> Yield 0.80.
    """
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='specs')
    method_name = models.CharField(max_length=50, verbose_name="Processing Method",
                                   help_text="E.g., 'Peeled', 'Sliced'")

    class Meta:
        unique_together = ('raw_material', 'method_name')  # Ensures distinct methods for same material
        verbose_name = "Processing Specification"

    def __str__(self):
        return f"{self.raw_material.name} [{self.method_name}]" #(Yield: {self.yield_rate})

# Dishes & Recipes
class Dish(models.Model):
    """
    Represents a specific dish (e.g., 'Tomato Beef Stew').
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Dish Name")
    seasonings = models.TextField(blank=True, default="", verbose_name="调料",
                                   help_text="如: 盐、酱油、料酒")
    cooking_method = models.TextField(blank=True, default="", verbose_name="制作工艺",
                                       help_text="如: 先炒后炖，大火收汁")

    # A dish might be suitable for multiple diets (e.g., Standard AND Diabetic)
    allowed_diets = models.ManyToManyField(DietCategory, blank=True, verbose_name="Suitable for Diets")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Dishes"


class DishIngredient(models.Model):
    """
    [The Recipe] 菜谱配方行：每个原料对应重量和可选的处理方法。
    """
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='ingredients')

    # 直接关联原料
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, verbose_name="原料")

    # 可选的处理方法（含出成率）
    processing = models.ForeignKey(
        ProcessedMaterial, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="处理方法",
        help_text="可选。若选择了处理方法，系统会自动使用对应的出成率。"
    )

    net_quantity = models.DecimalField(
        max_digits=8, decimal_places=3,
        verbose_name="重量(每份)",
        help_text="每份用量，单位与原料一致（通常为 kg）。"
    )

    def __str__(self):
        method = f" [{self.processing.method_name}]" if self.processing else ""
        return f"{self.dish.name} - {self.raw_material.name}{method}"


# Suppliers
class Supplier(models.Model):
    """
    Supplier entity. Tracks vendor contact info.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Supplier Name")
    contact_person = models.CharField(max_length=50, blank=True, default="", verbose_name="Contact Person")
    phone = models.CharField(max_length=30, blank=True, default="", verbose_name="Phone")
    address = models.CharField(max_length=200, blank=True, default="", verbose_name="Address")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"


class SupplierMaterial(models.Model):
    """
    供应商供货规格：哪个供应商提供哪种原料，以什么规格和价格。
    """
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="materials")
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name="suppliers")
    unit_name = models.CharField(max_length=20, default='kg', verbose_name="销售单位",
                                  help_text="如: 箱, 袋, 盒, kg")
    kg_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=1.00,
                                      verbose_name="每单位kg数",
                                      help_text="如: 1箱=10kg 则填 10")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                verbose_name="单价(每供应商单位)")
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        unique_together = ('supplier', 'raw_material')
        verbose_name = "Supplier Material"

    def __str__(self):
        return f"{self.supplier.name} - {self.raw_material.name} ({self.unit_name})"
