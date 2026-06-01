# API Reference — G-SET PV Plant Simulation Engine (`pvsim_engine.py`)

> Full parameter and function reference.
> For installation and quick start, see [README.md](README.md).

---

## Functions

### `set_seed(seed=42)`

Fix the random seed for fully reproducible simulation results.
Call once before any `run_season()` or `run_days()` call.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `seed` | `int` | `42` | Random seed value |

```python
set_seed(42)
data = run_season('summer')   # identical output for every participant
```

---

### `run_season(season, time_resolution_mins=5.0, force_weekday=True, **override_params)`

Simulate one representative day for the given season.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `season` | `str` | — | `'summer'` \| `'rainy'` \| `'winter'` |
| `time_resolution_mins` | `float` | `5.0` | Time step in minutes |
| `force_weekday` | `bool` | `True` | Shift reference date to nearest weekday so On-Peak TOU rates always apply |
| `location` | `str` | — | Optional location preset key — see [LocationPreset](#locationpreset) |
| `building_type` | `str` | — | Optional load profile preset key — see [BuildingPreset](#buildingpreset) |
| `**override_params` | — | — | Any parameter from the tables below. Takes precedence over all presets. |

**Returns:** `list[dict]` — one record per time step.

**Priority order (highest wins):** `override_params` > `BuildingPreset` > `LocationPreset` > `SeasonPreset`

```python
set_seed(42)
data = run_season('summer')
data = run_season('summer', building_type='office')
data = run_season('summer', location='tokyo', temp_base_c=28.0)
data = run_season('summer', location='london', building_type='office',
                  temp_base_c=20.0, cloud_mean=0.6)
data = run_season('rainy',  cloud_mean=0.9, pv_capacity_kw=10.0)
```

---

### `run_days(season, n_days=7, start_date=None, time_resolution_mins=5.0, **override_params)`

Simulate multiple consecutive days.
Cloud cover state carries over between days (Markov continuity).
TOU rates are applied correctly per weekday/weekend automatically.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `season` | `str` | — | `'summer'` \| `'rainy'` \| `'winter'` |
| `n_days` | `int` | `7` | Number of days to simulate |
| `start_date` | `datetime` | season reference date | First day of simulation |
| `time_resolution_mins` | `float` | `5.0` | Time step in minutes |
| `location` | `str` | — | Optional location preset key |
| `building_type` | `str` | — | Optional load profile preset key |
| `**override_params` | — | — | Any parameter from the tables below |

**Returns:** `list[dict]` — one record per time step across all days.

```python
from datetime import datetime

set_seed(42)
data = run_days('rainy', n_days=14, start_date=datetime(2026, 8, 19))
data = run_days('summer', n_days=7, building_type='factory', peak_load=12.0)
data = run_days('winter', n_days=30, location='tokyo', temp_base_c=5.0)
save_simulation_to_csv(data, 'output.csv')
```

---

### `get_financial_summary(season, dataset)`

Calculate energy and cost metrics. Returns a dict — no print side effects.

| Parameter | Type | Description |
|---|---|---|
| `season` | `str` | Label string written into the returned dict |
| `dataset` | `list[dict]` | Output from `run_season()` or `run_days()` |

**Returns:** `dict`

| Key | Type | Description |
|---|---|---|
| `season` | `str` | Season label |
| `avg_irradiance_wm2` | `float` | Average GHI over the period (W/m²) |
| `avg_temp_c` | `float` | Average ambient temperature (°C) |
| `peak_pv_kw` | `float` | Maximum PV output in any single time step (kW) |
| `total_pv_kwh` | `float` | Total PV energy generated (kWh) |
| `total_grid_kwh` | `float` | Total energy imported from grid (kWh) |
| `total_cost_thb` | `float` | Total TOU electricity cost (THB) |

```python
s = get_financial_summary('summer', data)
payback_years = 180_000 / (s['total_cost_thb'] * 365)

# Compare seasons
summaries = [get_financial_summary(k, v) for k, v in season_data.items()]
cheapest = min(summaries, key=lambda x: x['total_cost_thb'])
```

---

### `print_financial_summary(season, dataset)`

Print a formatted financial summary to stdout.
For downstream calculations, use `get_financial_summary()` instead.

---

### `save_simulation_to_csv(dataset, filename='simulation_output.csv')`

Export the dataset to a UTF-8 CSV file.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `dataset` | `list[dict]` | — | Output from `run_season()` or `run_days()` |
| `filename` | `str` | `'simulation_output.csv'` | Output file path |

---

### `plot_single_season(dataset, season, save_img=None, show_plot=True)`

Plot a 4-panel chart: (1) GHI + temperature, (2) cloud cover,
(3) energy balance, (4) TOU electricity cost.

Returns matplotlib.figure.Figure — for further customisation if needed

| Parameter   | Type         | Default | Description                                                    |
|-------------|--------------|---------|----------------------------------------------------------------|
| `dataset`   | `list[dict]` | —       | Simulation output                                              |
| `season`    | `str`        | —       | Controls colour scheme (`'summer'` \| `'rainy'` \| `'winter'`) |
| `save_img`  | `str`        | `None`  | Optional file path to save figure (e.g. `'report.png'`)        |
| `show_plot` | `bool`       | `True`  | Optional flag to turn on/off automatic plot display            |

---

### `plot_season_comparison(season_datasets, save_img=None)`

Overlay all three seasons on the same axes for direct comparison.

| Parameter | Type | Description |
|---|---|---|
| `season_datasets` | `dict` | `{'summer': [...], 'rainy': [...], 'winter': [...]}` |
| `save_img` | `str` | Optional output file path |

```python
plot_season_comparison({
    'summer': data_s,
    'rainy':  data_r,
    'winter': data_w,
})
```

---

## Classes

### `SeasonPreset`

Bangkok-calibrated weather and system parameter presets for three seasons.
Default location: **Bangkok, Thailand (13.75°N, 100.52°E, UTC+7)**.

| Method | Returns | Description |
|---|---|---|
| `SeasonPreset.get(season)` | `dict` | Full merged parameter dict for the season |
| `SeasonPreset.get_reference_date(season)` | `datetime` | Representative weekday date |
| `SeasonPreset.list_seasons()` | `list[str]` | All available season keys |

---

### `LocationPreset`

Geographic parameter presets for common cities.
Provides `latitude_deg`, `longitude_deg`, and `timezone_offset_h`.

| Method | Returns | Description |
|---|---|---|
| `LocationPreset.get(location)` | `dict` | Geographic parameters for the location |
| `LocationPreset.list_locations()` | `list[str]` | All available location keys |

**Available locations:**

| Key | Latitude | Longitude | UTC offset |
|---|---|---|---|
| `'bangkok'` | 13.75°N | 100.52°E | +7 (default) |
| `'tokyo'` | 35.68°N | 139.69°E | +9 |
| `'london'` | 51.51°N | 0.13°W | 0 |
| `'sydney'` | 33.87°S | 151.21°E | +10 |
| `'dubai'` | 25.20°N | 55.27°E | +4 |
| `'new_york'` | 40.71°N | 74.01°W | -5 |

> Any location not listed can be simulated by passing `latitude_deg`,
> `longitude_deg`, and `timezone_offset_h` directly in `override_params`.

```python
# Using a preset
data = run_season('summer', location='tokyo', temp_base_c=28.0)

# Custom location (no preset needed)
data = run_season('summer',
                  latitude_deg=48.85,
                  longitude_deg=2.35,
                  timezone_offset_h=1.0,
                  temp_base_c=22.0)
```

---

### `BuildingPreset`

Load profile presets for common building types.

| Method | Returns | Description |
|---|---|---|
| `BuildingPreset.get(building_type)` | `dict` | Load profile parameters |
| `BuildingPreset.list_types()` | `list[str]` | All available building type keys |

**Available building types:**

| Key | `base_load` | `peak_load` | `load_peak1_hour` | `load_peak2_hour` | Typical use |
|---|---|---|---|---|---|
| `'residential'` | 0.10 kW | 2.0 kW | 08:00 | 19:00 | Home / apartment |
| `'office'` | 0.05 kW | 3.0 kW | 09:30 | 13:30 | Commercial office |
| `'retail'` | 0.08 kW | 4.0 kW | 13:00 | 17:30 | Shop / mall |
| `'factory'` | 0.50 kW | 8.0 kW | 09:00 | 14:00 | Industrial / 2-shift |

```python
data = run_season('summer', building_type='office')
data = run_season('summer', building_type='factory', peak_load=12.0)
BuildingPreset.list_types()
```

---

## Override Parameters Reference

All parameters below can be passed as keyword arguments to `run_season()` or
`run_days()`. They override any preset value for that run only.

### Location

| Parameter | Default | Unit | Description |
|---|---|---|---|
| `latitude_deg` | 13.75 | ° | Latitude (negative = Southern Hemisphere) |
| `longitude_deg` | 100.52 | ° | Longitude (negative = West) |
| `timezone_offset_h` | 7.0 | h | UTC offset (e.g. UTC+7 → 7.0, UTC-5 → -5.0) |

### Cloud

| Parameter | Default (Summer) | Unit | Description |
|---|---|---|---|
| `cloud_mean` | 0.20 | 0–1 | Long-run mean cloud cover |
| `cloud_persistence` | 0.90 | 0–1 | Markov momentum — higher = clouds change more slowly |
| `cloud_noise_std` | 0.06 | — | Random shock standard deviation per time step |

### Temperature

| Parameter | Default (Summer) | Unit | Description |
|---|---|---|---|
| `temp_base_c` | 33.0 | °C | Mean daily base temperature |
| `temp_amplitude_c` | 7.0 | °C | Day/night temperature swing |
| `temp_peak_hour` | 14.5 | h | Hour of maximum daily temperature |

### Wind

| Parameter | Default (Summer) | Unit | Description |
|---|---|---|---|
| `wind_speed_mean_ms` | 1.8 | m/s | Mean wind speed (higher = better panel cooling) |
| `wind_speed_std_ms` | 0.5 | m/s | Wind speed standard deviation |

### PV Panel

| Parameter | Default | Unit | Description |
|---|---|---|---|
| `pv_capacity_kw` | — | kWp | System rated capacity — auto-derives `area` if set |
| `area` | 27.78 | m² | Total panel area (used when `pv_capacity_kw` is not set) |
| `eta_stc` | 0.18 | — | Panel efficiency at STC (0.18 = 18%) |
| `temp_coeff_power` | -0.004 | /°C | Power loss per °C above STC cell temperature |

> `pv_capacity_kw` and `area` are mutually exclusive.
> If both are provided, `pv_capacity_kw` takes precedence.

### Building Load

| Parameter | Default (Summer) | Unit | Description |
|---|---|---|---|
| `base_load` | 0.15 | kW | Night-time base load |
| `peak_load` | 2.8 | kW | Maximum building demand |
| `load_peak1_hour` | 8.0 | h | Morning demand peak hour |
| `load_peak2_hour` | 19.0 | h | Evening demand peak hour |
| `load_shape1_std` | 2.0 | h | Width of morning Gaussian peak |
| `load_shape2_std` | 2.5 | h | Width of evening Gaussian peak |

### TOU Electricity Tariff

| Parameter | Default | Unit | Description |
|---|---|---|---|
| `tou_on_peak_rate` | 4.18 | THB/kWh | On-Peak rate (weekdays 09:00–22:00) |
| `tou_off_peak_rate` | 2.60 | THB/kWh | Off-Peak rate (all other times + weekends) |
| `on_peak_start_hour` | 9.0 | h | On-Peak period start |
| `on_peak_end_hour` | 22.0 | h | On-Peak period end |

### Time Resolution

| Parameter | Default | Unit | Description |
|---|---|---|---|
| `time_resolution_mins` | 5.0 | min | Simulation time step (5 / 15 / 60 recommended) |

> **Resolution and cost accuracy:** TOU rates switch at fixed clock hours.
> Coarser resolution (e.g. 60 min) may straddle a rate-change boundary and
> underestimate cost. 5-minute resolution is recommended for financial analysis.

---

## Output Record Fields

Each time step produces one record dict with the following fields:

| Field | Type | Unit | Description |
|---|---|---|---|
| `timestamp` | `str` | — | ISO datetime (`YYYY-MM-DD HH:MM:SS`) |
| `season` | `str` | — | Season label passed to `run_season()` / `run_days()` |
| `hour` | `float` | h | Decimal hour of day (0.0–23.97) |
| `time_step_hours` | `float` | h | Duration of this time step |
| `cloud_cover` | `float` | 0–1 | Cloud cover fraction |
| `cos_zenith` | `float` | — | Cosine of solar zenith angle |
| `irradiance_wm2` | `float` | W/m² | Global Horizontal Irradiance (GHI) |
| `ambient_temp_c` | `float` | °C | Ambient air temperature |
| `wind_speed_ms` | `float` | m/s | Wind speed |
| `pv_generation_kw` | `float` | kW | PV system power output |
| `building_load_kw` | `float` | kW | Building electricity demand |
| `grid_power_kw` | `float` | kW | Power imported from grid |
| `grid_energy_kwh` | `float` | kWh | Grid energy consumed this time step |
| `tou_rate_thb` | `float` | THB/kWh | Applicable TOU electricity rate |
| `cost_thb` | `float` | THB | Electricity cost this time step |

---

## PEP 8 Compliance Note

The codebase is PEP 8 compliant with the following intentional style exceptions:

- **E221 / E241 / E272** — column-alignment spaces in parameter dicts and list
  comprehensions are retained for readability in a scientific/educational context.
- **W503** — line-break-before-binary-operator style is preferred for multi-line
  arithmetic expressions (accepted by PEP 8 since 2019).
- **E226** — whitespace around `*` and `/` in physics equations is omitted
  intentionally to group operands visually.

```bash
pycodestyle --max-line-length=100 --ignore=E221,E241,E272,W503,E226 pvsim_engine.py
```
