# QM-1100 Pick and Place Setup Guide
This repo includes scripts and instructions to program QM1100 Pick and Place Machine manufactured by SMT Max. We used these scripts to protoypes Ubo top PCB and wanted to share them with maker community.

[[WORK IN PROGRESS]]

## Overview

In order to prepare the Pick and Plance (PnP) machine, several steps must be taken. We will walk you through these steps below:

### 1. Export mounting coordinate file from Eagle or KiCAD:

The script supports two input formats: **EagleCAD** `.mnt` files and **KiCAD** position `.csv` files.

#### EagleCAD format

Export the mounting file from Eagle in the following format:

```
C1 45.99 105.42 180 10uF 0805-NO
C2 55.71 97.50 270 10uF 0805-NO
C3 51.19 101.13  90 0.1uF 0603-NO
...
```

To acccomplish this, go to ` File > Export > Mount SMD` in your board/layout window (See image below).

Please make sure the units are in mm (milimeters).The unit will follow the unit you have set in your layout grid. 

Each line in the '.mnt' file, includes the following values in order:

- Part Number: An unique id used to identify a part type & the feeder containing it.
- X: The X position of placement, in mm units.
- Y: The Y position of placement, in mm units.
- A: The rotation of the part in degrees.
- V: Part value 
- P: Part package

<img src="https://github.com/ubopod/QM1100/blob/main/images/export_mnt.png" alt="Export MNT file" width="500">

The export operation will give you two files, one for top side components and another for bottom side components. Since our design is one-sides and the machine only support single-sided placement, we will ignore the bottom `.mnt` file.

#### KiCAD format

Before exporting the parts coordinate file in KiCAD, you have to first place the Drill/Place origin in the lower left corner of the PCB. On the PnP machine, the origin will be on the top left corner of PCB when mounted on the machine. The images below show how/where to place the Drill/Place origin: 

<table>
  <tr>
    <td><img src="https://github.com/ubopod/QM1100/blob/main/images/kicad-select-place-origin.png" alt="Select Origin" width="500"></td>
    <td><img src="https://github.com/ubopod/QM1100/blob/main/images/kicad-place-origin.png" alt="Select Origin" width="500"></td>
   </tr> 
</table>

Next, you have to change direction of the X and Y axis to match the following image via Settings:

<table>
  <tr>
    <td><img src="https://github.com/ubopod/QM1100/blob/main/images/kicad-preferences.png" alt="Select Origin" width="500"></td>
    <td><img src="https://github.com/ubopod/QM1100/blob/main/images/kicad-setup-axis.png" alt="Select Origin" width="500"></td>
   </tr> 
</table>

In KiCAD, go to `File > Fabrication Outputs > Component Placement (.pos file)` and export as CSV. The file should have this format:

```
Ref,Val,Package,PosX,PosY,Rot,Side
"C1","10uF","C_0805_2012Metric_Pad1.18x1.45mm_HandSolder",108.532200,-61.053500,180.000000,top
"C2","0.1uF","C_0603_1608Metric_Pad1.08x0.95mm_HandSolder",116.990400,-61.904400,90.000000,top
...
```
Image below shows how to export Component Placement: 

<table>
  <tr>
    <td><img src="https://github.com/ubopod/QM1100/blob/main/images/component-placement.png" alt="Select Origin" width="500"></td>
    <td><img src="https://github.com/ubopod/QM1100/blob/main/images/kicad-generate.png" alt="Select Origin" width="500"></td>
   </tr> 
</table>

Make sure the units are in mm (millimeters) and the output is comma-separated with a header row. The `Side` column is ignored by the script.

**Note on package matching:** KiCAD package names (e.g. `C_0805_2012Metric_Pad1.18x1.45mm_HandSolder`) are typically more verbose than the short names used in feeder files (e.g. `0805-NO`). The script will automatically fall back to value-only matching when the package name doesn't match exactly, and will print a warning when this happens.

### 2. Setup the feeder file

We need to tell the machine on which feeder each component is mounted and provide some meta data on each feeder. This part needs to be prepare manually. Here is an example of the CSV format for this file:

```
# feeder_id angle value package z-height vision file skip pause note IC
38 90 Ferrite 0805-NO 700 No “””no””” No 0 None No
39 90 33pF 0603-NO 700 No “””no””” No 0 None No
40 90 100pF 0603-NO 700 No “””no””” No 0 None No
...
```

Here's a short description of each value on each column: 

  1. Feeder ID number 
  2. Part orientation in degrees on the feeder (must be calcuated by user)
  3. Component name/value as it appears on the Eagle mounting list (.mnt file)
  4. Component package it appears on the Eagle mounting list (.mnt file)
  5. Component z-axis height in machine units; 700 is the default but for taller parts it must be adjusted. Please a look at machine manual for more info.
  6. QM Vision enabled for this component. Default is No. If you wish to set up vision, consult with manual and change to Yes.
  7. Path to Vision file. Default is “””no””” if QM Vision is not selected.
  8. Whether to skip placing components on this feeder. Default is No.
  9. Pause time before attampting to pick component from tray. Default is 0 seconds.
  10. Notes regarding components on feader. Default is None.
  11. Whether the component is an IC. Default is No.
  12. Calculating the rotation angle

This can be a tricky to detemine feeder angle and it requires some geometic imagination. 

