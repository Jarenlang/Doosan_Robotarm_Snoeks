# README Snoeks automotive

This repository contains code and configuration used to automate a Doosan collaborative robot arm for production tasks at Snoeks.  
The focus is on repeatable, safe and maintainable motion programs that integrate with surrounding equipment.

## Features

- Control of a Doosan collaborative robot arm using the official Doosan controller and API
- Ready‑to‑use task programs for repetitive pick‑and‑place or handling operations
- Example logic for I/O interaction with external devices (conveyors, clamps, sensors)
- Basic structure for extending the project with new products or workcells

> Note: Please adapt the feature list to your actual code (e.g. Modbus‑TCP, vision, gripper type, etc.).

## Prerequisites

Make sure you have the following available before using this project:

- A compatible Doosan robot arm and controller (e.g. M‑/A‑series) with a working installation  
- Access to the Doosan programming environment (Teach Pendant / DRL Studio / API, depending on how this project is implemented) 
- Network connection between the robot controller and the development PC, if you deploy code from a PC  
- Required field devices (gripper, sensors, safety equipment) correctly wired and configured

Add or change items here to match your real setup (robot model, controller version, PC OS, etc.).

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/Jarenlang/Doosan_Robotarm_Snoeks.git
   cd Doosan_Robotarm_Snoeks

2. Open the project in the appropriate Doosan environment:
    For DRL scripts: import/copy the .drl or program files to the controller or DRL Studio project.
    For ROS / external control: place the package in your workspace and build it according to your ROS/Doosan setup.

3. Configure:
    Robot model and tool data (TCP, payload, center of gravity) on the controller
    Work object / base frames
    I/O mapping for grippers and other peripherals

## Usage

Typical workflow:
  - Power on and home the robot according to the Doosan manual.
  - Load the desired task or script from this project on the controller.
  - Adjust any product‑specific parameters (positions, speeds, delays) in the program or parameter file.
  - Test the cycle at reduced speed and with full safety measures in place.
  - Switch to automatic/production mode once validated.

You can add concrete examples, for instance:
  - Program:  main_snoeks.drl
  - Purpose:  Pick plastic parts from fixture A and place into fixture B
  - Start:    Run → main_snoeks
  - Stops:    Uses digital input DI_1 as part present signal

## Project Structure
Adapt this section to your actual folders and files, for example:
````bash 
  Doosan_Robotarm_Snoeks/
  ├─ programs/        # Main robot programs / DRL scripts
  ├─ config/          # Tool, base and parameter files
  ├─ io/              # I/O configuration or helper scripts
  └─ docs/            # Additional documentation, layouts, etc.
  ````
  Briefly describe what lives in each directory and which files are the main entry points.

## Safety
Working with industrial robots is potentially dangerous. Always:
- Follow the official Doosan safety and installation manuals.
- Validate all new programs at low speed and with limited workspace.
- Ensure all safety devices (safety PLC, scanners, emergency stops, fences) are installed and tested.
- Never run modified programs in production without proper risk assessment.

## Contact
For questions or suggestions about this project:
- Author: Eeuwe de Haan
- GitHub: https://github.com/Jarenlang/Doosan_Robotarm_Snoeks
- Email: eeuwedehaan(at)g mail(dot)com
