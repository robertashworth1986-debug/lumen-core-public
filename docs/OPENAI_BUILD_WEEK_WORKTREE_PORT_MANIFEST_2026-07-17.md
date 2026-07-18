# OpenAI Build Week Worktree Port Manifest

**Generated:** 2026-07-17 UTC

**Source worktree branch:** `codex/live-domain-proof-feed-bundle`

**Source worktree HEAD:** `e691cc99c79b9c914038622cf7759689a0840629`

**Source divergence from `origin/main`:** 1,830 commits behind / 274 commits ahead

**Clean base:** `origin/main` at `1faa6e642748637b2b2a5ce0a8db9012defda848`

**Clean branch:** `build-week/prooflock-judge-ready`

**Focused donor commit:** `1578504204c429d7f05779897dc3d5430038f681`

**Port method:** selected file restoration and bounded elevation; no branch merge or rebase

## Dirty Worktree Classification

The source worktree was preserved without reset, clean, delete, or broad staging. The machine-readable inventory is outside this branch at:

`C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\ops\build_week_worktree_inventory_latest.json`

- inventoried dirty paths: 73
- held for their owning workstreams: 60
- explicitly excluded from this release: 13
- unrelated source/runtime/proposal/audio files copied into this branch: 0

The inventory SHA-256 is `C25F6157C737A9EEA08FBE806436E07B4E291A2BD413A83583254C0239EAE070`.

## Donor-To-Destination Ledger

SHA-256 values below are byte hashes of the donor blob and the staged release blob. `Elevated` means the donor file was intentionally hardened or expanded on the clean branch. `.gitattributes` fixes the release fixture and static app sources at LF; the browser also normalizes editor text before exact-restoration comparison.

| Path | Donor SHA-256 | Destination SHA-256 | Result |
|---|---|---|---|
| `assets/hardware/flowform_curved_motherboard_honeycomb_battery_v2_concept.json` | `CC822AA047C9DBE6AB9044412F22F423C1D6CB772A2F4DC0753AD7F4E367C7A8` | `CC822AA047C9DBE6AB9044412F22F423C1D6CB772A2F4DC0753AD7F4E367C7A8` | unchanged |
| `assets/hardware/flowform_curved_motherboard_honeycomb_battery_v2_concept.png` | `B4D90B400D3AA4E95D41B3FAB259B27CE85DB663D7F2FFB5F273A22E00824962` | `B4D90B400D3AA4E95D41B3FAB259B27CE85DB663D7F2FFB5F273A22E00824962` | unchanged |
| `assets/hardware/flowform_curved_motherboard_honeycomb_battery_v3_concept.json` | `5146281AF36E0DDA090BD38D2699D847005E1DD02F41CF267104874D7D5EB98D` | `5146281AF36E0DDA090BD38D2699D847005E1DD02F41CF267104874D7D5EB98D` | unchanged |
| `assets/hardware/flowform_curved_motherboard_honeycomb_battery_v3_concept.png` | `10472C90DB0837827E9C37D3BD781A87B690F084CAF7ECB28988C02223FFECB7` | `10472C90DB0837827E9C37D3BD781A87B690F084CAF7ECB28988C02223FFECB7` | unchanged |
| `build_week/prooflock_console/README.md` | `26615A4750A4B87A910194FA14609A4787E872B35802DBD3448EB9ACF3A3DFB2` | `5F4470A21CFA310C6B140E7316F4CA0B8AE9D5AFB14E685BD29611FB6A15CBB6` | elevated |
| `build_week/prooflock_console/app.js` | `3A8AEF62513533960C5F6FC891145016EF35A1B5EB759F0B1A3A7DDE9259CAD2` | `5405917DE7F99548DCE48C8C3212E36C6E5AE98157AB33A96A77B2EDF6438D87` | elevated |
| `build_week/prooflock_console/index.html` | `DD313667755130E3F6542DF91E2F3A376090CEDBC06370CB0185E888D22D1AE7` | `27F892E6A1E6CC84D128C93BD6C7A988DA9556EB45C480C64533D91402DF7B3A` | elevated |
| `build_week/prooflock_console/sample_receipt.json` | `559BFC14D122D4B77F402660C3A0909EA3100385AC188E0809EBFB9621C74773` | `559BFC14D122D4B77F402660C3A0909EA3100385AC188E0809EBFB9621C74773` | unchanged |
| `build_week/prooflock_console/styles.css` | `E3B27FA4AAAC362630F5DA701F2EA7B4EA6A431E5EFC9DF0FC1A51F5D412705D` | `4132481BC75F267B9F5CE01D3AB6E8A624FC5D42D21322E22B526B08A8A57684` | elevated |
| `build_week/prooflock_console/verify_receipt.py` | `358299D05A1658BACB4705D76FC9FE1FA28D94265120A3D22012887FD905CF84` | `C9E7A170CCCA072286F7629E04C07EA4D7BAADC0EB63E136F61D04D12372B406` | elevated |
| `tests/test_prooflock_console.py` | `5808D6CC784FDB35031EC3E72DB7084536305107E9B66E49D398B59206299F33` | `FFD1F3B70C8B2C32F5C2E24661A5E1132DC9AB2A54410F5574EA6E6A9AE13E29` | elevated |

