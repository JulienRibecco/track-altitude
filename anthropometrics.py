"""Country-level mean anthropometrics for elite track athletes.

Built from published sport-science literature. Values are population means for
ELITE athletes within an event class — not general-population norms.

References:
  KEN distance:   Mooses et al. 2013 (Eur J Appl Physiol); Onywera et al. 2006;
                  Larsen 2003 (Comp Biochem Physiol A); Wilber & Pitsiladis 2012
                  (Int J Sports Physiol Perform 7:92-102).
  ETH distance:   Beis et al. 2011 (J Int Soc Sports Nutr); Tesfaye 2009.
  USA distance:   Costill 1985 (Med Sci Sports Exerc); Joyner & Coyle 2008
                  (J Physiol); Foster et al.
  GBR distance:   Jones 1998, 2002, 2006 (Br J Sports Med — Paula Radcliffe
                  longitudinal series); Williams & Nute.
  European mid:   Billat 2001-2003 (El Guerrouj, Aouita era); Brandon 1995.
  JPN distance:   Tanaka & Matsuura 1984; Suzuki et al.
  Sprinters:      Mackala 2007; Coh & Tomazin 2008; Hunter et al. 2004.

Coverage rationale: the 5000m geography test only needs distance-runner means
for nations with meaningful 5000m representation in the dataset. Sparse
nations are imputed from regional averages (documented per row). When a
country code is absent from the lookup we fall back to a sex-weighted
population-prior mean and flag the row.

Caveats:
  - Country MEAN, not athlete-specific. Within-country variation (e.g. small
    East African 5000m specialist vs larger 800m specialist of same nation)
    is not captured.
  - Distance-runner means do NOT apply to sprinters from the same country.
    USA distance runner ≈ 64 kg, USA sprinter ≈ 84 kg. Lookup is keyed on
    (country, sex, event_class) for this reason.
  - Older era (pre-1990) athletes were typically slightly heavier than modern
    elites; we ignore the temporal trend for now.
"""
from __future__ import annotations

# event_class buckets:
#   "sprint"  → 100, 200, 400 m
#   "middle"  → 800, 1500 m
#   "distance" → 3000, 5000, 10000 m


def event_class(distance_m: int) -> str:
    if distance_m <= 400:
        return "sprint"
    if distance_m <= 1500:
        return "middle"
    return "distance"


