#include <Wire.h>
#include "SparkFun_AS7265X.h"

AS7265X sensor;

void setup() {
  Serial.begin(9600);  // Must match Raspberry Pi code
  Wire.begin();

  if (!sensor.begin()) {
    Serial.println("{\"error\":\"AS7265x not detected!\"}");
    while (1);
  }
  Serial.println("{\"status\":\"AS7265x Initialized\"}");
}

void loop() {
  sensor.takeMeasurements();

  // Send data as JSON format for easy parsing by Raspberry Pi
  Serial.print("{");
  Serial.print("\"A\":");
  Serial.print(sensor.getCalibratedA(), 2);
  Serial.print(",\"B\":");
  Serial.print(sensor.getCalibratedB(), 2);
  Serial.print(",\"C\":");
  Serial.print(sensor.getCalibratedC(), 2);
  Serial.print(",\"D\":");
  Serial.print(sensor.getCalibratedD(), 2);
  Serial.print(",\"E\":");
  Serial.print(sensor.getCalibratedE(), 2);
  Serial.print(",\"F\":");
  Serial.print(sensor.getCalibratedF(), 2);
  Serial.print(",\"spectrum\":");
  Serial.print((sensor.getCalibratedA() + sensor.getCalibratedB() + sensor.getCalibratedC() + 
                sensor.getCalibratedD() + sensor.getCalibratedE() + sensor.getCalibratedF()) / 6.0, 2);
  Serial.println("}");

  delay(1000); // 1 second between readings
}
