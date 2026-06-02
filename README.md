# G-SET PV Plant Simulation Engine

**Version:** 1.0.5 &nbsp;|&nbsp; **License:** MIT &nbsp;|&nbsp; **Python:** 3.10+

> Physics-accurate rooftop solar PV simulation engine for education and research.
> Developed by the G-SET Research Unit, Kasetsart University Sriracha Campus.
> [www.g-set.education](https://www.g-set.education)

---

## Overview

`pvsim_engine.py` simulates a rooftop PV system on a commercial building
at any geographic location. Default parameters are calibrated for
**Bangkok, Thailand (13.75°N, 100.52°E, UTC+7)**.

Every variable is computed from physical first principles at configurable
time resolution (default: 5 minutes), producing a time-series dataset
suitable for energy analysis, IoT prototyping, and hands-on teaching.

### Physics Models

| Component | Model | Reference |
|---|---|---|
| Solar irradiance | ASHRAE clear-sky (Spencer declination, Kasten–Young air mass) | ASHRAE HOF 2009 |
| Cloud cover | Mean-reverting Markov chain | — |
| Cell temperature | Faiman model | PVGIS / Faiman (2008) |
| Ambient temperature | Sinusoidal diurnal + Gaussian noise | — |
| Building load | Dual-Gaussian (Bimodal) + First-Order Low-Pass Filter | — |
| PV power output | Temperature-corrected STC efficiency | IEC 61215 |
| Electricity tariff | Time-of-Use (TOU) — On-Peak / Off-Peak | PEA Thailand (default) |

### Location Support

The solar geometry engine is fully location-aware.
Simulate any site by passing `latitude_deg`, `longitude_deg`, and
`timezone_offset_h`, or use a built-in `LocationPreset`:

| Preset key | City | Latitude | Longitude | UTC |
|---|---|---|---|---|
| `'bangkok'` | Bangkok, Thailand | 13.75°N | 100.52°E | +7 (default) |
| `'tokyo'` | Tokyo, Japan | 35.68°N | 139.69°E | +9 |
| `'london'` | London, UK | 51.51°N | 0.13°W | 0 |
| `'sydney'` | Sydney, Australia | 33.87°S | 151.21°E | +10 |
| `'dubai'` | Dubai, UAE | 25.20°N | 55.27°E | +4 |
| `'new_york'` | New York, USA | 40.71°N | 74.01°W | -5 |

> Any unlisted location can be simulated by passing coordinates directly
> in `override_params` — no preset is required.

### Building Load Presets

| Preset key | Typical use | `peak_load` | Peak hours |
|---|---|---|---|
| `'residential'` | Home / apartment | 2.0 kW | Morning + Evening |
| `'office'` | Commercial office | 3.0 kW | Business hours only |
| `'retail'` | Shop / mall | 4.0 kW | All-day + evening surge |
| `'factory'` | Industrial / 2-shift | 8.0 kW | Narrow shift peaks |

### Three-Season Presets (Bangkok default)

| Season | Key | Period | `cloud_mean` | `temp_base_c` | `wind_speed_mean_ms` |
|---|---|---|---|---|---|
| Hot-Dry | `'summer'` | Mar–May | 0.20 | 33.0 °C | 1.8 m/s |
| Monsoon | `'rainy'` | Jun–Oct | 0.70 | 30.5 °C | 3.5 m/s |
| Cool-Dry | `'winter'` | Nov–Feb | 0.15 | 26.5 °C | 3.0 m/s |

---

## Quick Start (Google Colab)

```python
# Step 1 — load engine
!wget -q -O pvsim_engine.py https://raw.githubusercontent.com/YOUR-USERNAME/pviot-workshop/main/pvsim_engine.py
%run pvsim_engine.py

# Step 2 — fix random seed for reproducibility
set_seed(42)

# Step 3 — simulate (Bangkok default)
data = run_season('summer')
plot_single_season(data, 'summer')
print_financial_summary('summer', data)
```

### With location and building type

```python
# Office building in Tokyo
set_seed(42)
data = run_season('summer',
                  location='tokyo',
                  building_type='office',
                  temp_base_c=28.0)

# Factory in London — custom coordinates
set_seed(42)
data = run_days('winter', n_days=14,
                latitude_deg=51.51,
                longitude_deg=-0.13,
                timezone_offset_h=0.0,
                building_type='factory',
                temp_base_c=8.0,
                cloud_mean=0.65)

# Adjust figure size in Colab
import matplotlib.pyplot as plt
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['figure.dpi'] = 80
```

### Parameter override

```python
override_params = {
    # location
    # 'location'            : 'tokyo',

    # building
    # 'building_type'       : 'office',

    # cloud
    # 'cloud_mean'          : 0.50,

    # temperature
    # 'temp_base_c'         : 30.0,

    # PV panel
    'pv_capacity_kw'        : 5.0,    # auto-derives area
    # 'eta_stc'             : 0.22,   # premium panel

    # tariff
    # 'tou_on_peak_rate'    : 4.18,
}

set_seed(42)
data = run_season('summer', **override_params)
```

---

## Key Functions

| Function | Description |
|---|---|
| `set_seed(seed)` | Fix random seed for reproducibility |
| `run_season(season, **kw)` | Simulate one representative day |
| `run_days(season, n_days, **kw)` | Simulate multiple consecutive days |
| `get_financial_summary(season, data)` | Return energy/cost summary as dict |
| `print_financial_summary(season, data)` | Print formatted summary |
| `save_simulation_to_csv(data, filename)` | Export to CSV |
| `plot_single_season(data, season)` | 4-panel season chart |
| `plot_season_comparison(dict)` | Three-season overlay chart |

For full parameter tables and class references, see **[api_reference.md](api_reference.md)**.

---

## Citation
If you use this software in your research, please cite it as below.

```bibtex
@misc{pvsim-engine2026,
  author = {Kullawadee Somboonviwat and Umarin Sangpanich},
  title = {{pvsim-engine}: Physics-accurate rooftop solar {PV} simulation engine for education and research},
  year = {2026},
  publisher = {GitHub},
  howpublished = {\url{https://github.com/kullawadee-ku/pvsim-engine}}
}
```
---

## Creator

**Kullawadee Somboonviwat, Ph.D.**
[kullawadee.som@ku.th](mailto:kullawadee.som@ku.th)
[![ORCID](https://img.shields.io/badge/ORCID-0000--0003--3618--8562-A6CE39?logo=orcid&logoColor=white)](https://orcid.org/0000-0003-3618-8562)
[![Google Scholar](https://img.shields.io/badge/Google%20Scholar-Profile-4285F4?logo=google-scholar&logoColor=white)](https://scholar.google.com/citations?hl=th&user=DqIZWSgAAAAJ)

G-SET Research Unit
Faculty of Engineering at Sriracha, Kasetsart University
[www.g-set.education](https://www.g-set.education)

---

*MIT License — see LICENSE file for details.*
