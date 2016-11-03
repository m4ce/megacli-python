#!/usr/bin/env python
#
# __init__.py
#
# Author: Matteo Cerutti <matteo.cerutti@hotmail.co.uk>
#

import os
import re
import subprocess

class MegaCLI:
  def __init__(self, cli_path = '/opt/MegaRAID/MegaCli/MegaCli64'):
    self.cli_path = cli_path

    if not os.path.exists(cli_path):
      raise RuntimeError('{0} not found'.format(cli_path))

  def execute(self, cmd):
    proc = subprocess.Popen("{0} {1}".format(self.cli_path, cmd), shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = proc.communicate()

    if proc.returncode:
      raise RuntimeError('MegaCli returned a non-zero exit code ({0}) - Error: {1}'.format(proc.returncode, err.rstrip()))
    else:
      return [re.sub(':$', '', re.sub('\s*:\s*', ':', re.sub('(^\s*|\s*$)', '', line)).lower()) for line in filter(None, out.rstrip().split("\n"))]

  def __to_property(self, key, value):
    k = key.replace(' ', '_').replace("'s", '').replace('.', '').replace('/', '_')

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
    m = re.match('^(\d+)\s*(s|sec|secs|seconds|m|min|mins|minutes|h|hour|hours|d|day|days)', value)
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

        m = re.match('^enclosure (\d+)', line)
        if m:
          if 'id' in enc:
            ret.append(enc)
            enc = {'adapter_id': adapter_id}

          enc['id'] = int(m.group(1))
          continue

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
    ret = []

    data = self.execute("-LDInfo -LAll -aAll")
    if data:
      adapter_id = None
      ld = {}

      for line in data:
        m = re.match('^adapter (\d+) -- virtual drive information$', line)
        if m:
          if 'adapter_id' in ld and ld['adapter_id'] != None:
            ret.append(ld)
            ld = {}

          ld['adapter_id'] = int(m.group(1))
          adapter_id = ld['adapter_id']
          continue

        m = re.match('^virtual drive:(\d+)', line)
        if m:
          if 'id' in ld and ld['id'] != None:
            ret.append(ld)
            ld = {'adapter_id': adapter_id}

          ld['id'] = int(m.group(1))
          continue

        fields = line.split(':', 1)
        if len(fields) > 1:
          k, v = self.__to_property(*fields)

          if k == 'exit_code':
            continue

          ld[k] = v

      if len(ld):
        ret.append(ld)

    return ret

  def physicaldrives(self):
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

        m = re.match('^enclosure device id:(\d+)', line)
        if m:
          if 'enclosure_id' in pd:
            ret.append(pd)
            pd = {'adapter_id': adapter_id}

          pd['enclosure_id'] = int(m.group(1))
          continue

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
    ret = []

    data = self.execute("-AdpBbuCmd  -aAll")
    if data:
      adapter_id = None
      bbu = {}

      for line in data:
        m = re.match('^BBU status for Adapter: (\d+)', line)
        if m:
          if 'adapter_id' in pd:
            ret.append(bbu)
            bbu = {}

          bbu['adapter_id'] = int(m.group(1))
          adapter_id = bbu['adapter_id']
          continue

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
    ret = []

    data = self.execute("-AdpAllInfo -aAll")
    if data:
      adapter_id = None
      adapter = {}

      for line in data:
        m = re.match('^adapter #(\d+)', line)
        if m:
          if 'id' in adapter:
            ret.append(adapter)
            adapter = {}

          adapter['id'] = int(m.group(1))
          continue

        fields = line.split(':', 1)
        if len(fields) > 1:
          k, v = self.__to_property(*fields)

          if k == 'exit_code':
            continue

          adapter[k] = v

      if len(adapter):
        ret.append(adapter)

    return ret
