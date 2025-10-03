/*
 * Arduino - Turbidity Sensor
 * Reads turbidity sensor and sends data to Raspberry Pi via serial
 * The Pi will then publish this data to MQTT broker
 * 
 * NOTE TODO: this is not the actual one running, it's supposed to be filler code
 * when the owner of turbidity logic is done, please replace.
 */

const int TURBIDITY_PIN = A0;  // Analog pin for turbidity sensor

const unsigned long READ_INTERVAL = 5000; // 5 seconds
unsigned long lastReadTime = 0;

void setup() {
  Serial.begin(9600);
  pinMode(TURBIDITY_PIN, INPUT);
  delay(1000);
  Serial.println("Arduino Turbidity Sensor Ready");
}

void loop() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastReadTime >= READ_INTERVAL) {
    lastReadTime = currentTime;
    
    float turbidity = readTurbiditySensor();
    
    // Send data in JSON format for easy parsing
    Serial.print("{\"turbidity\":");
    Serial.print(turbidity, 2);
    Serial.println("}");
  }
}

float readTurbiditySensor() {
  // Take multiple readings for stability
  long sum = 0;
  const int numReadings = 10;
  
  for (int i = 0; i < numReadings; i++) {
    sum += analogRead(TURBIDITY_PIN);
    delay(10);
  }
  
  float avgReading = sum / numReadings;
  
  // Convert analog reading to voltage (0-5V)
  float voltage = avgReading * (5.0 / 1023.0);
  
  // Convert voltage to NTU (Nephelometric Turbidity Units)
  // Formula for common turbidity sensors like SEN0189
  // Calibrate based on your specific sensor
  
  float ntu;
  
  if (voltage > 4.2) {
    ntu = 0.0;  // Very clear water
  } else if (voltage < 2.5) {
    ntu = 3000.0 * (4.2 - voltage);  // Very turbid
  } else {
    // Quadratic approximation for mid-range
    ntu = -1120.4 * voltage * voltage + 5742.3 * voltage - 4352.9;
  }
  
  // Clamp to reasonable range
  if (ntu < 0) ntu = 0;
  if (ntu > 4000) ntu = 4000;
  
  return ntu;
}