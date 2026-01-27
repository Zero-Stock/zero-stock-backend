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
class Unit(models.Model):
    """
    Measurement units (e.g., kg, g, L, case).
    """
    name = models.CharField(max_length=20, unique=True, verbose_name="Unit Name")

    def __str__(self):
        return self.name


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


class RawMaterial(models.Model):
    """
    The base ingredient purchased from suppliers (Gross Material).
    Example: 'Potato (Raw/Unwashed)'
    """
    CATEGORY_CHOICES = (
        ('VEG', 'Vegetables'), ('MEAT', 'Meat/Poultry'),
        ('GRAIN', 'Grains'), ('COND', 'Condiments'), ('OTHER', 'Others')
    )
    name = models.CharField(max_length=100, unique=True, verbose_name="Material Name")
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, verbose_name="Category")
    default_unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, verbose_name="Purchase Unit")

    def __str__(self):
        return self.name


class ProcessedMaterial(models.Model):
    """
    [KEY LOGIC] Defines a specific processing method and its Yield Rate.
    Example: Raw 'Potato' -> Process 'Peeled & Diced' -> Yield 0.80.
    """
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='specs')
    method_name = models.CharField(max_length=50, verbose_name="Processing Method",
                                   help_text="E.g., 'Peeled', 'Sliced'")

    yield_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.00,
        verbose_name="Yield Rate",
        help_text="Format: 1.00 = 100%, 0.80 = 80%. Formula: Gross = Net / Yield"
    )

    class Meta:
        unique_together = ('raw_material', 'method_name')  # Ensures distinct methods for same material
        verbose_name = "Processing Specification"

    def __str__(self):
        return f"{self.raw_material.name} [{self.method_name}] (Yield: {self.yield_rate})"

# Dishes & Recipes
class Dish(models.Model):
    """
    Represents a specific dish (e.g., 'Tomato Beef Stew').
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Dish Name")

    # A dish might be suitable for multiple diets (e.g., Standard AND Diabetic)
    # This allows flexible classification.
    allowed_diets = models.ManyToManyField(DietCategory, blank=True, verbose_name="Suitable for Diets")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Dishes"


class DishIngredient(models.Model):
    """
    [The Recipe] Connects a Dish to a ProcessedMaterial with a specific Net Quantity.
    """
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='ingredients')

    # Critical: We link to the PROCESSED material (Net), not the raw one.
    material = models.ForeignKey(ProcessedMaterial, on_delete=models.PROTECT, verbose_name="Ingredient (Net)")

    net_quantity = models.DecimalField(
        max_digits=8, decimal_places=3,
        verbose_name="Net Qty per Serving",
        help_text="The weight AFTER processing (usually in kg or g)."
    )

    def __str__(self):
        return f"{self.dish.name} uses {self.material}"