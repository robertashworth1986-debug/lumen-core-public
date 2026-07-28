# LumenCore Production VPS Capacity Audit

- Observed at: `2026-07-28T01:59:46Z`
- Instance region: `us-ashburn-1`
- Audit mode: read-only

## Executive Decision

The production VPS does not currently need more CPU or memory. It needs storage
capacity, storage separation, retention controls, and restart-loop protection.

The current instance is `VM.Standard3.Flex` with 1 OCPU, 2 x86 vCPUs, 16 GB of
memory, and 1 Gbps networking. A five-second sample showed 67% to 100% idle CPU,
about 13 GB of available memory, and no swap use. Those observations do not
prove long-term headroom, but they do rule out CPU or memory exhaustion as the
cause of the current outage.

The blocking failure is the root filesystem:

| Measure | Observed state |
| --- | ---: |
| Boot disk | 50.04 GB |
| Root logical volume | 31.61 GB |
| Root bytes available | 20,480 bytes |
| Root utilization | 100% |
| Root inode utilization | 98% |
| `/var/oled` available | 15.88 GB |
| `/opt/lumencore/out` | 15.73 GB |
| Government snapshots | 9.61 GB across 66,194 files |

`/var/oled` is reserved by Oracle Linux for diagnostics, crash data, and
Performance Co-Pilot data. It is not the recommended permanent home for
LumenCore evidence.

## Failure Evidence

- `luma-gateway` cannot start because the deployed runtime is missing
  `booth_public_contract`.
- `luma-paper-ticker` and `luma-symbol-awareness` are failing on
  `No space left on device`.
- `luma-dashboard-refresh` repeatedly exits because another loop is already
  running.
- Restart counters observed during the audit exceeded 285,000 for the gateway,
  137,000 for the paper ticker, and 168,000 for symbol awareness.
- Nginx is the active public edge on ports 80 and 443. The failed Caddy unit is
  stale and conflicts with Nginx, rather than serving production traffic.
- The public root answered, while selected dynamic evidence, health, and booth
  routes returned `502`.

The endpoint result is a point-in-time contract observation. It is not a score
for repository quality, scientific validity, company value, or performance.

## Storage Growth

Before the high-volume burst, the snapshot collector wrote roughly 85 MB to
92 MB and about 800 files per active day. It then produced burst days including:

| UTC date | Files | Bytes |
| --- | ---: | ---: |
| 2026-07-15 | 3,833 | 596,741,008 |
| 2026-07-16 | 28,616 | 4,665,759,316 |
| 2026-07-17 | 5,117 | 782,476,758 |
| 2026-07-18 | 9,967 | 1,352,156,783 |

The production collector therefore needs both byte and inode controls.
Increasing disk size without deduplication, retention, and burst alarms would
only postpone recurrence.

## Recommended Capacity

### Recovery Floor

Keep the current 1 OCPU and 16 GB memory. Expand the boot volume from 50 GB to
150 GB at Balanced performance, then extend the Oracle Linux root filesystem.

This is the fastest bounded recovery because Oracle supports online boot-volume
growth. Create a boot-volume backup first. A Linux resize still requires the
guest OS to recognize the larger disk and extend the partition, LVM, and XFS
filesystem. Oracle provides `oci-growfs` for this purpose.

Target after recovery:

- at least 20 GiB free on `/`;
- less than 70% root byte utilization;
- less than 70% root inode utilization;
- gateway, health, evidence, and booth contracts passing;
- no service in an unbounded restart loop.

### Growth-Safe Layout

The recommended durable layout is:

| Resource | Target | Purpose |
| --- | ---: | --- |
| Compute | 1 OCPU, 16 GB | Public gateway and bounded scheduled services |
| Boot volume | 100 to 150 GB, Balanced | OS, packages, application, logs |
| Data block volume | 200 GB, Balanced | `/opt/lumencore/out` active evidence |
| Object Storage | Lifecycle-managed | Immutable archive and older snapshots |

