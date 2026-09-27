# User Guide — Poultry Module

How to actually run a farm in this app, day to day. This is written for the people using the module, not the people building it — if you're looking for doctype specs or design rationale, see [FRD.md](./FRD.md) and [BRD.md](./BRD.md) instead.

## Getting to the module

Open the **Poultry** workspace from the app switcher, or go to `/app/poultry`. The left sidebar groups everything by area (Flock Management, Vaccination, Feed Mill, Hatchery, Contract Farming, Reports); the workspace itself shows live counts (Active Batches, Total Active Birds, Pending Vaccinations, Active Feed Formulas) and quick-access cards for the same groups.

## Who can do what

| Role | Can do | Can't do |
|---|---|---|
| **Poultry Manager** | Everything — masters, batches, closing batches, all transactions | — |
| **Poultry Attendant** | Create and submit Daily Logs | Edit Sheds/Breeds/Batches, close a batch, delete anything |
| **Vaccination In-charge** | Create Vaccination Records, update Vaccination Due status | Edit Batches, Sheds, Breeds |
| **Feed Mill Operator** | Create/edit Feed Formulas and Feed Productions | Edit Batches, Sheds, Breeds |
| **System Manager** | Everything, including role and permission setup | — |

If someone can't do something the table above says they should be able to, check their role assignment under **User** before assuming it's a bug.

## One-time setup

Do this once before placing any flocks. All of it lives under Flock Management, Vaccination, Feed Mill, Hatchery, or Contract Farming in the sidebar.

1. **ERPNext itself** — Company, Chart of Accounts, at least one Warehouse, an Item Group, a UOM. This app doesn't set these up for you; if a feed-related action throws an error about a missing Company or Item, this is why.
2. **Poultry Shed** — one record per physical housing unit. Set **Capacity (Birds)** honestly; batch placement is blocked if you try to place more birds than the shed can hold.
3. **Poultry Breed** — one per breed you raise, with its **Breed Type** (Broiler / Layer / Breeder / Dual Purpose).
4. **Poultry Benchmark** *(optional but recommended)* — standard mortality %, feed/bird, and body weight for a breed at specific ages. Once these exist, every Daily Log for that breed automatically shows the standard next to the actual figure. You don't need every age covered — the nearest earlier age is used if an exact match isn't there.
5. **Poultry Vaccination Schedule Template** *(optional but recommended)* — one per breed, listing vaccines by age in days. Once this exists, placing a batch of that breed automatically generates its full vaccination due-list — you stop having to remember what's due when.
6. **Poultry Feed Formula** *(before you produce feed)* — see "Running the Feed Mill" below.
7. **Poultry Farmer** and **Poultry Growing Charge Scheme** *(only if you place contract flocks)* — see "Contract farming" below.
8. **Poultry Hatchery** *(only if you hatch your own chicks)* — see "Hatchery" below.

## Running a flock

### Placing a batch

Go to **Poultry Batch → New**. Pick a Shed and Breed, set the Start Date and Initial Bird Count. Leave **Flock Source** as *Owned* unless this batch belongs to a contract farmer (see below). If you set a **Feed Warehouse** here, every Daily Log against this batch can post real feed stock consumption straight from that warehouse — set it now, not later, or feed logging will ask you for it the first time you try.

The moment you save, two things happen automatically: **Current Bird Count** is seeded from Initial Bird Count, and if there's an active Vaccination Schedule Template for this breed, a full due-list appears under **Poultry Vaccination Due** filtered to this batch.

### Logging a day

**Poultry Daily Log → New**, pick the batch, set the date (defaults to today). One log per batch per day — the system will reject a second one for the same date. Fill in whatever applies:

- **Mortality** — add a row per cause under Mortality Detail (Disease, Injury, Heat Stress, Culled, Predator, Unknown, Other), with a count and optional sex and description. The total is computed for you; you never type a raw mortality number.
- **Feed** — pick the Feed Item and enter kg consumed. If the batch has a Feed Warehouse set, submitting the log posts a real stock issue against it — if that warehouse doesn't have enough stock, the submit will fail with ERPNext's own stock error, which means it's time to record a feed production or purchase, not a bug in this log.
- **Body weight** — average weight in grams. If a Benchmark exists for this breed/age, the standard weight shows alongside it automatically.
- **Eggs** — add a row per grade (Hatching / Table / Jumbo / Cracked / Waste) with the count produced that day. Opening count carries forward from the previous day automatically; you only ever enter production. HDEP % is computed for you.

**Submit** the log when you're done — nothing here is enforced until submission. Bird count, cumulative feed, FCR, and CFCR on the batch itself update the moment you submit, and reverse cleanly if you cancel.

### Reading a batch's health

Open the batch itself: **Current Bird Count**, **Total Mortality**, **Cumulative Feed (kg)**, **FCR**, and **CFCR** are always live, always derived from submitted logs — never something you set by hand. If a number here looks wrong, the fix is in the Daily Logs, not on the batch.

### Closing a batch

From the batch, use the **Close Batch** action. This sets Status to Closed and stamps an End Date. Once closed, no new Daily Logs can be created against it — if you need to log something after closing, that's a sign the batch shouldn't have been closed yet.

## Vaccination

If a Vaccination Schedule Template exists for the batch's breed, its due-list is already sitting under **Poultry Vaccination Due**, filtered by batch, each row showing the vaccine, dose, method, and due date. When you actually administer one, create a **Poultry Vaccination Record** and set its **Due** field to the matching due row — that closes the due item out automatically (status becomes Done, linked back to your record). You can also log a vaccination without picking a Due row if it wasn't on the schedule; that's fine, it just won't close anything out.

