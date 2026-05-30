"""
climate_financial_model.py — Translate physical simulation outputs into financial value
========================================================================================
Four sequential layers:

  Layer 1  Energy cost linkage        UTCI improvement → kWh saved → NOI → asset value
  Layer 2  Hedonic pricing regression  ClimateGrade score → $/m² premium (Ridge)
  Layer 3  Demand signal calibration   Days-on-market, search velocity, vacancy proxy
  Layer 4  Climate risk discount       RCP 2.6 / 4.5 / 8.5 → projected UTCI → value risk

Usage
-----
    from climate_financial_model import ClimateFinancialModel

    model = ClimateFinancialModel("riyadh")
    npv = model.renovation_npv(
        capex_usd     = 180_000,
        scenario_key  = "B",
        floor_area_m2 = 12_000,
    )
    print(npv)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

# ── Optional ML / stats dependencies ─────────────────────────────────────────
try:
    import pandas as pd
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# ── Site imports ──────────────────────────────────────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).parent))
from sites import SITES

ANALYSIS_DIR = Path(__file__).parent


# ─────────────────────────────────────────────────────────────────────────────
# Configuration tables
# ─────────────────────────────────────────────────────────────────────────────

# Energy tariffs (USD / kWh retail, 2024)
ENERGY_TARIFFS: dict[str, float] = {
    "riyadh": 0.013,   # 0.048 SAR/kWh  cooling electricity
    "mecca":  0.013,   # 0.048 SAR/kWh  cooling electricity
    "almaty": 0.040,   # ~KZT 19/kWh    district heating
    "astana": 0.055,   # ~KZT 25/kWh    gas + district heating
}

# Base building energy use intensity (kWh / m² / yr) for the adjacent building stock.
# Hot sites are cooling-dominated; cold sites are heating-dominated.
# Sources: IEA Building Energy Outlook 2023, Gulf Cooperation Council, Kazakh SNiP.
BASE_ENERGY_INTENSITY: dict[str, float] = {
    "riyadh": 150.0,   # kWh/m²/yr  Gulf office/mixed-use, cooling-dominated
    "mecca":  150.0,
    "almaty": 120.0,   # kWh/m²/yr  Kazakh residential, heating-dominated
    "astana": 140.0,
}

# HVAC load reduction per 1 °C UTCI improvement (fraction of base intensity).
# Based on EnergyPlus sensitivity studies for perimeter zones (10 m depth).
# Outdoor comfort improvements propagate through glazing / infiltration loads.
UTCI_HVAC_ELASTICITY: dict[str, float] = {
    "riyadh": 0.025,   # 2.5 % cooling reduction per °C outdoor thermal comfort
    "mecca":  0.025,
    "almaty": 0.020,   # 2.0 % heating reduction per °C
    "astana": 0.020,
}

# Capitalisation rates for asset-value conversion
CAP_RATES: dict[str, float] = {
    "riyadh": 0.065,   # Grade-A office
    "mecca":  0.070,   # residential / serviced apt
    "almaty": 0.080,   # residential
    "astana": 0.090,   # office / mixed-use
}

# CMIP6 delta T_air (°C) relative to 2020 baseline, horizon 2050
CMIP6_DELTA: dict[str, dict[str, float]] = {
    "riyadh": {"rcp26": 1.1, "rcp45": 1.8, "rcp85": 3.2},
    "mecca":  {"rcp26": 1.2, "rcp45": 1.9, "rcp85": 3.4},
    "almaty": {"rcp26": 1.4, "rcp45": 2.3, "rcp85": 4.1},
    "astana": {"rcp26": 1.6, "rcp45": 2.7, "rcp85": 4.8},
}

# Empirical UTCI sensitivity: ΔUTCI per ΔT_air (°C)
# Source: UTCI-A dataset, Błażejczyk 2021
UTCI_SENSITIVITY = 0.70

# Stranded-asset thresholds
STRANDED_UTCI_MEAN  = 46.0   # °C — extreme heat stress (WHO)
STRANDED_FRAC_BAD   = 0.85   # fraction of hours outside comfort band

# Comfort UTCI band (ISO 15743 / EN 16798-1 moderate activity)
UTCI_COMFORT_LOW  = -13.0    # °C
UTCI_COMFORT_HIGH =  26.0    # °C

# Discount rate for NPV (nominal, USD)
DISCOUNT_RATE = 0.08

# Renovation lifetime (years) for NPV calculation
RENOVATION_LIFETIME_YRS = 25


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EnergyResult:
    delta_utci_c:            float   # UTCI improvement from simulation (°C)
    comfort_hours_reclaimed: float   # comfort-hours per m² per year
    delta_kwh_per_m2_yr:     float   # kWh saved per m² per year
    annual_saving_usd:       float   # total annual utility saving ($)
    asset_value_uplift_usd:  float   # NOI premium capitalised ($)


@dataclass
class HedonicResult:
    coeff_per_10pts:    float   # $/m² per 10-point score improvement
    score_delta:        float   # score improvement from simulation
    uplift_per_m2:      float   # $/m²
    total_uplift_usd:   float   # $/m² × floor_area_m2
    model_r2:           float   # Ridge regression R²
    n_listings:         int     # training set size


@dataclass
class DemandResult:
    dom_ratio:            float   # median DOM near site / city median
    search_velocity_idx:  float   # normalised keyword frequency index
    vacancy_proxy:        float   # fraction relisted within 90 days
    demand_premium_usd:   float   # estimated demand-driven value premium ($)


@dataclass
class ClimateRiskResult:
    rcp: str                         # "rcp26" | "rcp45" | "rcp85"
    delta_t_air_c:         float     # CMIP6 air temperature delta by 2050
    delta_utci_c:          float     # projected UTCI shift
    projected_utci_mean_c: float     # 2050 UTCI mean
    projected_frac_bad:    float     # 2050 fraction outside comfort
    stranded_flag:         bool      # True if exceeds habitability threshold
    value_discount_frac:   float     # fraction discount applied to asset value
    value_at_risk_usd:     float     # $ discount on total_asset_value


@dataclass
class RenovationNPV:
    capex_usd:               float
    scenario_key:            str
    floor_area_m2:           float
    annual_energy_saving_usd:float
    hedonic_uplift_usd:      float
    demand_premium_usd:      float
    climate_risk_avoided_usd:float
    total_value_usd:         float
    npv_usd:                 float
    roi_pct:                 float
    payback_years:           float
    energy:                  EnergyResult
    climate_risk_rcp45:      ClimateRiskResult


# ─────────────────────────────────────────────────────────────────────────────
# Main model class
# ─────────────────────────────────────────────────────────────────────────────

class ClimateFinancialModel:
    """
    Translate Infrared simulation outputs into financial value metrics.

    Parameters
    ----------
    site_key : str
        One of the keys in SITES: "almaty", "riyadh", "astana", "mecca".
    total_asset_value_usd : float, optional
        Total appraised value of adjacent buildings within 300 m.
        Required for climate risk layer.  Defaults to a rough estimate
        from price_per_m2 × floor_area_m2.
    """

    def __init__(
        self,
        site_key: str,
        total_asset_value_usd: Optional[float] = None,
    ) -> None:
        if site_key not in SITES:
            raise ValueError(f"Unknown site_key '{site_key}'. Valid: {list(SITES)}")
        self.site_key  = site_key
        self.site      = SITES[site_key]
        self.climate   = self.site["climate"]   # "hot" | "cold"
        self.tariff    = ENERGY_TARIFFS[site_key]
        self.cap_rate  = CAP_RATES[site_key]
        self._total_asset_value = total_asset_value_usd

        self._out_dir = ANALYSIS_DIR / "results" / site_key
        self._baseline_stats:  Optional[dict] = None
        self._scenarios_summary: Optional[dict] = None
        self._courtyard_score: Optional[dict] = None
        self._hedonic_model:   Optional[object] = None   # fitted Ridge
        self._hedonic_scaler:  Optional[object] = None

    # ── Data loaders ──────────────────────────────────────────────────────────

    def _load_baseline(self) -> dict:
        if self._baseline_stats is None:
            p = self._out_dir / "baseline_stats.json"
            if not p.exists():
                raise FileNotFoundError(f"Run baseline.py first: {p}")
            with open(p) as f:
                self._baseline_stats = json.load(f)
        return self._baseline_stats

    def _load_scenarios(self) -> dict:
        if self._scenarios_summary is None:
            p = self._out_dir / "scenarios_summary.json"
            if not p.exists():
                raise FileNotFoundError(f"Run scenarios.py first: {p}")
            with open(p) as f:
                self._scenarios_summary = json.load(f)
        return self._scenarios_summary

    def _load_courtyard_score(self) -> dict:
        if self._courtyard_score is None:
            p = self._out_dir / "courtyard_score.json"
            if not p.exists():
                raise FileNotFoundError(f"Run score.py first: {p}")
            with open(p) as f:
                self._courtyard_score = json.load(f)
        return self._courtyard_score

    def _load_utci_grid(self) -> np.ndarray:
        p = self._out_dir / "baseline_utci.npy"
        if not p.exists():
            raise FileNotFoundError(f"UTCI grid not found: {p}")
        return np.load(p)

    # ─────────────────────────────────────────────────────────────────────────
    # Layer 1 — Energy Cost Linkage
    # ─────────────────────────────────────────────────────────────────────────

    def energy_savings_annual(
        self,
        scenario_key: str,
        floor_area_m2: float,
        occupied_hours_yr: float = 4_000.0,
    ) -> EnergyResult:
        """
        Estimate annual utility savings from a scenario's UTCI improvement.

        Parameters
        ----------
        scenario_key : str
            Scenario identifier ("A", "B", "C", "D").
        floor_area_m2 : float
            Total gross floor area of adjacent buildings within 300 m.
        occupied_hours_yr : float
            Occupied hours per year for which outdoor conditions influence HVAC.
            Default 4,000 h (≈ office + mixed-use); use 8,760 for 24h residential.

        Returns
        -------
        EnergyResult
        """
        scenarios = self._load_scenarios()
        if scenario_key not in scenarios:
            raise KeyError(
                f"Scenario '{scenario_key}' not found for {self.site_key}. "
                f"Available: {list(scenarios)}"
            )

        delta_utci = scenarios[scenario_key]["utci_improvement"]   # °C improvement

        # ── Energy savings via UTCI-delta approach ─────────────────────────
        # Annual kWh saved per m² of adjacent GFA:
        #   = base_intensity [kWh/m²/yr]
        #     × utci_elasticity [fraction / °C]
        #     × |delta_utci| [°C]
        #
        # base_intensity: typical annual HVAC energy use for this climate type
        # utci_elasticity: HVAC load reduction per 1°C outdoor comfort improvement
        #   (EnergyPlus perimeter-zone sensitivity; conservative central estimate)
        base_kwh    = BASE_ENERGY_INTENSITY[self.site_key]
        elasticity  = UTCI_HVAC_ELASTICITY[self.site_key]
        delta_utci_abs    = abs(delta_utci)
        delta_kwh_m2_yr   = base_kwh * elasticity * delta_utci_abs

        annual_saving = delta_kwh_m2_yr * floor_area_m2 * self.tariff
        asset_value   = (annual_saving / self.cap_rate) if self.cap_rate > 0 else 0.0

        # Comfort-hours reclaimed (informational, no longer used in energy formula)
        frac_improved   = scenarios[scenario_key].get("frac_utci_improved", 0.0)
        comfort_hours   = (occupied_hours_yr or 4_000.0) * frac_improved

        return EnergyResult(
            delta_utci_c            = delta_utci,
            comfort_hours_reclaimed = comfort_hours,
            delta_kwh_per_m2_yr     = delta_kwh_m2_yr,
            annual_saving_usd       = annual_saving,
            asset_value_uplift_usd  = asset_value,
        )

    def value_from_energy(
        self,
        annual_saving_usd: float,
        lifetime_yrs: int = RENOVATION_LIFETIME_YRS,
        discount_rate: float = DISCOUNT_RATE,
    ) -> float:
        """
        NPV of a perpetual annual saving stream, discounted over `lifetime_yrs`.

        Returns
        -------
        float — NPV in USD
        """
        if discount_rate <= 0:
            return annual_saving_usd * lifetime_yrs
        # Annuity formula
        npv = annual_saving_usd * (1 - (1 + discount_rate) ** -lifetime_yrs) / discount_rate
        return npv

    # ─────────────────────────────────────────────────────────────────────────
    # Layer 2 — Hedonic Pricing Regression
    # ─────────────────────────────────────────────────────────────────────────

    def fit_hedonic(self, listings_df) -> "ClimateFinancialModel":
        """
        Fit Ridge regression on listing data.

        Parameters
        ----------
        listings_df : pd.DataFrame
            Columns required:
              price_per_m2 (float)  — listing price per m²
              climate_score (float) — ClimateGrade composite score of nearest site
              dist_to_metro_m (float)
              floor (int)
              building_age (int)    — years since construction
              rooms (int)

        Returns
        -------
        self (for chaining)
        """
        if not HAS_SKLEARN:
            raise ImportError("pip install scikit-learn pandas")

        import pandas as pd

        required = {"price_per_m2", "climate_score", "dist_to_metro_m",
                    "floor", "building_age", "rooms"}
        missing = required - set(listings_df.columns)
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        df = listings_df.dropna(subset=list(required)).copy()

        # Feature engineering
        X = pd.DataFrame({
            "climate_score":      df["climate_score"],
            "log_dist_metro":     np.log1p(df["dist_to_metro_m"]),
            "floor":              df["floor"],
            "building_age":       df["building_age"],
            "rooms":              df["rooms"],
        })
        y = np.log(df["price_per_m2"].clip(lower=1.0))

        self._hedonic_scaler = StandardScaler()
        X_scaled = self._hedonic_scaler.fit_transform(X)

        self._hedonic_model = Ridge(alpha=1.0)
        self._hedonic_model.fit(X_scaled, y)

        self._hedonic_n_listings = len(df)
        self._hedonic_r2 = self._hedonic_model.score(X_scaled, y)

        # Coefficient for climate_score (index 0 after scaling)
        # Convert back to $/m² per 10-point improvement
        idx = 0   # climate_score is first feature
        raw_coeff  = self._hedonic_model.coef_[idx]
        scale      = self._hedonic_scaler.scale_[idx]
        # d(log_price)/d(score) = raw_coeff / scale
        # -> % change per unit score -> multiply by median price for $/m²
        self._coeff_per_pt = raw_coeff / scale
        return self

    def predict_uplift(
        self,
        score_before: float,
        score_after: float,
        floor_area_m2: float,
        price_per_m2_current: float = 1_000.0,
    ) -> HedonicResult:
        """
        Predict price premium from a score improvement.

        If no hedonic model has been fitted, uses literature-based priors.

        Parameters
        ----------
        score_before : float       baseline composite score (0–100)
        score_after : float        scenario composite score (0–100)
        floor_area_m2 : float      GFA of adjacent buildings
        price_per_m2_current : float   current market price/m²

        Returns
        -------
        HedonicResult
        """
        # score runs 0 (best) → 100 (worst).  A comfort improvement LOWERS the
        # score.  score_improvement is positive when comfort improves.
        score_improvement = score_before - score_after   # > 0 when scenario helps

        if self._hedonic_model is not None:
            # Use fitted model: raw coefficient sign already accounts for direction
            coeff_per_10 = abs(self._coeff_per_pt * 10 * price_per_m2_current)
            r2 = self._hedonic_r2
            n  = self._hedonic_n_listings
        else:
            # Literature priors: $/m² per 10-point score decrease (= comfort gain)
            # Source: studies on proximity to green/comfort urban spaces
            prior = {"hot": 25.0, "cold": 13.0}
            coeff_per_10 = prior[self.climate]
            r2 = float("nan")
            n  = 0

        uplift_per_m2  = coeff_per_10 * (score_improvement / 10.0)
        total_uplift   = uplift_per_m2 * floor_area_m2

        return HedonicResult(
            coeff_per_10pts  = coeff_per_10,
            score_delta      = -score_improvement,   # negative = improvement
            uplift_per_m2    = uplift_per_m2,
            total_uplift_usd = total_uplift,
            model_r2         = r2,
            n_listings       = n,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Layer 3 — Demand Signal Calibration
    # ─────────────────────────────────────────────────────────────────────────

    def dom_signal(
        self,
        dom_near_site: float,
        dom_city_median: float,
    ) -> float:
        """
        Returns the ratio of Days-on-Market near this site vs. city median.
        Values < 1.0 indicate higher demand (faster sales).
        """
        if dom_city_median <= 0:
            return 1.0
        return dom_near_site / dom_city_median

    def search_velocity(
        self,
        keyword_frequency_site: float,
        keyword_frequency_city: float,
    ) -> float:
        """
        Normalised search-velocity index.
        Outdoor comfort keywords: "тень" (KZ), "ظل"/"هواء" (AR).
        Returns index > 1.0 when site-adjacent listings over-index on comfort terms.
        """
        if keyword_frequency_city <= 0:
            return 1.0
        return keyword_frequency_site / keyword_frequency_city

    def vacancy_proxy(
        self,
        relisted_within_90d: int,
        total_listings: int,
    ) -> float:
        """Returns fraction of listings re-listed within 90 days (vacancy proxy)."""
        if total_listings <= 0:
            return 0.0
        return relisted_within_90d / total_listings

    def demand_premium_estimate(
        self,
        dom_ratio: float,
        search_velocity_idx: float,
        vacancy_frac: float,
        annual_rent_psm: float,
        floor_area_m2: float,
    ) -> DemandResult:
        """
        Estimate demand-driven value premium from the three signals.

        The demand premium is modelled as:
            annual_rent_income * demand_multiplier * floor_area_m2 / cap_rate

        Where demand_multiplier is derived from the three demand signals:
            - DOM ratio < 1 → positive multiplier (faster absorption)
            - Search velocity > 1 → positive
            - Vacancy < city_avg → positive
        """
        # Simple additive demand index (-1 to +1 range per signal)
        dom_signal_contribution    = max(-0.15, min(0.15, (1.0 - dom_ratio) * 0.3))
        vel_signal_contribution    = max(-0.10, min(0.10, (search_velocity_idx - 1.0) * 0.2))
        vac_signal_contribution    = max(-0.10, min(0.10, (0.15 - vacancy_frac) * 0.5))

        demand_multiplier = dom_signal_contribution + vel_signal_contribution + vac_signal_contribution
        annual_demand_premium = annual_rent_psm * demand_multiplier * floor_area_m2
        # Capitalise to get one-off asset value premium
        demand_premium_usd = max(0.0, annual_demand_premium / self.cap_rate)

        return DemandResult(
            dom_ratio            = dom_ratio,
            search_velocity_idx  = search_velocity_idx,
            vacancy_proxy        = vacancy_frac,
            demand_premium_usd   = demand_premium_usd,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Layer 4 — Climate Risk Discount & RCP Scenarios
    # ─────────────────────────────────────────────────────────────────────────

    def climate_risk_score(
        self,
        rcp: str = "rcp45",
        total_asset_value_usd: Optional[float] = None,
    ) -> ClimateRiskResult:
        """
        Project UTCI to 2050 under a given RCP scenario and compute value discount.

        Parameters
        ----------
        rcp : str
            "rcp26" | "rcp45" | "rcp85"
        total_asset_value_usd : float, optional
            Total appraised value of adjacent assets.  Falls back to
            self._total_asset_value if not provided.

        Returns
        -------
        ClimateRiskResult
        """
        if rcp not in ("rcp26", "rcp45", "rcp85"):
            raise ValueError(f"rcp must be one of rcp26/rcp45/rcp85, got '{rcp}'")

        baseline = self._load_baseline()
        utci_mean_now  = baseline["utci"]["mean_c"]
        frac_bad_now   = baseline["utci"]["frac_utci_bad"]

        # utci_offset_c: optional adjustment from a renovation scenario.
        # Positive = improvement (UTCI lowered for hot, raised for cold).
        # Stored as an instance variable set by renovation_npv() for the
        # "with-renovation" risk calculation; reset to 0 otherwise.
        utci_offset = getattr(self, "_utci_offset_for_risk", 0.0)

        delta_t_air    = CMIP6_DELTA[self.site_key][rcp]
        delta_utci     = delta_t_air * UTCI_SENSITIVITY

        # For hot sites: renovation improves (lowers) current UTCI before projecting.
        # For cold sites: warming is beneficial, offset is less meaningful.
        if self.climate == "hot":
            utci_mean_now = utci_mean_now - utci_offset   # lower UTCI = better
        else:
            utci_mean_now = utci_mean_now + utci_offset   # higher UTCI = warmer = better

        projected_mean = utci_mean_now + delta_utci

        # ── Projected frac_bad ────────────────────────────────────────────────
        # Approximate future frac_bad by shifting the distribution by delta_utci.
        # Hot sites: warming pushes more cells above the upper comfort ceiling.
        # Cold sites: warming REDUCES cold stress (fewer cells below −13 °C) but
        #   may eventually create summer heat stress. The net effect at 2050 for
        #   Almaty/Astana is still improved comfort, so frac_bad decreases.
        if self.climate == "hot":
            projected_frac_bad = min(1.0, frac_bad_now + delta_utci * 0.04)
        else:
            projected_frac_bad = max(0.0, frac_bad_now - delta_utci * 0.02)

        # ── Stranded-asset logic ───────────────────────────────────────────────
        # Hot sites: stranded when projected UTCI exceeds habitability threshold OR
        #            when an extreme fraction of hours is above comfort ceiling.
        # Cold sites: climate change is generally BENEFICIAL at 2050 time horizon —
        #             warming reduces cold stress. Flag stranded only if the site
        #             crosses INTO heat-stress territory (projected_mean > 38 °C).
        if self.climate == "hot":
            stranded = (
                projected_mean >= STRANDED_UTCI_MEAN or
                projected_frac_bad >= STRANDED_FRAC_BAD
            )
        else:
            # Cold sites only become stranded when projected mean crosses into
            # strong heat stress (UTCI > 38 °C) — very unlikely by 2050
            stranded = projected_mean >= 38.0

        # ── Value discount ────────────────────────────────────────────────────
        if stranded and projected_mean >= STRANDED_UTCI_MEAN:
            years_above = max(0.0, (projected_mean - STRANDED_UTCI_MEAN) / max(delta_t_air * 0.7, 0.01))
            value_discount = min(0.25, 0.05 * years_above)
        elif stranded and projected_frac_bad >= STRANDED_FRAC_BAD:
            value_discount = 0.15
        elif stranded:   # cold site crossing 38 °C
            value_discount = 0.10
        else:
            value_discount = 0.0

        asset_val = total_asset_value_usd or self._total_asset_value or 0.0
        value_at_risk = asset_val * value_discount

        return ClimateRiskResult(
            rcp                    = rcp,
            delta_t_air_c          = delta_t_air,
            delta_utci_c           = delta_utci,
            projected_utci_mean_c  = projected_mean,
            projected_frac_bad     = projected_frac_bad,
            stranded_flag          = stranded,
            value_discount_frac    = value_discount,
            value_at_risk_usd      = value_at_risk,
        )

    def stranded_asset_flag(self, rcp: str = "rcp45") -> bool:
        """Quick check — returns True if this site is climate-stranded under `rcp`."""
        return self.climate_risk_score(rcp).stranded_flag

    # ─────────────────────────────────────────────────────────────────────────
    # Combined NPV calculator
    # ─────────────────────────────────────────────────────────────────────────

    def renovation_npv(
        self,
        capex_usd: float,
        scenario_key: str,
        floor_area_m2: float,
        price_per_m2_current: float = 1_000.0,
        annual_rent_psm: float = 60.0,
        dom_ratio: float = 1.0,
        search_velocity_idx: float = 1.0,
        vacancy_frac: float = 0.10,
        total_asset_value_usd: Optional[float] = None,
        rcp_for_risk: str = "rcp45",
        occupied_hours_yr: float = 4_000.0,
    ) -> RenovationNPV:
        """
        Full renovation NPV combining all four financial layers.

        Parameters
        ----------
        capex_usd : float
            Total renovation cost (USD).
        scenario_key : str
            Scenario identifier: "A" | "B" | "C" | "D".
        floor_area_m2 : float
            GFA of adjacent buildings within 300 m that benefit.
        price_per_m2_current : float
            Current market price per m² (for hedonic layer).
        annual_rent_psm : float
            Annual rent per m² per year (for demand premium layer).
        dom_ratio : float
            Days-on-market near site / city median.
        search_velocity_idx : float
            Comfort-keyword frequency index vs. city average.
        vacancy_frac : float
            Current vacancy rate proxy near site.
        total_asset_value_usd : float, optional
            Total appraised asset value for climate risk calculation.
        rcp_for_risk : str
            RCP scenario for climate risk comparison ("rcp26"|"rcp45"|"rcp85").
        occupied_hours_yr : float
            Occupied hours per year influencing HVAC.

        Returns
        -------
        RenovationNPV
        """
        # ── Score before/after ─────────────────────────────────────────────
        score_obj    = self._load_courtyard_score()
        score_before = score_obj["composite_score"]
        scenarios    = self._load_scenarios()
        utci_improv  = scenarios[scenario_key]["utci_improvement"]   # positive = improvement

        # Approximate post-scenario score.
        # The composite score runs 0 (best) → 100 (worst), so a positive UTCI
        # improvement lowers the score.  The UTCI weight drives the reduction.
        sc_cfg       = self.site["score_config"]
        utci_weight  = sc_cfg.get("utci_weight", 0.5)
        # Heuristic: each 1 °C UTCI improvement reduces the 0–100 composite by
        # ~ utci_weight × 10 points (calibrated from score.py normalise() range).
        score_after  = max(0.0, score_before - abs(utci_improv) * utci_weight * 10)

        # ── Layer 1: Energy ────────────────────────────────────────────────
        energy       = self.energy_savings_annual(
            scenario_key, floor_area_m2, occupied_hours_yr)
        energy_npv   = self.value_from_energy(energy.annual_saving_usd)

        # ── Layer 2: Hedonic ───────────────────────────────────────────────
        hedonic      = self.predict_uplift(
            score_before, score_after,
            floor_area_m2, price_per_m2_current)
        hedonic_usd  = hedonic.total_uplift_usd

        # ── Layer 3: Demand ────────────────────────────────────────────────
        demand       = self.demand_premium_estimate(
            dom_ratio, search_velocity_idx, vacancy_frac,
            annual_rent_psm, floor_area_m2)
        demand_usd   = demand.demand_premium_usd

        # ── Layer 4: Climate risk avoided ──────────────────────────────────
        # Compares the site's projected 2050 asset value discount:
        #   without renovation  (baseline UTCI)
        #   with renovation     (UTCI improved by scenario utci_improvement)
        # The difference is the climate risk that the renovation avoids.
        total_val_est = (
            total_asset_value_usd or
            self._total_asset_value or
            (price_per_m2_current * floor_area_m2)
        )
        utci_improv_abs = abs(utci_improv)

        # Risk WITHOUT renovation (baseline UTCI)
        self._utci_offset_for_risk = 0.0
        risk_without = self.climate_risk_score(rcp_for_risk, total_val_est)

        # Risk WITH renovation (UTCI shifted by scenario improvement)
        self._utci_offset_for_risk = utci_improv_abs
        risk_with = self.climate_risk_score(rcp_for_risk, total_val_est)

        self._utci_offset_for_risk = 0.0   # reset

        risk_avoided = max(
            0.0,
            risk_without.value_at_risk_usd - risk_with.value_at_risk_usd
        )
        # Use risk_without as the reference for the card display
        risk_rcp_mid = risk_without

        # ── Totals ─────────────────────────────────────────────────────────
        total_value = energy_npv + hedonic_usd + demand_usd + risk_avoided
        npv         = total_value - capex_usd
        roi_pct     = (npv / capex_usd * 100) if capex_usd > 0 else 0.0
        payback_yrs = (capex_usd / energy.annual_saving_usd
                       if energy.annual_saving_usd > 0 else float("inf"))

        return RenovationNPV(
            capex_usd                = capex_usd,
            scenario_key             = scenario_key,
            floor_area_m2            = floor_area_m2,
            annual_energy_saving_usd = energy.annual_saving_usd,
            hedonic_uplift_usd       = hedonic_usd,
            demand_premium_usd       = demand_usd,
            climate_risk_avoided_usd = risk_avoided,
            total_value_usd          = total_value,
            npv_usd                  = npv,
            roi_pct                  = roi_pct,
            payback_years            = payback_yrs,
            energy                   = energy,
            climate_risk_rcp45       = risk_rcp_mid,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Portfolio & reporting helpers
    # ─────────────────────────────────────────────────────────────────────────

    def portfolio_risk_report(self) -> dict:
        """
        Generate a per-site climate risk summary across all three RCP scenarios.

        Returns
        -------
        dict with keys:
          site_key, site_name, current_utci_mean, current_frac_bad,
          rcp26, rcp45, rcp85  (each a ClimateRiskResult as dict)
        """
        baseline = self._load_baseline()
        report = {
            "site_key":          self.site_key,
            "site_name":         self.site["name"],
            "current_utci_mean": baseline["utci"]["mean_c"],
            "current_frac_bad":  baseline["utci"]["frac_utci_bad"],
        }
        for rcp in ("rcp26", "rcp45", "rcp85"):
            r = self.climate_risk_score(rcp)
            report[rcp] = {
                "delta_t_air_c":         r.delta_t_air_c,
                "delta_utci_c":          r.delta_utci_c,
                "projected_utci_mean_c": r.projected_utci_mean_c,
                "projected_frac_bad":    r.projected_frac_bad,
                "stranded_flag":         r.stranded_flag,
                "value_discount_frac":   r.value_discount_frac,
            }
        return report

    def print_npv_card(self, npv: RenovationNPV) -> None:
        """Print a formatted NPV summary card to stdout."""
        W = 62
        sep = "-" * W
        print(f"\n{'=' * W}")
        print(f"  RENOVATION NPV   {self.site['name']}  Scenario {npv.scenario_key}")
        print(f"{'=' * W}")
        print(f"  {'Capex':.<36}  ${npv.capex_usd:>12,.0f}")
        print(sep)
        print(f"  {'Energy NPV (Layer 1)':.<36}  ${self.value_from_energy(npv.annual_energy_saving_usd):>12,.0f}")
        print(f"    annual saving:  ${npv.annual_energy_saving_usd:,.0f}/yr")
        print(f"    dUTCI:          {npv.energy.delta_utci_c:+.2f} degC")
        print(f"  {'Hedonic uplift (Layer 2)':.<36}  ${npv.hedonic_uplift_usd:>12,.0f}")
        print(f"  {'Demand premium (Layer 3)':.<36}  ${npv.demand_premium_usd:>12,.0f}")
        print(f"  {'Climate risk avoided (Layer 4)':.<36}  ${npv.climate_risk_avoided_usd:>12,.0f}")
        print(sep)
        print(f"  {'Total value':.<36}  ${npv.total_value_usd:>12,.0f}")
        print(f"  {'NPV':.<36}  ${npv.npv_usd:>12,.0f}")
        print(f"  {'ROI':.<36}  {npv.roi_pct:>11.0f}%")
        print(f"  {'Payback':.<36}  {npv.payback_years:>10.1f} yr")
        risk = npv.climate_risk_rcp45
        flag = "STRANDED RISK" if risk.stranded_flag else "OK"
        print(sep)
        print(f"  Climate risk (RCP 4.5)  UTCI 2050: {risk.projected_utci_mean_c:.1f} degC  [{flag}]")
        print(f"{'=' * W}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="ClimateFinancialModel — renovation NPV from simulation results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python climate_financial_model.py --site riyadh --scenario B --area 12000 --capex 180000
  python climate_financial_model.py --site almaty --scenario A --area 8000  --capex 90000
  python climate_financial_model.py --site astana --risk                    # climate risk only
""",
    )
    parser.add_argument("--site",     required=True, choices=list(SITES))
    parser.add_argument("--scenario", default="B",   help="Scenario key A/B/C/D")
    parser.add_argument("--area",     type=float, default=10_000.0,
                        help="Adjacent GFA m2 (default 10000)")
    parser.add_argument("--capex",    type=float, default=180_000.0,
                        help="Renovation cost USD (default 180000)")
    parser.add_argument("--price",    type=float, default=1_000.0,
                        help="Current price/m2 USD (default 1000)")
    parser.add_argument("--asset-value", type=float, default=None,
                        help="Total adjacent asset value USD (optional)")
    parser.add_argument("--risk",     action="store_true",
                        help="Print portfolio risk report only")
    args = parser.parse_args()

    model = ClimateFinancialModel(args.site, total_asset_value_usd=args.asset_value)

    if args.risk:
        import json as _json
        report = model.portfolio_risk_report()
        print(_json.dumps(report, indent=2))
    else:
        npv = model.renovation_npv(
            capex_usd             = args.capex,
            scenario_key          = args.scenario,
            floor_area_m2         = args.area,
            price_per_m2_current  = args.price,
            total_asset_value_usd = args.asset_value,
        )
        model.print_npv_card(npv)
