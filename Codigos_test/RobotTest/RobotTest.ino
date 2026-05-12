// RobotTest.ino
// Este script simula el comportamiento esperado del microcontrolador 
// para probar la comunicación serial del servicio de robot.

String inputString = "";

void setup() {
  Serial.begin(9600);
  inputString.reserve(32);
}

void loop() {
  // Leer serial hasta encontrar salto de línea
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      processCommand(inputString);
      inputString = "";
    } else {
      inputString += inChar;
    }
  }
}

void processCommand(String cmd) {
  if (cmd.length() > 0) {
    char motor = cmd[0]; // A, B, C, D, E, F
    int pwmValue = cmd.substring(1).toInt(); // Extraer el valor PWM (0-1023)

    // Convertir a escala 0-300
    float val300 = (float)pwmValue * (300.0 / 1023.0);
    
    // Invertir: si entra 300 retorna 0, si entra 0 retorna 300
    float invertedVal = 300.0 - val300;

    // Retornar la posición invertida y temperatura simulada
    Serial.print(motor);
    Serial.print(invertedVal, 0); // Enviar como entero
    Serial.print("T");
    Serial.print(motor);
    Serial.print("25;");
  }
}
