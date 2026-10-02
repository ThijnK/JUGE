#!/usr/bin/env python3
"""Read-only prerequisites and machine records; never changes host settings."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time


def output(command):
    value = subprocess.check_output(command, stderr=subprocess.PIPE, timeout=30)
    # Windows tools invoked through WSL may emit UTF-16LE.
    return value.decode('utf-16le' if b'\x00' in value else 'utf-8', errors='replace').strip('\ufeff \r\n')


def container_user():
    """Match host ownership without chmod/chown or privileged worker containers."""
    return ['--user=' + str(os.getuid()) + ':' + str(os.getgid()), '-e', 'HOME=/tmp', '-e', 'MAVEN_CONFIG=/tmp/.m2']


def check_capacity(info, config):
    jobs = max(config['generation_jobs'], config['measurement_jobs'])
    if min(jobs, config['generation_jobs'], config['measurement_jobs'], config['cpus'], config['memory_gb']) < 1:
        raise ValueError('Resource limits and job counts must be positive.')
    if jobs * config['cpus'] > info['NCPU'] or (jobs * config['memory_gb'] + 1) * 1024**3 > info['MemTotal']:
        raise ValueError('Frozen concurrency exceeds Docker resources including 1 GiB memory headroom. Choose resources explicitly before preparation.')


def optional(command):
    try:
        return {'value': output(command)}
    except (OSError, subprocess.SubprocessError) as e:
        return {'unavailable': str(e)}


def inspect_host(directory, config):
    if sys.version_info < (3, 9):
        raise ValueError('Host Python 3.9+ required; use a separate interpreter or virtual environment.')
    if platform.system() not in ('Linux', 'Darwin'):
        raise ValueError('Run inside Linux/WSL2 or macOS, not a Windows Python interpreter.')
    directory = Path(directory).resolve()
    existing = directory
    while not existing.exists():
        existing = existing.parent
    if not existing.is_dir() or not os.access(existing, os.W_OK | os.X_OK):
        raise ValueError('Output parent is not a writable directory: ' + str(existing))
    wsl = platform.system() == 'Linux' and 'microsoft' in platform.release().lower()
    if wsl and (directory == Path('/mnt') or any(str(directory).startswith('/mnt/' + drive + '/') or directory == Path('/mnt/' + drive) for drive in 'abcdefghijklmnopqrstuvwxyz')):
        raise ValueError('WSL checkout/results must be in the Linux filesystem, not a Windows drive mount.')
    if wsl and platform.release().lower().endswith('-microsoft'):
        raise ValueError('WSL2 required; detected a WSL1 kernel.')
    try:
        info = json.loads(output(['docker', 'info', '--format', '{{json .}}']))
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        raise ValueError('Docker must be running and reachable in this terminal: ' + str(e)) from e
    if info.get('OSType') != 'linux':
        raise ValueError('Docker must use Linux containers.')
    check_capacity(info, config)
    disk = shutil.disk_usage(existing)
    if disk.free < 10 * 1024**3:
        raise ValueError('At least 10 GiB free storage required before preparation.')
    record = dict(captured_at=time.time(), python=dict(version=platform.python_version(), executable=sys.executable),
                  host=dict(name=platform.node(), system=platform.system(), release=platform.release(), architecture=platform.machine(), logical_processors=os.cpu_count()),
                  directory=str(directory), disk=dict(total_bytes=disk.total, free_bytes=disk.free),
                  operator=dict(uid=os.getuid(), gid=os.getgid()), resources=config,
                  docker={k: info.get(k) for k in ('ServerVersion','Architecture','OSType','OperatingSystem','NCPU','MemTotal','Driver','CgroupVersion')},
                  docker_context=output(['docker','context','show']), docker_version=optional(['docker','version','--format','{{json .}}']),
                  containers=optional(['docker','ps','--format','{{json .}}']), warnings=[])
    if info.get('Architecture') not in ('x86_64','amd64'):
        record['warnings'].append('Linux AMD64 execution uses emulation on this Docker architecture.')
    if platform.system() == 'Linux':
        record['cpu'] = optional(['lscpu','-J'])
        record['memory'] = Path('/proc/meminfo').read_text()
        record['distribution'] = Path('/etc/os-release').read_text()
        record['filesystem'] = optional(['findmnt','-J','-T',str(existing)])
        record['processes'] = optional(['ps','-eo','comm,pcpu,pmem','--sort=-pcpu'])
        memory_kb = next(int(line.split()[1]) for line in record['memory'].splitlines() if line.startswith('MemTotal:'))
        record['host']['installed_or_vm_memory_bytes'] = memory_kb * 1024
    else:
        record['cpu'] = optional(['sysctl','-n','machdep.cpu.brand_string'])
        record['physical_cores'] = optional(['sysctl','-n','hw.physicalcpu'])
        record['installed_memory_bytes'] = optional(['sysctl','-n','hw.memsize'])
        record['power'] = optional(['pmset','-g','custom'])
    if wsl:
        record['wsl'] = dict(distribution=os.environ.get('WSL_DISTRO_NAME'), version=optional(['wsl.exe','--version']), distributions=optional(['wsl.exe','--list','--verbose']))
        record['windows'] = optional(['powershell.exe','-NoProfile','-NonInteractive','-Command',
            "$cpu=Get-CimInstance Win32_Processor; $os=Get-CimInstance Win32_OperatingSystem; $ram=Get-CimInstance Win32_PhysicalMemory; "
            "$cfg=Join-Path $env:USERPROFILE '.wslconfig'; "
            "@{cpu=@($cpu|Select-Object Name,NumberOfCores,NumberOfLogicalProcessors); ram_bytes=($ram|Measure-Object Capacity -Sum).Sum; "
            "windows=($os|Select-Object Caption,Version,BuildNumber); power_scheme=(powercfg /getactivescheme|Out-String); "
            "sleep=(powercfg /query SCHEME_CURRENT SUB_SLEEP|Out-String); "
            "workloads=@(Get-CimInstance Win32_PerfFormattedData_PerfProc_Process | Where-Object {$_.Name -notin '_Total','Idle'} | "
            "Sort-Object PercentProcessorTime -Descending | Select-Object -First 12 Name,PercentProcessorTime,WorkingSetPrivate); "
            "wslconfig=$(if(Test-Path -LiteralPath $cfg){Get-Content -LiteralPath $cfg -Raw}else{$null})} | ConvertTo-Json -Depth 5"])
        if 'unavailable' in record['windows']:
            record['warnings'].append('Windows hardware/power information unavailable; record it manually in operator-log.md.')
    record['warnings'].append('Keep the computer awake and Docker/WSL running; inspect competing workloads and leave Windows/WSL headroom. CPU quotas do not dedicate cores.')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path.cwd())
    for name, default in [('generation-jobs',1),('measurement-jobs',1),('cpus',2),('memory-gb',4)]:
        parser.add_argument('--'+name,type=int,default=default)
    args=parser.parse_args()
    try:
        report=inspect_host(args.directory,{k:getattr(args,k) for k in ('generation_jobs','measurement_jobs','cpus','memory_gb')})
    except ValueError as e:
        parser.exit(2,str(e)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
