# Solid-state electrolyte doping study notes

## Material system
Li7La3Zr2O12 (LLZO) garnet, Ta-doped at 0/2/4/6 mol% on Zr site.

## Measurements taken

### Structural
- XRD Rietveld refinement -> lattice parameter, dislocation density
- SEM/EDS -> grain size, Ta distribution
- ICP-OES -> confirms nominal Ta content
- Bond valence sum analysis -> Ta5+ vs Zr4+ coordination

### Performance
- AC impedance (RT to 200 C) -> ionic conductivity
- DC polarization -> electronic conductivity (sanity check)
- Cyclic voltammetry -> electrochemical window
- Nano-indentation -> Young's modulus + hardness
- Sound velocity measurement -> bulk + shear modulus

### Observations summary

1. **Ionic conductivity** sigma_RT increases from 1.8e-4 to 4.2e-4 S/cm with doping (4-fold)
2. **Lattice parameter** decreases monotonically by 0.4% (Ta5+ < Zr4+ radius — expected)
3. **Mechanical properties** (E, H, nu) effectively unchanged within 2% across Ta0-Ta6
4. **Activation energy** for ion hopping decreases from 0.42 to 0.31 eV (counterintuitive — usually lattice contraction RAISES E_a)

## Open questions

- Why does smaller lattice parameter (less ion channel) give HIGHER conductivity?
- Why does E_a DECREASE when path is geometrically tighter?
- Is the carrier concentration increasing faster than the geometric penalty?
