# LumenCore VPS Capacity Change Receipt

- Change window: `2026-07-28T02:29:10Z` to `2026-07-28T02:33:35Z`
- Region: `us-ashburn-1`
- Change scope: full boot backup, online boot-volume resize, and guest
  partition/LVM/XFS expansion
- Compute shape change: `none`
- Reboot: `none`
- Evidence deletion or movement: `none`

## Authorization

The action-time authorization was:

`APPROVE OCI BOOT BACKUP AND RESIZE FROM 50 GB TO 150 GB BALANCED, ESTIMATED +$5.57/MONTH.`

No separate data volume, Object Storage purchase, instance-shape change,
service deployment, evidence deletion, or live-trading change was included.
The monthly amount is the previously documented public list-price estimate;
the account invoice remains the billing authority.

## Cloud Change

| Step | Result |
| --- | --- |
| Existing manual backups | `0` |
| New backup type | `FULL` |
| Backup state before resize | `AVAILABLE` |
| OCI size before | `47 GB` |
| OCI size after | `150 GB` |
| Performance before and after | `10 VPUs/GB`, Balanced |
| Final boot-volume state | `AVAILABLE` |

Oracle reports storage in decimal GB. The pre-change `47 GB` volume appeared
to Linux as a `50.04 GB` disk. The requested `150 GB` volume appears to Linux
as a `150 GiB` block device.

## Guest Expansion

Before expansion:

- root logical volume: `29.5 GiB`;
- root filesystem: `30 GiB`, `100%` used;
- available root bytes: `20,480`.

After expansion:

- block device: `150 GiB`;
- root logical volume: `132.9 GiB`;
- root filesystem: `133 GiB`;
- root available: approximately `103 GiB`;
- root utilization: `23%`;
- Oracle diagnostics logical volume: unchanged at `15 GiB`.

The first `oci-growfs` attempt made no change because `/tmp` could not create a
temporary directory. After the block device was rescanned, a second attempt
expanded partition 3 but could not write LVM's metadata archive on the full
root filesystem. The completed path copied the LVM system directory to
`/var/oled`, resized the physical volume, extended the root logical volume with
the new extents, and grew XFS online. The full cloud backup was already
`AVAILABLE` before those guest changes.

## Private Receipts

Resource identifiers and Oracle request metadata remain in the private
E-drive custody folder. Public integrity references:

| Private receipt | Bytes | SHA-256 |
| --- | ---: | --- |
| `boot_backup_create_receipt.json` | 607 | `f70494b475e0405c847c11be37447d1e403ffd2f827f9b502e33899cdffaf1d7` |
| `boot_volume_resize_receipt.json` | 500 | `5ac80a8b28d2ad0b7943e222fffb9bc182d5e25686ce4c67f110df57d2c1bde5` |

Private receipt root:
`E:\LumaProofVault\private\oci\20260728T022910Z`

## Remaining Runtime Gates

The storage incident is repaired, but public application health is not.

- `https://lumen-core.ai/health` returned `502` after the resize.
- `luma-gateway` still restart-loops because
  `booth_public_contract` is missing from the deployed runtime.
- `luma-paper-ticker` reached the paper safety gate but then failed to append
  its ledger due to file ownership or permissions.
- `luma-symbol-awareness` was active at the observation point, but its historic
  restart count remains evidence of an unresolved reliability problem.
- Caddy remains a stale failed unit while Nginx owns ports 80 and 443.
- A backup object exists, but a restore has not yet been tested.

No runtime code, service state, ownership, Nginx configuration, DNS,
certificate, or trading authorization was changed in this capacity operation.
The guarded deployment remains blocked until a valid private
`LUMA_HUMAN_UNLOCK_TOKEN` is present and the reviewed repair path is rerun.

## Verification Boundary

This receipt proves the bounded cloud and guest-storage change and its
point-in-time measurements. It does not prove application recovery, scientific
performance, customer value, external validation, or a successful backup
restore.
