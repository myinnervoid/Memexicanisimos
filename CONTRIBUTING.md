# Contributing to Memexicanisimos

We love your input! We want to make contributing to this project as easy and transparent as possible.

## Development Process

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the installer script still works on a clean system.
5. Issue that pull request!

## Local Testing

To test the installer locally without affecting your system, you can use a Docker container (like Ubuntu) or a virtual machine.

```bash
docker run -it --rm ubuntu:22.04 bash
# inside container, install curl, then run the installer
```

## Tool Development
The memory tool (`src/memex_tools.py`) should remain lightweight and dependency‑free (only `pydantic` is allowed). If you need additional libraries, discuss in an issue first.

## License
By contributing, you agree that your contributions will be licensed under the GPLv3 License.
