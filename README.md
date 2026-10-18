# Home-Assistant-BK300
Home Assistant (HA) Integration for a Konnwei BK300 Battery Monitor

This integration only retrieves voltages. SOC and Temperature do not seem to be available.

The files need to reside in this directory structure on the HA Server:

config_path\
--custom_components\
----bk300_monitor\
------manifest.json\
------\_\_init\_\_.py\
------config_flow.py\
------sensor.py\
------strings.json

Once copied, restart HA and then you can added integratiuons for each BK300.\
You need to supply the BK300 MAC address - get it using the "BKMonitor" App on a phone.\
The default poll interval is 5000ms. If you change it then you will have to restart HA.

If you add more than one BK300, Google adding drift alerts using Home Assistant template automation, stacking voltage curves, summing the voltages and adding alerts to the total voltage etc.


Update - 10/10/2026
Added the ability to calibrate using a known voltage source individual sensors using new "Zero" and "Span" settings in each integration.
Zero adds an offset to the reading, this offset can be positive or negative. So if a sensor is always high by 0.2 volts, set zero to -0.2, this will reduce the reading by 0.2)
Span will multiply the value read by the value configured. EG is 1.1 is used then the value is increates 10% (0.1 ids 10%, 1.1 is use current value + 10%)

******* Please share back any code that you improve on *******


