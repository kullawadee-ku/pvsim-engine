# =====================================================================
# test_pvsim_engine.py  —  Unit Tests for PV-IoT Simulation Engine
#
# Kullawadee Somboonviwat (kullawadee.som@ku.th)
#
# G-SET Research Unit
# Faculty of Engineering at Sriracha, Kasetsart University
#
# https://www.g-set.education
# Version : 1.0.2a
# License : MIT
# =====================================================================
"""
Run all tests:
    python -m pytest test_pvsim_engine.py -v

Run a specific class:
    python -m pytest test_pvsim_engine.py::TestSeasonPreset -v

Run with coverage:
    pip install pytest-cov
    python -m pytest test_pvsim_engine.py --cov=pvsim_engine --cov-report=term-missing
"""
import csv
import matplotlib.pyplot as plt
from unittest.mock import patch
import math
import os
import random
import tempfile
import unittest
from datetime import datetime, timedelta

import pvsim_engine as eng


# =====================================================================
# Helpers
# =====================================================================
def make_engine(**overrides) -> eng.TelemetryGenerator:
    """Create a TelemetryGenerator with summer defaults + any overrides."""
    params = eng.SeasonPreset.get('summer')
    params.update(overrides)
    return eng.TelemetryGenerator(**params)


def make_dataset(season='summer', n_days=1, **overrides) -> list:
    """Run a short simulation and return the dataset."""
    random.seed(42)
    if n_days == 1:
        return eng.run_season(season, **overrides)
    return eng.run_days(season, n_days=n_days, **overrides)


# =====================================================================
# 1. SeasonPreset
# =====================================================================
class TestSeasonPreset(unittest.TestCase):

    def test_list_seasons_returns_three(self):
        seasons = eng.SeasonPreset.list_seasons()
        self.assertEqual(len(seasons), 3)
        self.assertIn('summer', seasons)
        self.assertIn('rainy',  seasons)
        self.assertIn('winter', seasons)

    def test_get_returns_dict_with_required_keys(self):
        required = [
            'latitude_deg', 'longitude_deg', 'timezone_offset_h',
            'temp_base_c', 'cloud_mean', 'eta_stc', 'area',
            'tou_on_peak_rate', 'tou_off_peak_rate',
        ]
        for season in eng.SeasonPreset.list_seasons():
            params = eng.SeasonPreset.get(season)
            for key in required:
                self.assertIn(key, params, f"Missing '{key}' in {season} preset")

    def test_get_returns_independent_copy(self):
        """Mutating the returned dict must not affect the class."""
        p1 = eng.SeasonPreset.get('summer')
        p2 = eng.SeasonPreset.get('summer')
        p1['temp_base_c'] = 9999.0
        self.assertNotEqual(p2['temp_base_c'], 9999.0)

    def test_get_invalid_season_raises_value_error(self):
        with self.assertRaises(ValueError):
            eng.SeasonPreset.get('monsoon')

    def test_reference_dates_are_weekdays(self):
        """All reference dates must be Mon–Fri so On-Peak TOU applies."""
        for season in eng.SeasonPreset.list_seasons():
            ref = eng.SeasonPreset.get_reference_date(season)
            self.assertLess(
                ref.weekday(), 5,
                f"{season} reference date {ref.date()} falls on a weekend"
            )

    def test_summer_hotter_than_winter(self):
        s = eng.SeasonPreset.get('summer')
        w = eng.SeasonPreset.get('winter')
        self.assertGreater(s['temp_base_c'], w['temp_base_c'])

    def test_rainy_cloudier_than_summer(self):
        r = eng.SeasonPreset.get('rainy')
        s = eng.SeasonPreset.get('summer')
        self.assertGreater(r['cloud_mean'], s['cloud_mean'])

    def test_winter_least_cloudy(self):
        w = eng.SeasonPreset.get('winter')
        s = eng.SeasonPreset.get('summer')
        r = eng.SeasonPreset.get('rainy')
        self.assertLess(w['cloud_mean'], s['cloud_mean'])
        self.assertLess(w['cloud_mean'], r['cloud_mean'])


# =====================================================================
# 2. LocationPreset
# =====================================================================
class TestLocationPreset(unittest.TestCase):

    def test_list_locations_not_empty(self):
        locations = eng.LocationPreset.list_locations()
        self.assertGreater(len(locations), 0)
        self.assertIn('bangkok', locations)

    def test_get_returns_three_keys(self):
        for loc in eng.LocationPreset.list_locations():
            p = eng.LocationPreset.get(loc)
            self.assertIn('latitude_deg',      p)
            self.assertIn('longitude_deg',     p)
            self.assertIn('timezone_offset_h', p)

    def test_get_returns_independent_copy(self):
        p1 = eng.LocationPreset.get('bangkok')
        p2 = eng.LocationPreset.get('bangkok')
        p1['latitude_deg'] = 0.0
        self.assertNotEqual(p2['latitude_deg'], 0.0)

    def test_invalid_location_raises_value_error(self):
        with self.assertRaises(ValueError):
            eng.LocationPreset.get('atlantis')

    def test_sydney_southern_hemisphere(self):
        p = eng.LocationPreset.get('sydney')
        self.assertLess(p['latitude_deg'], 0.0)

    def test_new_york_negative_timezone(self):
        p = eng.LocationPreset.get('new_york')
        self.assertLess(p['timezone_offset_h'], 0.0)

    def test_bangkok_defaults_match_season_preset_base(self):
        """LocationPreset bangkok must match SeasonPreset._BASE location."""
        loc = eng.LocationPreset.get('bangkok')
        base = eng.SeasonPreset._BASE
        self.assertAlmostEqual(loc['latitude_deg'],      base['latitude_deg'],      places=2)
        self.assertAlmostEqual(loc['longitude_deg'],     base['longitude_deg'],     places=2)
        self.assertAlmostEqual(loc['timezone_offset_h'], base['timezone_offset_h'], places=1)


