# WikiLearn Plugin for [Tutor](https://docs.tutor.edly.io)

WikiLearn plugin for Tutor. If you want to set up WikiLearn, this is the first thing you'll want to install.

## Installation

```bash
git clone https://github.com/wikimedia/tutor-contrib-wikilearn.git
cd tutor-contrib-wikilearn/
make install
```

Installing this will also install the following dependencies:

- `tutor>=20.0.0,<21.0.0`
- `tutor-mfe>=20.0.0,<21.0.0`
- `tutor-forum>=20.0.0,<21.0.0`
- `tutor-notes>=20.0.0,<21.0.0`

Additionally, the following plugins will be installed:

- `tutor-indigo-wikilearn@git+https://github.com/wikimedia/tutor-indigo-wikilearn@develop#egg=tutor-indigo-wikilearn`
- `tutor-contrib-notifications@git+https://github.com/openedx/tutor-contrib-notifications.git@main#egg=tutor-contrib-notifications`

**TODO: Note:** Installing in `[release]` mode will install all custom plugins from their latest release.

## Usage

Enable the WikiLearn plugin and all its required plugins:

```bash
make setup
tutor dev launch
```

## For Development

The following instructions help you set up a local development environment for **Wikilearn**.

### 1. Installation

Install this plugin and its dependencies in editable mode:
```bash
make install
```
### 2. Cloning Dependencies
Before running setup, clone all related repositories one level above your tutor-contrib-wikilearn directory:

```bash
make clone-all
```

This will:
- Clone all Wikilearn-related repositories (including MFEs and edx-platform)
- Install the frontend-related plugins (frontend-plugins-wikilearn, tutor-indigo-wikilearn) in editable mode
- Mount the cloned repos automatically inside Tutor

You can also clone individual repos as needed:

```bash
make clone-edx-platform
make clone-messenger
make clone-discussions
make clone-features
```
### 3. Setup Tutor
Once all dependencies are cloned, configure Tutor and enable plugins:

```bash
make setup 
```
### 4. Mount openedx-wikilearn-features
For Tutor to recognize the openedx-wikilearn-features mount locally, you’ll need to create and enable a small custom Tutor plugin and add the following line:

```python
hooks.Filters.MOUNTED_DIRECTORIES.add_item(("openedx", "openedx-wikilearn-features"))
```
You can follow the official Tutor plugin development tutorial here:
[Tutor Plugin Development Guide](https://docs.tutor.edly.io/tutorials/plugin.html#plugin-development-tutorial)

### 5. Build Images and Run

After setup, build Tutor images and start the platform:

```bash
tutor dev launch 
```
### Optional Optimization
Since the Wikilearn MFE image is large, developers can **reduce build time** by adding the following optimization to their custom plugin as described in the same [Tutor plugin guide](https://docs.tutor.edly.io/tutorials/plugin.html#plugin-development-tutorial).

This helps skip unnecessary rebuilds during development.


## License

This software is licensed under the terms of the AGPLv3.
