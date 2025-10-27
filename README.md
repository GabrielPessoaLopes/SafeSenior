# SafeSenior – IoT Monitoring and Assistance System

SafeSenior is an IoT-based monitoring and safety platform that connects a wearable device to a cloud backend and a web-app frontend.  
It aims to support elderly and dependent people by continuously collecting sensor data, detecting emergencies, and notifying caregivers through an online interface.

---

## Overview

The system combines:
- **Embedded hardware (ESP32/ESP8266)** for data capture and Wi-Fi communication.  
- **Flask REST API** for authentication, device registration, and event handling.  
- **Supabase PostgreSQL database** for persistent storage of users, devices, and health data.  
- **Frontend** for caregivers and users to view alerts, history, and system status in real time.

The architecture enables autonomous local detection with cloud-level management and communication between devices and caregivers.

---

## Features

- Continuous monitoring through sensors (motion, heart rate, temperature, etc.)  
- Automatic event detection and alert transmission  
- Secure user authentication (JWT)  
- SHA-256 encrypted credentials  
- Device management with permanent UUIDs  
- Event logging and caregiver notifications  
- Cloud-based database and hosting  
- Web-app dashboard for system monitoring  

---

## System Architecture
[Arduino Device + Sensors] → [Flask API on Vercel] → [Supabase Database] → [Web-App Frontend]
Data Capture / Wi-Fi Auth & Logic Persistent Storage User & Caregiver UI

---

## Tech Stack

| Layer | Technology |
|-------|-------------|
| Backend | Flask (Python) |
| Database | Supabase (PostgreSQL) |
| Authentication | JWT |
| IoT Device | Arduino (ESP32/ESP8266) |
| Frontend | |
| Hosting | Vercel |
| Communication | HTTP (JSON over Wi-Fi) |

---

## Future Improvements

- Integration of additional biometric and environmental sensors  
- GPS and location tracking  
- Push notifications for caregivers  
- MQTT for real-time communication  
- Local data caching for offline operation  
- Predictive analytics for proactive health-risk detection  

---

## Author

**Gabriel Lopes**  