It is basically the amount of rotation (Clock Wise) that the pickup nozzle must make after it picks up the part from the feeder to place it with correct orientaton on the board. The orientation for passive components such as resistors and ceramin capacitors can be offset by 180 degree and still not cause any problems electrically. 

However, orientation of diodes, LEDS, ICS, etc must be calculated with care. The positional angle of parts on PCB is calcuated by EAGLE (included in the .mnt file) based on a cartesian coordiate with an origin marketed with cross sign on the board layout. 

Basically the amount of rotation nozzle must make to correctly place a part after it picks it up from the feeder can be calculated as:

```
Head rotation angle = ( part angle position on the feer - part angle of position on PCB ) % 360
```

The best way derive part angle for each feer is to imagin picking that component by hand and having to rotate it clockwise before placing it on the board and imagine the amount of rotation needed to place it correctly on the PCB for a given part on PCB coming from the target feeder. This feed this number on the left hand side of the above formula and also add part angle from .mnt file into the formula and calculate part angle on feeder. You can re-try this for different parts from the same feeder to make sure formula gives you the right amount of rotation based on the value derived for the first component (place note that the part feeder angle is a constant and works like and offset value for all parts coming from that feeder).

### 4. run script

In order to generate the part list to program the machine with:

```
python3 QM1100_v2.py -f <feeders.fds> -p <parts_file> -o <output.pts> --orientation <angle> [--format eagle|kicad]
```

**CLI arguments:**

| Flag | Description |
| --- | --- |
| `-f` / `--feeders` | Feeder definition file (`.fds`) — required |
| `-p` / `--parts` | Parts/coordinate file (`.mnt` or `.csv`) — required |
| `-o` / `--output` | Output file (`.pts`) — required |
| `--orientation` | PCB orientation angle: `0`, `90`, `-90`, or `180` — required |
| `--format` | Input format: `eagle` (default) or `kicad` |

The script takes the feeder list and mounting coordinates, and outputs a parts list that includes all parts, placement coordinates in machine units, correct amount of rotation for each part, etc. This list will then be uploaded to the machine along with the feeder list to configure it.

The PCB orientation angle is the amount of rotation needed clockwise to rotate PCB from the CAD orientation to the orientation on the pick and place bed. For example, the axis of the PCB in the EAGLE board layout must rotate 90 degrees clockwise so that the PCB has the position shown in the image below on the PnP machine bed.

| Orientation on the machine| Orientation in Eagle |
| ------------- | ------------- |
| ![alt text](https://github.com/ubopod/QM1100/blob/main/images/pnp_pcb_orientation.png?raw=true)  | ![alt text](https://github.com/ubopod/QM1100/blob/main/images/eagle_pcb_orientation.png?raw=true) |

**Example with EagleCAD format:**

```
> python3 QM1100_v2.py -f Ubo_v1.4_rear_feeder.fds -p Ubo_v1.4_variant_2.mnt -o Ubo_v1.4_parts.pts --orientation 90

Orientation: 90
Wrote output file "Ubo_v1.4_parts.pts"
```

**Example with KiCAD format:**

```
> python3 QM1100_v2.py -f Ubo_v1.4_rear_feeder.fds -p Uno_v1.7_led_topview-top-pos.csv -o output.pts --orientation 90 --format kicad

Orientation: 90
WARNING: Part C1 (10uF, C_0805_2012Metric_Pad1.18x1.45mm_HandSolder) matched feeder 51 by value only (feeder package: 0805-NO)
...
Wrote output file "output.pts"
```


### 5. Inspect the output parts file

Here's an example of the output parts list:

```
# Part Numer, X, Y, Z, A, Feeder, Vision, File, Skip, Pause, Notes, IC, Component
C1,-9897,1600,700,-2000,51,No,C1.tif,No,0,None,No,10uF-0805-NO
C2,-9812,2446,700,0,42,No,C2.tif,No,0,None,No,0.1uF-0603-NO
C3,-9818,2267,700,0,51,No,C3.tif,No,0,None,No,10uF-0805-NO
C4,-9713,1605,700,-2000,39,No,C4.tif,No,0,None,No,33pF-0603-NO
....
```

Each line in the parts list has a number of features/columns:

- Part Number: An unique id used to identify a part type & the feeder containing it.
- X: The X position of placement, in machine units.
- Y: The Y position of placement, in machine units.
- Z: The Z position of placement, in machine units.
- A: The rotation of the part upon placement, relative to its pickup rotation, in degrees.
- Feeder: The feeder number (id) used to find the part.
- Vision: Whether to use the vision system to validate placement, either yes or no.
- File: If Vision is marked yes, then this feature selects the reference photo to be used for vision checking.
- Skip: Whether the sequence should be performed during operation, either yes or no.
- Pause: How many microseconds to pause when the part is placed.
- Notes: Notes for the operator.
- IC: Whether to use customized speed control (under the IC panel) instead of the default, either yes or no. Useful when the default speed might cause the part to slip.
- Component: Presently unused by the machine but we populated it with part value concatenated with package 

IMPORTANT: The unit of conversion from standard units to QM internal units is as follows:

|1 inch | 2000 steps |
| ------------- | ------------- |
|90 degrees | 2000 steps |

### 6. Program the machine 

#### 6.1. Upload feeder file
#### 6.2. Upload parts file 
#### 6.3. Set board offset
