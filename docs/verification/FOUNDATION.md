# Foundation verification receipt

Date: 19 October 2026 Asia/Kolkata. This is technical evidence, not owner acceptance.

## Source and images

- Application code/deployment: `0f826038da2248c4044dc2178bc743f77e68fafb`.
- Backend image ID: `sha256:4e6b6086158af703021451b6a28b3411633053adf00abd8c04de5f8f3acc6109`.
- Web image ID: `sha256:cadba8ac7c86227fa50d0c3a30d03e09d4b677c9f104c991bda96cadb0752b05`.
- Images are tagged with the application source revision. Base-image digests, npm lockfile and hashed Python requirements are committed.
- Database schema: `0001_foundation`.
- Environment: dedicated Debian 13 Docker VM, 4 vCPU / 4 GiB RAM. No application build ran on the owner's PC.

## Checks and results

| Check | Result / boundary |
| --- | --- |
| Compose configuration, API and compiled TypeScript/web builds | Passed on dedicated VM |
| Clean PostgreSQL 18 migration | Passed in isolated temporary test database |
| PostgreSQL integration suite | 16 passed in 7.06 seconds on application revision above |
| [GitHub Actions foundation checks](https://github.com/pragalbhdwivedi/wedding-room-planner/actions/runs/39161926597) | Passed for the same source revision; Docker web/backend/test builds, clean migration and integration suite |
| Single owner / concurrent setup / private key | Wrong/missing key rejected; exactly one concurrent setup succeeds; database rejects second owner and demotion/removal |
| Authentication and session controls | Passwords and stored session tokens hashed; expiry/logout, CSRF/origin, persistent throttle and access-change revocation checked |
| Viewer administration and disclosure | Family/reception mutations rejected by API; viewer inventory responses contain no cost fields; stale access edits rejected |
| Database privilege separation | Runtime role is not superuser; schema creation and audit update/delete rejected |
| Structural inventory | 50 hotel rooms total; 44 Wyndham, 20 Superior, 24 Premium, 20 ground-floor Wyndham rooms, four twin rooms, six unnamed second-hotel rooms and 12 separate staff beds |
| Browser interaction | Owner login/logout, floor filtering (44 to 20 ground-floor rooms), room details, Escape/focus restoration, property tabs and user forms checked with synthetic fixtures |
| Reception browser | View-only badge present; no cost panel or users/access button |
| Responsive browser | Nominal 1440x900 laptop and 390x844 phone viewports checked; phone table overflow fixed; document widths equal viewport widths after correction (1425 / 375 CSS px excluding scrollbar) |
| Browser console | No captured warning/error entries during final owner review |
| Real deployment | Four long-running services healthy; migration exited successfully; initial setup required; no real guest/user data entered |
| Persistence | At `e7cabaf95c79cbdfc044b16208b5bf9918be708e`, recreated the PostgreSQL container while retaining its named volume; controlled heartbeat marker, 50 rooms and 12 beds survived. Marker removed. Later UI/test-harness update uses the same schema and volume. |
| Cleanup | Temporary browser/test containers, database and QA tunnel removed; real application services remain healthy |
| Infrastructure handover | Complete local and Proxmox Notes updated and provider readback matched; source template 9001 config remained unchanged |

The suite reports one upstream Starlette TestClient deprecation warning about httpx. Tests pass; replacement test-client dependency compatibility is future maintenance. The initial import-path failure was corrected before the passing runs. No failed run is counted as passing evidence.

## Limits

No guest assignment, editable topology, reservation selection, solver, calculated costs, attendance, import/export or live-update workflows are claimed. The worker performs a heartbeat only. Physical adjacency and unresolved business rates remain open.

No real-phone network test or shared HTTPS ingress is claimed. Browser checks used responsive viewports through a private SSH-forwarded preview. The VM remains manually started (`onboot=0`) during this preview stage.

Backup was explicitly deferred by the owner. Container persistence does not demonstrate backup recovery. Real owner credentials and acceptance are supplied by the owner privately after technical delivery.
