# FinalsPing

A lightweight, open-source ping overlay for **THE FINALS** on Windows.

FinalsPing automatically detects your match server and shows live latency in a transparent, movable overlay. It stops measuring when you leave a match and requires no Npcap or Wireshark.

## Download

Get **FinalsPing.exe** from [Releases](../../releases/latest). Run it, approve the Windows administrator prompt, and join a match.

## Features

- Live ping display with optional region and city details
- Ping-based colors or plain white text
- Movable, resizable overlay with screen-edge constraints and position lock
- System tray controls and automatic match detection
- Single executable; no additional runtime installation

## How it works

FinalsPing detects the active match server through Windows networking APIs.

- **Europe and North America:** When the match server supports QLKN on UDP port `7600`, the tool measures its round-trip time directly.
- **Other regions:** When direct QLKN is unavailable, FinalsPing measures a one-time handshake to the match server, subtracts `30 ms` as a calibration target, then selects the responding QLKN endpoint closest to that target. It measures the selected endpoint for the rest of the match.

The fallback is an **estimate**, not an official in-game ping reading. The 30 ms offset is empirical, and actual latency may differ. A timed-out probe displays `999ms`.

## Build

Requires Windows and Python 3 with Tkinter. Clone the repository and run:

```bat
build.bat
```

The standalone executable is generated at `dist\FinalsPing.exe`. Version tags trigger the included GitHub Actions release workflow.

## Privacy

No accounts, analytics, or telemetry. FinalsPing checks game-related network traffic, sends latency probes to the match server or QLKN endpoints, and uses `ipwho.is` to resolve the server's approximate location.

## Contributing

Forks, modifications, issues, and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License & disclaimer

[MIT License](LICENSE). FinalsPing is an independent community project and is **not affiliated with or endorsed by Embark Studios**. THE FINALS and related names belong to their respective owners.