# =====================================================================
# 3. BuildingPreset
# =====================================================================
class TestBuildingPreset(unittest.TestCase):

    REQUIRED_KEYS = [
        'base_load', 'peak_load',
        'load_peak1_hour', 'load_peak2_hour',
        'load_shape1_std', 'load_shape2_std',
    ]

    def test_list_types_contains_expected(self):
        types = eng.BuildingPreset.list_types()
        for t in ('residential', 'office', 'retail', 'factory'):
            self.assertIn(t, types)

    def test_get_returns_required_keys(self):
        for btype in eng.BuildingPreset.list_types():
            p = eng.BuildingPreset.get(btype)
            for key in self.REQUIRED_KEYS:
                self.assertIn(key, p, f"Missing '{key}' in {btype} preset")

    def test_get_returns_independent_copy(self):
        p1 = eng.BuildingPreset.get('office')
        p2 = eng.BuildingPreset.get('office')
        p1['peak_load'] = 9999.0
        self.assertNotEqual(p2['peak_load'], 9999.0)

    def test_invalid_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            eng.BuildingPreset.get('warehouse')

    def test_factory_highest_base_load(self):
        loads = {t: eng.BuildingPreset.get(t)['base_load']
                 for t in eng.BuildingPreset.list_types()}
        self.assertEqual(max(loads, key=loads.get), 'factory')

    def test_factory_highest_peak_load(self):
        loads = {t: eng.BuildingPreset.get(t)['peak_load']
                 for t in eng.BuildingPreset.list_types()}
        self.assertEqual(max(loads, key=loads.get), 'factory')

    def test_peak_load_greater_than_base_load(self):
        for btype in eng.BuildingPreset.list_types():
            p = eng.BuildingPreset.get(btype)
            self.assertGreater(
                p['peak_load'], p['base_load'],
                f"{btype}: peak_load must exceed base_load"
            )


# =====================================================================
# 4. TelemetryGenerator — solar geometry
# =====================================================================
class TestSolarGeometry(unittest.TestCase):

    def setUp(self):
        self.gen = make_engine()

    def test_midnight_zero_irradiance(self):
        midnight = datetime(2026, 4, 15, 0, 0)
        geo = self.gen._solar_geometry(midnight)
        self.assertEqual(geo['ghi_wm2'], 0.0)
        self.assertEqual(geo['cos_zenith'], 0.0)

    def test_solar_noon_positive_irradiance(self):
        noon = datetime(2026, 4, 15, 12, 0)
        geo = self.gen._solar_geometry(noon)
        self.assertGreater(geo['ghi_wm2'], 0.0)
        self.assertGreater(geo['cos_zenith'], 0.0)

    def test_ghi_equals_beam_plus_diffuse(self):
        noon = datetime(2026, 4, 15, 12, 0)
        geo = self.gen._solar_geometry(noon)
        self.assertAlmostEqual(
            geo['ghi_wm2'],
            geo['beam_wm2'] + geo['diffuse_wm2'],
            places=3
        )

    def test_cos_zenith_bounded_0_to_1(self):
        for hour in range(0, 24):
            dt = datetime(2026, 4, 15, hour, 0)
            geo = self.gen._solar_geometry(dt)
            self.assertGreaterEqual(geo['cos_zenith'], 0.0)
            self.assertLessEqual(geo['cos_zenith'], 1.0)

    def test_irradiance_never_negative(self):
        for hour in range(0, 24):
            dt = datetime(2026, 4, 15, hour, 0)
            geo = self.gen._solar_geometry(dt)
            self.assertGreaterEqual(geo['ghi_wm2'], 0.0)
            self.assertGreaterEqual(geo['beam_wm2'], 0.0)
            self.assertGreaterEqual(geo['diffuse_wm2'], 0.0)

    def test_summer_noon_higher_ghi_than_winter(self):
        """Bangkok summer noon should be brighter than winter noon."""
        gen_s = make_engine(**eng.SeasonPreset.get('summer'))
        gen_w = make_engine(**eng.SeasonPreset.get('winter'))
        noon_s = datetime(2026, 4, 15, 12, 0)
        noon_w = datetime(2026, 1, 21, 12, 0)
        ghi_s = gen_s._solar_geometry(noon_s)['ghi_wm2']
        ghi_w = gen_w._solar_geometry(noon_w)['ghi_wm2']
        self.assertGreater(ghi_s, ghi_w)

    def test_location_affects_ghi(self):
        """London (51°N) should produce less noon GHI than Bangkok (13°N) in summer."""
        gen_bkk = make_engine(latitude_deg=13.75, longitude_deg=100.52, timezone_offset_h=7.0)
        gen_lon = make_engine(latitude_deg=51.51, longitude_deg=-0.13,  timezone_offset_h=0.0)
        noon_bkk = datetime(2026, 4, 15, 12, 0)
        noon_lon = datetime(2026, 4, 15, 12, 0)
        ghi_bkk = gen_bkk._solar_geometry(noon_bkk)['ghi_wm2']
        ghi_lon = gen_lon._solar_geometry(noon_lon)['ghi_wm2']
        self.assertGreater(ghi_bkk, ghi_lon)