## New Clean-Branch Files

| Path | Destination SHA-256 | Bytes |
|---|---|---:|
| `build_week/prooflock_console/bootstrap.js` | `811BB4971E98EB8FCB28366329B88E734A6CB397989FC47F00576181BADA2DA3` | 206 |
| `build_week/prooflock_console/prooflock_core.js` | `55E1C09CDC8BBB9A0259B401EEA2B35F4AAB1875BF01BEB289DE5E4B40FA88D8` | 10,165 |
| `build_week/prooflock_console/prooflock_favicon.svg` | `FCCFAA85618A824CD186613006113ADD6BEF64CCE33122FEE4167AB897765F82` | 313 |
| `build_week/prooflock_console/prooflock_lattice.css` | `C6A0F40A856D8DC0530DF6B8C1F0E8A138335F88BF09FC9FCD65FED7208B150A` | 1,821 |
| `build_week/prooflock_console/prooflock_lattice.js` | `1D637CCA788B1B7F9F8982CD62657770175A58ADF7A9E1B52554AFD2B7167F26` | 21,835 |
| `tests/test_prooflock_visual.py` | `62D7D771743B6FF7C4C9DACE8DCEF6E749EB2BF1C8C0A0DB92EC43D0036CB6E5` | 9,695 |
| `dashboard/assets/vendor/three.module.min.js` | `36A60B0120335F89A80A0DAB70292292B0EC414B3D05E83CD09A3EA428C6712A` | 364,998 |
| `dashboard/assets/vendor/three.core.min.js` | `6486AA0D719CFA87EC88DC47223B59B1FB8417A1A407FC0E52467C943E2F8CC9` | 384,222 |
| `dashboard/assets/vendor/THREE_LICENSE.txt` | `8B378EBE60E2FE500158CB0AC71CB5E8B7D92953C2ABCC63A0EB90499653B5BC` | 1,081 |
| `docs/OPENAI_BUILD_WEEK_PROOFLOCK_SUBMISSION_READINESS_2026-07-17.md` | `30A2C3240F565878F54C1585B1E01F2B0BA41C61E81A9F8ED3A54F9D43489109` | 3,945 |

## Scope And Safety Decision

Included work is limited to the public FLOWFORM fixture, ProofLock static application, verifier parity and tamper tests, local vendored visualization runtime, release provenance, and readiness documentation. MissionWeave files, credentials, private proposals, patent-sensitive material, outreach content, trading behavior, live-domain deploy state, audio, and generated runtime output are excluded.
