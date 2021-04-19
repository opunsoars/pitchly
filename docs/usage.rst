=====
Usage
=====

To use pitchly in a project::

	import pitchly


As of now , `pitchly` works only with Metrica Sports data format (old and new EPTS FIFA)

Data Loading
============
`kloppy` and `codeball` are used to load the tracking and event data from Metrica. Click `here <https://github.com/metrica-sports/sample-data>`_ for the sample open data

.. code-block:: python
  :linenos:

  # match directory
  match_dir = "/home/opunsoars/xFootball/datahub/"

  # tracking data [METRICA]
  from codeball import GameDataset

  metadata_file = (glob.glob(f"{match_dir}/*metadata*")[0])
  tracking_file = (glob.glob(f"{match_dir}/*tracking*")[0])

  dataset = GameDataset(
      tracking_metadata_file=metadata_file,
      tracking_data_file=tracking_file
  )

  # event data [METRICA]
  from kloppy.helpers import load_metrica_json_event_data

  dataset = load_metrica_json_event_data(raw_data_filename=glob.glob(f"{match_dir}/*json")[0],
                                            metadata_filename=glob.glob(f"{match_dir}/*metadata*")[0], 
                                            options=None) 


Tracking Data
=============