# =====================================================================
# 5. TelemetryGenerator — cloud model
# =====================================================================
class TestCloudModel(unittest.TestCase):

    def test_cloud_cover_stays_in_0_1(self):
        gen = make_engine(cloud_cover_init=0.5, cloud_noise_std=2.0)
        for _ in range(1000):
            gen._update_cloud_cover()
            self.assertGreaterEqual(gen.cloud_cover, 0.0)
            self.assertLessEqual(gen.cloud_cover, 1.0)

    def test_mean_reversion(self):
        """With high persistence and forced starting point, cloud should drift toward mean."""
        gen = make_engine(cloud_cover_init=0.0, cloud_mean=0.8,
                          cloud_persistence=0.5, cloud_noise_std=0.0)
        for _ in range(50):
            gen._update_cloud_cover()
        self.assertGreater(gen.cloud_cover, 0.3)

    def test_full_overcast_reduces_irradiance(self):
        gen = make_engine(cloud_cover_init=0.99)
        gen.cloud_cover = 0.99
        reduced = gen._apply_cloud_to_irradiance(800.0, 100.0)
        self.assertLess(reduced, 300.0)

    def test_clear_sky_preserves_irradiance(self):
        gen = make_engine(cloud_cover_init=0.0)
        gen.cloud_cover = 0.01
        preserved = gen._apply_cloud_to_irradiance(800.0, 100.0)
        self.assertGreater(preserved, 700.0)

    def test_apply_cloud_never_negative(self):
        gen = make_engine()
        for cloud in [0.0, 0.3, 0.7, 1.0]:
            gen.cloud_cover = cloud
            result = gen._apply_cloud_to_irradiance(500.0, 80.0)
            self.assertGreaterEqual(result, 0.0)


# =====================================================================
# 6. TelemetryGenerator — cell temperature (Faiman model)
# =====================================================================
class TestCellTemperature(unittest.TestCase):

    def setUp(self):
        self.gen = make_engine()

    def test_zero_irradiance_returns_ambient(self):
        self.assertEqual(self.gen._cell_temperature(0.0, 30.0, 2.0), 30.0)

    def test_cell_hotter_than_ambient_under_irradiance(self):
        t_cell = self.gen._cell_temperature(800.0, 30.0, 2.0)
        self.assertGreater(t_cell, 30.0)

    def test_wind_cools_cell(self):
        t_calm  = self.gen._cell_temperature(800.0, 30.0, wind=0.5)
        t_windy = self.gen._cell_temperature(800.0, 30.0, wind=8.0)
        self.assertGreater(t_calm, t_windy)

    def test_more_irradiance_means_hotter_cell(self):
        t_low  = self.gen._cell_temperature(200.0, 30.0, 2.0)
        t_high = self.gen._cell_temperature(900.0, 30.0, 2.0)
        self.assertGreater(t_high, t_low)


