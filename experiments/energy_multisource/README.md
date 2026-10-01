# Energy multi-source wedge discovery lane

This lane evaluates public external energy data without promoting registration, simulation, or an internal benchmark into field validation.

## Registered sources

- DOE Geothermal Data Repository / Utah FORGE GDR 1683 — extended circulation field data, 2024, public/no-key.
- DOE GDR Utah FORGE 1109 — injection-test flow and pressure data, public/no-key.
- DOE GDR Utah FORGE 1149 — stimulation pressure, temperature, and flow data, public/no-key.
- NOAA NDBC — real-time buoy meteorological and spectral-wave feeds, public/no-key.
- USGS OFR 83-250 digital release — national low-temperature geothermal resource data, public/no-key.
- OEDI/AASG EGS borehole data — bottom-hole temperature/depth resource-screening data, public/no-key.

Authenticated sources already represented in the main live-source registry, including NREL, EIA, and NOAA NCEI, are not duplicated with secret values. Repository files contain environment-variable names only; secrets belong in the runtime/Actions secret store.

## High-priority experiments

### EGS / hot-rock circulation

1. Data-quality and missingness profile.
2. Injection/production recovery screening proxy.
3. Low-recovery and high-recovery regime comparison.
4. Pump-to-production and pressure-response lag screening on first differences.
5. Frozen persistence-vs-rolling forecast benchmarks at 10, 30, and 60 minutes for production flow, production-side wellhead pressure, and production temperature.
6. Negative-result retention: a candidate may not be promoted when it loses to persistence.
7. Transient/startup edge-case search focused on low recovery, rapid ramps, and sensor gaps.

### Marine wave

1. Multi-buoy ingestion from NOAA NDBC.
2. Deep-water wave-power resource proxy from significant wave height and average period.
3. Persistence-vs-rolling forecast benchmarks at approximately 1, 3, and 6 hours.
4. Ramp-event screening using a frozen 90th-percentile absolute-change threshold.
5. Cross-station resource variability and complementarity can be added only after timestamp-aligned station coverage is sufficient.

## Promotion rule

A computational candidate is tagged `PROMOTE_FOR_FURTHER_TEST` only when its held-out primary-metric improvement is at least 5% and sample support meets the lane minimum. This is a prioritization signal, not a production, safety, causal, bankability, or commercial-performance claim.

## Claim boundary

- External field data are external evidence of the measured system, not independent validation of LumenCore.
- The recovery ratio used here is a contemporaneous screening proxy, not a reservoir mass-balance calculation.
- The wave-power calculation is a resource proxy, not device output, capacity factor, LCOE, or bankable yield.
- No algorithm may control a physical energy system from this research lane.
