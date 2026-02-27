from django.db import models
from core.models import ClientCompany, DietCategory, Dish, RawMaterial, Unit


# ==========================================
# 1. Operational Settings (Regions & Menu Config)
# ==========================================

class ClientCompanyRegion(models.Model):
    """
    [Was 'Ward'] Represents a physical area or department within the client company.
    Examples: 'East Wing', 'ICU', 'VIP Building', 'Staff Canteen'.
    Used for logistics (delivery destinations) and headcount statistics.
    """
    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE, verbose_name="Hospital/Company")
    name = models.CharField(max_length=50, verbose_name="Region Name")

    def __str__(self):
        return f"{self.name} ({self.company.code})"

    class Meta:
        unique_together = ('company', 'name')
        verbose_name = "Client Region / Ward"
        verbose_name_plural = "Client Regions"


class WeeklyMenu(models.Model):
    """
    [NEW LOGIC] Static Menu Configuration (Cycle Menu).
    Instead of inputting the menu every day, we define a standard weekly cycle for each Diet Type.
    Example: "Standard A" on "Monday Lunch" always serves "Potato Beef".
    """
    DAY_CHOICES = (
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
        (7, 'Sunday'),
    )

    MEAL_CHOICES = (
        ('B', 'Breakfast'),
        ('L', 'Lunch'),
        ('D', 'Dinner'),
    )

    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE)
    diet_category = models.ForeignKey(DietCategory, on_delete=models.CASCADE, verbose_name="Diet Set (e.g. Standard A)")

    day_of_week = models.IntegerField(choices=DAY_CHOICES, verbose_name="Day of Week")
    meal_time = models.CharField(max_length=1, choices=MEAL_CHOICES, verbose_name="Meal Period")

    # The fixed dishes for this specific slot
    dishes = models.ManyToManyField(Dish, verbose_name="Fixed Dishes")

    class Meta:
        verbose_name = "Weekly Menu Config"
        verbose_name_plural = "Weekly Menu Configs"
        # Ensure one config per Company + Diet + Day + Meal
        unique_together = ('company', 'diet_category', 'day_of_week', 'meal_time')

    def __str__(self):
        return f"{self.diet_category} - {self.get_day_of_week_display()} {self.get_meal_time_display()}"


# ==========================================
# 2. Daily Input (Only Headcount Needed Now!)
# ==========================================

class DailyCensus(models.Model):
    """
    [INPUT] Daily Patient/Staff Count.
    Now simpler: We only need to know HOW MANY people are in a Region.
    The system will look up WHAT they eat based on the WeeklyMenu.
    """
    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE)
    date = models.DateField(verbose_name="Target Date")

    # Renamed from 'ward' to 'region'
    region = models.ForeignKey(ClientCompanyRegion, on_delete=models.CASCADE, verbose_name="Region/Ward")

    diet_category = models.ForeignKey(DietCategory, on_delete=models.CASCADE, verbose_name="Diet Type")
    count = models.PositiveIntegerField(default=0, verbose_name="Headcount")

    class Meta:
        unique_together = ('company', 'date', 'region', 'diet_category')
        verbose_name = "Daily Census (Headcount)"

    def __str__(self):
        return f"{self.date} | {self.region.name} | {self.diet_category.name}: {self.count}"


# ==========================================
# 3. Procurement Output (Calculation)
# ==========================================

class ProcurementRequest(models.Model):
    """
    [OUTPUT] Purchase Order Header.
    """
    STATUS_CHOICES = (
        ('DRAFT', 'Draft (Calculating)'),
        ('CONFIRMED', 'Confirmed (Sent)'),
    )

    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE)
    target_date = models.DateField(verbose_name="For Usage Date")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    def __str__(self):
        return f"PO-{self.target_date}-{self.company.code}"


class ProcurementItem(models.Model):
    """
    [OUTPUT] Calculated Ingredients.
    Logic: Census(Count) * WeeklyMenu(Dishes) * Dish(Recipe) / Yield
    """
    request = models.ForeignKey(ProcurementRequest, on_delete=models.CASCADE, related_name='items')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)

    total_gross_quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Qty (kg)")
    notes = models.TextField(blank=True)  # To store logs like "Monday Menu: 50 people x 0.2kg"

    class Meta:
        verbose_name = "Procurement Line Item"



#Below is what chief need to enter daily:
class MealType(models.TextChoices):
    ' Choose the meal type'
    BREAKFAST = "B", "Breakfast"
    LUNCH = "L", "Lunch"
    DINNER = "D", "Dinner"

class DailyMenu(models.Model):
    """
    Defines which dishes are served for a specific company,
    on a specific date, for a specific diet type and meal time.

    Example:
        Company A
        2026-02-10
        Diet: Standard A
        Meal: Lunch
        → Dishes: Tomato Beef, Stir-fried Cabbage
    """

    # Company (data isolation)
    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE)

    # Service date
    date = models.DateField()

    # Diet type (e.g., Standard A, Diabetic)
    diet = models.ForeignKey(DietCategory, on_delete=models.CASCADE)

    # Meal time (Breakfast / Lunch / Dinner)
    meal_type = models.CharField(max_length=1, choices=MealType.choices)

    # Dishes included in this meal
    dishes = models.ManyToManyField(Dish, blank=True)

    class Meta:
        # Prevent duplicate menu entries for same company/date/diet/meal
        unique_together = ('company', 'date', 'diet', 'meal_type')

class StapleType(models.TextChoices):
    """
    Types of staple food.
    Used to distinguish rice and noodle demand.
    """
    RICE = "RICE", "Rice"
    NOODLE = "NOODLE", "Noodle"

class StapleDemand(models.Model):
    """
    Stores staple food demand for a specific company,
    date, diet type, and meal time.

    Example:
        2026-02-10
        Diet: Standard A
        Lunch
        Rice: 120 kg
        Noodle: 30 kg
    """

    # Company (data isolation)
    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE)

    # Service date
    date = models.DateField()

    # Diet type
    diet = models.ForeignKey(DietCategory, on_delete=models.CASCADE)

    # Meal time (Breakfast / Lunch / Dinner)
    meal_type = models.CharField(max_length=1, choices=MealType.choices)

    # Staple category (Rice or Noodle)
    staple_type = models.CharField(max_length=10, choices=StapleType.choices)

    # Required quantity
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    # Unit of measurement (e.g., kg)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)

    class Meta:
        # Prevent duplicate staple entries for same combination
        unique_together = ('company', 'date', 'diet', 'meal_type', 'staple_type')