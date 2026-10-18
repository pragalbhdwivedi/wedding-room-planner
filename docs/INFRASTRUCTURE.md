# Docker host preparation

Owner instruction: create a fresh Debian template with VMID 9002 and a separate dedicated application VM on the selected Proxmox node's local-lvm. The owner subsequently selected normal VLAN 1 and supplied the application VM's static address. Detailed addresses, MACs, management routes, and login inventory remain in Git-excluded local VM_NOTES and matching Proxmox Notes.

## Recorded resources

| Resource | Verified state |
| --- | --- |
| Template 9002, debian13-cloudinit | Debian 13.7 (trixie), amd64; 2 vCPU, 2 GiB fixed RAM, 8 GiB root disk; cloud-init; stopped template |
| VM 9601, wedding-room-planner | Full independent clone; 4 vCPU, 4 GiB fixed RAM, 40 GiB root disk; running dedicated Docker host |
| Disk placement | Root and cloud-init drives on owner-selected local-lvm; no Ceph or shared NAS disks used |
| Networking | Existing vmbr0 bridge, native/untagged VLAN 1; template DHCP, VM uses owner-supplied static /23 address |
| Access | Cloud-init login name retained from template 9001; existing Windows and WSL administrator public keys; both key logins and sudo verified |
| Passwords | No password created/reset; effective guest SSH password and keyboard-interactive authentication disabled; login password locked |
| QEMU guest agent | First-boot installation configured in prepared template image; active and verified in clone |
| Docker Engine | 29.9.1, official Docker Debian stable repository |
| Docker Compose | 5.6.0 |
| Docker Buildx | 0.38.0 |
| Startup | Docker enabled inside guest; automatic VM startup after hypervisor boot remains disabled until service deployment |

## Image provenance

Official source: [Debian 13 genericcloud amd64](https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2).

Downloaded image size: 342,818,816 bytes. SHA512 verified against Debian's HTTPS SHA512SUMS:

```text
ec584ccabfef7120b4c4f7482adf0e615894d9292cedec446b64194b951ebe5dd97c336b5dcbae458333764b0edd516334506017f33c4f2020ef8d38b569ffe3
```

The index supplied no detached checksum signature; no signature verification is claimed. qemu-img check passed. An isolated prepared copy adds first-boot qemu-guest-agent setup; the original download is retained unchanged. No hypervisor packages were installed. Existing source template 9001 was read only and its configuration hash was verified unchanged afterward.

Template 9001 had a cloud-init login name but no cloud-init SSH keys/password recorded. Its user name was retained; the owner's two existing administrator public keys were configured on the new template and clone. Private keys were never copied.

## Verified checks

- VM root filesystem expanded to the requested 40 GiB disk.
- Requested static address had no matching guest config or observed ARP-probe conflict before boot; gateway DNS queries succeeded.
- First boot completed with no provisioning errors; guest agent active.
- Windows and WSL SSH key authentication and passwordless sudo succeeded with a trusted guest host-key pin obtained through Proxmox.
- Docker service active and enabled; installed from Docker's official Debian apt repository with repository-scoped signing key.
- Isolated hello-world container passed with network disabled, read-only filesystem, dropped capabilities, no-new-privileges, and automatic removal.
- No containers or volumes were left after the initial infrastructure smoke check. Subsequent application work is recorded separately in STATUS.md.
- One graceful reboot passed: static address, SSH identity, guest agent, Docker Engine, and Compose available afterward.
- Complete non-secret handovers are maintained locally and in Proxmox Notes, with provider readback verification.

## Remaining limits

- Existing backup server was unreachable during inspection; neither new resource is included in a scheduled backup job. The owner subsequently deferred backup work under D26. Existing backup jobs were not changed.
- Cloud-init reports a deprecation notice for Proxmox's generated string user field. Its provisioning errors list is empty; future cloud-init compatibility still needs monitoring.
- The template itself was not booted; its first-boot behaviour was exercised through the full clone.
- This receipt covers infrastructure only; application implementation, checks and deployment are tracked in STATUS.md. Public ingress and user acceptance are not claimed here.
- Domain, HTTPS routing and backup policy remain separate work. This is a dedicated wedding-planner host, not a shared CI worker.

Installation reference: [Docker Engine on Debian](https://docs.docker.com/engine/install/debian/).
