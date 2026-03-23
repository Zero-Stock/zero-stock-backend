from django.db import models
from core.models import ClientCompany, DietCategory, Dish, RawMaterial, ProcessedMaterial


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

    # The fixed dishes for this specific slot (with quantity via through table)
    dishes = models.ManyToManyField(Dish, through='WeeklyMenuDish', verbose_name="Fixed Dishes")

    class Meta:
        verbose_name = "Weekly Menu Config"
        verbose_name_plural = "Weekly Menu Configs"
        # Ensure one config per Company + Diet + Day + Meal
        unique_together = ('company', 'diet_category', 'day_of_week', 'meal_time')

    def __str__(self):
        return f"{self.diet_category} - {self.get_day_of_week_display()} {self.get_meal_time_display()}"


class WeeklyMenuDish(models.Model):
    """
    Through table for WeeklyMenu <-> Dish relationship.
    Stores the quantity (number of plates/servings) for each dish in a menu slot.
    Example: 普食1 Friday Lunch -> 番茄炒蛋 x2, 土豆丝 x3
    """
    menu = models.ForeignKey(WeeklyMenu, on_delete=models.CASCADE, related_name='menu_dishes')
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, verbose_name="份数",
                                           help_text="该菜品在此餐次的数量（盘数），默认1")

    class Meta:
        unique_together = ('menu', 'dish')
        verbose_name = "Weekly Menu Dish"
        verbose_name_plural = "Weekly Menu Dishes"

    def __str__(self):
        return f"{self.menu} - {self.dish.name} x{self.quantity}"


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
    Status flow: CREATED → SUBMITTED → CONFIRMED
    """
    STATUS_CHOICES = (
        ('CREATED', 'Created (Generated)'),
        ('SUBMITTED', 'Submitted (Pending Receiving)'),
        ('CONFIRMED', 'Confirmed (Receiving Done)'),
    )

    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE)
    target_date = models.DateField(verbose_name="For Usage Date")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CREATED')

    def __str__(self):
        return f"PO-{self.target_date}-{self.company.code}"


class ProcurementItem(models.Model):
    """
    [OUTPUT] Calculated Ingredients.
    Logic: Census(Count) * WeeklyMenu(Dishes) * Dish(Recipe) / Yield
    Tracks demand, current stock snapshot, and purchase quantity.
    """
    request = models.ForeignKey(ProcurementRequest, on_delete=models.CASCADE, related_name='items')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)

    # Quantities in kg
    demand_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="需求量(kg)")
    stock_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="库存快照(kg)")
    purchase_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="采购量(kg)")

    # Supplier assignment (pre-filled from default_supplier, modifiable)
    supplier = models.ForeignKey(
        'core.Supplier', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="供应商"
    )
    supplier_unit_name = models.CharField(max_length=20, blank=True, default='', verbose_name="供应商单位")
    supplier_kg_per_unit = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="每单位kg数",
        help_text="用于 kg ↔ 供应商单位换算"
    )
    supplier_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="单价(每供应商单位)"
    )

    notes = models.TextField(blank=True)

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
    unit = models.CharField(max_length=20, default='kg', verbose_name="Unit")

    class Meta:
        # Prevent duplicate staple entries for same combination
        unique_together = ('company', 'date', 'diet', 'meal_type', 'staple_type')


# ==========================================
# 5. Receiving Record
# ==========================================

class ReceivingRecord(models.Model):
    """
    Receiving/inspection record, linked to a Procurement Request.
    Tracks actual received quantities vs. expected quantities.
    """
    STATUS_CHOICES = (
        ('PENDING', 'Pending Inspection'),
        ('COMPLETED', 'Completed'),
    )

    procurement = models.ForeignKey(ProcurementRequest, on_delete=models.CASCADE, related_name='receivings')
    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE)
    received_date = models.DateField(auto_now_add=True, verbose_name="Received Date")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Receiving Record"

    def __str__(self):
        return f"RCV-{self.procurement}-{self.received_date}"


class ReceivingItem(models.Model):
    """
    Receiving line item: expected vs. actual quantity for each raw material.
    """
    receiving = models.ForeignKey(ReceivingRecord, on_delete=models.CASCADE, related_name='items')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    expected_quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Expected Qty")
    actual_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Actual Qty")
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Receiving Item"


# ==========================================
# 6. Processing Order
# ==========================================

class ProcessingOrder(models.Model):
    """
    Processing demand order header.
    Auto-calculated from daily menu + headcount.
    """
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('CONFIRMED', 'Confirmed'),
    )

    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE)
    target_date = models.DateField(verbose_name="Processing Date")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    class Meta:
        verbose_name = "Processing Order"

    def __str__(self):
        return f"PROC-{self.target_date}-{self.company.code}"


class ProcessingItem(models.Model):
    """
    Processing demand line item: required quantity for each
    raw material + processing method combination, linked to the source dish.
    """
    order = models.ForeignKey(ProcessingOrder, on_delete=models.CASCADE, related_name='items')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    processed_material = models.ForeignKey(ProcessedMaterial, on_delete=models.SET_NULL, null=True, blank=True)
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, verbose_name="Source Dish")
    net_quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Net Qty (kg)")
    gross_quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Gross Qty (kg)")

    class Meta:
        verbose_name = "Processing Item"

    def __str__(self):
        method = self.processed_material.method_name if self.processed_material else "无加工"
        return f"{self.raw_material.name}[{method}] for {self.dish.name}"


# ==========================================
# 7. Delivery Order
# ==========================================

class DeliveryOrder(models.Model):
    """
    Delivery demand order: generated per date + meal time.
    """
    MEAL_CHOICES = (
        ('B', 'Breakfast'),
        ('L', 'Lunch'),
        ('D', 'Dinner'),
    )

    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE)
    target_date = models.DateField(verbose_name="Delivery Date")
    meal_time = models.CharField(max_length=1, choices=MEAL_CHOICES, verbose_name="Meal Time")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Delivery Order"
        unique_together = ('company', 'target_date', 'meal_time')

    def __str__(self):
        return f"DLV-{self.target_date}-{self.get_meal_time_display()}-{self.company.code}"


class DeliveryItem(models.Model):
    """
    Delivery line item: number of servings per region per diet type.
    """
    delivery = models.ForeignKey(DeliveryOrder, on_delete=models.CASCADE, related_name='items')
    region = models.ForeignKey(ClientCompanyRegion, on_delete=models.CASCADE, verbose_name="Region")
    diet_category = models.ForeignKey(DietCategory, on_delete=models.CASCADE, verbose_name="Diet Type")
    count = models.PositiveIntegerField(default=0, verbose_name="Servings")

    class Meta:
        verbose_name = "Delivery Item"

    def __str__(self):
        return f"{self.region.name}: {self.diet_category.name} x {self.count}"