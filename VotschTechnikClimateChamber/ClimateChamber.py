import socket
from threading import RLock

# The manuals with the documentation are really hard (or impossible) to
# find using Google. My code is based in Izaak's code [1]. He sent me 
# via email some manuals, in particular the one in reference [2] which 
# seems to have the most up to date information on the programming 
# interface. I found the document from reference [3] which has some 
# partial information, not as complete as [2] but better than nothing.
#
# The communication protocol of this climate chamber is among the worse 
# protocols I have worked with.
#
# [1] https://github.com/IzaakWN/ClimateChamberMonitor/blob/858ca67f8fbf2f89cf5b2d85955ca76395e694f4/chamber_commands.py
# [2] Operation manual, Communication protocol S!MPAC® simserv, file named "SIMPAC_SimServ_en_2019.05_64636625_new.pdf". I could not find this document on Internet.
# [3] Untitled document, http://lampx.tugraz.at/~hadley/semi/ch9/instruments/VT4002/Simpati_Simserv_Manual_(en).pdf

def _generate_list_of_all_possible_commands(dictionary):
	"""This function is for internal usage only. The argument <dictionary>
	is supposed to be <COMMANDS_DICT>."""
	if not isinstance(dictionary, dict): 
		return ['DELETE_ME_LALALALALALA'] 
	else: 
		return_list = [] 
		for key in dictionary.keys(): 
			sub_keys = _generate_list_of_all_possible_commands(dictionary[key]) 
			for sub_key in sub_keys: 
				return_list.append(f'{key} {sub_key}') 
		return sorted([s.replace(' DELETE_ME_LALALALALALA','') for s in return_list])
COMMANDS_DICT = {
	# This dictionary was created by Izaak, see reference [1]. I just adapted it a little bit to be more human readable, and fixed typos in command numbers.
	# See [2] section 5 for reference on these commands.
	# Those marked with ✅ I have checked in reference [2].
	'GET': {
		'CHAMBER': {
			'INFO': 99997, # ✅
			'STATUS': 10012, # ✅
		},
		'CONTROL_VARIABLE': {
			'NUMBER_OF': 11018, # ✅
			'NAME': 11026, # ✅
			'UNIT': 11023, # ✅
			'SET_POINT': 11002, # ✅
			'ACTUAL_VALUE': 11004, # ✅
			'INPUT_LIMIT_MIN': 11007, # ✅
			'INPUT_LIMIT_MAX': 11009, # ✅
			'WARNING_LIMIT_MIN': 11016, # ✅
			'WARNING_LIMIT_MAX': 11017, # ✅
			'ALARM_LIMIT_MIN': 11014, # ✅
			'ALARM_LIMIT_MAX': 11015, # ✅
		},
		'CONTROL_VALUE': {
			# ~ 'NUMBER_OF': 13007, This is bad documented in [2], it says "GET NUMBER OF SET VALUES" and description "Number of control values".
			'NAME': 13011, # ✅
			'UNIT': 13010, # ✅
			'SET_POINT': 13005, # ✅
			'INPUT_LIMIT_MIN': 13002, # ✅
			'INPUT_LIMIT_MAX': 13004, # ✅
		},
		'MEASURED_VALUE': {
			'NUMBER_OF': 12012, # ✅
			'NAME': 12019, # ✅
			'UNIT': 12016, # ✅
			'ACTUAL_VALUE': 12002, # ✅
			'WARNING_LIMIT_MIN': 12010, # ✅
			'WARNING_LIMIT_MAX': 12011, # ✅
			'ALARM_LIMIT_MIN': 12008, # ✅
			'ALARM_LIMIT_MAX': 12009, # ✅
		},
		'DIGITAL_IN': {
			'NUMBER_OF': 15004, # ✅
			'NAME': 15005, # ✅
			'VALUE': 15002, # ✅
		},
		'DIGITAL_OUT': {
			'NUMBER_OF': 14007, # ✅
			'NAME': 14010, # ✅
			'VALUE': 14003, # ✅
		},
		'MESSAGE': {
			'NUMBER_OF': 17002, # ✅
			'TEXT': 17007, # ✅
			'TYPE': 17005, # ✅
			'CATEGORY': 17111, # ✅
			'STATUS': 17009, # ✅
		},
		'ERROR': {
			# ~ 'PLC_LIST': 17012, Command 17012 is "RESET ALL ERRORS"
			# ~ 'ID_LIST': 17012, Command 17012 is "RESET ALL ERRORS"
		},
		'GRADIENT_UP': { 
			'VALUE': 11066, # ✅
		},
		'GRADIENT_DOWN': { 
			'VALUE': 11070, # ✅
		},
		'PROGRAM':{ # In reference [2] this is called PRG.
			'NUMBER': 19204, # ✅
			'NAME': 19031, # ✅
			'TOTAL_LOOPS': 19004, # ✅
			'COMPLETED_LOOPS': 19006, # ✅
			'START_DATETIME': 19208, # ✅
			'LEAD_TIME': 19010, # ✅
			'ACTIVE_TIME': 19021, # ✅
			'STATUS': 19210, # ✅
		},
	},
	'SET': {
		'CONTROL_VARIABLE': { 
			'SET_POINT': 11001, # ✅
		},
		'CONTROL_VALUE': { 
			'SET_POINT': 13006, # ✅
		},
		'DIGITAL_OUT': { 
			# ~ 'VALUE': 14001, Command 14001 is "START MAN MODE".
		},
		'GRADIENT_UP': {
			'VALUE': 11068, # ✅
		},
		'GRADIENT_DOWN': { 
			'VALUE': 11072, # ✅
		},
		'PROGRAM':{
			'CONTROL': 19209, # ✅
			'TOTAL_LOOPS': 19003, # ✅
			'START_DATE': 19207, # ✅
		},
	},
	'START': {
		'MANUAL_MODE': 14001, # ✅
		'PROGRAM': 19014, # ✅
	},
	'STOP': {
		'PROGRAM': 19015, # ✅
	},
	'RESET': {
		'ERRORS': 17012, # ✅
	},
}
COMMANDS_LIST = _generate_list_of_all_possible_commands(COMMANDS_DICT)

