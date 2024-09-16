# Copyright 2021 DeepMind Technologies Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Singularity launch script for Alphafold Singularity image."""

import os
import sys
import pathlib
import signal
from typing import Tuple

from absl import app
from absl import flags
from absl import logging

import tempfile
import subprocess


#### USER CONFIGURATION ####

# Verify alphafold is loaded with the correct version


# Path to a directory that will store the results.
if 'TMP' in os.environ:
    output_dir = os.environ['TMP']
elif 'TMPDIR' in os.environ:
    output_dir = os.environ['TMPDIR']
else:
    output_dir = tempfile.mkdtemp(dir='/tmp', prefix='alphafold-')

# set tmp dir the same as output dir
tmp_dir = output_dir

#### END USER CONFIGURATION ####


flags.DEFINE_bool(
    'use_gpu', True, 'Enable NVIDIA runtime to run with GPUs.')
flags.DEFINE_string(
    'models_to_relax', "all",
    'The models to run the final relaxation step on. '
    'If `all`, all models are relaxed, which may be time '
    'consuming. If `best`, only the most confident model '
    'is relaxed. If `none`, relaxation is not run. Turning '
    'off relaxation might result in predictions with '
    'distracting stereochemical violations but might help '
    'in case you are having issues with the relaxation '
    'stage.')
flags.DEFINE_bool(
    'enable_gpu_relax', True, 'Run relax on GPU if GPU is enabled.')
flags.DEFINE_string(
    'gpu_devices', 'all',
    'Comma separated list of devices to pass to NVIDIA_VISIBLE_DEVICES.')
flags.DEFINE_list(
    'fasta_paths', None, 'Paths to FASTA files, each containing a prediction '
    'target that will be folded one after another. If a FASTA file contains '
    'multiple sequences, then it will be folded as a multimer. Paths should be '
    'separated by commas. All FASTA paths must have a unique basename as the '
    'basename is used to name the output directories for each prediction.')
flags.DEFINE_string(
    'output_dir', output_dir,
    'Path to a directory that will store the results.')
flags.DEFINE_string(
    'data_dir', None,
    'Path to directory with supporting data: AlphaFold parameters and genetic '
    'and template databases. Set to the target of download_all_databases.sh.')
flags.DEFINE_string(
    'docker_image_name', 'alphafold', 'Name of the AlphaFold Docker image.')
flags.DEFINE_string(
    'max_template_date', None,
    'Maximum template release date to consider (ISO-8601 format: YYYY-MM-DD). '
    'Important if folding historical test sets.')
flags.DEFINE_enum(
    'db_preset', 'full_dbs', ['full_dbs', 'reduced_dbs'],
    'Choose preset MSA database configuration - smaller genetic database '
    'config (reduced_dbs) or full genetic database config (full_dbs)')
flags.DEFINE_enum(
    'model_preset', 'monomer',
    ['monomer', 'monomer_casp14', 'monomer_ptm', 'multimer'],
    'Choose preset model configuration - the monomer model, the monomer model '
    'with extra ensembling, monomer model with pTM head, or multimer model')
flags.DEFINE_integer('num_multimer_predictions_per_model', 5, 'How many '
                     'predictions (each with a different random seed) will be '
                     'generated per model. E.g. if this is 2 and there are 5 '
                     'models then there will be 10 predictions per input. '
                     'Note: this FLAG only applies if model_preset=multimer')
flags.DEFINE_boolean(
    'benchmark', False,
    'Run multiple JAX model evaluations to obtain a timing that excludes the '
    'compilation time, which should be more indicative of the time required '
    'for inferencing many proteins.')
flags.DEFINE_boolean(
    'use_precomputed_msas', False,
    'Whether to read MSAs that have been written to disk instead of running '
    'the MSA tools. The MSA files are looked up in the output directory, so it '
    'must stay the same between multiple runs that are to reuse the MSAs. '
    'WARNING: This will not check if the sequence, database or configuration '
    'have changed.')
flags.DEFINE_string(
    'docker_user', f'{{os.geteuid()}}:{{os.getegid()}}',
    'UID:GID with which to run the Docker container. The output directories '
    'will be owned by this user:group. By default, this is the current user. '
    'Valid options are: uid or uid:gid, non-numeric values are not recognised '
    'by Docker unless that user has been created within the container.')

FLAGS = flags.FLAGS


