# Poultry Daily Log Refactor Specification

**Target Module:** Poultry Management (`ob_poultry` Frappe App)  
**Document:** Functional & Technical Implementation Plan  
**Design Standard:** 100% Native Frappe/ERPNext UI, Standard DocTypes, Form Views, and Child Table Grids (No alien UI frameworks or popup modals)

---

## 1. User Journey & Navigation Flow

The navigation strictly follows this 3-tier structure:

```
[ 1. Poultry Daily Log List View ]
        |
        +--> Action Button: "Add today's log"
        |    (Automatically LOCKED / Disabled if today's log already exists)
        v
[ 2. Today's Daily Register (Farm / Date Level) ]
        |
        +--> Lists all active Sheds (Shed 1, Shed 2, Layer Shed A, etc.)
        |    Clicking any Shed opens that shed's register page
        v
[ 3. Shed Daily Register Page ]
        |
        +--> Top Header (Non-Editable): Shed Name, Date, Day of Week, Breed, Sex
        +--> Weight Entry: [ ] Checkbox -> Weight Input (Unlocked only when checked)
        |
        +--> 4 Data Entry Tables (Each having Batch as first column & Week/Day as second):
             1. Eggs Table (InStock, Good, Double Yolk, Broken, Waste, Total, Production %, Broken %, Trays + Left, Totals)
             2. Feeds Table (Warehouse inline dropdown, Opening Stock, Feed Spent Kg, Feed Spent g/bird, Available, Rate/Kg, Total Feed Cost, Totals)
             3. Chickens Table (Opening Birds, Dead, Culled, Closing Birds, Totals)
             4. Sales Table (Customer, Good, Double Yolk, Broken, Rate, Total Amount, Row & Column Totals)
```

---

## 2. Detailed Screen Specifications

### Screen 1: Poultry Daily Log List View
- **Button Label:** Change standard "Add Poultry Daily Log" to **"Add today's log"**.
- **Button Lock Guard:**
  - On list view load, query if a log exists for `log_date = frappe.datetime.get_today()`.
  - **If today's log exists:**
    - The button is locked / disabled (showing a lock indicator e.g. `🔒 Add today's log (Created)`).
    - Prevents duplicate register creation for the same day.
    - Clicking the today row opens the existing daily register.
  - **If today's log does NOT exist:**
    - The button is active (`➕ Add today's log`).
    - Clicking creates and opens today's register.

---

### Screen 2: Today's Daily Register & Shed Selection
- Shows the date and the active **Sheds** (`Poultry Shed`).
- Attendant clicks a Shed to enter daily logs for all flocks housed in that shed.

---

### Screen 3: Shed Daily Register Form

#### 3.1 Non-Editable Header Information
Top section cards display read-only context:
- **Shed Name**: Display name of the shed (read-only)
- **Date**: Today's date (read-only)
- **Day**: Day of the week (e.g., *Friday*, *Saturday*) (read-only)
- **Breed**: Bird breed in this shed (read-only, derived from active batch)
- **Sex**: Sex of birds (`Male`, `Female`, `Mixed`) (read-only, derived from active batch)

#### 3.2 Body Weight Entry
- **[ ] Record Bird Weight Today** (Checkbox, unchecked by default)
- **Average Body Weight (g)** (Float/Number field):
  - Read-only / locked by default.
  - Unlocked for typing only when the checkbox is checked.

---

### 3.3 Table 1: Eggs Production Table
*Native child table with batch-wise rows:*

| Column Name | Type | Behavior / Formula |
|---|---|---|
| **Batch** | Link | Active Batch in this shed |
| **Week / Day** | Data | Age from batch `start_date` (e.g. `W14 D2`) |
| **InStock** | Int | Opening eggs in hand (previous day balance) |
| **Good** | Int | Standard marketable eggs collected |
| **Double Yolk** | Int | Double yolk eggs collected |
| **Broken** | Int | Cracked / damaged eggs |
| **Waste** | Int | Spoiled / unusable eggs |
| **Total** | Int | **Auto-Calculated**: `Good + Double Yolk + Broken + Waste` |
| **Egg Production %** | Percent | **Auto-Calculated**: `(Total Eggs Produced ÷ Opening Birds) × 100` |
| **Broken Egg %** | Percent | **Auto-Calculated**: `(Broken Eggs ÷ Total Eggs Produced) × 100` |
| **Trays (Eggs Left)** | Data | **Auto-Calculated**: `"{Total // 30} Trays, {Total % 30} Eggs"` |

