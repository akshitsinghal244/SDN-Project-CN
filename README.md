# SDN Link Failure Detection and Recovery

**Author:** Akshit Singhal  
**SRN:** PES1UG24AM027  
**Project:** Software Defined Networking (SDN) - Link Monitoring & Automated Recovery

## 📌 Project Overview
This project implements an intelligent SDN application that automatically detects link failures in a network and performs real-time rerouting to maintain connectivity. It utilizes the **Ryu Controller** and **Mininet** to simulate a fault-tolerant network topology.

The system also includes a web-based **Real-Time Dashboard** that visualizes the network graph and logs recovery events, including the precise time taken (in milliseconds) to restore traffic flow.

## 🚀 Key Features
- **Dynamic Topology Discovery:** Automatically maps switches, hosts, and links using LLDP.
- **Fault Detection:** Monitors the network state and instantly identifies when a link goes down.
- **Automated Rerouting:** Uses Dijkstra’s algorithm (via NetworkX) to find the next best path and updates flow tables across the network without manual intervention.
- **Interactive Dashboard:** A Flask-based web interface showing:
  - Live topology graph (Green for active, Red dashed for failed links).
  - Detailed event logs with timestamps.
  - Performance metrics (Recovery time in ms).

## 📂 Project Structure
- `controller.py`: The main Ryu Controller logic for flow management and rerouting.
- `topology.py`: Mininet script defining a "Diamond" topology for testing path redundancy.
- `app.py`: Flask backend that serves the dashboard API.
- `static/dashboard.html`: Frontend visualization using D3.js.

## 🛠️ Installation & Setup

### Prerequisites
- Ubuntu 20.04+
- Mininet
- Ryu SDN Framework
- Python 3.9+
- NetworkX, Flask

### Execution Steps
1. **Start the Controller:**
   ```bash
   ryu-manager controller.py
