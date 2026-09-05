# Home-Assistant-BK300
Home Assistant (HA) Integration for a Konnwei BK300 Battery Monitor

The files need to reside in this directory structure on the HA Server:

config_path\
.....custom_components\
........bk300_monitor\
............manifest.json
............__init__.py
............config_flow.py
............sensor.py

Once copied, restart HA and then you can added integratiuons for each BK300.
You need to supply the BK300 MAC address - get it using the App oin a phone.
The defauly poll interval is 5000ms. If you change it then you will have to restart HA.

If you add more than one BK300, Google adding drift alerts using Home Assistant template automation, stacking voltage traves, summing the voltages and adding alerts to the total voltage.

Please share the code back if you modify anything.
