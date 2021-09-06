# Votschtechnik (Weiss Technik) climate chamber control from Python

This Python package allows to communicate with a Votschtechnik (or Weiss Technik?) climate chamber like this one 
![Picture of a climate chamber](https://www.weiss-technik.com/fileadmin/Redakteur/Weiss/Produkte/Images/Umweltsimulation/ClimeEvent2.png)
in an easy way using Python.

## Installation

Option 1:

```
pip3 install git+https://github.com/SengerM/VotschTechnik-climate-chamber-Python
```

Option 2:

Clone the repo wherever you want and then

```
pip3 install -e /wherever/you/wanted/to/clone/this/repo
```

## Usage

Just import and start using:

```Python
from VotschTechnikClimateChamber.ClimateChamber import ClimateChamber

chamber = ClimateChamber(ip='130.60.165.218') # Use the IP address shown in the display of the climate chamber.
chamber.temperature_set_point = 0 # Set it to 0 °C.
print(f'The set temperature of the chamber is {chamber.temperature_set_point} °C.')
print(f'The actual temperature in the chamber is {chamber.temperature_measured} °C.')
```
