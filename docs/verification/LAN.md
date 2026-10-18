# LAN preview verification

Date: 19 October 2026, Asia/Kolkata. Owner instruction: D29.

Application code and deployed image tags: `7fee89fde677d594b2183c3e2cf6ec657467bf77`.

- Dedicated-VM Docker builds and clean PostgreSQL migration passed. The isolated suite reports 17 passed in 6.82 seconds; one existing upstream TestClient deprecation warning remains.
- [GitHub Actions run 39162980332](https://github.com/pragalbhdwivedi/wedding-room-planner/actions/runs/39162980332) passed for that source.
- All four actual application services are healthy. Web is published on the VM's explicit private IPv4 address, port 8080. API/database ports remain unpublished.
- From the owner's PC, direct LAN page and health requests returned HTTP 200. The page contains the application title, and unauthenticated inventory returned HTTP 401.
- Browser navigation directly to the LAN address rendered the real owner-setup form. No real credentials were entered during verification.
- Existing credential files and owner-setup state were preserved. Schema and persistent database volume are unchanged.
- LAN transport tests accept explicit private-IP/loopback origins, reject public/malformed origins and retain production HTTPS/Secure-cookie requirements. CSRF/origin and owner/viewer tests continue to pass.
- Private local and Proxmox handovers were updated together and provider readback compared. Existing provider text was preserved; its field length limit required a concise current-transport section.

The network address is kept in private runtime/handover records, not this public repository. The LAN URL supersedes the earlier PC-only forwarded preview URL.

This is an HTTP LAN preview: credentials and sessions are not encrypted in transit. Trusted HTTPS ingress remains pending. No internet forwarding, real-phone acceptance, backup/restore completion or owner acceptance is claimed. Temporary verification database services are removed after checks; the real application remains running.