# =====================================================================
# 7. TelemetryGenerator — PV power output
# =====================================================================
class TestPVPower(unittest.TestCase):

    def setUp(self):
        self.gen = make_engine()

    def test_zero_irradiance_zero_power(self):
        self.assertEqual(self.gen.calculate_solar_pv(0.0, 30.0, 2.0), 0.0)

    def test_below_threshold_zero_power(self):
        # threshold is min_irradiance_threshold_wm2 = 10 W/m²
        self.assertEqual(self.gen.calculate_solar_pv(5.0, 30.0, 2.0), 0.0)

    def test_positive_irradiance_positive_power(self):
        pv = self.gen.calculate_solar_pv(800.0, 30.0, 2.0)
        self.assertGreater(pv, 0.0)

    def test_power_never_negative(self):
        for irr in [0, 5, 50, 500, 1000]:
            pv = self.gen.calculate_solar_pv(irr, 35.0, 2.0)
            self.assertGreaterEqual(pv, 0.0)

    def test_higher_irradiance_more_power(self):
        pv_low  = self.gen.calculate_solar_pv(200.0, 30.0, 2.0)
        pv_high = self.gen.calculate_solar_pv(800.0, 30.0, 2.0)
        self.assertGreater(pv_high, pv_low)

    def test_thermal_derating_at_high_temperature(self):
        """Hot cell should produce less power than cool cell at same irradiance."""
        pv_cool = self.gen.calculate_solar_pv(800.0, t_amb=15.0, wind=2.0)
        pv_hot  = self.gen.calculate_solar_pv(800.0, t_amb=40.0, wind=2.0)
        self.assertGreater(pv_cool, pv_hot)

    def test_pv_capacity_kw_doubles_power(self):
        """Doubling pv_capacity_kw should double power output."""
        gen_5kw  = make_engine(pv_capacity_kw=5.0)
        gen_10kw = make_engine(pv_capacity_kw=10.0)
        pv_5  = gen_5kw.calculate_solar_pv(800.0, 30.0, 2.0)
        pv_10 = gen_10kw.calculate_solar_pv(800.0, 30.0, 2.0)
        self.assertAlmostEqual(pv_10 / pv_5, 2.0, places=1)

    def test_pv_capacity_kw_derives_area(self):
        gen = make_engine(eta_stc=0.18, pv_capacity_kw=5.0)
        expected_area = 5.0 / 0.18
        self.assertAlmostEqual(gen.area, expected_area, places=3)

    def test_area_used_when_capacity_not_set(self):
        gen = make_engine(area=30.0)
        self.assertAlmostEqual(gen.area, 30.0, places=3)


# =====================================================================
# 8. TelemetryGenerator — building load
# =====================================================================
class TestBuildingLoad(unittest.TestCase):

    def test_load_never_below_base(self):
        gen = make_engine(base_load=0.1, load_noise_std_kw=0.0)
        for hour in [h * 0.5 for h in range(48)]:
            load = gen.calculate_building_load(hour)
            self.assertGreaterEqual(load, gen.base_load - 1e-9)

    def test_load_positive(self):
        gen = make_engine()
        random.seed(0)
        for hour in range(24):
            load = gen.calculate_building_load(float(hour))
            self.assertGreater(load, 0.0)

    def test_lpf_smoothing_limits_step_change(self):
        """LPF means load cannot jump from base to peak in one step."""
        gen = make_engine(base_load=0.1, peak_load=10.0, load_lpf_alpha=0.9,
                          load_noise_std_kw=0.0)
        gen.last_building_load = gen.base_load
        load_t1 = gen.calculate_building_load(8.0)   # peak hour
        # With alpha=0.9, smoothed = 0.9*0.1 + 0.1*target << target
        self.assertLess(load_t1, 5.0)


# =====================================================================
# 9. TelemetryGenerator — TOU tariff
# =====================================================================
class TestTOURate(unittest.TestCase):

    def setUp(self):
        self.gen = make_engine()

    def test_weekday_on_peak_hours(self):
        # Wednesday 12:00 — should be on-peak
        dt = datetime(2026, 4, 15, 12, 0)   # Wednesday
        self.assertEqual(self.gen.get_tou_rate(dt), self.gen.tou_on_peak_rate)

    def test_weekday_off_peak_early_morning(self):
        # Wednesday 06:00 — before on-peak window
        dt = datetime(2026, 4, 15, 6, 0)
        self.assertEqual(self.gen.get_tou_rate(dt), self.gen.tou_off_peak_rate)

    def test_weekend_always_off_peak(self):
        # Saturday noon
        dt = datetime(2026, 4, 18, 12, 0)   # Saturday
        self.assertEqual(self.gen.get_tou_rate(dt), self.gen.tou_off_peak_rate)

    def test_sunday_always_off_peak(self):
        dt = datetime(2026, 4, 19, 15, 0)   # Sunday
        self.assertEqual(self.gen.get_tou_rate(dt), self.gen.tou_off_peak_rate)

    def test_on_peak_rate_greater_than_off_peak(self):
        self.assertGreater(self.gen.tou_on_peak_rate, self.gen.tou_off_peak_rate)

    def test_boundary_on_peak_start(self):
        # Exactly at on_peak_start_hour (09:00) should be on-peak
        dt = datetime(2026, 4, 15, 9, 0)
        self.assertEqual(self.gen.get_tou_rate(dt), self.gen.tou_on_peak_rate)

    def test_boundary_off_peak_end(self):
        # Exactly at on_peak_end_hour (22:00) should be off-peak
        dt = datetime(2026, 4, 15, 22, 0)
        self.assertEqual(self.gen.get_tou_rate(dt), self.gen.tou_off_peak_rate)


