# HarborSentinel AIS Pilot Acquisition

Generated UTC: 2026-06-20T21:32:26.053531+00:00

Posture: `PUBLIC_AIS_RAW_ACQUIRED_HASHED_PROFILED`

## Source

- Candidate: NOAA daily AIS CSV ZIP 2024-01-01
- Source family: NOAA daily AIS CSV ZIP
- URL: https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/AIS_2024_01_01.zip
- Official index: https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/index.html

## Raw External File

- Path: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\private_data\HarborSentinel\raw\noaa_ais\AIS_2024_01_01.zip`
- Bytes: 290340871
- SHA-256: `03ed1e16f4445361d3d7cd6e0f0b4175dce4e63b0c5c8c99252728c64de9253c`

## Schema/Profile

- Profile status: sampled
- Sample rows: 10000
- Columns: MMSI, BaseDateTime, LAT, LON, SOG, COG, Heading, VesselName, IMO, CallSign, VesselType, Status, Length, Width, Draft, Cargo, TransceiverClass
- Time range in sample: 2024-01-01T00:00:00 to 2024-01-01T00:03:22
- Latitude sample bounds: 16.82941 to 49.77816
- Longitude sample bounds: -159.29003 to -63.05322

## Claim Boundary

This acquisition proves that a public AIS raw file was staged on the external data drive, hashed, and schema-profiled. It does not prove HarborSentinel performance, Navy/SSDS integration, field validation, ADS-B rights, radar performance, or operational suitability.

## Next Step

Extract a bounded development/validation split on the external drive, freeze split hashes, then rerun the HarborSentinel gate without moving thresholds after validation is held out.
