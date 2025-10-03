#include <Wire.h>
#include "SparkFun_AS7265X.h"

AS7265X sensor;

void setup() {
  Serial.begin(9600);  // Must match Raspberry Pi code
  Wire.begin();

  if (!sensor.begin()) {
    Serial.println("AS7265x not detected!");
    while (1);
  }
  Serial.println("AS7265x Initialized");
}

void loop() {
  sensor.takeMeasurements();

  // Print first 6 channels (A-F) as comma-separated values
  Serial.print(sensor.getCalibratedA()); Serial.print(",");
  Serial.print(sensor.getCalibratedB()); Serial.print(",");
  Serial.print(sensor.getCalibratedC()); Serial.print(",");
  Serial.print(sensor.getCalibratedD()); Serial.print(",");
  Serial.print(sensor.getCalibratedE()); Serial.print(",");
  Serial.println(sensor.getCalibratedF());

  delay(1000); // 1 second between readings
}