# Mean body mass (kg) for elite male athletes in each event class, by country.
# Values rounded to nearest kg from cited sources.
_MASS_M = {
    "distance": {
        # East African highland — Mooses, Wilber, Larsen, Onywera, Beis
        "KEN": 56, "ETH": 54, "ERI": 55, "UGA": 57, "TAN": 56,
        "BDI": 56, "RWA": 56, "DJI": 55,
        # Maghreb / North Africa — Billat (Aouita/El Guerrouj era), Hue
        "MAR": 62, "ALG": 62, "TUN": 62, "EGY": 63, "LBA": 62,
        # Bahrain/Qatar — mostly naturalised KEN/ETH
        "BRN": 56, "QAT": 56, "TUR": 60, "AZE": 64, "ISR": 64,
        # Andean
        "MEX": 60, "COL": 60, "ECU": 60, "BOL": 60, "PER": 60,
        "VEN": 62, "CHL": 63, "ARG": 64, "BRA": 62, "URU": 64,
        # Anglosphere
        "USA": 64, "GBR": 64, "CAN": 64, "AUS": 65, "NZL": 65,
        "IRL": 64, "RSA": 63,
        # Western/Northern Europe
        "GER": 65, "FRG": 65, "GDR": 66, "FRA": 64, "ITA": 64,
        "ESP": 63, "POR": 63, "BEL": 64, "NED": 65, "SUI": 64,
        "AUT": 64, "NOR": 65, "SWE": 65, "FIN": 65, "DEN": 65,
        "ISL": 66,
        # Eastern Europe
        "POL": 65, "RUS": 66, "URS": 66, "UKR": 65, "BLR": 65,
        "ROU": 65, "HUN": 65, "BUL": 65, "CZE": 65, "TCH": 65,
        "SVK": 65, "SLO": 65, "CRO": 65, "SRB": 65, "YUG": 65,
        "GRE": 64, "MKD": 64, "ALB": 63, "MDA": 65, "EST": 65,
        "LAT": 65, "LTU": 65, "GEO": 64, "ARM": 63,
        # East Asia
        "JPN": 58, "CHN": 58, "KOR": 58, "TPE": 58, "HKG": 58,
        "MGL": 60, "PRK": 58, "VIE": 56, "THA": 58, "IDN": 58,
        "MAS": 58, "PHI": 58, "SGP": 58, "IND": 58, "PAK": 60,
        "IRI": 62, "IRQ": 62, "SYR": 62, "JOR": 62, "LBN": 62,
        "SUD": 60, "GHA": 62, "NGR": 64, "SEN": 62, "CIV": 62,
        "CMR": 64, "ZIM": 60, "ZAM": 60, "BOT": 60, "NAM": 60,
        "MDG": 58, "SOM": 55,
    },
    "middle": {
        # Middle-distance athletes are typically +3-4 kg over distance runners
        # in same country (more anaerobic muscle).
        "KEN": 60, "ETH": 58, "ERI": 58, "UGA": 60, "TAN": 60,
        "BDI": 60, "RWA": 60, "DJI": 58,
        "MAR": 65, "ALG": 65, "TUN": 65, "EGY": 66, "LBA": 65,
        "BRN": 60, "QAT": 60, "TUR": 64, "AZE": 67, "ISR": 67,
        "MEX": 64, "COL": 64, "ECU": 64, "BOL": 64, "PER": 64,
        "VEN": 65, "CHL": 66, "ARG": 67, "BRA": 65, "URU": 67,
        "USA": 68, "GBR": 68, "CAN": 68, "AUS": 69, "NZL": 69,
        "IRL": 68, "RSA": 67,
        "GER": 70, "FRG": 70, "GDR": 71, "FRA": 69, "ITA": 69,
        "ESP": 67, "POR": 67, "BEL": 68, "NED": 69, "SUI": 68,
        "AUT": 68, "NOR": 70, "SWE": 70, "FIN": 70, "DEN": 70,
        "POL": 70, "RUS": 71, "URS": 71, "UKR": 70, "BLR": 70,
        "ROU": 70, "HUN": 70, "BUL": 70, "CZE": 70, "TCH": 70,
        "SVK": 70, "SLO": 70, "CRO": 70, "SRB": 70, "YUG": 70,
        "GRE": 69, "MKD": 69, "ALB": 67, "MDA": 70, "EST": 70,
        "LAT": 70, "LTU": 70, "GEO": 68, "ARM": 67,
        "JPN": 62, "CHN": 62, "KOR": 62, "TPE": 62, "HKG": 62,
        "MGL": 64, "PRK": 62, "VIE": 60, "THA": 62, "IDN": 62,
        "MAS": 62, "PHI": 62, "SGP": 62, "IND": 62, "PAK": 64,
        "IRI": 66, "IRQ": 66, "SYR": 66, "JOR": 66, "LBN": 66,
        "SUD": 64, "GHA": 66, "NGR": 68, "SEN": 66, "CIV": 66,
        "CMR": 68, "ZIM": 64, "ZAM": 64, "BOT": 64, "NAM": 64,
        "MDG": 62, "SOM": 58,
    },
    "sprint": {
        # Sprinters are an entirely different morphology cluster.
        # USA/JAM/TTO/BAH dominate so we anchor on Mackala 2007 + Coh 2008.
        "USA": 84, "JAM": 84, "TTO": 84, "BAH": 84, "BAR": 82,
        "GBR": 82, "FRA": 82, "GER": 84, "FRG": 84, "GDR": 85,
        "ITA": 80, "ESP": 78, "POR": 78, "NED": 82, "BEL": 80,
        "POL": 82, "RUS": 84, "URS": 84, "UKR": 82, "BLR": 82,
        "CAN": 84, "AUS": 80, "NZL": 80, "IRL": 78, "RSA": 80,
        "NOR": 82, "SWE": 82, "FIN": 80, "DEN": 80, "ISL": 80,
        "ROU": 80, "HUN": 80, "BUL": 80, "CZE": 80, "TCH": 80,
        "SVK": 80, "SLO": 80, "CRO": 80, "SRB": 80, "YUG": 80,
        "GRE": 78, "MKD": 78, "MDA": 80, "EST": 80,
        "LAT": 80, "LTU": 80, "GEO": 78, "ARM": 78, "AZE": 80,
        "JPN": 70, "CHN": 70, "KOR": 70, "TPE": 70, "HKG": 70,
        "VIE": 65, "THA": 68, "IDN": 68, "MAS": 68, "PHI": 68,
        "SGP": 68, "IND": 70, "PAK": 72, "IRI": 75, "TUR": 78,
        "ISR": 78, "JOR": 75, "LBN": 75,
        # African sprinters — typically lighter than caribbean/USA group
        "NGR": 80, "GHA": 78, "SEN": 78, "CIV": 78, "CMR": 78,
        "RSA": 80, "ZIM": 76, "ZAM": 76, "BOT": 76, "NAM": 78,
        "KEN": 70, "ETH": 68, "ERI": 70, "UGA": 70, "TAN": 70,
        "MAR": 76, "ALG": 76, "TUN": 76, "EGY": 78, "LBA": 76,
        "MEX": 75, "COL": 75, "ECU": 73, "BOL": 73, "PER": 73,
        "VEN": 76, "CHL": 75, "ARG": 78, "BRA": 80, "URU": 78,
        "BRN": 70, "QAT": 70, "SUD": 76,
    },
}

