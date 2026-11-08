# Historical local D101 verification — 2026-09-08

This translates the original local record; it does not report a new run.

2 source tests passed with `mmay test . --engine both`. Acceptance covered
26 exact status/stdout/stderr scenarios in VM, Native Debug and Native
Release (denied builds used VM and Native Release), plus 3 closed pipes.
Cases include Unicode, CRLF, final lines, limits, errors, symlinks, capability
denial and 2097152-byte input. Frequency/logstats additionally cover 4096
distinct keys. Input files remained unchanged.

| Scenario | Native Release | VM |
|---|---:|---:|
| 2 MiB, median of 3 runs | 71.94 ms | 420.53 ms |
| 20 MiB, one run | 662.53 ms | 2051.80 ms |
| Peak RSS at 20 MiB | 37.36 MiB | 59.48 MiB |

Repeated test-both cycle: 366.14 ms. The first native execution immediately
after build was **378.37 ms**, above the fixed 100 ms budget; subsequent
executions met it. Control C17 programs without Marimay spent 370–512 ms before
main, but the exact startup subsystem responsible was not established.
First-execution performance acceptance remained blocked. Budgets, data and
macOS security settings were unchanged.

The host was macOS arm64, Release compiler with D101, managed heap 32 MiB,
with sequential measurements after compiler verification and ordinary desktop
background applications. This was not a disk-cold/fully idle-host study or
Tier 1-complete evidence. The 2 MiB medians do not characterize every format
or key distribution.

Reports: `build/acceptance/report.json` and `build/measure-1788863930152738000/report.json`.
Snapshots/hashes were also recorded in the language repository under
`docs/implementation/evidence/cp42-file-lines-2026-09-08.json`.
Compiler SHA-256: `076f9fce9bec61bb1fc7e4cf54934311a893246dcdd230c830c9b62111bcaf9c`.
Native SHA-256: `6ef5018294646e225c11ad4332cbba488b17fc009d0cbc35b406cf6e7b1624e5`.
Other open gates are listed in `ERGONOMICS.md` and the CP42 portfolio.
