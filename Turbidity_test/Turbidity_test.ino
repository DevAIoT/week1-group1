// Turbidity quick tester
const int sensorPin = A0;

void setup() {
  Serial.begin(9600);
  delay(1000);
  //Serial.println("Turbidity tester starting...");
}

void loop() {
  int raw = analogRead(sensorPin);     // 0 - 1023
  float voltage = raw * (5.0 / 1023.0);
  //Serial.print("ADC: ");
  //Serial.print(raw);
  //Serial.print("Voltage:");
  Serial.println(voltage, 3);
  delay(1000);
}