# Female ratio relative to male within same (country, event_class).
# Distance: 0.86 (Wilber/Pitsiladis); middle: 0.84; sprint: 0.84-0.85.
_FEMALE_RATIO = {"distance": 0.86, "middle": 0.84, "sprint": 0.85}

# Default mean by event_class when country is absent (sex-weighted).
_DEFAULT_M = {"distance": 63, "middle": 67, "sprint": 78}

# Mean body height (cm) — coarser since drag depends on frontal area which we
# proxy as mass^(2/3); height is a secondary refinement.
_HEIGHT_M = {
    "distance": {"KEN": 173, "ETH": 170, "ERI": 171, "UGA": 173, "TAN": 172,
                 "MAR": 175, "ALG": 175, "TUN": 175,
                 "USA": 178, "GBR": 178, "GER": 180, "FRA": 179, "ITA": 178,
                 "ESP": 176, "POR": 175, "JPN": 172, "CHN": 172,
                 "RUS": 180, "URS": 180, "POL": 180},
    "middle": {"KEN": 175, "ETH": 173, "MAR": 178, "ALG": 178,
               "USA": 182, "GBR": 182, "GER": 184, "FRA": 183, "ITA": 182,
               "ESP": 179, "JPN": 175, "RUS": 184, "URS": 184},
    "sprint": {"USA": 184, "JAM": 184, "TTO": 184, "BAH": 184,
               "GBR": 183, "GER": 185, "FRA": 183, "ITA": 181,
               "JPN": 175, "CHN": 178, "RUS": 186, "POL": 184, "NGR": 182},
}
_DEFAULT_H = {"distance": 178, "middle": 181, "sprint": 184}
_FEMALE_HEIGHT_RATIO = {"distance": 0.94, "middle": 0.94, "sprint": 0.94}


def lookup(country: str, sex: str, distance_m: int) -> tuple[float, float, bool]:
    """Return (mass_kg, height_cm, is_imputed) for the (country, sex, event) cell."""
    cls = event_class(distance_m)
    mass_table = _MASS_M[cls]
    height_table = _HEIGHT_M.get(cls, {})

    if country in mass_table:
        m = mass_table[country]
        imputed = False
    else:
        m = _DEFAULT_M[cls]
        imputed = True

    h = height_table.get(country, _DEFAULT_H[cls])

    if sex == "women":
        m = m * _FEMALE_RATIO[cls]
        h = h * _FEMALE_HEIGHT_RATIO[cls]

    return float(m), float(h), imputed


def area_proxy(mass_kg: float) -> float:
    """A ∝ mass^(2/3) — geometric scaling for frontal area."""
    return mass_kg ** (2.0 / 3.0)
