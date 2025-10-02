// Turbidity Sensor - JSON Output
const int sensorPin = A0;

void setup() {
  Serial.begin(9600);
  delay(2000);
  Serial.println("{\"status\":\"Turbidity sensor initialized\"}");
}

void loop() {
  int raw = analogRead(sensorPin);     // 0 - 1023
  float voltage = raw * (5.0 / 1023.0);
  
  // Convert voltage to NTU (adjust formula based on your sensor calibration)
  // This is a typical conversion, but you may need to calibrate for your specific sensor
  float turbidity = 0.0;
  
  if (voltage < 2.5) {
    turbidity = 3000;  // Very turbid
  } else {
    // Linear approximation: higher voltage = clearer water = lower NTU
    turbidity = -1120.4 * voltage * voltage + 5742.3 * voltage - 4352.9;
  }
  
  // Ensure turbidity is non-negative
  if (turbidity < 0) {
    turbidity = 0;
  }
  
  // Send data as JSON format for easy parsing by Raspberry Pi
  Serial.print("{");
  Serial.print("\"raw\":");
  Serial.print(raw);
  Serial.print(",\"voltage\":");
  Serial.print(voltage, 3);
  Serial.print(",\"turbidity\":");
  Serial.print(turbidity, 2);
  Serial.println("}");
  
  delay(1000); // 1 second between readings
}
