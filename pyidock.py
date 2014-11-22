import serialimport datetimeimport inspectimport timeclass PyiDock:    """ Class for controlling iPod """    def __init__(self, serialport="/dev/tty.usbserial", serialspeed=38400, timeout=1):        self.serialPort = serialport        self.serialSpeed = serialspeed        self.timeout = timeout        self.queue = {}        self.timedata = ""        self.currenttype = 0        self.laststatus = {}        self.connected = False    def connect(self):        self.connected = True        try:            self.serial = serial.Serial(self.serialPort, baudrate=self.serialSpeed, timeout=self.timeout)        except:            self.connected = False        if self.connected:            self.serial.write(self.mkcmd(0, "0104"))  # Enable AIR            self.flush()        return self.connected    def disconnect(self):        self.serial.close()    def mkcmd(self, lingo, s):        s = s.decode("hex")        checksum = 0        s = chr(len(s) + 1) + chr(lingo) + s        for ch in s:            checksum = checksum + ord(ch)        checksum = 0x100 - (checksum & 0xff)        if checksum == 256:            checksum = 0        return chr(0xff) + chr(0x55) + s + chr(checksum)    def flush(self, what="all"):        in_queue = True        out_queue = True        if what.lower() == "in":            out_queue = False        if what.lower() == "out":            in_queue = False        if in_queue:            self.serial.flushInput()        if out_queue:            self.serial.flushOutput()    def int_to_hex_str(self, x, length=4):        if x > 4294967295:  # Boy, do you have a large library!            x = 4294967295  # Probably redundant..        length = length * 2        return hex(x).split("x")[1].zfill(length)    def read_response(self, fullmessage=False):        ret = []        while self.serial.inWaiting():            if self.serial.read(2) == "ff55".decode("hex"):                length = self.serial.read(1)                lingo = self.serial.read()                body = self.serial.read(int(length.encode('hex'), 16)-1)                checksum = self.serial.read()                message = "ff55".decode("hex") + length + lingo + body + checksum                if self.mkcmd(int(lingo.encode('hex')), body.encode('hex')) == message:  # Valid response?                    if message.startswith("ff5508040027".decode("hex")):  # if we're in pulling mode.                        self.timedata = message                    elif message.startswith("ff5506040001".decode("hex")):                        message = message.encode("hex")                        cmd = message[len(message)-4:len(message)-2]                        code = message[len(message)-8:len(message)-6]                        self.laststatus[cmd] = code                    else:                        if not fullmessage:                            ret.append(body)                        else:                            ret.append(message)        return ret    def strip_response(self, msg):        return msg[2:]    def get_response(self, cmd="", multi=False):        if not cmd:            cmd = inspect.stack()[1][3]        if multi:            ret = []        else:            ret = ""        data = self.read_response()        responses = {'get_ipod_name': '0015',                     'get_type_count': '0019',                     'get_type_range': '001b',                     'get_time_and_status': '001d',                     'get_playlist_position': '001f',                     'get_song_title': '0021',                     'get_song_artist': '0023',                     'get_song_album': '0025',                     'get_time_current_song': '0027',                     'get_shuffle': '002d',                     'get_repeat': '0030',                     'get_playlist_songs': '0036'}        if cmd in responses:            cmd = responses[cmd]        elif type(cmd) is int:            cmd = self.int_to_hex_str(cmd, 2)        elif type(cmd) is hex:            cmd = "00" + cmd        for response in data:            if response[:len(cmd)/2].encode('hex') == cmd:                if multi:                    ret.append(response[2:])                else:                    ret = response[2:]        return ret    def get_ipod_type(self):        cmd = self.mkcmd(4, "0012")        self.serial.write(cmd)    def get_ipod_name(self):        self.flush()        self.serial.write(self.mkcmd(4, "0014"))        ret = ""        while not ret:            ret = self.get_response()[:-1]        return ret    def set_playlist_to_all(self):        self.serial.write(self.mkcmd(4, "0016"))    def switch_to_type(self, itemtype=0, number=0):        self.serial.write(self.mkcmd(4, "0017" + self.int_to_hex_str(itemtype, 1) + self.int_to_hex_str(number)))    def get_all_by_type(self, itemtype=0):        self.flush()        return self.get_type_range(itemtype, self.get_type_count(itemtype))    def get_type_count(self, itemtype=1):        self.flush()        self.serial.write(self.mkcmd(4, "0018" + self.int_to_hex_str(itemtype, 1)))        ret = ""        while not ret:            ret = self.get_response().encode("hex")        return int(ret, 16)    def get_type_range(self, itemtype=1, count=1, offset=0):        if count > 1:            ret = []            t = count            while len(ret) < t:                if count > 64:                    get = 64                else:                    get = count                cmd = "001A" + self.int_to_hex_str(itemtype, 1) + self.int_to_hex_str(offset) + self.int_to_hex_str(get)                self.serial.write(self.mkcmd(4, cmd))                lastlen = len(ret)                if count > 64:                    count -= 64                    offset += 64                time.sleep(get * 0.02 * (float(19200) / self.serialSpeed))  # Need to sleep. .018 seconds                                                                            # per item seems ok for 19200bps                while len(ret) != lastlen + get:                    ret = ret + self.get_response(multi=True)            tmp = []            for q in ret:                tmp.append(q[4:len(q)-1])            ret = tmp        else:            self.serial.write(self.mkcmd(4, "001A" + self.int_to_hex_str(itemtype, 1) + self.int_to_hex_str(offset) +                                         self.int_to_hex_str(count)))            ret = ""            while not ret:                ret = self.get_response()[4:]        return ret    def get_time_and_status(self):        self.flush()        self.serial.write(self.mkcmd(4, "001C"))        ret = ""        while not ret:            ret = self.get_response()        rawstatus = int(ret[-1:].encode("hex"), 16)        position = int(ret[4:-1].encode("hex"), 16)        length = int(ret[:4].encode("hex"), 16)        if rawstatus == 1:            status = "play"        elif rawstatus == 2:            status = "pause"        else:            status = "stop"        return {'status': status,                'length': length,                'position': position,                'lengthtime': datetime.timedelta(seconds=length/1000),                'positiontime': datetime.timedelta(seconds=position/1000),                'rawstatus': rawstatus}    def get_playlist_position(self):        self.flush()        self.serial.write(self.mkcmd(4, "001E"))        ret = ""        while not ret:            ret = self.get_response().encode("hex")        return int(ret, 16)    def get_song_title(self, song=0):        self.flush()        self.serial.write(self.mkcmd(4, "0020" + self.int_to_hex_str(song)))        ret = ""        while not ret:            ret = self.get_response()[:-1]        return ret    def get_song_artist(self, song=0):        self.flush()        self.serial.write(self.mkcmd(4, "0022" + self.int_to_hex_str(song)))        ret = ""        while not ret:            ret = self.get_response()[:-1]        return ret    def get_song_album(self, song=0):        self.flush()        self.serial.write(self.mkcmd(4, "0024" + self.int_to_hex_str(song)))        ret = ""        while not ret:            ret = self.get_response()[:-1]        return ret    def set_pulling_mode(self, mode=True):        if mode:            m = 1        else:            m = 0        self.serial.write(self.mkcmd(4, "0026" + self.int_to_hex_str(m, 1)))    def execute_playlist_switch(self, song=0xFFFFFFFF):        self.serial.write(self.mkcmd(4, "0028" + self.int_to_hex_str(song)))    def raw_control(self, cmd=1):        self.flush()  # Let's clear the serial data...        self.timedata = ""        self.set_pulling_mode(False)        cmd = self.mkcmd(4, "0029" + self.int_to_hex_str(cmd, 1))        self.serial.write(cmd)    def play(self):        self.raw_control()    def pause(self):        self.raw_control(2)    def skip_forward(self):        self.raw_control(3)    def skip_backwards(self):        self.raw_control(4)    def forward(self):        self.raw_control(5)    def reverse(self):        self.raw_control(6)    def stop_fr(self):        self.raw_control(7)    def get_shuffle(self, numeric=False):        self.flush()        self.serial.write(self.mkcmd(4, "002c"))        ret = ""        while not ret:            ret = self.get_response().encode("hex")        ret = int(ret)        if not numeric:            if ret == 1:                ret = "songs"            elif ret == 2:                ret = "albums"            else:                ret = "off"        return ret    def toggle_shuffle(self):        state = self.get_shuffle(numeric=True)        state += 1        if state > 2:            state = 0        self.set_shuffle(state)    def set_shuffle(self, mode="songs"):        cmd = mode        if type(mode) is str:            if mode.lower() == "off":                cmd = 0            if mode.lower() == "songs":                cmd = 1            if mode.lower() == "albums":                cmd = 2        self.serial.write(self.mkcmd(4, "002e" + self.int_to_hex_str(cmd, 1)))    def get_repeat(self, numeric=False):        self.flush()        self.serial.write(self.mkcmd(4, "002f"))        ret = ""        while not ret:            ret = self.get_response().encode("hex")        ret = int(ret)        if not numeric:            if ret == 1:                ret = "one"            elif ret == 2:                ret = "all"            else:                ret = "off"        return ret    def toggle_repeat(self):        state = self.get_repeat(numeric=True)        state += 1        if state > 2:            state = 0        self.set_repeat(state)    def set_repeat(self, mode="one"):        cmd = mode        if type(mode) is str:            if mode.lower() == "off":                cmd = 0            if mode.lower() == "one":                cmd = 1            if mode.lower() == "all":                cmd = 2        self.serial.write(self.mkcmd(4, "0031" + self.int_to_hex_str(cmd, 1)))    def get_playlist_songs(self):        self.serial.write(self.mkcmd(4, "0035"))        ret = ""        while not ret:            ret = self.get_response().encode("hex")        return int(ret, 16)    def set_song_in_playlist(self, song=0):        self.serial.write(self.mkcmd(4, "0037" + self.int_to_hex_str(song, 4)))        time.sleep(.1)        ret = self.get_playlist_position()        return ret    def raw_read(self):        cmd = ""        while self.serial.inWaiting():            cmd = cmd + self.serial.read(1).encode("hex")        return cmd    def goto_audiobook(self, number=0):        self.switch_to_type(7, number)        self.execute_playlist_switch(number)    def goto_podcast(self, number=0):        self.switch_to_type(8, number)        self.execute_playlist_switch()