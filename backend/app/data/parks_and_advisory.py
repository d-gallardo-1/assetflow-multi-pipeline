"""Synthetic assets: multi-tenant parks and advisory work.

Site names, engineers and figures are invented. Regions are real areas, and the
coordinates are rounded to one decimal so they do not pinpoint any facility.
Columns: id, name, stage, region, area (sqm), capital value (GBP), lead
engineer, latitude, longitude, grid capacity (MVA), permits verified, risk.
"""

from __future__ import annotations

MULTI_TENANT_PARKS = [
    ("AST-409", "Greater Manchester Trade Park Unit 7", "UNIT_AVAILABLE", "Greater Manchester",
     6400, "5200000.00", "Marta Kowalczyk-Reid", 53.5, -2.3, 1.5, True, "LOW"),
    ("AST-410", "Solent Gateway Warehouse Block C", "TECHNICAL_FIT_OUT", "Solent",
     11800, "12750000.00", "Marta Kowalczyk-Reid", 50.9, -1.4, 3, True, "MEDIUM"),
    ("AST-411", "Tees Valley Multi-Let Estate Phase 2", "LEASE_CONTRACT_REVIEW", "Tees Valley",
     15200, "16400000.00", "Imogen Vasquez-Hale", 54.6, -1.3, 4, True, "MEDIUM"),
    ("AST-412", "Humber Port-Side Storage Terrace", "ACTIVE_OPERATION", "Humber",
     9800, "8900000.00", "Dev Ramaswamy-Clarke", 53.7, -0.4, 2, True, "LOW"),
]

ADVISORY_VALUATION = [
    ("AST-413", "West Midlands Foundry Land Contamination Audit", "SCOPE_INTAKE", "West Midlands",
     21000, "180000.00", "Oluwaseun Brightwater", 52.5, -2.0, 0, False, "HIGH"),
    ("AST-414", "Thames Estuary Flood Resilience Valuation", "FIELD_INSPECTION", "Thames Estuary",
     64000, "240000.00", "Oluwaseun Brightwater", 51.5, 0.5, 0, False, "MEDIUM"),
    ("AST-415", "South Yorkshire Grid Headroom Study", "COMPLIANCE_MODELLING", "South Yorkshire",
     33000, "95000.00", "Imogen Vasquez-Hale", 53.5, -1.2, 60, True, "LOW"),
    ("AST-416", "East Anglia Solar-Ready Roof Survey", "CERTIFIED_REPORT", "East Anglia",
     18500, "72000.00", "Rowan Achterberg", 52.6, 1.2, 5, True, "LOW"),
]

#: Already in the trash bin at start-up, so restore can be tried at once.
#: Asset id -> days since it was deleted.
DELETED_DAYS_AGO = {"AST-412": 6, "AST-414": 21}
