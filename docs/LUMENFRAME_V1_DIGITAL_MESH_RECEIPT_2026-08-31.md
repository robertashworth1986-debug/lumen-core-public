# LumenFrame V1 Digital Mesh Measurement Receipt

**Measured UTC:** 2026-08-31T23:55:00Z
**Source identity:** `28c96fbc19d032d0cfe70f4252b4abf8e5daa444fff825a706b01bca6fdd1ad4` (4884 bytes)
**Receipt identity:** `007fd1f64f59000e5f6f472408f8e14ccd9af32bf45c1be0366bdf670b22a309`

## Measured digital structure

| Measure | Result |
|---|---:|
| STL format | binary |
| Triangles | 96 |
| Unique vertices | 64 |
| Unique edges | 144 |
| Connected components | 8 |
| Degenerate triangles | 0 |
| Boundary edges | 0 |
| Non-manifold edges | 0 |
| Watertight by edge incidence | true |
| Bounds, source units | [-30.0, -30.0, -2.5] to [30.0, 57.5, 117.5] |
| Extents, source units | [60.0, 87.5, 120.0] |
| Surface area, source units squared | 10000.000000 |
| Absolute signed volume, source units cubed | 12000.000000 |

The coordinate unit is not declared. Area and volume therefore remain unitless source-coordinate calculations, not physical dimensions.

## Quality assessment

- Severity: **medium**
- Confidence: **high for digital structure; none for physical performance**
- Finding: The file is a non-empty parseable digital mesh. Multiple disconnected components and an undeclared coordinate unit require design-owner review before slicing, fabrication, or dimensional interpretation.

## Allowed measured claims

- The exact source file exists at the recorded SHA-256 and byte count.
- The mesh contains the recorded number of triangles, vertices, edges, and connected components.
- The recorded bounds, extents, area, and signed-volume calculations are digital measurements in undeclared source units.
- Edge-incidence checks establish only the recorded digital topology result.

## Not proven

- coordinate unit or intended physical scale
- design intent or source-CAD provenance
- printability, slicer success, or fabricated prototype
- dimensional accuracy or manufacturing tolerance
- material, structural, thermal, vibration, resonance, aerospace, or safety performance
- patent scope, public license, certification, or external validation

## Next evidence gate

1. Founder declares units, intended function, and source-CAD provenance.
2. Run qualified mesh checks for normals, self-intersections, minimum wall thickness, and intended component relationships.
3. Generate a slicer receipt using declared printer, material, orientation, supports, and tolerances.
4. Print a low-risk test article and preserve measurement photos, failures, settings, and hashes.
5. Complete IP and public-license review before releasing the raw STL.

The raw STL remains private and is not authorized for public release by this receipt.