# =====================================================================
# 10. TelemetryGenerator — grid interaction
# =====================================================================
class TestGridInteraction(unittest.TestCase):

    def setUp(self):
        self.gen = make_engine(time_resolution_mins=60.0)

    def test_no_grid_when_pv_exceeds_load(self):
        result = self.gen.calculate_grid_interaction(pv=3.0, load=1.0, tou=4.18)
        self.assertEqual(result['grid_power_kw'], 0.0)
        self.assertEqual(result['grid_energy_kwh'], 0.0)
        self.assertEqual(result['cost_thb'], 0.0)

    def test_grid_import_when_load_exceeds_pv(self):
        result = self.gen.calculate_grid_interaction(pv=1.0, load=3.0, tou=4.18)
        self.assertEqual(result['grid_power_kw'], 2.0)

    def test_energy_equals_power_times_time_step(self):
        gen_5min  = make_engine(time_resolution_mins=5.0)
        gen_60min = make_engine(time_resolution_mins=60.0)
        r5  = gen_5min.calculate_grid_interaction(0.0, 2.0, 4.18)
        r60 = gen_60min.calculate_grid_interaction(0.0, 2.0, 4.18)
        # Engine rounds grid_energy_kwh to 3 decimal places, so use places=3
        self.assertAlmostEqual(r5['grid_energy_kwh'],  round(2.0 * (5/60),  3), places=3)
        self.assertAlmostEqual(r60['grid_energy_kwh'], round(2.0 * (60/60), 3), places=3)

    def test_cost_equals_energy_times_rate(self):
        result = self.gen.calculate_grid_interaction(pv=0.0, load=2.0, tou=4.18)
        expected_cost = result['grid_energy_kwh'] * 4.18
        self.assertAlmostEqual(result['cost_thb'], expected_cost, places=3)

    def test_grid_power_never_negative(self):
        for pv, load in [(5.0, 1.0), (0.0, 0.0), (1.0, 1.0)]:
            result = self.gen.calculate_grid_interaction(pv, load, 4.18)
            self.assertGreaterEqual(result['grid_power_kw'], 0.0)


# =====================================================================
# 11. simulate_time_range
# =====================================================================
class TestSimulateTimeRange(unittest.TestCase):

    def test_record_count_matches_resolution(self):
        gen = make_engine(time_resolution_mins=60.0)
        start = datetime(2026, 4, 15, 0, 0)
        end   = datetime(2026, 4, 15, 23, 0)
        data  = eng.simulate_time_range(gen, start, end)
        self.assertEqual(len(data), 24)

    def test_record_count_5min_resolution(self):
        gen = make_engine(time_resolution_mins=5.0)
        start = datetime(2026, 4, 15, 0, 0)
        end   = datetime(2026, 4, 15, 23, 55)
        data  = eng.simulate_time_range(gen, start, end)
        self.assertEqual(len(data), 288)

    def test_all_required_fields_present(self):
        required = [
            'timestamp', 'season', 'hour', 'time_step_hours',
            'cloud_cover', 'cos_zenith', 'irradiance_wm2', 'ambient_temp_c',
            'wind_speed_ms', 'pv_generation_kw', 'building_load_kw',
            'grid_power_kw', 'grid_energy_kwh', 'tou_rate_thb', 'cost_thb',
        ]
        gen  = make_engine(time_resolution_mins=60.0)
        data = eng.simulate_time_range(gen, datetime(2026, 4, 15, 0, 0),
                                       datetime(2026, 4, 15, 1, 0))
        for field in required:
            self.assertIn(field, data[0], f"Field '{field}' missing from record")

    def test_timestamps_sequential(self):
        gen  = make_engine(time_resolution_mins=60.0)
        data = eng.simulate_time_range(gen, datetime(2026, 4, 15, 0, 0),
                                       datetime(2026, 4, 15, 5, 0))
        timestamps = [d['timestamp'] for d in data]
        self.assertEqual(timestamps, sorted(timestamps))

    def test_irradiance_zero_at_night(self):
        gen  = make_engine(time_resolution_mins=60.0)
        data = eng.simulate_time_range(gen, datetime(2026, 4, 15, 0, 0),
                                       datetime(2026, 4, 15, 4, 0))
        for record in data:
            self.assertEqual(record['irradiance_wm2'], 0.0,
                             f"Expected 0 irradiance at {record['timestamp']}")

    def test_pv_zero_when_irradiance_below_threshold(self):
        gen  = make_engine(time_resolution_mins=60.0)
        data = eng.simulate_time_range(gen, datetime(2026, 4, 15, 0, 0),
                                       datetime(2026, 4, 15, 4, 0))
        for record in data:
            self.assertEqual(record['pv_generation_kw'], 0.0)

    def test_grid_power_equals_load_minus_pv(self):
        gen  = make_engine(time_resolution_mins=60.0)
        data = eng.simulate_time_range(gen, datetime(2026, 4, 15, 8, 0),
                                       datetime(2026, 4, 15, 14, 0))
        for record in data:
            expected = max(0.0, record['building_load_kw'] - record['pv_generation_kw'])
            self.assertAlmostEqual(
                record['grid_power_kw'], expected, places=2,
                msg=f"grid_power mismatch at {record['timestamp']}"
            )

    def test_time_step_hours_matches_resolution(self):
        for mins in [5.0, 15.0, 60.0]:
            gen  = make_engine(time_resolution_mins=mins)
            data = eng.simulate_time_range(gen, datetime(2026, 4, 15, 0, 0),
                                           datetime(2026, 4, 15, 1, 0))
            for record in data:
                self.assertAlmostEqual(
                    record['time_step_hours'], mins / 60.0, places=5
                )

    def test_cost_equals_energy_times_tou(self):
        gen  = make_engine(time_resolution_mins=60.0)
        data = eng.simulate_time_range(gen, datetime(2026, 4, 15, 10, 0),
                                       datetime(2026, 4, 15, 14, 0))
        for record in data:
            expected = round(record['grid_energy_kwh'] * record['tou_rate_thb'], 3)
            self.assertAlmostEqual(record['cost_thb'], expected, places=3)


