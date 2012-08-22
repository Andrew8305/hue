#!/usr/bin/env python
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import posixpath

from django.core import management
from django.core.management.base import NoArgsCommand

from hadoop import cluster

from oozie.conf import LOCAL_SAMPLE_DATA_DIR, LOCAL_SAMPLE_DIR
from oozie.models import Workflow


LOG = logging.getLogger(__name__)


class Command(NoArgsCommand):
  def handle_noargs(self, **options):
    remote_fs = cluster.get_hdfs()
    remote_dir = Workflow.objects.create_data_dir(remote_fs)

    # Copy sample binaries
    for demo in ('lib', 'pig'):
      local_dir = posixpath.join(LOCAL_SAMPLE_DIR.get(), demo)
      remote_data_dir = posixpath.join(remote_dir, demo)
      LOG.info('Copying workflows %s to %s\n' % (local_dir, remote_data_dir))
      copy_dir(local_dir, remote_fs, remote_data_dir)

    # Copy sample data
    local_dir = LOCAL_SAMPLE_DATA_DIR.get()
    remote_data_dir = posixpath.join(remote_dir, 'data')
    LOG.info('Copying data %s to %s\n' % (local_dir, remote_data_dir))
    copy_dir(local_dir, remote_fs, remote_data_dir)

    # Load jobs
    management.call_command('loaddata', 'apps/oozie/src/oozie/fixtures/initial_data.json', verbosity=2)

  def has_been_setup(self):
    return False


def copy_dir(local_dir, remote_fs, remote_dir, mode=755):
  remote_fs.mkdir(remote_dir, mode=mode)

  for f in os.listdir(local_dir):
    local_src = os.path.join(local_dir, f)
    remote_dst = posixpath.join(remote_dir, f)
    copy_file(local_src, remote_fs, remote_dst)


CHUNK_SIZE = 1024 * 1024

def copy_file(local_src, remote_fs, remote_dst):
  if remote_fs.exists(remote_dst):
    LOG.info('%s already exists.  Skipping.' % remote_dst)
    return
  else:
    LOG.info('%s does not exist. trying to copy' % remote_dst)

  if os.path.isfile(local_src):
    src = file(local_src)
    try:
      remote_fs.create(remote_dst, permission=01755)
      chunk = src.read(CHUNK_SIZE)
      while chunk:
        remote_fs.append(remote_dst, chunk)
        chunk = src.read(CHUNK_SIZE)
      LOG.info('Copied %s -> %s' % (local_src, remote_dst))
    finally:
      src.close()
  else:
    LOG.info('Skipping %s (not a file)' % local_src)
