
import sys
import os
from buildtools.bt_logging import log

cmd_output = None


def InstallDpkgPackages(packages):
    import apt  # IGNORE:import-error
    with log.info('Checking dpkg packages...'):
        cache = apt.Cache()
        num_changes = 0
        with cache.actiongroup():
            for pkg in packages:
                if pkg not in cache:
                    log.critical('UNKNOWN APT PACKAGE {}!'.format(pkg))
                    sys.exit(1)
                package = cache[pkg]
                if not package.is_installed:
                    package.mark_install()
                    num_changes += 1
        if num_changes == 0:
            log.info('No changes required, skipping.')
            return

        cache.commit(apt.progress.text.AcquireProgress(),
                     apt.progress.base.InstallProgress())


def GetDpkgShlibs(files):
    deps = {}
    stdout, stderr = cmd_output(['perl', os.path.join(scripts_dir, 'dpkg-dump-shpkgs.pl')] + files, critical=True)
    if stdout or stderr:
        for line in (stdout + stderr).split('\n'):
            line = line.strip()
            if line == '':
                continue
            # dpkg-dump-shpkgs.pl: warning: binaries to analyze should already
            # be installed in their package's directory
            if 'dpkg-dump-shpkgs.pl:' in line:
                (_, msgtype, msg) = [x.strip() for x in line.split(':')]
                if msg == 'binaries to analyze should already be installed in their package\'s directory':
                    continue
                if msgtype == 'warning':
                    log.warning(msg)
                elif msgtype == 'error':
                    log.error(msg)
                continue
            elif line.startswith('shlibs:'):
                # shlibs:Depends=libboost-context1.55.0,
                # libboost-filesystem1.55.0, libboost-program-options1.55.0,
                # ...
                lc = line.split('=', 1)
                assert len(lc) == 2
                assert not lc[0][7:].startswith(':')
                deps[lc[0][7:]] = [x.strip() for x in lc[1].split(',')]
            else:
                log.warning('UNHANDLED: %s', line)
    return deps


def DpkgSearchFiles(files):
    '''Find packages for a given set of files.'''

    stdout, stderr = cmd_output(['dpkg', '--search'] + files, critical=True)

    '''
    libc6:amd64: /lib/x86_64-linux-gnu/libc-2.19.so
    libcap2:amd64: /lib/x86_64-linux-gnu/libcap.so.2
    libcap2:amd64: /lib/x86_64-linux-gnu/libcap.so.2.24
    libc6:amd64: /lib/x86_64-linux-gnu/libcidn-2.19.so
    libc6:amd64: /lib/x86_64-linux-gnu/libcidn.so.1
    libcomerr2:amd64: /lib/x86_64-linux-gnu/libcom_err.so.2
    libcomerr2:amd64: /lib/x86_64-linux-gnu/libcom_err.so.2.1
    libc6:amd64: /lib/x86_64-linux-gnu/libcrypt-2.19.so
    libcryptsetup4:amd64: /lib/x86_64-linux-gnu/libcryptsetup.so.4
    libcryptsetup4:amd64: /lib/x86_64-linux-gnu/libcryptsetup.so.4.6.0
    libc6:amd64: /lib/x86_64-linux-gnu/libcrypt.so.1
    libc6:amd64: /lib/x86_64-linux-gnu/libc.so.6
    '''

    packages = []
    if stdout or stderr:
        for line in (stdout + stderr).split('\n'):
            line = line.strip()
            if line == '':
                continue

            chunks = line.split()
            # libc6:amd64: /lib/x86_64-linux-gnu/libc.so.6
            if len(chunks) == 2:
                pkgName = chunks[0][:-1]  # Strip ending colon
                if pkgName not in packages:
                    packages += [pkgName]
            else:
                log.error('UNHANDLED dpkg --search LINE (len == %d): "%s"', len(chunks), line)

    return packages