Moving `/opt/lumencore/out` to its own block volume isolates evidence growth
from the OS and public edge. Keep active/recent artifacts on Balanced block
storage. Copy sealed older artifacts to private Object Storage only after a
manifest, hashes, counts, restore instructions, and access controls exist.

Do not delete the source tree until the new volume survives a mount validation,
service validation, external route probe, and reboot validation.

### Compute Scale Gate

Do not increase OCPUs or memory now. Reconsider compute only after seven days of
valid monitoring with the disk incident repaired. Scale when one of these
conditions is sustained:

- CPU above 70% for 15 minutes while useful work is running;
- memory above 80% or sustained swap activity;
- queue age violates an explicit service objective;
- request latency violates an explicit service objective;
- a bounded benchmark shows that more compute improves the named workflow.

For heavy simulations or benchmark sweeps, prefer a separate worker over
competing with the public gateway on one instance.

## Estimated List Cost

These are public Oracle list-price estimates using 730 hours per month. They
exclude taxes, backups, Object Storage, outbound transfer, support, discounts,
free allowances, and account-specific credits. The Oracle Console estimate is
the action-time authority.

| Configuration | Estimated monthly list cost | Delta from current |
| --- | ---: | ---: |
| Current Standard3 1 OCPU / 16 GB + 50 GB Balanced | $64.02 | - |
| Same compute + 150 GB Balanced boot | $69.59 | +$5.57 |
| Same compute + 100 GB boot + 200 GB Balanced data | $77.94 | +$13.92 |
| Standard3 2 OCPU / 24 GB + growth-safe storage | $127.69 | +$63.67 |

The 2 OCPU option is not supported by current utilization evidence.

`VM.Standard.E4.Flex` can be less expensive at the same x86 resource level, but
a shape change is a separate maintenance event and must be checked against
regional capacity, image compatibility, account pricing, and rollback options.
Ampere A1 is an ARM architecture migration, not an in-place cost toggle. The
current x86 virtual environment includes compiled packages and must not be
assumed compatible.

## Required Controls

1. Create and confirm a current boot-volume backup before any resize.
2. Stop or rate-limit failing restart loops before repair work.
3. Expand storage before deploying the gateway repair.
4. Apply the exact runtime dependency repair and content-addressed snapshot
   controls from the reviewed branch.
5. Bring services back one at a time and verify their bounded contracts.
6. Alert at 70%, 80%, and 90% for both filesystem bytes and inodes.
7. Alert on restart rate, not only active/failed state.
8. Track snapshot files and bytes per day and alert on an absolute burst or a
   multiple of the rolling median.
9. Keep at least 20 GiB free on the root filesystem.
10. Test one restore from backup before treating the backup policy as proven.

## Approval Boundary

This audit made no production changes. Each of the following remains
action-time approval gated:

- creating a billable backup or volume;
- changing a boot-volume size or performance level;
- attaching or mounting a block volume;
- stopping, starting, restarting, or disabling a production service;
- moving, compressing, archiving, or deleting evidence;
- editing `/etc/fstab`, LVM, XFS, Nginx, DNS, or certificates;
- deploying the repair branch;
- changing instance shape, OCPUs, or memory;
- rebooting the instance.

## Sources

- Live OCI instance metadata and read-only SSH inspection at the observation
  timestamp.
- Oracle Compute shapes:
  https://docs.oracle.com/en-us/iaas/Content/Compute/References/computeshapes.htm
- Oracle online volume resizing:
  https://docs.oracle.com/en-us/iaas/Content/Block/Tasks/update-online-resize-block-boot-volume.htm
- Oracle Linux `oci-growfs`:
  https://docs.oracle.com/en-us/iaas/oracle-linux/oci/oci-utilities-reference.htm
- Oracle block-volume performance:
  https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/blockvolumeperformance.htm
- Oracle boot-volume backups:
  https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/bootvolumebackups.htm
- Oracle Object Storage lifecycle policies:
  https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/usinglifecyclepolicies.htm
- Oracle public IaaS pricing:
  https://www.oracle.com/cloud/iaas-paas/