def main(argv):
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')

  # You can individually override the following paths if you have placed the
  # data in locations other than the FLAGS.data_dir.

  # Path to the Uniref90 database for use by JackHMMER.
  uniref90_database_path = os.path.join(
      FLAGS.data_dir, 'uniref90', 'uniref90.fasta')

  # Path to the Uniprot database for use by JackHMMER.
  uniprot_database_path = os.path.join(
      FLAGS.data_dir, 'uniprot', 'uniprot.fasta')

  # Path to the MGnify database for use by JackHMMER.
  mgnify_database_path = os.path.join(
      FLAGS.data_dir, 'mgnify', 'mgy_clusters_2022_05.fa')

  # Path to the BFD database for use by HHblits.
  bfd_database_path = os.path.join(
      FLAGS.data_dir, 'bfd',
      'bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt')

  # Path to the Small BFD database for use by JackHMMER.
  small_bfd_database_path = os.path.join(
      FLAGS.data_dir, 'small_bfd', 'bfd-first_non_consensus_sequences.fasta')

  # Path to the Uniref30 database for use by HHblits.
  uniref30_database_path = os.path.join(
      FLAGS.data_dir, 'uniref30', 'UniRef30_2021_03')

  # Path to the PDB70 database for use by HHsearch.
  pdb70_database_path = os.path.join(FLAGS.data_dir, 'pdb70', 'pdb70')

  # Path to the PDB seqres database for use by hmmsearch.
  pdb_seqres_database_path = os.path.join(
      FLAGS.data_dir, 'pdb_seqres', 'pdb_seqres.txt')

  # Path to a directory with template mmCIF structures, each named <pdb_id>.cif.
  template_mmcif_dir = os.path.join(FLAGS.data_dir, 'pdb_mmcif', 'mmcif_files')

  # Path to a file mapping obsolete PDB IDs to their replacements.
  obsolete_pdbs_path = os.path.join(FLAGS.data_dir, 'pdb_mmcif', 'obsolete.dat')

  alphafold_path = pathlib.Path(__file__).parent.parent
  data_dir_path = pathlib.Path(FLAGS.data_dir)
  if alphafold_path == data_dir_path or alphafold_path in data_dir_path.parents:
    raise app.UsageError(
        f'The download directory {{FLAGS.data_dir}} should not be a subdirectory '
        f'in the AlphaFold repository directory. If it is, the Singularity build is '
        f'slow since the large databases are copied during the image creation.')

  command_args = []

  command_args.append(f'--fasta_paths={{",".join(FLAGS.fasta_paths)}}')

  database_paths = [
      ('uniref90_database_path', uniref90_database_path),
      ('mgnify_database_path', mgnify_database_path),
      ('data_dir', FLAGS.data_dir),
      ('template_mmcif_dir', template_mmcif_dir),
      ('obsolete_pdbs_path', obsolete_pdbs_path),
  ]

  if FLAGS.model_preset == 'multimer':
    database_paths.append(('uniprot_database_path', uniprot_database_path))
    database_paths.append(('pdb_seqres_database_path',
                           pdb_seqres_database_path))
  else:
    database_paths.append(('pdb70_database_path', pdb70_database_path))

  if FLAGS.db_preset == 'reduced_dbs':
    database_paths.append(('small_bfd_database_path', small_bfd_database_path))
  else:
    database_paths.extend([
        ('uniref30_database_path', uniref30_database_path),
        ('bfd_database_path', bfd_database_path),
    ])
  for name, path in database_paths:
    if path:
      command_args.append(f'--{{name}}={{path}}')

  tmp_target_path = '/tmp'

  use_gpu_relax = FLAGS.enable_gpu_relax and FLAGS.use_gpu

  command_args.extend([
      f'--output_dir={{output_dir}}',
      f'--max_template_date={{FLAGS.max_template_date}}',
      f'--db_preset={{FLAGS.db_preset}}',
      f'--model_preset={{FLAGS.model_preset}}',
      f'--benchmark={{FLAGS.benchmark}}',
      f'--use_precomputed_msas={{FLAGS.use_precomputed_msas}}',
      f'--num_multimer_predictions_per_model={{FLAGS.num_multimer_predictions_per_model}}',
      f'--models_to_relax={{FLAGS.models_to_relax}}',
      f'--use_gpu_relax={{use_gpu_relax}}',
      '--logtostderr',
  ])

  os.environ['CUDA_VISIBLE_DEVICES'] = FLAGS.gpu_devices
  os.environ['TF_FORCE_UNIFIED_MEMORY'] = str({})
  os.environ['XLA_PYTHON_CLIENT_MEM_FRACTION'] = str({})
  os.environ['PYTHONNOUSERSITE'] = str(1)

  # Execute run_alphafold.py (converted to frontier)
  run_alphafold = os.path.join(os.environ['OLCF_AF2_ROOT'], 'alphafold-2.3.2', 'run_alphafold.py')
  command = ['python', run_alphafold] + command_args
  logging.info(f'Running command: {{command}}')
  os.system(' '.join(command))

if __name__ == '__main__':
  flags.mark_flags_as_required([
      'data_dir',
      'fasta_paths',
      'max_template_date',
  ])
  app.run(main)