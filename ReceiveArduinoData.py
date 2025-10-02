import serial

# Change /dev/ttyACM0 if your Arduino shows differently
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)

print("Listening for data from Arduino...")

try:
    while True:
        line = ser.readline().decode('utf-8').rstrip()  # Read one line
        if line:  # Only print if data is received
            print("Received:", line)
except KeyboardInterrupt:
    print("Exiting...")
finally:
    ser.close()
