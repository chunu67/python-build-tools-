import os
from buildtools.bt_logging import log
from buildtools.os_utils import cmd, ENV

def configure_distcc(cfg):
    global ENV
    with log.info('Configuring distcc...'):
        if not cfg.get('env.distcc.enabled', False):
            log.info('distcc disabled, skipping.')
            return
        distcc_hosts = []
        english_hosts = []
        maxjobs = 0
        canpump = False
        for hostname, hostcfg in cfg['env']['distcc']['hosts'].items():
            h = hostname
            info_e = []
            if 'max-jobs' in hostcfg:
                njobs = hostcfg.get('max-jobs', 0)
                if njobs > 0:
                    h += '/' + str(njobs)
                    info_e += ['{} max jobs'.format(njobs)]
                    maxjobs += njobs
            if 'opts' in hostcfg:
                h += ',' + ','.join(hostcfg['opts'])
                info_e += ['with options: ({})'.format(', '.join(hostcfg['opts']))]
                # Check for lzo & cpp before permitting distcc-pump.
                if 'lzo' in hostcfg['opts'] and 'cpp' in hostcfg['opts']:
                    canpump = True
            if len(info_e) > 0:
                english_hosts += ['* {}: {}'.format(hostname, ', '.join(info_e))]
                
            distcc_hosts += [h]
        if len(distcc_hosts) > 0:
            with log.info('Compiling with {} hosts:'.format(len(distcc_hosts))):
                for hostline in english_hosts:
                    log.info(hostline)
            log.info('Max jobs....: {0}'.format(maxjobs))
            cfg['env']['make']['jobs'] = maxjobs
            log.info('Pump enabled: {0}'.format(bool2yn(maxjobs > 0 and canpump)))
            if maxjobs > 0 and canpump:
                cfg['bin']['make'] = '{pump} {make}'.format(pump=cfg.get('bin.pump', 'distcc-pump'), make=cfg.get('bin.make', 'make'))
                
            ENV.set('DISTCC_HOSTS', ' '.join(distcc_hosts))
