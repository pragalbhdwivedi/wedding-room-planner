# Implementation status

Baseline: 19 October 2026, Asia/Kolkata.

| Area | State | Evidence / limit |
| --- | --- | --- |
| Requirements and latest answers | Recorded | Canonical requirements and decision log in this repository |
| Workbook structural inventory | Recorded | Derived room counts/block/floor mapping; original attachment remains private |
| Access model | Confirmed requirement | Owner alone edits; family/reception viewers; not implemented |
| Docker host | Prepared and checked | Dedicated Debian VM, Docker/Compose installation and isolated smoke/reboot checks; see INFRASTRUCTURE.md |
| Application Docker delivery | Not implemented | No application Dockerfile, Compose deployment or image build |
| Technical stack and schema | Proposed design | No application code, migrations, or installed dependencies |
| UI / topology / mobile | Planned | No working screen or browser acceptance |
| Solver / shared rules | Planned | No solver execution or functional evidence |
| Rates / attendance | Recorded requirements | Known rates plus explicit provisional/unpriced items; no calculation implementation |
| Import/export / live views | Planned | No integration evidence |
| Backups / restore | Pending | New resources have no scheduled backup; existing backup server unreachable; no recovery test |
| CI | Not configured | Documentation review is not application CI |
| Application deployment | Not started | Host prepared; domain/HTTPS and application absent |
| Owner acceptance | Pending | No implementation to accept yet |

## Current scope

This repository establishes the source of truth requested by the owner. Dedicated infrastructure is now prepared under a separate explicit instruction. This does not represent a runnable application, a production application deployment, hotel-policy confirmation, or acceptance of the proposed application technology choices.

## Verification of this baseline

Initial documentation commit: `6f4f9174fc6f18d7c4f11caabdf397e6444fb610`.

- Local relative Markdown links and required-document presence: passed.
- Room-count arithmetic and category/floor reconciliation: passed.
- Exact staged list: 15 documentation/policy/template files; no source workbook, guest records, runtime data, or credentials included.
- Targeted public-content scan and Git whitespace check: passed. This is a bounded publication check, not a comprehensive security audit.
- [Remote repository](https://github.com/pragalbhdwivedi/wedding-room-planner): verified public, default branch main, owner pragalbhdwivedi.
- Remote main matched the initial commit, all 15 committed paths matched, and the public README was retrieved successfully.
- Application tests, Docker builds, database migrations, live deployment, and owner acceptance: not performed; no application exists yet.

This status receipt and the canonical README link were added in a follow-up documentation commit. Publication checks do not establish functional application readiness.

## Infrastructure follow-up

Owner-authorised Debian template 9002 and dedicated full clone 9601 were created. Host-only verification covers image checksums, independent local-lvm disks, guest network/disk expansion, both administrator keys, effective SSH policy, guest agent, Docker/Compose, isolated hello-world, and one graceful reboot. Full non-secret local and Proxmox handovers are read back and matched. Source template 9001 configuration remained unchanged. These checks are not application CI or owner acceptance. See INFRASTRUCTURE.md for versions and remaining limits.

## Next work

Begin application foundation implementation after the next implementation instruction: actual Docker application services, database migrations, owner login, and enforced view-only roles on the prepared host. Domain/HTTPS and backup protection still require completion before production use.
