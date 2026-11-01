# A Micropython script for Geolux SmartObserverPlus datalogger
#
# This script reads raw 10 Hz data sent from Licor LI-720 instrument via RS-232 serial
# interface and prints received measurements to the datalogger's debug console. The
# script illustrates datalogger's capability to easily handle 10 Hz serial date in real-time.
#
import serial, logger, json

# ---- Serial configuration (RS-232 port 2 @ 115200, 8N1) ----
PORT = serial.RS232_2
serial.configure(PORT, 115200, serial.PARITY_NONE, serial.DATA_EIGHT, serial.STOP_ONE)

# ---- Variable names (order aligned to LI-720 'data' array) ----
VAR_NAMES = [
	"IDX","U","V","W","T_SONIC","T_SONICH","SOS","TA","RH","PA",
	"V_r0","V_w0","V_c0","V_ref","V_h2o","V_co2","V_par","V_det",
	"T_det","T_src","RH_src","VTX","PITCH","ROLL","HEADING","Status",
	"SEQ","VIN","RSSI","PPFD","H2O_ABS","CO2_ABS","H2O","CO2",
	"CO2_MOLAR_DENSITY","H2O_MOLAR_DENSITY"
]

# ---- Helpers ----
remainder = bytearray()

def _parse_one_line(line: bytearray, encoding: str):
	# Fast prefilter: skip empty/whitespace; accept only likely JSON objects
	i, j = 0, len(line) - 1
	while i <= j and line[i] in (9, 10, 13, 32):  # \t \n \r space
		i += 1
	while j >= i and line[j] in (9, 10, 13, 32):
		j -= 1
	if i > j or line[i] != 123 or line[j] != 125:  # '{'==123, '}'==125
		return None
	try:
		# Decode only the tight slice
		obj = json.loads(line[i:j+1].decode(encoding))
		return obj if isinstance(obj, dict) else None
	except Exception:
		return None

def parse_json_lines(buf: bytearray, encoding: str = "utf-8"):
	"""
	Parses complete EOL-delimited lines from buf (EOL: \r, \n, \r\n).
	Returns (list_of_dicts, index_of_last_EOL_byte). For CRLF, index is the '\n'.
	Consumes nothing; caller decides how to trim.
	"""
	out = []
	n = len(buf)
	i = 0
	start = 0
	last_eol = -1
	while i < n:
		b = buf[i]
		if b == 13:  # '\r'
			# handle CRLF
			if i + 1 < n and buf[i + 1] == 10:
				eol_next = i + 2
				last_eol = i + 1
			else:
				eol_next = i + 1
				last_eol = i
			if i > start:
				# Parse this line
				candidate = buf[start:i]  # bytearray slice (copy of just the line)
				v = _parse_one_line(candidate, encoding)
				if v is not None:
					out.append(v)
			start = eol_next
			i = eol_next
			continue
		if b == 10:  # '\n'
			last_eol = i
			if i > start:
				candidate = buf[start:i]
				v = _parse_one_line(candidate, encoding)
				if v is not None:
					out.append(v)
			start = i + 1
			i += 1
			continue
		i += 1
	return out, last_eol

def feed_chunk(remainder: bytearray, chunk: bytes | bytearray, encoding: str = "utf-8"):
	"""
	Append chunk, parse complete lines, and **trim remainder in-place** up to the last EOL.
	Returns the parsed dicts for this call. The caller keeps `remainder` between calls.
	"""
	# Append without reallocating a new object
	remainder.extend(chunk)
	objs, last_eol = parse_json_lines(remainder, encoding=encoding)
	if last_eol >= 0:
		remainder[:] = remainder[last_eol + 1:]
	return objs

def _map_vars(values):
	# If it's a dict with variable names as keys, map by name.
	if isinstance(values, dict) and any(k in values for k in VAR_NAMES):
		return {name: values[name] for name in VAR_NAMES if name in values}

	# If it's a dict with integer indices, map by index (skip missing).
	if isinstance(values, dict) and all(isinstance(k, int) for k in values.keys()):
		out = {}
		for i, name in enumerate(VAR_NAMES):
			if i in values:
				out[name] = values[i]
			else:
				break
		return out

	# Otherwise treat as a sequence (list/tuple/array/bytearray with int indexing)
	n = min(len(values), len(VAR_NAMES))
	return {VAR_NAMES[i]: values[i] for i in range(n)}

# ---- Main loop ----
while True:
	# Read up to 512 bytes; wait up to 150 ms for more bytes to arrive
	# (serial.read returns a bytearray; empty if no data by timeout) :contentReference[oaicite:3]{index=3}
	chunk = serial.read(PORT, 512, 150)
	if not chunk:
		continue
	for obj in feed_chunk(remainder, chunk):
		if not obj:
			continue

		values = obj.get("data", [])
		crc    = obj.get("crc32")

		mapped = _map_vars(values)

		# Example print — tweak as needed:
		# show a few key fields + crc to confirm parsing
		out = {
			"IDX": mapped.get("IDX"),
			"U":   mapped.get("U"),
			"V":   mapped.get("V"),
			"W":   mapped.get("W"),
			"TA":  mapped.get("TA"),
			"RH":  mapped.get("RH"),
			"PA":  mapped.get("PA"),
			"crc32": crc
		}
		print(out)

	# gentle pacing for ~10 Hz stream
	logger.delay_ms(10)