- **Column Totals**: Summary footer calculating sum for all numeric columns (InStock, Good, Double Yolk, Broken, Waste, Total, Trays, etc.).

---

### 3.4 Table 2: Feeds Consumption & Inventory Table
*Native child table with batch-wise feed usage:*

| Column Name | Type | Behavior / Formula |
|---|---|---|
| **Batch** | Link | Active Batch in this shed |
| **Week / Day** | Data | Age from batch `start_date` (e.g. `W14 D2`) |
| **Warehouse** | Link/Select | Prepopulated if default warehouse is set on Batch or Shed. If blank: clicking opens an inline dropdown listing active warehouses (no popup/dialog modal). |
| **Opening Stock (Kg)** | Float | Stock available in warehouse before today's feeding (*Stock presented before*) |
| **Feed Spent (Kg)** | Float | Total feed consumed by the batch today |
| **Feed Spent (g/bird)** | Float | **Auto-Calculated**: `(Feed Spent Kg × 1000) ÷ Opening Birds` |
| **Currently Available (Kg)**| Float | **Auto-Calculated**: `Opening Stock (Kg) - Feed Spent (Kg)` |
| **Rate / Kg** | Currency | Auto-fetched from ERPNext item valuation / purchase rate |
| **Total Feed Cost** | Currency | **Auto-Calculated**: `Feed Spent (Kg) × Rate / Kg` |

- **Column Totals**: Summary footer calculating total Feed Spent (Kg) and total Feed Cost.

---

### 3.5 Table 3: Chickens Table (Flock Population & Mortality)
*Native child table with flock headcount tracking:*

| Column Name | Type | Recommended Standard Terminology & Behavior |
|---|---|---|
| **Batch** | Link | Active Batch in this shed |
| **Week / Day** | Data | Age from batch `start_date` (e.g. `W14 D2`) |
| **Opening Birds** | Int | Bird count at the start of today (*Presented in batch before*) |
| **Dead** | Int | Mortality count today |
| **Culled** | Int | Culls count today |
| **Closing Birds** | Int | **Auto-Calculated**: `Opening Birds - Dead - Culled` (*Currently alive*) |

- **Column Totals**: Summary footer calculating total Opening Birds, Dead, Culled, and Closing Birds.

---

### 3.6 Table 4: Sales Table (Daily Egg Sales)
*Native child table with customer dispatches & live ERPNext integration:*

| Column Name | Type | Behavior / Formula |
|---|---|---|
| **Batch** | Link | Active Batch in this shed |
| **Week / Day** | Data | Age from batch `start_date` (e.g. `W14 D2`) |
| **Customer Name** | Link | Customer link from ERPNext (`Customer`) |
| **Good Eggs** | Int | Quantity of Good eggs sold |
| **Double Yolk** | Int | Quantity of Double Yolk eggs sold |
| **Broken Eggs** | Int | Quantity of Broken eggs sold |
| **Rate** | Currency | Prepopulated from ERPNext price list / daily egg rate |
| **Total Amount** | Currency | **Auto-Calculated**: `Eggs Sold × Rate` (both row amount and column totals) |

- **Column Totals**: Summary footer calculating total eggs sold and grand total revenue.

---

## 4. Architectural Rules
1. **100% Native Frappe/ERPNext UI**: Preserves Frappe standard layouts, forms, and table components.
2. **Draft & Submit Workflow**: Attendants save as Draft (`docstatus: 0`) during shifts; supervisor submits (`docstatus: 1`) in the evening.
3. **No Modals**: In-table warehouse selection uses standard inline Link/Select field dropdowns.
