from serial_connection import SerialConnection
import signal


def new_packet(incoming_queue):
    packet = incoming_queue.get()
    print(packet)
    incoming_queue.task_done()


def exit_handler(signal, frame):
    print("Exit called")
    con.stop()

con = SerialConnection('/dev/pts/2', 19200, new_packet, "ACK\n")
items = ["esimene", "teine", "kolmas", "neljas"]

con.start()

for i in items:
    con.write(i)

print("items added to write queue")

# register exit handler
signal.signal(signal.SIGINT, exit_handler)