def _validate_type(var, var_name, typ):
	if not isinstance(var, typ):
		raise TypeError(f'<{var_name}> must be of type {typ}, received object of type {type(var)}.')

def _validate_float(var, var_name):
	try:
		float(var)
	except:
		raise TypeError(f'Cannot interpret <{var_name}> as a float number, received object of type {type(var)}.')

def create_command_string(command_number: str, *arguments):
	"""Given the command number and a list of arguments, creates the 
	string that has to be sent to the chamber. Note that this creates an 
	encoded string, i.e. a byte-string.
	
	- command_number: string, the number of the command as a five digit
	string, e.g. '11001'.
	- arguments: Arguments for the command. These arguments will be 
	converted into a string so if they need some formatting, you better
	give me strings already formatted."""
	# See page 5 of reference [2] or page 3 of [3].
	_validate_type(command_number, 'command_number', str)
	try:
		int(command_number)
	except:
		raise ValueError(f'<command_number> must be a string with an integer number, received {command_number} which I dont know how to convert into an integer number.')
	if len(command_number) != 5:
		raise ValueError(f'<command_number> musut be a string containing a 5 digits integer number, received {command_number}.')
	chamber_index = '1' # According to [2], "the chamber index is irrelevant and can always have the value 1"...
	if len(arguments) > 4:
		raise ValueError(f'The maximum number of arguments is 4, but received {len(arguments)}.')
	command_string = ''.encode('ascii')
	separator_character = b'\xb6' # ASCII code 182, according to [2] page 5.
	for element in [command_number, str(chamber_index)] + [str(arg) for arg in arguments]:
		command_string += element.encode('ascii') + separator_character
	command_string = command_string[:-1] + '\r'.encode('ascii')
	return command_string

def translate_command_name_to_command_number(command_name: str):
	"""Given a command name	returns the corresponding command number as 
	a string. Example:
	print(repr(translate_command_name_to_command_number('GET CONTROL_VARIABLE WARNING_LIMIT_MAX')))
	'11017'"""
	_validate_type(command_name, 'command_name', str)
	command_name = command_name.upper() # This makes this function case insensitive, more human.
	def recursive_search(commands_dict, command_name):
		current_command = command_name.split(' ')[0]
		if current_command not in commands_dict:
			return None
		else:
			if isinstance(commands_dict[current_command], dict):
				return recursive_search(commands_dict[current_command], ' '.join(command_name.split(' ')[1:]))
			else:
				return commands_dict[current_command]
	command_number = recursive_search(COMMANDS_DICT, command_name)
	if command_number is None:
		raise ValueError(f'Invalid command "{command_name}". This is a list of all possible command names: {COMMANDS_LIST}.')
	return str(command_number)

