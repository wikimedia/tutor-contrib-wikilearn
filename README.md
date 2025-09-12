# WikiLearn Plugin for [Tutor](https://docs.tutor.edly.io)

WikiLearn plugin for Tutor. If you want to set up WikiLearn, this is the first thing you'll want to install.

## Installation

### For Development

```bash
git clone https://github.com/wikimedia/tutor-contrib-wikilearn.git
cd tutor-contrib-wikilearn/
pip install -e '.[dev]'
```

Installing this will also install the following dependencies:

- `tutor>=20.0.0,<21.0.0`
- `tutor-mfe>=20.0.0,<21.0.0`
- `tutor-forum>=20.0.0,<21.0.0`
- `tutor-notes>=20.0.0,<21.0.0`
- `tutor-contrib-aspects==2.4.0`

Additionally, the following custom plugins will be installed from their develop branch:

- `tutor-indigo-wikilearn@git+https://github.com/wikimedia/tutor-indigo-wikilearn@develop#egg=tutor-indigo-wikilearn`

**Note:** Installing in `[release]` mode will install all custom plugins from their latest release.

## Usage

Enable the WikiLearn plugin:

```bash
tutor plugins enable wikilearn
```

Then enable all WikiLearn required plugins:

```bash
tutor wikilearn enable
```

## License

This software is licensed under the terms of the AGPLv3.
