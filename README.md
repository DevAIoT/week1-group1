# Arduino Water Quality Sensor Hub (pH & Turbidity)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains the Arduino C++ (`.ino`) code and setup instructions for building a simple water quality monitoring system. It uses a pH sensor and a turbidity sensor to collect data, which can be viewed through the Arduino Serial Monitor.

This project is perfect for students, hobbyists, and anyone interested in DIY environmental monitoring.



---

## 📖 Table of Contents
- [Hardware Required](#-hardware-required)
- [Wiring and Connections](#-wiring-and-connections)
- [Software Setup](#-software-setup)
- [Usage](#-usage)
- [Code Structure](#-code-structure)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🔬 Hardware Required
* Arduino Uno (or any compatible board)
* Atlas-scientific Analog pH Sensor Kit (or similar)
* Analog Turbidity Sensor (e.g., DFRobot SKU:SEN0189)
* Breadboard
* Jumper Wires

---

## 🔌 Wiring and Connections
Properly connecting the sensors to the Arduino is crucial. Below are the pin connections. **It is highly recommended to add a photo or a Fritzing diagram of your own setup here.**

### pH Sensor Connections
| pH Sensor Probe BNC | pH Sensor Board | Arduino Pin |
| :--- | :--- | :--- |
| Connect to Board | VCC (+) | `5V` |
| | GND (-) | `GND` |
| | AOUT (Po) | `A0` (Analog Pin 0) |

### Turbidity Sensor Connections
| Turbidity Sensor | Arduino Pin |
| :--- | :--- |
| VCC (Red Wire) | `5V` |
| GND (Black Wire) | `GND` |
| Signal (Yellow Wire) | `A1` (Analog Pin 1) |

---

## 💻 Software Setup

1.  **Install Arduino IDE:** Download and install the latest version from the [official Arduino website](https://www.arduino.cc/en/software).
2.  **Install Libraries:** _(If your specific pH sensor or other components require a library, list it here. For standard analog sensors, no special library is usually needed)._
    * Example: `Go to Sketch > Include Library > Manage Libraries... and search for [Library Name].`

---

## 🚀 Usage

1.  **Connect** your Arduino to your computer via USB.
2.  **Open** either the `pH_test/pH_test.ino` or `Turbidity_test/Turbidity_test.ino` file in the Arduino IDE.
3.  **Select** your board and port under the `Tools` menu (e.g., `Tools > Board > Arduino Uno` and `Tools > Port > COM3 / /dev/ttyACM0`).
4.  **Upload** the code to the Arduino by clicking the arrow icon.
5.  **Open** the Serial Monitor (magnifying glass icon in the top right) and set the baud rate to **9600** to see the sensor readings.

---

## 📂 Code Structure

* **`pH_test/`**: Contains the code to read the analog voltage from the pH sensor and convert it into a standard pH value (0-14).
* **`Turbidity_test/`**: Contains the code to read the analog voltage from the turbidity sensor and convert it into Nephelometric Turbidity Units (NTU).

---

## 🤝 Contributing

DevAIoT Team - Week 1 Group 1. Contributions are welcome! If you have suggestions for improving the code or documentation, please fork the repository and open a pull request.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

## 📜 License

Distributed under the MIT License. See `LICENSE.txt` for more information.
