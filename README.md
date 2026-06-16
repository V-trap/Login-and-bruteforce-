# VTRAP

VTRAP is a multithreaded educational network login testing tool designed for security professionals, students, and lab environments. It supports multiple authentication protocols and helps users understand authentication mechanisms, security testing workflows, and credential validation processes in authorized environments.

> **Warning:** This tool is intended solely for systems you own or have explicit written permission to test. Unauthorized use may violate laws, regulations, or organizational policies.

## Features

* Multi-threaded testing for improved performance
* SSH authentication testing
* FTP authentication testing
* HTTP Basic Authentication testing
* HTTP Form-based Login testing
* Username and password wordlist support
* Single credential testing support
* Configurable connection timeouts
* Stop-on-success option
* Result export functionality
* Real-time progress tracking
* Colored terminal output

## Supported Services

| Service         | Default Port |
| --------------- | ------------ |
| SSH             | 22           |
| FTP             | 21           |
| HTTP Basic Auth | 80           |
| HTTP Form Login | 80           |

## Installation

### Requirements

* Python 3.8+
* Paramiko (for SSH testing)
* Requests (for HTTP testing)

### Install Dependencies

```bash
pip install paramiko requests
```

### Clone Repository

```bash
git clone https://github.com/yourusername/vtrap.git
cd vtrap
```

## Usage

### SSH Authentication Testing

```bash
python vtrap.py ssh://192.168.1.10 -l admin -P passwords.txt -t 8
```

### FTP Authentication Testing

```bash
python vtrap.py ftp://192.168.1.10 -L users.txt -P passwords.txt
```

### HTTP Basic Authentication

```bash
python vtrap.py http-basic://192.168.1.10 -l admin -P passwords.txt --path /admin
```

### HTTP Form Authentication

```bash
python vtrap.py http-form://192.168.1.10 \
    -l admin \
    -P passwords.txt \
    --path /login \
    --user-field username \
    --pass-field password \
    --fail-string "Invalid credentials"
```

## Command-Line Options

| Option      | Description              |
| ----------- | ------------------------ |
| `-l`        | Single username          |
| `-L`        | Username wordlist        |
| `-p`        | Single password          |
| `-P`        | Password wordlist        |
| `-t`        | Number of threads        |
| `-s`        | Custom port              |
| `--timeout` | Connection timeout       |
| `-f`        | Stop after first success |
| `-v`        | Verbose mode             |
| `-o`        | Save results to file     |

## Example

```bash
python vtrap.py ssh://10.10.10.10 \
    -L users.txt \
    -P passwords.txt \
    -t 10 \
    -f \
    -o results.txt
```

## Educational Use Cases

* Cybersecurity training labs
* Authentication security demonstrations
* Penetration testing practice environments
* Capture The Flag (CTF) exercises
* Network security education
* Authorized security assessments

## Disclaimer

This project is provided for educational and authorized security testing purposes only. Users are responsible for ensuring they have permission to test any target systems. The author assumes no liability for misuse, damage, or legal consequences resulting from the use of this software.

## License

MIT License

## Author

Created by Vtrap

---

**Use Responsibly. Test Only What You Own or Have Permission to Test.**
