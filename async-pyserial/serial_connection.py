from queue import Queue
import serial
import threading
import time


class SerialConnection(threading.Thread):
    def __init__(self, port, speed, packet_read_callback, ack_string=None):
        # thread
        threading.Thread.__init__(self)
        self._stop_event = threading.Event()
        self._packet_read_callback = packet_read_callback

        # serial
        self._serial = None
        self._port = port
        self._speed = speed
        self._timeout = 1
        self.encoding = 'utf-8'

        # queues
        self._write_queue = Queue()
        self._last_write_time = 0.0
        self.write_rate = 0.2
        self._read_queue = Queue()

        # ack
        self._ack_string = ack_string
        self.ack_timeout = 10

        self._open()

    def run(self):
        """
        Runs the main serial loop to Read and Write until stop() is called.
        """
        while True and not self._stop_event.is_set():
            if not self._serial or not self._serial.isOpen():
                self._open()

            self._read_loop()
            self._write_loop()
            if not self._read_queue.empty():
                self._packet_read_callback(self._read_queue)

        print("stop() has been called, stopping Serial Thread")
        self._serial.close()

    def write(self, packet):
        """
        Public function to convert a packet to bytes and write it to the serial port
        :param packet: Packet to write to serial port
        """
        self._write_queue.put(packet)

    def stop(self):
        self._stop_event.set()

    def _write_loop(self):
        """
        Checks the self._write_queue for new items and writes any to the serial port if serial port is writable
        and self.write_rate < time_since_last_write.
        if self._ack_string is defined waits for an ACK response.
        """
        time_since_last_write = time.time() - self._last_write_time
        if not self._write_queue.empty() and self._serial.writable() and time_since_last_write > self.write_rate:
            packet = self._write_queue.get()
            self._write_serial(packet)
            self._wait_ack(packet)
            self._write_queue.task_done()

    def _write_serial(self, packet):
        """
        Converts the given packet to bytes and writes them to the serial port.
        :param packet: packet to write
        """
        if isinstance(packet, bytearray):
            packet_bytes = bytes(packet)
        else:
            packet_bytes = bytes(packet, self.encoding)
        self._serial.write(packet_bytes)
        self._last_write_time = time.time()

    def _read_loop(self):
        """
        Checks if there are any new packets coming from the serial port.
        If any are found adds them to the self._read_queue
        """
        if self._serial.in_waiting > 0:
            packet = self._serial.read(self._serial.in_waiting)
            if len(packet) > 1:
                self._read_queue.put(packet)

    def _wait_ack(self, sent_packet):
        """
        if self._ack_string has been defined, waits for an ACK response to the previously sent packet.
        :param sent_packet: packet that was sent
        """
        timeout = 0
        if not self._ack_string:
            return

        while self._serial.isOpen() and not self._stop_event.is_set() and timeout < self.ack_timeout:
            timeout += 1
            print('waiting for ACK')
            packet = self._serial.readline()
            if len(packet) > 1:
                if packet == bytes(self._ack_string, self.encoding):
                    return
                else:
                    self._read_queue.put(packet)
        print('ACK failed for: ', sent_packet)

    def _open(self):
        """
        Sets up the serial port and opens it.
        """
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
        try:
            self._serial = serial.Serial(self._port, self._speed)
            self._serial.timeout = self._timeout
            self._serial.writeTimeout = self._timeout
            self._serial.flush()
        except Exception as e:
            print("Serial Connection Open Failed: ", e)
            raise e
