# python-build-tools

A toolkit containing many powerful utilities, including:

 * OS utilities (buildtools.os_utils)
 * Indented logging with colorama support (buildtools.bt_logging.log)
 * The powerful Maestro build management system (buildtools.maestro)
 * A powerful VCS repository wrapper system (buildtools.repo)
 * A mess of other random things.

## os_utils
```python
from buildtools import os_utils

# Ensure test/ exists
os_utils.ensureDirExists('test')

# Get copy of current environmental variables.
ENV = os_utils.ENV.clone()

# Add .bin/ to the beginning of PATH in our virtual environment
ENV.prependTo('PATH', '.bin/')

# Remove any duplicate entries from PATH
ENV.removeDuplicatedEntries('PATH')

# Find gcc in our virtual environment (checks PATHEXT on Windows, too!)
# Returns the path to gcc, or None if it couldn't be found.
GCC = ENV.which('gcc')

# Ensure bash exists before continuing (same rules as above)
ENV.assertWhich('bash')

# Bring up gcc's help page. Crash if non-0 exit code, echo command to console, and output STDOUT/STDERR to console.
os_utils.cmd([GCC, '--help'], critical=True, echo=True, show_output=True)
```

## Logging
```python
from buildtools import log

def a():
  log.info('This will be indented if a() is called in a log block.')

log.info('No indentation, yet.')
with log.warning('A warning. Next line will be indented.'):
  log.error('Error!')
  with log.info('The following function\'s log output will be indented by another layer.')
    a()
    log.critical('So will %s!', 'this')
```

## Maestro
```python
from buildtools.maestro import BuildMaestro
from buildtools.maestro.fileio import ReplaceTextTarget
from buildtools.maestro.coffeescript import CoffeeBuildTarget
from buildtools.maestro.web import SCSSBuildTarget, SCSSConvertTarget

bm = BuildMaestro()

# Compile CoffeeScript to JS
bm.add(CoffeeBuildTarget('htdocs/js/vgws.js',                 ['coffee/src/vgws.coffee']))
bm.add(CoffeeBuildTarget('htdocs/js/editpoll.multichoice.js', ['coffee/editpoll.multichoice.coffee'], dependencies=['htdocs/js/vgws.js']))
bm.add(CoffeeBuildTarget('htdocs/js/editpoll.option.js',      ['coffee/editpoll.editpoll.coffee'], dependencies=['htdocs/js/vgws.js']))

# Convert CSS to SCSS
bm.add(SCSSBuildTarget('htdocs/css/style.css', ['style/style.scss'], [], import_paths=['style'], compass=True))

# Compile, taking dependencies into count when ordering operations.
bm.run()

# Same as above, but providing command line arguments such as --clean, and --rebuild.
bm.as_app()
```
