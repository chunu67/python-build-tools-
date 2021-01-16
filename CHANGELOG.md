# 0.4.0 - IN DEV

* Removed PyYAML in favor of ruamel.yaml, which is YAML 1.2-compliant and updated more frequently.
* `os_utils._args2str()` now uses `shlex.quote` instead of a homebrew solution.
* Fix error regarding `__failed` attribute in some Maestro targets.

# 0.3.6 - July 13th, 2020

* Fix CopyFileTarget not accepting filename as target. **BREAKING CHANGE!**

# 0.3.5 - July 4th, 2020

* Fix lack of default values in maestro args.
* Fix crashes in Maestro.

# 0.3.4 - July 4th, 2020

* Fix Jinja2 rendering issues in BaseConfig.
* Fix default arguments to YAMLConfig being template_dir = `.`, which bugs out things that expect absolute pathing.

# 0.3.2 - June 19th, 2020

* Fix pathing issues with BaseConfig.

# 0.3.1 - June 19th, 2020

* Fixed debug spam in PipeReader

# 0.3.0 - June 11th, 2020

Python >=3.6 release. Change tracking begins.
