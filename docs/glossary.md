# Glossary

Domain terms used in the code and docs, one line each. Code names use these words. Add a term when it first appears in code; remove it when it's no longer used.

| Term | Meaning | Used in |
|---|---|---|
| Package-temperature exposure | Time, peak, and degree-hours a shipment's package sensor is outside configured temperature limits. | `src/risk_assessment/thermal.py` |
| Thermal time constant | Scenario parameter describing the response speed of the package/load model; it requires package-specific characterization for operational use. | `src/risk_assessment/thermal.py` |
| Traffic volume anomaly | Difference from comparable counter volumes, scaled by median absolute deviation; it does not establish congestion. | `src/risk_assessment/logistics.py` |
| Quality review | Human review action when temperature evidence is out of range, uncertain, missing, or incomplete. | `src/risk_assessment/decision.py` |