# =====================================================================
# 12. set_seed — reproducibility
# =====================================================================
class TestSetSeed(unittest.TestCase):

    def test_same_seed_same_results(self):
        eng.set_seed(42)
        data1 = eng.run_season('summer')
        eng.set_seed(42)
        data2 = eng.run_season('summer')
        self.assertEqual(len(data1), len(data2))
        for r1, r2 in zip(data1, data2):
            self.assertEqual(r1['irradiance_wm2'],   r2['irradiance_wm2'])
            self.assertEqual(r1['pv_generation_kw'], r2['pv_generation_kw'])
            self.assertEqual(r1['cost_thb'],         r2['cost_thb'])

    def test_different_seeds_different_results(self):
        eng.set_seed(1)
        data1 = eng.run_season('summer')
        eng.set_seed(999)
        data2 = eng.run_season('summer')
        irr1 = [d['irradiance_wm2'] for d in data1]
        irr2 = [d['irradiance_wm2'] for d in data2]
        self.assertNotEqual(irr1, irr2)


# =====================================================================
# 13. run_season
# =====================================================================
class TestRunSeason(unittest.TestCase):

    def test_returns_list(self):
        eng.set_seed(42)
        data = eng.run_season('summer')
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_default_288_records_5min(self):
        eng.set_seed(42)
        data = eng.run_season('summer')
        self.assertEqual(len(data), 288)   # 24h × 12 per hour

    def test_resolution_override_via_override_params(self):
        eng.set_seed(42)
        data = eng.run_season('summer', time_resolution_mins=60)
        self.assertEqual(len(data), 24)

    def test_resolution_60_via_override_params_dict(self):
        eng.set_seed(42)
        data = eng.run_season('summer', **{'time_resolution_mins': 60})
        self.assertEqual(len(data), 24)

    def test_last_timestamp_depends_on_resolution(self):
        eng.set_seed(42)
        data5  = eng.run_season('summer', time_resolution_mins=5)
        data60 = eng.run_season('summer', time_resolution_mins=60)
        self.assertTrue(data5[-1]['timestamp'].endswith('23:55:00'))
        self.assertTrue(data60[-1]['timestamp'].endswith('23:00:00'))

    def test_invalid_season_raises_value_error(self):
        with self.assertRaises(ValueError):
            eng.run_season('spring')

    def test_force_weekday_true_default(self):
        """Reference date must be a weekday when force_weekday=True."""
        eng.set_seed(42)
        data = eng.run_season('rainy')
        ts = datetime.strptime(data[0]['timestamp'], '%Y-%m-%d %H:%M:%S')
        self.assertLess(ts.weekday(), 5)

    def test_override_cloud_mean(self):
        """cloud_mean=0.0 should allow higher irradiance than cloud_mean=0.9."""
        eng.set_seed(42)
        data_clear = eng.run_season('summer', cloud_mean=0.02)
        eng.set_seed(42)
        data_cloudy = eng.run_season('summer', cloud_mean=0.95)
        max_irr_clear  = max(d['irradiance_wm2'] for d in data_clear)
        max_irr_cloudy = max(d['irradiance_wm2'] for d in data_cloudy)
        self.assertGreater(max_irr_clear, max_irr_cloudy)

    def test_building_type_office_applied(self):
        eng.set_seed(42)
        data_office = eng.run_season('summer', building_type='office')
        data_factory = eng.run_season('summer', building_type='factory')
        max_load_office  = max(d['building_load_kw'] for d in data_office)
        max_load_factory = max(d['building_load_kw'] for d in data_factory)
        self.assertGreater(max_load_factory, max_load_office)

    def test_location_preset_applied(self):
        """London (higher latitude) should have lower noon GHI than Bangkok."""
        eng.set_seed(42)
        data_bkk = eng.run_season('summer')
        eng.set_seed(42)
        data_lon = eng.run_season('summer', location='london',
                                  temp_base_c=20.0, cloud_mean=0.4)
        noon_bkk = next(d for d in data_bkk if d['hour'] == 12.0)
        noon_lon = next(d for d in data_lon if d['hour'] == 12.0)
        self.assertGreater(noon_bkk['irradiance_wm2'], noon_lon['irradiance_wm2'])

    def test_pv_capacity_doubles_generation(self):
        eng.set_seed(42)
        data5  = eng.run_season('summer', pv_capacity_kw=5.0)
        eng.set_seed(42)
        data10 = eng.run_season('summer', pv_capacity_kw=10.0)
        pv5  = sum(d['pv_generation_kw'] for d in data5)
        pv10 = sum(d['pv_generation_kw'] for d in data10)
        self.assertAlmostEqual(pv10 / pv5, 2.0, places=1)


