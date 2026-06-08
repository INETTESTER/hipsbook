# Hipsbook Live Load Test

Load testing tool for Hipsbook HLS Live Streaming using Locust.

---

## Requirements

| Tool   | Version |
| ------ | ------- |
| Python | 3.10+   |
| Locust | 2.43.4  |

---

## Setup

```bash
git clone <repository-url>
cd hipsbook-live-loadtest

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
locust --version

mkdir -p results
```

For larger tests on macOS / Linux:

```bash
ulimit -n 65535
```

---

## Environment Setup

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

Edit `.env`:

```env
REQUEST_TIMEOUT_SECONDS=20

WEB_BASE=https://hipsbook.gbydigitaltech.co.th
STREAM_API_BASE=https://hips-stream.com

LIVE_ID=your-live-id
STREAM_API_KEY=your-stream-api-key

TEST_PROFILE=realistic

LIVE_DETAIL_MODE=cache
LIVE_DETAIL_CACHE_TTL_SECONDS=86400

# Required only when LIVE_DETAIL_MODE=off
MASTER_M3U8_URL=
```

Do not commit real `.env` files.

---

## Live Detail API Mode

The livestream detail API is used to get the HLS master playlist URL from `playbackHlsUrl`.

```text
/api/livestream/:id
```

You can control how this API is used with `LIVE_DETAIL_MODE`.

Recommended default:

```env
LIVE_DETAIL_MODE=cache
LIVE_DETAIL_CACHE_TTL_SECONDS=86400

# Required only when LIVE_DETAIL_MODE=off
MASTER_M3U8_URL=
```

| Mode     | Behavior                                                                          | When to Use                         |
| -------- | --------------------------------------------------------------------------------- | ----------------------------------- |
| `normal` | Poll `/api/livestream/:id` based on the configured interval                       | Full flow test                      |
| `cache`  | Call `/api/livestream/:id` only to get `playbackHlsUrl`, then reuse it from cache | Recommended for most HLS load tests |
| `off`    | Do not call `/api/livestream/:id` at all                                          | HLS-only test                       |

### Cache Mode

Use `cache` when you want Locust to get the latest `playbackHlsUrl` automatically but avoid polling `/api/livestream/:id` repeatedly.

```env
LIVE_DETAIL_MODE=cache
LIVE_DETAIL_CACHE_TTL_SECONDS=86400
MASTER_M3U8_URL=
```

Important:

```text
When using --processes, each Locust process has its own cache.
For example, --processes 4 may call /api/livestream/:id about once per process
when the cache is empty or expired.
```

### Off Mode

Use `off` only when you already know the HLS master playlist URL.

```env
LIVE_DETAIL_MODE=off
MASTER_M3U8_URL=https://hips-stream.com/hls/<stream-key>/index.m3u8
```

`MASTER_M3U8_URL` is the same value as `playbackHlsUrl` from the livestream detail API.

Example response:

```json
{
  "playbackHlsUrl": "https://hips-stream.com/hls/<stream-key>/index.m3u8"
}
```

You can also get it from Chrome DevTools:

```text
1. Open the live page
2. Open DevTools > Network
3. Filter by m3u8
4. Find index.m3u8
5. Copy the Request URL
```

---

## Test Profiles

| Profile     | Purpose                           |
| ----------- | --------------------------------- |
| `realistic` | Normal live viewer simulation     |
| `stress`    | Heavier traffic for limit testing |

Default:

```env
TEST_PROFILE=realistic
```

If `TEST_PROFILE` is already set in `.env`, you do not need to repeat it in every command.

Use `stress` only when intentionally testing bottlenecks, rate limits, or breaking points.

To temporarily override the profile without editing `.env`, prefix the command:

```bash
TEST_PROFILE=stress locust ...
```

---

## Commands

Make sure `.env` is configured before running commands.

The commands below use standard Locust CLI options such as:

```text
--headless
--users
--spawn-rate
--run-time
--html
--csv
--processes
```

Reference:

- Locust configuration options: https://docs.locust.io/en/stable/configuration.html

The commands below assume `TEST_PROFILE` is already set in `.env`.

Example:

```env
TEST_PROFILE=realistic
```

To run a different profile for one command only, prefix the command with `TEST_PROFILE=stress` or `TEST_PROFILE=realistic`.

