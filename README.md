python-build-tools
==================

A toolkit containing many powerful utilities, including:

 * OS utilities (buildtools.os_utils)
 * Indented logging with colorama support (buildtools.bt_logging.log)
 * The powerful Maestro build management system (buildtools.maestro)
 * A powerful VCS repository wrapper system (buildtools.repo)
 * A mess of other random things.
 
Maestro
=======

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

### PMK FILES

# Tell Maestro what target types to recognize
bm.RecognizeType(SCSSBuildTarget)
bm.RecognizeType(SCSSConvertTarget)
bm.RecognizeType(CoffeeBuildTarget)
bm.RecognizeType(ReplaceTextTarget)

# Save previously-made rules to disk.
bm.saveRules('Makefile.pmk')

# Load previously-made rules.
bm.loadRules('Makefile.pmk')

### COMPILE
# Sort all targets by dependency
bm.run()
```