# =====================================================================
# 14. run_days
# =====================================================================
class TestRunDays(unittest.TestCase):

    def test_correct_record_count_7_days(self):
        eng.set_seed(42)
        data = eng.run_days('summer', n_days=7)
        self.assertEqual(len(data), 7 * 288)   # 7 days × 288 per day at 5 min

    def test_custom_start_date(self):
        eng.set_seed(42)
        start = datetime(2026, 6, 1)
        data  = eng.run_days('summer', n_days=3, start_date=start)
        self.assertTrue(data[0]['timestamp'].startswith('2026-06-01'))

    def test_weekday_tou_rate_on_monday(self):
        """Monday noon must use on-peak rate."""
        eng.set_seed(42)
        start = datetime(2026, 4, 13)   # Monday
        data  = eng.run_days('summer', n_days=1, start_date=start)
        noon_records = [d for d in data if d['hour'] == 12.0]
        for rec in noon_records:
            self.assertEqual(rec['tou_rate_thb'], 4.18)

    def test_weekend_tou_rate_on_saturday(self):
        """Saturday noon must use off-peak rate."""
        eng.set_seed(42)
        start = datetime(2026, 4, 18)   # Saturday
        data  = eng.run_days('summer', n_days=1, start_date=start)
        noon_records = [d for d in data if d['hour'] == 12.0]
        for rec in noon_records:
            self.assertEqual(rec['tou_rate_thb'], 2.60)

    def test_resolution_override_in_override_params(self):
        eng.set_seed(42)
        data = eng.run_days('summer', n_days=1, **{'time_resolution_mins': 60})
        self.assertEqual(len(data), 24)

    def test_cloud_continuity_across_days(self):
        """Cloud cover at end of day 1 should differ slightly from start — not reset."""
        eng.set_seed(42)
        data = eng.run_days('summer', n_days=2)
        # End of day 1 (record 287) and start of day 2 (record 288)
        cc_end_d1   = data[287]['cloud_cover']
        cc_start_d2 = data[288]['cloud_cover']
        # They should be close (same Markov chain) but not identical
        self.assertAlmostEqual(cc_end_d1, cc_start_d2, delta=0.3)


# =====================================================================
# 15. get_financial_summary
# =====================================================================
class TestGetFinancialSummary(unittest.TestCase):

    def setUp(self):
        eng.set_seed(42)
        self.data = eng.run_season('summer')

    def test_returns_dict_with_required_keys(self):
        keys = ['season', 'avg_irradiance_wm2', 'avg_temp_c', 'peak_pv_kw',
                'total_pv_kwh', 'total_grid_kwh', 'total_cost_thb']
        summary = eng.get_financial_summary('summer', self.data)
        for key in keys:
            self.assertIn(key, summary)

    def test_values_are_non_negative(self):
        summary = eng.get_financial_summary('summer', self.data)
        for key, val in summary.items():
            if key != 'season':
                self.assertGreaterEqual(val, 0.0, f"'{key}' should be >= 0")

    def test_total_pv_kwh_uses_time_step(self):
        """total_pv_kwh must use time_step_hours, not a hardcoded 5/60."""
        eng.set_seed(42)
        data5  = eng.run_season('summer', time_resolution_mins=5)
        eng.set_seed(42)
        data60 = eng.run_season('summer', time_resolution_mins=60)
        s5  = eng.get_financial_summary('s5',  data5)
        s60 = eng.get_financial_summary('s60', data60)
        # Both should give similar total PV (within ~5% due to resolution difference)
        ratio = s5['total_pv_kwh'] / s60['total_pv_kwh']
        self.assertAlmostEqual(ratio, 1.0, delta=0.08)

    def test_season_label_preserved(self):
        summary = eng.get_financial_summary('my_test', self.data)
        self.assertEqual(summary['season'], 'my_test')

    def test_cost_ordering_summer_gt_rainy_gt_winter(self):
        eng.set_seed(42); s = eng.get_financial_summary('summer', eng.run_season('summer'))
        eng.set_seed(42); r = eng.get_financial_summary('rainy',  eng.run_season('rainy'))
        eng.set_seed(42); w = eng.get_financial_summary('winter', eng.run_season('winter'))
        self.assertGreater(s['total_cost_thb'], r['total_cost_thb'])
        self.assertGreater(r['total_cost_thb'], w['total_cost_thb'])

    def test_peak_pv_leq_sum_pv(self):
        """Peak per-slot PV should not exceed total generation."""
        summary = eng.get_financial_summary('summer', self.data)
        self.assertLessEqual(summary['peak_pv_kw'], summary['total_pv_kwh'])