class ClimateChamber:
	def __init__(self, ip: str, temperature_min: float, temperature_max: float, timeout=1):
		"""Creates an object of class ClimateChamber and starts the network connection to use it.
		- ip: string, IP address of the climate chamber to control.
		- temperature_min: float, minimum value of temperature to use. This is required for safety reasons to avoid accidentaly setting a temperature outside of this limit. This protection is implemented in this class, it does not touches anything into the climate chamber. If you use the methods provided by this class to control the temperature, everything should be fine. You can also set limits manually in the chamber itself using the control pannel.
		- temperature_max: float, maximum value of temperature to use. See `temperature_min` description."""
		_validate_float(temperature_min, 'temperature_min')
		_validate_float(temperature_max, 'temperature_max')
		self._temperature_min = float(temperature_min)
		self._temperature_max = float(temperature_max)
		_validate_type(ip, 'ip', str)
		self._communication_lock = RLock() # To make a thread safe implementation.
		with self._communication_lock:
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.socket.connect((ip, 2049)) # According to [2] § 2.2 this is the port, always.
			self.socket.settimeout(timeout)
	
	def query_command_low_level(self, command_number, *arguments):
		"""Given the command number and the arguments, the command string is created and sent to the climate chamber. The response from the chamber to that command is returned without any processing."""
		string_to_send = create_command_string(str(command_number), *arguments)
		with self._communication_lock:
			self.socket.send(string_to_send)
			response = self.socket.recv(512) # The example in [2] § 6, and also the code in [1], does this.
		return response
	
	def query(self, command_name: str, *arguments):
		"""Given a command name (e.g. 'SET CONTROL_VALUE SET_POINT', for all available command names see `VotschTechnikClimateChamber.ClimateChamber.COMMANDS_LIST`) and the arguments, the command is sent to the chamber. Returns a list with the data from the response from the climate chamber. This function checks if the command was successfully accepted and executed by the climate chamber, or if there was any kind of error reported by the chamber; in such a case a RuntimeError is raised."""
		command_number = translate_command_name_to_command_number(command_name)
		raw_response = self.query_command_low_level(command_number, *arguments)
		separator_character = '¶'
		response = raw_response.decode('utf-8', errors='backslashreplace').replace('\\xb6',separator_character).replace('\r\n','')
		if 'read failed' in response.lower() or int(response.split(separator_character)[0]) != 1:
			raise RuntimeError(f'Command "{command_name}" was sent to the climate chamber with arguments {arguments} and the climate chamber responded with an error code. I have no idea what happened, sorry. The raw response from the climate chamber is: {raw_response}.')
		response = response.split(separator_character)
		response = response[1:]
		return response
	
	@property
	def serial_number(self):
		"""Returns the serial number as a string."""
		return self.query('get chamber info', 3)[0]
	
	@property
	def test_system_type(self):
		"""Returns the "test system type" (model?)."""
		return self.query('get chamber info', 1)[0]
	
	@property
	def year_manufactured(self):
		"""Returns the year manufactured as a string."""
		return f"20{self.query('get chamber info', 2)[0]}"
	
	@property
	def idn(self):
		"""Returns a string with information to identify the climate chamber."""
		return f'Climate chamber vötschtechnik, {self.test_system_type}, serial N° {self.serial_number}, manufactured in {self.year_manufactured}'
	
	@property
	def temperature_measured(self):
		"""Returns the measured temperature as a float number in Celsius."""
		return float(self.query('GET CONTROL_VARIABLE ACTUAL_VALUE', 1)[0])
	
	@property
	def temperature_set_point(self):
		"""Returns the set temperature as a float number in Celsius."""
		return float(self.query('GET CONTROL_VARIABLE SET_POINT', 1)[0])
	@temperature_set_point.setter
	def temperature_set_point(self, celsius: float):
		"""Set the temperature in Celsius."""
		_validate_float(celsius, 'celsius')
		if not self._temperature_min <= celsius <= self._temperature_max:
			raise ValueError(f'Trying to set temperature to {celsius} °C which is outside the temperature limits configured for this instance. These limits allow to set the temperature between {self._temperature_min} and {self._temperature_max} °C.')
		else:
			self.query('SET CONTROL_VARIABLE SET_POINT', 1, str(celsius)) # This is based in an example for setting the temperature from [2] § 3.2.
	
	@property
	def temperature_min(self):
		"""Returns the minimum temperature limit in Celsius as a float number."""
		return self._temperature_min
	@temperature_min.setter
	def temperature_min(self, celsius: float):
		"""Set the minimum temperature limit in Celsius."""
		_validate_float(celsius, 'celsius')
		self._temperature_min = float(celsius)
	
	@property
	def temperature_max(self):
		"""Returns the maximum temperature limit in Celsius as a float number."""
		return self._temperature_max
	@temperature_max.setter
	def temperature_max(self, celsius: float):
		"""Set the maximum temperature limit in Celsius."""
		_validate_float(celsius, 'celsius')
		self._temperature_max = float(celsius)
	
	@property
	def dryer(self):
		"""Returns either `True` or `False` depending on whether the status of the dryer is on or off."""
		status = self.query('GET DIGITAL_OUT VALUE', 8)[0]
		if status == '0':
			return False
		elif status == '1':
			return True
		else:
			raise RuntimeError(f'Queried for dryer status to the climate chamber, I was expecting the answer to be either 0 or 1 but received `{status}` which I dont know how to interpret...')
	
	@property
	def compressed_air(self):
		"""Returns either `True` or `False` depending on whether the status of the compressed air is on or off."""
		status = self.query('GET DIGITAL_OUT VALUE', 7)[0]
		if status == '0':
			return False
		elif status == '1':
			return True
		else:
			raise RuntimeError(f'Queried for compressed air status to the climate chamber, I was expecting the answer to be either 0 or 1 but received `{status}` which I dont know how to interpret...')
	
	def start(self):
		"""Starts the climate chamber."""
		self.query('START MANUAL_MODE', 1, 1)
	
	def stop(self):
		"""Stops the climate chamber."""
		self.query('START MANUAL_MODE', 1, 0)

if __name__ == '__main__':
	print(repr(translate_command_name_to_command_number('GET GRADIENT_DOWN VALUE')))
