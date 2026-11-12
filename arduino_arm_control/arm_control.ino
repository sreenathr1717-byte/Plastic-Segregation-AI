/*
  Plastic Segregation - 6-DOF Robotic Arm Controller
  Hardware: ESP8266 NodeMCU 1.0 (ESP-12E) + PCA9685 + Shakti 12V SMPS + 5V Buck Converter

  3D Printed Arm: base, waist, arm1(shoulder), arm2(elbow), arm3(wrist), gripper

  Serial commands from Python (115200 baud):
    B<angle> = Base rotation (0-180)
    W<angle> = Waist (0-180)
    S<angle> = Shoulder / arm1 (0-180)
    E<angle> = Elbow / arm2 (0-180)
    R<angle> = Wrist / arm3 (0-180)
    G<angle> = Gripper (0-180)
    H        = Home position
    T        = Test sweep all servos

  Wiring:
    ESP8266 NodeMCU -> PCA9685:
      D2 (GPIO4)  -> SDA
      D1 (GPIO5)  -> SCL
      3V3         -> VCC (logic power - PCA9685 accepts 3.3V)
      GND         -> GND

    Shakti 12V SMPS -> LM2596 Buck Converter:
      12V+ -> IN+
      GND  -> IN-
      (ADJUST TRIMPOT TO 5V OUTPUT BEFORE CONNECTING!)

    LM2596 Buck Converter -> PCA9685:
      OUT+ (5V) -> V+ (servo power screw terminal)
      OUT- (GND) -> GND (servo power screw terminal)

    Shakti 12V SMPS -> ESP8266 NodeMCU (optional, can use USB instead):
      12V+ -> Vin (onboard regulator handles 5-12V)
      GND  -> GND

    PCA9685 channels (assign strongest servos to highest-torque joints):
      Ch 0 -> Base servo       = MG996R  (heaviest load, rotates entire arm)
      Ch 1 -> Waist servo      = MG995   (supports arm weight)
      Ch 2 -> Shoulder servo   = MG995   (major lifting joint)
      Ch 3 -> Elbow servo      = SG90    (lighter load above here)
      Ch 4 -> Wrist servo      = SG90    (minimal load)
      Ch 5 -> Gripper servo    = SG90    (just gripping force)

  Arduino IDE setup:
    Board Manager: install "esp8266" by ESP8266 Community
    Board: "NodeMCU 1.0 (ESP-12E Module)"
    Upload Speed: 115200
    Library: Adafruit PWM Servo Driver Library
*/

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

#define NUM_SERVOS 6

#define BASE_CH     0
#define WAIST_CH    1
#define SHOULDER_CH 2
#define ELBOW_CH    3
#define WRIST_CH    4
#define GRIPPER_CH  5

#define SERVO_MIN  150
#define SERVO_MAX  600

int angles[NUM_SERVOS] = {90, 90, 90, 90, 90, 60};
int homeAngles[NUM_SERVOS] = {90, 90, 90, 90, 90, 60};

uint8_t chMap[NUM_SERVOS] = {BASE_CH, WAIST_CH, SHOULDER_CH, ELBOW_CH, WRIST_CH, GRIPPER_CH};
const char* names[NUM_SERVOS] = {"BASE", "WAIST", "SHOULDER", "ELBOW", "WRIST", "GRIPPER"};
char cmdChars[NUM_SERVOS] = {'B', 'W', 'S', 'E', 'R', 'G'};

uint16_t angleToPulse(int angle) {
  angle = constrain(angle, 0, 180);
  return map(angle, 0, 180, SERVO_MIN, SERVO_MAX);
}

void setServo(uint8_t channel, int angle) {
  pwm.setPWM(channel, 0, angleToPulse(angle));
}

void smoothMove(int idx, int targetAngle) {
  targetAngle = constrain(targetAngle, 0, 180);
  int step = (targetAngle > angles[idx]) ? 1 : -1;

  while (angles[idx] != targetAngle) {
    angles[idx] += step;
    setServo(chMap[idx], angles[idx]);
    delay(15);
  }
}

void goHome() {
  smoothMove(5, homeAngles[5]);
  smoothMove(4, homeAngles[4]);
  smoothMove(3, homeAngles[3]);
  smoothMove(2, homeAngles[2]);
  smoothMove(1, homeAngles[1]);
  smoothMove(0, homeAngles[0]);
}

void testSweep() {
  Serial.println("TEST_START");
  for (int i = 0; i < NUM_SERVOS; i++) {
    Serial.print("TESTING_");
    Serial.println(names[i]);
    smoothMove(i, 110);
    delay(300);
    smoothMove(i, 70);
    delay(300);
    smoothMove(i, homeAngles[i]);
    delay(500);
  }
  Serial.println("TEST_DONE");
}

void setup() {
  Serial.begin(115200);

  Wire.begin(D2, D1);  // SDA=D2(GPIO4), SCL=D1(GPIO5)
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(10);

  goHome();
  delay(500);
  Serial.println("ARM_READY");
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() == 0) return;

    char c = cmd.charAt(0);
    int angle = cmd.substring(1).toInt();

    if (c == 'H') {
      goHome();
      Serial.println("OK_HOME");
      return;
    }
    if (c == 'T') {
      testSweep();
      return;
    }

    for (int i = 0; i < NUM_SERVOS; i++) {
      if (c == cmdChars[i]) {
        smoothMove(i, angle);
        Serial.print("OK_");
        Serial.print(names[i]);
        Serial.print(":");
        Serial.println(angles[i]);
        return;
      }
    }

    Serial.println("ERR");
  }
}