# =====================================================================
# 16. save_simulation_to_csv
# =====================================================================
class TestSaveCSV(unittest.TestCase):

    def test_csv_created_and_readable(self):
        eng.set_seed(42)
        data = eng.run_season('summer', time_resolution_mins=60)
        with tempfile.NamedTemporaryFile(
                mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            fname = f.name
        try:
            eng.save_simulation_to_csv(data, fname)
            self.assertTrue(os.path.exists(fname))
            with open(fname, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 24)
        finally:
            os.unlink(fname)

    def test_csv_has_correct_headers(self):
        eng.set_seed(42)
        data = eng.run_season('summer', time_resolution_mins=60)
        with tempfile.NamedTemporaryFile(
                mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            fname = f.name
        try:
            eng.save_simulation_to_csv(data, fname)
            with open(fname, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
            for key in data[0].keys():
                self.assertIn(key, headers)
        finally:
            os.unlink(fname)

    def test_empty_dataset_does_not_raise(self):
        """save_simulation_to_csv with empty list should not crash."""
        with tempfile.NamedTemporaryFile(
                mode='w', suffix='.csv', delete=False) as f:
            fname = f.name
        try:
            eng.save_simulation_to_csv([], fname)   # should silently return
        finally:
            if os.path.exists(fname):
                os.unlink(fname)


# =====================================================================
# 17. _nearest_weekday helper
# =====================================================================
class TestNearestWeekday(unittest.TestCase):

    def test_weekday_unchanged(self):
        # Wednesday
        dt = datetime(2026, 4, 15)
        self.assertEqual(eng._nearest_weekday(dt), dt)

    def test_saturday_shifts_to_monday(self):
        saturday = datetime(2026, 4, 18)
        result   = eng._nearest_weekday(saturday)
        self.assertEqual(result.weekday(), 0)   # Monday

    def test_sunday_shifts_to_monday(self):
        sunday = datetime(2026, 4, 19)
        result = eng._nearest_weekday(sunday)
        self.assertEqual(result.weekday(), 0)   # Monday

    def test_result_is_always_weekday(self):
        for day_offset in range(14):
            dt     = datetime(2026, 4, 13) + timedelta(days=day_offset)
            result = eng._nearest_weekday(dt)
            self.assertLess(result.weekday(), 5,
                            f"Expected weekday, got {result.strftime('%A')}")



# =====================================================================
# 18. __all__ and plot function interface
# =====================================================================
class TestPublicAPI(unittest.TestCase):

    def test_all_defined(self):
        """__all__ must be present and non-empty."""
        self.assertTrue(hasattr(eng, '__all__'))
        self.assertGreater(len(eng.__all__), 0)

    def test_all_names_are_importable(self):
        """Every name in __all__ must actually exist in the module."""
        for name in eng.__all__:
            self.assertTrue(
                hasattr(eng, name),
                f"'{name}' listed in __all__ but not found in module"
            )

    @patch('matplotlib.pyplot.show')
    def test_plot_single_season_returns_figure(self, mock_show):
        """plot_single_season must return a matplotlib Figure."""
        import matplotlib.figure
        eng.set_seed(42)
        data = eng.run_season('summer', time_resolution_mins=60)
        fig = eng.plot_single_season(data, 'summer')
        self.assertIsInstance(fig, matplotlib.figure.Figure)
        plt.close('all')

    @patch('matplotlib.pyplot.show')
    def test_plot_single_season_show_plot_true_calls_show(self, mock_show):
        eng.set_seed(42)
        data = eng.run_season('summer', time_resolution_mins=60)
        eng.plot_single_season(data, 'summer', show_plot=True)
        mock_show.assert_called_once()
        plt.close('all')

    @patch('matplotlib.pyplot.show')
    def test_plot_single_season_show_plot_false_no_show(self, mock_show):
        eng.set_seed(42)
        data = eng.run_season('summer', time_resolution_mins=60)
        eng.plot_single_season(data, 'summer', show_plot=False)
        mock_show.assert_not_called()
        plt.close('all')

    @patch('matplotlib.pyplot.show')
    def test_plot_season_comparison_returns_figure(self, mock_show):
        import matplotlib.figure
        eng.set_seed(42); ds = eng.run_season('summer', time_resolution_mins=60)
        eng.set_seed(42); dr = eng.run_season('rainy',  time_resolution_mins=60)
        eng.set_seed(42); dw = eng.run_season('winter', time_resolution_mins=60)
        fig = eng.plot_season_comparison(
            {'summer': ds, 'rainy': dr, 'winter': dw}
        )
        self.assertIsInstance(fig, matplotlib.figure.Figure)
        plt.close('all')

    @patch('matplotlib.pyplot.show')
    def test_plot_season_comparison_show_plot_false(self, mock_show):
        eng.set_seed(42); ds = eng.run_season('summer', time_resolution_mins=60)
        eng.set_seed(42); dr = eng.run_season('rainy',  time_resolution_mins=60)
        eng.set_seed(42); dw = eng.run_season('winter', time_resolution_mins=60)
        eng.plot_season_comparison(
            {'summer': ds, 'rainy': dr, 'winter': dw},
            show_plot=False
        )
        mock_show.assert_not_called()
        plt.close('all')

# =====================================================================
# Entry point
# =====================================================================
if __name__ == '__main__':
    unittest.main(verbosity=2)