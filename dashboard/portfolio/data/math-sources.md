# Sources and model derivations

Reviewed 4 October 2026. The diagrams are original programmatic constructions; no source artwork or proprietary coordinate dataset is reproduced.

## Regular polyhedra

[Wolfram Language: PolyhedronData](https://reference.wolfram.com/language/ref/PolyhedronData.html) is primary software documentation covering the five Platonic solids and vertex, edge, face, and incidence representations.

This implementation uses standard algebraic coordinates, then divides every coordinate by the circumradius. Let φ = (1 + √5)/2. The tetrahedron is the four cube corners with coordinate product +1. The cube uses every (±1, ±1, ±1). The octahedron uses the six signed coordinate-axis unit vectors. The icosahedron uses cyclic permutations of (0, ±1, ±φ). The dodecahedron uses the eight cube corners and cyclic permutations of (0, ±1/φ, ±φ).

Edges are all minimum-distance vertex pairs. Faces are computed from supporting planes of the convex hull. The tests independently check expected V/E/F values of 4/6/4, 8/12/6, 6/12/8, 20/30/12, and 12/30/20, regular incidence, equal edge lengths, and V − E + F = 2.

## Phyllotaxis

Helmut Vogel, [“A better way to construct the sunflower head”](https://www.sciencedirect.com/science/article/pii/0025556479900804), *Mathematical Biosciences* 44 (1979), 179–189. [DOI: 10.1016/0025-5564(79)90080-4](https://doi.org/10.1016/0025-5564(79)90080-4). Bibliographic record and abstract were available; the full publisher text was not retrieved.

The implemented variant uses rᵢ = R√((i + 1/2)/N) and θᵢ = iα, with α = π(3 − √5), approximately 137.508°. The half-index places samples at equal-area annular midpoints and avoids a special central dot. This is an idealized geometric placement inspired by Vogel's construction, not a faithful botanical reconstruction or an assertion that every plant uses the golden angle.

## Fastest descent

Eric A. Carlen, Rutgers University, [*Note on the Brachistochrone Problem*](https://sites.math.rutgers.edu/~carlen/292S13/brach.pdf), 21 April 2013, especially §§1–3. This author-hosted mathematical note derives the cycloid and proves the minimizing property for the ideal model.

With downward y, x(θ) = a(θ − sin θ) and y(θ) = a(1 − cos θ). Energy conservation gives speed √(2gy). Integrating ds/speed gives T = θ√(a/g). For the same final horizontal displacement X and vertical drop Y, the straight incline takes √(2(X² + Y²)/(gY)). The implementation retains SI gravity rather than the note's convenient 2g = 1 normalization. Numerical tests integrate the original ds/speed expression separately from the analytic time calculation. The comparison assumes an ideal sliding point mass, not a rolling ball or a real track with friction.

## Branching radius relation

Cecil D. Murray, [“The Physiological Principle of Minimum Work: I. The Vascular System and the Cost of Blood Volume”](https://doi.org/10.1073/pnas.12.3.207), *PNAS* 12 (1926), 207–214. [Original paper scan, University of Vermont](https://pdodds.w3.uvm.edu/files/papers/others/1926/murray1926a.pdf).

The illustration enforces r₀³ = r₁³ + r₂³ by setting r₁ = r₀f^(1/3) and r₂ = r₀(1 − f)^(1/3). In the classical model the cubic flow-radius scaling follows from balancing viscous pumping and a volume-related maintenance cost. Here no flow field, pressure, viscosity, biological remodeling, or branch-angle optimization is computed. Segment lengths and angles are aesthetic choices, explicitly labeled schematic; the drawing is not evidence that an arbitrary natural branching network obeys this ideal relation.
