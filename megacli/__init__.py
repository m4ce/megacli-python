#!/usr/bin/env python
#
# __init__.py
#
# Author: Matteo Cerutti <matteo.cerutti@hotmail.co.uk>
#

import os
import re
import subprocess

class MegaCLIError(Exception):
  pass

class MegaCLI:
  def __init__(self, cli_path = '/opt/MegaRAID/MegaCli/MegaCli64'):
    """
    Construct a new 'MegaCLI' object

    :param cli_path: path to MegaCli executable (default: /opt/MegaRAID/MegaCli/MegaCli64)
    :return: nothing
    """
    self.cli_path = cli_path

    if not os.path.exists(cli_path):
      raise RuntimeError('{0} not found'.format(cli_path))

  def execute(self, cmd):
    """
    Execute a MegaCLI command

    :param cmd: command line arguments for MegaCLI
    :return: MegaCLI command output
    """
    proc = subprocess.Popen("{0} {1} -NoLog".format(self.cli_path, cmd), shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = proc.communicate()
    if isinstance(out, bytes):
      out = out.decode()
    if isinstance(err, bytes):
      err = err.decode()

    if proc.returncode:
      ex = MegaCLIError(err.rstrip())
      ex.exitcode = proc.returncode
      raise ex
    else:
      return [re.sub(':$', '', re.sub('\s*:\s*', ':', re.sub('(^\s*|\s*$)', '', line)).lower()) for line in filter(None, out.rstrip().split("\n"))]

  def __raid_level(self, level):
    """
    Map a RAID level string to a RAID level integer

    :param level: text RAID level
    :return: integer RAID level
    """

    levels = {
      'primary-0, secondary-0, raid level qualifier-0': 0,
      'primary-1, secondary-0, raid level qualifier-0': 1,
      'primary-5, secondary-0, raid level qualifier-3': 5,
      'primary-6, secondary-0, raid level qualifier-3': 6,
      'primary-1, secondary-3, raid level qualifier-0': 10,
    }

    if level in levels:
      return levels[level]
    else:
      return None

  def __to_property(self, key, value):
    """
    Decode raw MegaCLI key value pairs into properties

    :param key: raw property name
    :param value: raw property value
    :return: decoded property name and value
    """
    k = key.replace(' ', '_').replace("'s", '').replace('.', '').replace('/', '_').replace('&', 'and')

    if value == 'n/a' or value == 'none':
      return k, None

    if value == 'yes':
      return k, True

    if value == 'no':
      return k, False

    # deal with integers
    m = re.match('^(\d+)\s*%?$', value)
    if m:
      return k, int(m.group(1))

    # deal with floats
    m = re.match('^(\d+)(?:\.\d+)?\s*%?$', value)
    if m:
      return k, float(m.group(1))

    # deal with temperatures
    if re.match('.*temperature.*', key):
      m = re.match('^(\d+)\s*(?:c|degree celcius)', value)
      if m:
        return k, int(m.group(1))

    # deal with sizes
    m = re.match('^(\d+(?:\.\d+)?)\s*(b|kb|mb|gb|tb|pb)', value)
    if m:
      size = float(m.group(1))
      unit = m.group(2)

      multiplier = 1
      if unit == 'kb':
        multiplier = 1024
      elif unit == 'mb':
        multiplier = 1024 * 1024
      elif unit == 'gb':
        multiplier = 1024 * 1024 * 1024
      elif unit == 'tb':
        multiplier = 1024 * 1024 * 1024 * 1024
      elif unit == 'pb':
        multiplier = 1024 * 1024 * 1024 * 1024 * 1024

      return k, (size * multiplier)

    # deal with times
    m = re.match('^(\d+)\s*(s|sec|secs|seconds|m|min|mins|minutes|h|hour|hours|d|day|days)$', value)
    if m:
      time = int(m.group(1))
      unit = m.group(2)

      multiplier = 1
      if unit == 'm' or unit == 'min' or unit == 'minute' or unit == 'mins' or unit =='minutes':
        mutiplier = 60
      elif unit == 'h' or unit == 'hour' or unit == 'hours':
        mutiplier = 60 * 60
      elif unit == 'd' or unit == 'day' or unit == 'days':
        mutiplier = 60 * 60 * 24

      return k, (time * multiplier)

    return k, value

  def enclosures(self):
    """
    Get enclosures

    :return: a list of all available enclosures
    """
    ret = []

    data = self.execute("-EncInfo -aALL")
    if data:
      adapter_id = None
      enc = {}

      for line in data:
        m = re.match('^number of enclosures on adapter (\d+) --', line)
        if m:
          if 'adapter_id' in enc:
            ret.append(enc)
            enclosure = {}

          enc['adapter_id'] = int(m.group(1))
          adapter_id = enc['adapter_id']
          continue

        if adapter_id is not None:
          m = re.match('^enclosure (\d+)', line)
          if m:
            if 'id' in enc:
              ret.append(enc)
              enc = {'adapter_id': adapter_id}

            enc['id'] = int(m.group(1))
            continue

          if 'id' in enc:
            fields = line.split(':', 1)
            if len(fields) > 1:
              k, v = self.__to_property(*fields)

              if k == 'exit_code':
                continue

              enc[k] = v

      if len(enc):
        ret.append(enc)

    return ret

  def logicaldrives(self):
    """
    Get logical drives

    :return: a list of all configured logical drives
    """
    ret = []

    data = self.execute("-LDInfo -LAll -aAll")
    if data:
      adapter_id = None
      ld = {}

      for line in data:
        m = re.match('^adapter (\d+) -- virtual drive information$', line)
        if m:
          if 'adapter_id' in ld:
            ret.append(ld)
            ld = {}

          ld['adapter_id'] = int(m.group(1))
          adapter_id = ld['adapter_id']
          continue

        if adapter_id is not None:
          m = re.match('^virtual drive:(\d+)', line)
          if m:
            if 'id' in ld:
              ret.append(ld)
              ld = {'adapter_id': adapter_id}

            ld['id'] = int(m.group(1))
            continue

          if 'id' in ld:
            fields = line.split(':', 1)
            if len(fields) > 1:
              k, v = self.__to_property(*fields)

              if k == 'exit_code':
                continue

              if k == 'raid_level':
                level = self.__raid_level(v)
                if level is not None:
                  v = level

              ld[k] = v
              continue

      if len(ld):
        ret.append(ld)

    return ret

  def physicaldrives(self):
    """
    Get physical drives

    :return: a list of all installed physical drives
    """
    ret = []

    data = self.execute("-PDList -aAll")
    if data:
      adapter_id = None
      pd = {}

      for line in data:
        m = re.match('^adapter #(\d+)', line)
        if m:
          if 'adapter_id' in pd:
            ret.append(pd)
            pd = {}

          pd['adapter_id'] = int(m.group(1))
          adapter_id = pd['adapter_id']
          continue

        if adapter_id is not None:
          m = re.match('^enclosure device id:(\d+)', line)
          if m:
            if 'enclosure_id' in pd:
              ret.append(pd)
              pd = {'adapter_id': adapter_id}

            pd['enclosure_id'] = int(m.group(1))
            continue

          if 'enclosure_id' in pd:
            fields = line.split(':', 1)
            if len(fields) > 1:
              k, v = self.__to_property(*fields)

              if k == 'exit_code':
                continue

              pd[k] = v

      if len(pd):
        ret.append(pd)

    return ret

  def bbu(self):
    """
    Get battery backup units

    :return: a list of all installed BBUs
    """
    ret = []

    data = self.execute("-AdpBbuCmd  -aAll")
    if data:
      bbu = {}

      for line in data:
        m = re.match('^bbu status for adapter:(\d+)', line)
        if m:
          if 'adapter_id' in bbu:
            ret.append(bbu)
            bbu = {}

          bbu['adapter_id'] = int(m.group(1))
          continue

        if 'adapter_id' in bbu:
          fields = line.split(':', 1)
          if len(fields) > 1:
            k, v = self.__to_property(*fields)

            if k == 'exit_code':
              continue

            bbu[k] = v

      if len(bbu):
        ret.append(bbu)

    return ret

  def adapters(self):
    """
    Get MegaRAID adapters

    :return: a list of all installed MegaRAID adapters
    """
    ret = []

    data = self.execute("-AdpAllInfo -aAll")
    if data:
      adapter_id = None
      adapter = {}

      for line in data:
        m = re.match('^adapter #(\d+)', line)
        if m:
          if 'id' in adapter:
            ret.append(adapter)a
            adapter = {}

          adapter['id'] = int(m.group(1))
          continue

        if 'id' in adapter:
          fields = line.split(':', 1)
          if len(fields) > 1:
            k, v = self.__to_property(*fields)

            if k == 'exit_code':
              continue

            adapter[k] = v

      if len(adapter):
        ret.append(adapter)

    return ret

  def create_ld(self, raid_level, devices, adapter, write_policy = None, read_policy = None, cache_policy = None, cached_bad_bbu = None, size = None, stripe_size = None, hot_spares = [], after_ld = None, force = False):
    """
    Create a new logical drive

    :param raid_level: type string, specifies the RAID level. Valid arguments: 0, 1, 5 or 6.
    :param devices: type list, specifies the drive enclosures and slot numbers to construct the drive group. E.g.: ['E0:S1', E1:S1, ..]
    :param write_policy: type string, specifies the device write policy. Valid arguments: WT (write through) or WB (write back)
    :param read_policy: type string, specifies the device read policy. Valid arguments: NORA (no read ahead), RA (read ahead), ADRA (adaptive read ahead).
    :param cache_policy: type string, specifies the device cache policy. Valid arguments: Direct, Cached.
    :param cached_bad_bbu: type bool, specifies whether to use write cache when BBU is bad.
    :param size: type int, specifies the capacity for the virtual drive in MB.
    :param stripe_size: type int, specifies the stripe size. Valid arguments: 8, 16, 32, 64, 128, 256, 512, or 1024.
    :param hot_spares: type list, specifies the device hot spares. E.g.: ['E5:S5', ..]
    :param after_ld: type string, specifies which free slot should be used.
    :param force: type bool, whether to force or not the creation of the logical device
    :return: MegaCLI command output
    """
    cmd = []

    if isinstance(raid_level, int):
      if raid_level not in [0, 1, 5, 6]:
        raise ValueError("Logical drive's RAID level must be one of 0, 1, 5 or 6")
    else:
      raise ValueError("Logical drive's RAID level must be type int")

    if not isinstance(devices, list):
      raise ValueError("Logical drive's devices must be type list")

    cmd.append("-R{0}[{1}]".format(raid_level, ','.join(devices)))

    if isinstance(adapter, int):
      cmd.append('-a{0}'.format(adapter))
    else:
      raise ValueError("Logical drive's adapter ID must be type int")

    if write_policy:
      if write_policy not in ['WT', 'WB']:
        raise ValueError("Logical drive's write policy must be either WT (write through) or WB (write back)")
      else:
        cmd.append(write_policy)

    if read_policy:
      if read_policy not in ['NORA', 'RA', 'ADRA']:
        raise ValueError("Logical drive's read policy must be one of NORA (no read ahead), RA (read ahead) or ADRA (adaptive read ahead)")
      else:
        cmd.append(read_policy)

    if cache_policy:
      if cache_policy not in ['Direct', 'Cached']:
        raise ValueError("Logical drive's cache policy can be either Direct or Cached")
      else:
        cmd.append(cache_policy)

    if cached_bad_bbu is not None:
      if isinstance(cached_bad_bbu, bool):
        if cached_bad_bbu:
          cmd.append('CachedBadBBU')
        else:
          cmd.append('NoCachedBadBBU')
      else:
        raise ValueError("Logical drive's cached bad bbu flag must be type bool")

    if size:
      if isinstance(size, int):
        cmd.append("-sz{0}".format(size))
      else:
        raise ValueError("Logical drive's size must be type int")

    if stripe_size:
      if isinstance(stripe_size, int):
        if stripe_size in [8, 16, 32, 64, 128, 256, 512, 1024]:
          cmd.append("-strpsz{0}".format(stripe_size))
        else:
          raise ValueError("Logical drive's stripe size must be one of 8, 16, 32, 64, 128, 256, 512, 1024")
      else:
        raise ValueError("Logical drive's stripe size must be type int")

    if isinstance(hot_spares, list):
      if len(hot_spares) > 0:
        cmd.append("-Hsp[{0}]".format(','.join(hot_spares)))
    else:
      raise ValueError("Logical drive's hot spares must be type list")

    if after_ld:
      cmd.append("-afterLd {0}".format(after_ld))

    if isinstance(force, bool):
      if force:
        cmd.append('-Force')
    else:
      raise ValueError("Logical drive's force flag must be type bool")

    return self.execute("-CfgLDAdd {0}".format(' '.join(cmd)))

  def remove_ld(self, drive, adapter, force = False):
    """
    Delete a logical drive

    :param drive: type int, specifies the drive to remove
    :param adapter: type int, specifies the drive's controller
    :param force: type bool, specifies whether to force or not the removal of the drive
    :return: MegaCLI command output
    """
    cmd = []

    cmd.append("-L{0}".format(device))

    if isinstance(adapter, int):
      cmd.append('-a{0}'.format(adapter))
    else:
      raise ValueError("Logical drive's adapter ID must be type int")

    if isinstance(force, bool):
      if force:
        cmd.append('-Force')
    else:
      raise ValueError("Logical drive's force flag must be type bool")

    return self.execute("-CfgLdDel {0}".format(' '.join(cmd)))

