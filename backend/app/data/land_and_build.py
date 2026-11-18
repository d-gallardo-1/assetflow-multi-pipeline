"""Synthetic assets: land acquisition and build-to-suit.

Site names, engineers and figures are invented. Regions are real areas, and the
coordinates are rounded to one decimal so they do not pinpoint any facility.
Columns: id, name, stage, region, area (sqm), capital value (GBP), lead
engineer, latitude, longitude, grid capacity (MVA), permits verified, risk.
"""

from __future__ import annotations

LAND_ACQUISITION = [
    ("AST-401", "Tees Valley Modular Logistics Hub Plot", "SITE_SCOUTING", "Tees Valley",
     185000, "14250000.00", "Rowan Achterberg", 54.6, -1.2, 12, False, "MEDIUM"),
    ("AST-402", "Humber Grid Substation Plot B", "TECHNICAL_DUE_DILIGENCE", "Humber",
     42000, "6800000.00", "Imogen Vasquez-Hale", 53.7, -0.3, 90, False, "HIGH"),
    ("AST-403", "South Yorkshire Brownfield Rail Sidings", "COMMERCIAL_NEGOTIATION", "South Yorkshire",
     96000, "9400000.00", "Rowan Achterberg", 53.5, -1.3, 8, True, "MEDIUM"),
    ("AST-404", "East Anglia Agri-Logistics Parcel", "TITLE_CLOSED", "East Anglia",
     230000, "11900000.00", "Callum Oyelaran", 52.4, 0.9, 6, True, "LOW"),
]

BUILD_TO_SUIT = [
    ("AST-405", "Midlands Automated Cold-Store BTS", "ENGINEERING_DESIGN", "West Midlands",
     38000, "62500000.00", "Freya Lindqvist-Moss", 52.5, -1.8, 18, False, "MEDIUM"),
    ("AST-406", "Thames Corridor Intermodal Yard", "PLANNING_GRID_PERMITS", "Thames Estuary",
     74000, "88000000.00", "Dev Ramaswamy-Clarke", 51.5, 0.4, 25, False, "HIGH"),
    ("AST-407", "Central Scotland Battery Assembly Hall", "CIVIL_EXECUTION", "Central Scotland",
     52000, "134000000.00", "Freya Lindqvist-Moss", 55.9, -3.7, 40, True, "HIGH"),
    ("AST-408", "South Wales Parcel Sortation Centre", "OPERATIONAL_HANDOVER", "South Wales",
     29000, "47300000.00", "Callum Oyelaran", 51.6, -3.2, 9, True, "LOW"),
]