## Running the Feed Mill

### Defining a formula

**Poultry Feed Formula → New**. Set the finished **Feed Item** (must already exist in ERPNext's Item list) and a **Batch Size (kg)** — the basis the recipe is written against, typically 100kg. Add ingredient rows: raw material, quantity in kg, and category (**Raw Material** for bulk ingredients like maize and soya, **Medicine** for small-dose additives like premix and amino acids). Percentages and category subtotals compute themselves as you add rows.

Once the ingredient list is right, use the **Create BOM** button in the toolbar (it reads **Update BOM** once one already exists) — this builds or refreshes a real ERPNext Bill of Materials from your ingredients. You need a Company set up in ERPNext for this to work.

### Producing feed

**Poultry Feed Production → New**, pick the formula, set **Planned Batches** (a multiplier on the formula's batch size — 5 planned batches against a 100kg formula plans 500kg). Use **Create Work Order** to generate the actual ERPNext Work Order against the formula's BOM. Once production actually happens, come back and set **Actual Output (kg)** — Yield % computes automatically against what was planned.

## Contract farming

If a batch belongs to a farmer rather than being raised in-house, set its **Flock Source** to *Contract* — this reveals **Farmer** and **Growing Charge Scheme** fields, both required once Contract is selected. Everything else about the batch (Daily Log, vaccination, FCR) works exactly the same as an owned batch.

Once the batch has at least one submitted Daily Log with a body weight recorded, use **Calculate Growing Charge** on the batch — it looks up the farmer's payout rate for the current weight bracket in the Growing Charge Scheme and computes the amount owed from current bird count × weight × rate. Re-run it any time weight or bird count changes materially; it isn't automatic on every log submission.

**Poultry Farmer** records just need a name, phone, and optionally which branch/line they belong to (free text — this app doesn't yet manage a formal branch/route hierarchy). **Poultry Growing Charge Scheme** needs at least one rate bracket (min weight, optional max weight, rate per kg); leave the top bracket's max weight blank for "and above."

## Hatchery

**Poultry Hatchery** is just a facility record. **Poultry Hatch** tracks one incubation run: schedule/setting/candling/transfer/hatch dates, eggs set, and a standard hatchability % — enter that and **Estimated Chicks** computes itself. Once chicks actually hatch, fill in **Actual Chicks**.

To move hatched chicks into a batch, create a **Poultry Chick Transfer** linking the hatch and the destination batch, with a quantity. The system checks the running total of everything already transferred out of that hatch against its Actual Chicks and blocks you if you try to over-allocate.

## Reports

All under the Poultry workspace's **Reports** section. Each one takes filters (usually a date range, sometimes a specific batch/farmer/formula) — leave a filter blank to see everything.

| Report | Answers |
|---|---|
| **Mortality Report** | What died, by cause, across which batches, in a date range |
| **Batch Analysis** | Snapshot of every batch's birds, feed, FCR/CFCR, growing charge |
| **Batch Performance Review** | Same, plus Mortality % — the go-to for comparing batches side by side |
| **Bird Count Trend** | Day-by-day bird count for one specific batch, reconstructed from its log history |
| **Empty Sheds** | Which sheds have no active batch right now — where you have free capacity |
| **Egg Production Report** | Daily egg counts by grade and batch, with HDEP % |
| **Feed Consumption Report** | Daily feed use by batch, with a running total *within the filtered range* (not the batch's all-time total — that's on the batch itself) |
| **Bodyweight Report** | Actual vs. standard body weight over time, per batch |
| **Feed Production Summary** | Every production run — group by Formula or Feed Item in the report UI itself to get poultry.care's separate "by Formula"/"by Feed" views from this one report |
| **Compare Formula** | Every active formula's ingredients side by side, raw materials then medicine, with a totals row |
| **Growing Charges** | Every contract batch's computed payout, filterable by farmer or scheme |
| **Chick Summary** | Eggs set, estimated and actual chicks, hatchability %, rolled up by hatchery |
| **Chick Stock** | How many chicks from each hatch haven't been transferred out yet |

## When something gets rejected

The app is designed to fail loudly right where the problem is, rather than silently accepting bad data. If you hit a validation error, it's almost always one of these:

- **"Initial Bird Count exceeds the capacity of Shed..."** — the shed's Capacity field is lower than what you're trying to place; fix one or the other.
- **"A log for batch ... on ... already exists"** — you're trying to log the same batch twice on the same date; edit the existing log instead.
- **"Total removed birds would exceed the initial bird count"** — the mortality/cull you're entering, added to everything already submitted, would take the batch below zero birds; double-check the numbers.
- **"Batch ... is closed and cannot receive new daily logs"** — you're logging against a closed batch; if that's wrong, don't reopen it casually — check with whoever closed it first.
- **"Set a Feed Warehouse on Poultry Batch ... before logging feed consumption"** — go set it on the batch, then retry the log.
- **"Set a Farmer for a Contract flock" / "Set a Growing Charge Scheme for a Contract flock"** — you set Flock Source to Contract but left one of the two required fields blank.
- A raw ERPNext stock error on submitting a Daily Log with feed consumption — the feed warehouse doesn't have enough stock; that's ERPNext protecting your inventory, not a bug here. Record a Feed Production or Purchase first.
