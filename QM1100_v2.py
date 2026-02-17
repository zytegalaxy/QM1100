#!/usr/bin/env python
#
# QM1100
# Change exported part list from Eagle or KiCAD to match provided feeder
# list/definition loaded on QM1100 Machine
#
# Copyright (c) 2021 Mehrdad Majzoobi
# Released under MIT license

import argparse
import csv
import codecs
from collections import namedtuple

PartDef = namedtuple('PartDef', 'part_id x y angle value package')
FeederDef = namedtuple('FeederDef', 'feeder_id angle value package '
                       + 'z vision file skip pause note IC')
UpdatedPartDef = namedtuple('UpdatedPartDef', 'part_id x y z angle '
                            + 'feeder_id vision file skip pause note IC component')


def parse_parts_file(filename):
    """Parse an EagleCAD .mnt file (space-delimited, no header, 6 columns)
    and return a list of PartDef namedtuples."""
    part = []
    with open(filename, 'rb') as csvfile:
        reader = csv.reader(codecs.iterdecode(csvfile, 'utf-8'), skipinitialspace=True, delimiter=" ")
        for row in reader:
            # for those components that do not have a value assigned in Eagle
            if len(row) == 5:
                row.insert(4, 'None')
            p = PartDef._make(row[:6])
            part.append(p)
    return part


def parse_kicad_parts_file(filename):
    """Parse a KiCAD position CSV file (comma-delimited, header row, 7 columns
    with quoted fields: Ref,Val,Package,PosX,PosY,Rot,Side) and return a list
    of PartDef namedtuples."""
    part = []
    with open(filename, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # skip header row
        for row in reader:
            if not row or len(row) < 6:
                continue
            ref, val, package, pos_x, pos_y, rot = row[0], row[1], row[2], row[3], row[4], row[5]
            # Convert rotation to integer string (strip trailing .000000)
            rot = str(int(float(rot)))
            p = PartDef(part_id=ref, x=pos_x, y=pos_y, angle=rot, value=val, package=package)
            part.append(p)
    return part


def parse_feeders_file(filename):
    """Parse a file with CSV format and return an object containing
    the stack and part definitions"""
    feeder = []
    with open(filename, 'rb') as csvfile:
        reader = csv.reader(codecs.iterdecode(csvfile, 'utf-8'), skipinitialspace=True, delimiter=" ")
        for row in reader:
            f = FeederDef._make(row[:11])
            feeder.append(f)
    return feeder


def generate_updated_part(feeder_obj, part_obj, scale=2.54):
    updated_part = []
    sequence = 1
    for p in part_obj:
        matched_feeder = None

        # 1. Exact match: value AND package both match
        for f in feeder_obj:
            if p.value == f.value and p.package == f.package:
                matched_feeder = f
                break

        # 2. Value-only match: fallback if no exact match
        if matched_feeder is not None:
            print('Part %s (%s, %s) matched feeder %s exactly'
                  % (p.part_id, p.value, p.package, matched_feeder.feeder_id))

        if matched_feeder is None:
            value_matches = [f for f in feeder_obj if p.value == f.value]
            if len(value_matches) == 1:
                matched_feeder = value_matches[0]
                print('WARNING: Part %s (%s, %s) matched feeder %s by value only '
                      '(feeder package: %s)' % (p.part_id, p.value, p.package,
                      matched_feeder.feeder_id, matched_feeder.package))
            elif len(value_matches) > 1:
                feeder_ids = ', '.join(f.feeder_id for f in value_matches)
                print('WARNING: Part %s (%s, %s) has ambiguous value-only matches '
                      'on feeders [%s] — skipping' % (p.part_id, p.value, p.package, feeder_ids))
                continue

        # 3. No match at all
        if matched_feeder is None:
            print('Part %s (%s, %s) is not loaded on any feeder — skipping'
                  % (p.part_id, p.value, p.package))
            continue

        f = matched_feeder
        component = p.value + '-' + p.package
        angle = (int(f.angle) - int(p.angle)) % 360
        if angle > 180:
            angle -= 360
        a_rotation = angle * 2000 // 90
        x = round(float(p.x) * scale)
        y = round(float(p.y) * scale)
        file = p.part_id + ".tif"
        new_p = UpdatedPartDef(part_id=p.part_id, x=x, y=y, z=f.z,
                               angle=a_rotation, feeder_id=f.feeder_id,
                               vision=f.vision, file=file, skip=f.skip,
                               pause=f.pause, note=f.note, IC=f.IC,
                               component=component)
        sequence = sequence + 1
        updated_part.append(new_p)
    return updated_part


def write_csv_file(csv_file, obj, orientation):
    """Write out the QM100 prt file from the provided object"""
    for part in obj:
        if orientation == "0":
            X = "{:.0f}".format(-part.x)
            Y = "{:.0f}".format(-part.y)
        elif orientation == "90":
            X = "{:.0f}".format(-part.y)
            Y = "{:.0f}".format(part.x)
        elif orientation == "-90":
            X = "{:.0f}".format(part.y)
            Y = "{:.0f}".format(-part.x)
        else:  # 180
            X = "{:.0f}".format(part.x)
            Y = "{:.0f}".format(part.y)
        A = "{:.0f}".format(part.angle)
        csv_file.write("%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (part.part_id,
            X, Y, part.z, A, part.feeder_id, part.vision, part.file, part.skip,
            part.pause, part.note, part.IC, part.component))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert EagleCAD or KiCAD part coordinates to QM1100 pick-and-place format.')
    parser.add_argument('-f', '--feeders', required=True,
                        help='Feeder definition file (.fds)')
    parser.add_argument('-p', '--parts', required=True,
                        help='Parts/coordinate file (.mnt or .csv)')
    parser.add_argument('-o', '--output', required=True,
                        help='Output file (.pts)')
    parser.add_argument('--orientation', required=True,
                        choices=['0', '90', '-90', '180'],
                        help='PCB orientation angle on machine bed (degrees)')
    parser.add_argument('--format', default='eagle',
                        choices=['eagle', 'kicad'],
                        help='Input coordinate file format (default: eagle)')
    args = parser.parse_args()

    # Load and parse input files
    feeder_obj = parse_feeders_file(args.feeders)

    if args.format == 'kicad':
        part_obj = parse_kicad_parts_file(args.parts)
    else:
        part_obj = parse_parts_file(args.parts)

    print('Orientation: %s' % args.orientation)

    # Process files to generate output
    # Eagle coords are in mils: * 2.54 → QM1100 units (0.01mm)
    # KiCad coords are in mm:   * 100  → QM1100 units (0.01mm)
    scale = 100.0 if args.format == 'kicad' else 2.54
    new_part_obj = generate_updated_part(feeder_obj, part_obj, scale=scale)

    # Write output file
    with open(args.output, 'w') as f:
        write_csv_file(f, new_part_obj, args.orientation)

    print('Wrote output file "%s"' % args.output)