### Smoke Test

Use this first to verify live ID, API key, and HLS access.

```bash
locust -f locustfile.py \
  --host=https://hipsbook.gbydigitaltech.co.th \
  --users 10 \
  --spawn-rate 1 \
  --run-time 1m \
  --headless \
  --html results/live_smoke.html \
  --csv results/live_smoke
```

---

### Baseline Test

Use this to measure normal behavior under low load.

```bash
locust -f locustfile.py \
  --host=https://hipsbook.gbydigitaltech.co.th \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m \
  --headless \
  --html results/live_baseline.html \
  --csv results/live_baseline
```

---

### Realistic Load Test

Use this to validate expected production traffic.

```bash
locust -f locustfile.py \
  --host=https://hipsbook.gbydigitaltech.co.th \
  --users <expected-concurrent-users> \
  --spawn-rate <users-per-second> \
  --run-time <duration> \
  --headless \
  --html results/live_realistic_load.html \
  --csv results/live_realistic_load
```

Example:

```bash
locust -f locustfile.py \
  --host=https://hipsbook.gbydigitaltech.co.th \
  --users 100 \
  --spawn-rate 10 \
  --run-time 15m \
  --headless \
  --html results/live_realistic_100.html \
  --csv results/live_realistic_100
```

---

### 500 Users Test

Use this only after smoke, baseline, and smaller realistic tests are stable.

```bash
ulimit -n 65535

locust -f locustfile.py \
  --host=https://hipsbook.gbydigitaltech.co.th \
  --users 500 \
  --spawn-rate 2 \
  --run-time 20m \
  --headless \
  --processes 4 \
  --html results/live_realistic_500_p4_cache.html \
  --csv results/live_realistic_500_p4_cache
```

Recommended `.env` for this test:

```env
TEST_PROFILE=realistic
LIVE_DETAIL_MODE=cache
LIVE_DETAIL_CACHE_TTL_SECONDS=86400
MASTER_M3U8_URL=
```

---

### Stress Test

Use this to find system limits.

If `.env` already has `TEST_PROFILE=stress`, you can remove `TEST_PROFILE=stress` from the command.  
If `.env` is set to `realistic`, keep `TEST_PROFILE=stress` to override it for this run only.

```bash
TEST_PROFILE=stress locust -f locustfile.py \
  --host=https://hipsbook.gbydigitaltech.co.th \
  --users <stress-users> \
  --spawn-rate <safe-spawn-rate> \
  --run-time 15m \
  --headless \
  --html results/live_stress_<users>.html \
  --csv results/live_stress_<users>
```

Example:

```bash
TEST_PROFILE=stress locust -f locustfile.py \
  --host=https://hipsbook.gbydigitaltech.co.th \
  --users 100 \
  --spawn-rate 10 \
  --run-time 10m \
  --headless \
  --html results/live_stress_100.html \
  --csv results/live_stress_100
```

---

## Optional: `--processes`

Start without `--processes`.

Use `--processes` only when one Locust process cannot generate enough load.

According to Locust documentation, distributed mode is used to run load generation across multiple processes or machines. The master process controls the test and workers run the users and report statistics back to the master.

`--processes` is a convenience option that forks Locust into multiple processes on one machine. Locust documentation notes that this option is experimental and is not available on Windows.

References:

- Distributed load generation: https://docs.locust.io/en/stable/running-distributed.html
- Locust configuration options: https://docs.locust.io/en/stable/configuration.html

Important:

```text
--users 200 --processes 4
```

means 200 users total, not 200 users per process.

Also note:

```text
LIVE_DETAIL_MODE=cache is process-level.
If you use --processes 4, each process has its own cache.
```

---

### Check CPU Cores

macOS:

```bash
sysctl -n hw.ncpu
```

Linux:

```bash
nproc
```

Windows PowerShell:

```powershell
Get-CimInstance Win32_Processor | Select-Object NumberOfCores,NumberOfLogicalProcessors
```

Use logical processors as the reference.

---

### Recommended Process Count

These values are practical starting points, not strict Locust limits.

Locust does not define one fixed `--processes` value for each CPU size. The correct value depends on the test script, network traffic, response sizes, machine resources, and target system behavior.

Use this only after confirming that a single Locust process is not enough.

References:

- Distributed load generation: https://docs.locust.io/en/stable/running-distributed.html
- Increasing request rate and high CPU warning: https://docs.locust.io/en/stable/increasing-request-rate.html
- Locust configuration options: https://docs.locust.io/en/stable/configuration.html

Suggested starting points:

| CPU Logical Cores | Suggested `--processes` |
| ----------------: | ----------------------: |
|           2 cores |              Do not use |
|           4 cores |                       2 |
|           6 cores |                   2 - 3 |
|           8 cores |                   3 - 4 |
|     10 - 12 cores |                   4 - 6 |
|          16 cores |                   6 - 8 |
|         24+ cores |                  8 - 12 |

Recommended rule:

```text
1. Start without --processes.
2. Monitor CPU usage, failure rate, and response time.
3. If CPU becomes high or RPS stops increasing, try --processes.
4. Start with about 50% of logical CPU cores.
5. Increase gradually only if the machine still has spare CPU.
```

If Locust shows a high CPU warning, Locust documentation recommends using distributed mode to utilize multiple CPU cores or multiple machines. It also recommends checking the test code and considering `FastHttpUser` when CPU usage is the bottleneck.

---

### Example

This example uses `TEST_PROFILE=stress` because process scaling is usually needed during heavier tests.

```bash
TEST_PROFILE=stress locust -f locustfile.py \
  --host=https://hipsbook.gbydigitaltech.co.th \
  --users 200 \
  --spawn-rate 10 \
  --run-time 10m \
  --headless \
  --processes 4 \
  --html results/live_stress_200.html \
  --csv results/live_stress_200
```

---

### When to Use `--processes`

Use it when:

- One Locust process has high CPU usage
- Requests per second stops increasing
- Increasing users does not create more traffic
- The machine still has spare CPU cores

Do not use `--processes` to fix:

- `401 / 403`
- `429`
- `5xx`
- Invalid API key
- HLS access issues

---

## Results

Locust can generate HTML and CSV reports using `--html` and `--csv`.

Reference:

- Locust configuration options: https://docs.locust.io/en/stable/configuration.html

Typical output files:

```text
results/<name>.html
results/<name>_stats.csv
results/<name>_stats_history.csv
results/<name>_failures.csv
```

Depending on the Locust version and runtime behavior, additional files such as exception reports may also be generated.

Use HTML for quick review and CSV for detailed analysis.

---

## Troubleshooting

The table below is a project-specific troubleshooting guide based on common HTTP and HLS load testing behavior.

| Problem                           | Check                                                                 |
| --------------------------------- | --------------------------------------------------------------------- |
| `401 / 403`                       | `STREAM_API_KEY`, `LIVE_ID`, request headers, HLS access rules        |
| `404`                             | HLS URL may be expired, live may not be active, or stream key changed |
| `429`                             | Reduce users, reduce spawn rate, use `TEST_PROFILE=realistic`         |
| `5xx`                             | Check server logs, reduce load, compare with previous stable result   |
| Users reach target but RPS is low | Normal for realistic HLS tests; 100 users does not mean 100 RPS       |

---

## Recommended Workflow

```text
1. Smoke Test
2. Baseline Test
3. Realistic Load Test
4. 500 Users Test if smaller tests are stable
5. Stress Test if needed
6. Review HTML and CSV reports
```

---

## Notes

- Do not commit real `.env` files.
- Do not hardcode `STREAM_API_KEY`.
- Use `TEST_PROFILE=realistic` for normal viewer simulation.
- Use `TEST_PROFILE=stress` only for limit testing.
- Use `LIVE_DETAIL_MODE=cache` to reduce repeated calls to `/api/livestream/:id`.
- Use `LIVE_DETAIL_MODE=off` only when you have a valid `MASTER_M3U8_URL`.
- For large-scale testing, prefer Locust distributed mode with `--master` and `--worker` instead of relying on a single machine.
- Reference: https://docs.locust.io/en/stable/running-distributed.html

---

## References

- Locust configuration options: https://docs.locust.io/en/stable/configuration.html
- Locust distributed load generation: https://docs.locust.io/en/stable/running-distributed.html
- Locust increasing request rate: https://docs.locust.io/en/stable/increasing-request-rate.html
- Locust API reference for `FastHttpUser`: https://docs.locust.io/en/stable/api.html
py -m pip install -r requirements.txt