// Crescent PCB packaging prototype. No tested retention, cooling or RF claim.
// See kb/pcb-packaging.md and analysis/pcb-fit/ for actual mesh/check evidence.
include <parameters.scad>
use <internals.scad>
use <../cad/lib/sensor.scad>

pcb_angle = 0;
pcb_bottom_z = 33;
pcb_thickness = 1.6;
pcb_top_z = pcb_bottom_z+pcb_thickness;
pcb_cradle_angles = [-30,0];
pcb_cradle_z = deck_top-tec_t-sink_h-3; // Z55: full 40 mm sink retained
pcb_tail_length = 3.2; // conservative projection BELOW board; verify samples

module pcb_frame() { rotate([0,0,pcb_angle]) children(); }
module pcb_outline() {
    // Project the delivered, enclosure-centred actual KiCad outline mesh.
    projection(cut=false)
        import("../electronics/pcb/views/board-envelope.stl",convexity=8);
}
module pcb_envelope() {
    pcb_frame() translate([0,0,pcb_bottom_z])
        import("../electronics/pcb/views/board-envelope.stl",convexity=8);
}

// KiCad footprint origin -> enclosure XY, preserving native rotation.
module pcb_at(x,y,a=0,z=pcb_top_z) {
    pcb_frame() translate([x+41,90-y,z]) rotate([0,0,a]) children();
}

// Reference, X, Y, rotation, pin count. Origins from design-bom.csv.
pcb_headers = [
    ["J2",94,88,0,3], ["J3",94,73,0,4],
    ["J4",54,76,0,3], ["J5",54,85,0,3],
    ["J6",54,96,0,3], ["J7",54,105,0,3],
    ["J8",94,59,0,4], ["J9",94,101,0,3],
    ["J10",94,112,0,2], ["J11",54,60,0,4],
    ["J12",78,78.5,90,2], ["J13",54,72.2,90,2]
];
pcb_terminals = [["J1",85.5,123],["J16",58,123],["J17",70,123]];

module pcb_component_envelopes(harness=true,lift=0) {
    // Sourced U1 18 x 25.5 body; 3.3 mm including a height allowance.
    pcb_at(75,63) translate([-9,-12.75,0]) cube([18,25.5,3.3+lift]);
    // C10 actual D8 x 11.5; origin is pin 1, centre is +2.5 mm.
    pcb_at(82,94) translate([2.5,0,0]) cylinder(d=8,h=11.5+lift,$fn=48);
    for(t=pcb_terminals) pcb_at(t[1],t[2])
        translate([-2.56,-4.6,0]) cube([10.2,9.8,15+lift]);
    for(h=pcb_headers) pcb_at(h[1],h[2],h[3])
        translate([-1.5,-2.54*(h[4]-1)-1.5,0])
            cube([3,2.54*(h[4]-1)+3,(harness?18:8.5)+lift]);
    // Actual 15.24 mm row spacing, 8 x 2.54 mm pins; 8.5 mm socket height.
    for(x=[59,74.24]) pcb_at(x,91)
        translate([-1.5,-19.28,0]) cube([3,20.78,8.5+lift]);
    // PROVISIONAL carrier: 20.32 x 22.86 x 1.6; 2 mm devices above it.
    // 10 x 10 x 10 heatsink on its centre is a trial allowance, NOT selected.
    pcb_at(66.62,99.89) translate([-10.16,-11.43,8.5])
        cube([20.32,22.86,3.6+lift]);
    pcb_at(66.62,99.89) translate([-5,-5,12.1]) cube([10,10,10+lift]);
    // Low SMT allowance from actual occupied placement region, below tall parts.
    // It intentionally conservatively includes spaces between small components.
    pcb_at(57,59) translate([0,-57,0]) cube([38,57,2+lift]);
    if(harness) for(t=pcb_terminals) pcb_at(t[1],t[2])
        // 12 mm straight exit/bend reservation; final gauge/radius unverified.
        translate([-2.56,-16.6,4]) cube([10.2,12,14+lift]);
}

module pcb_underside_pins() {
    for(h=pcb_headers) pcb_at(h[1],h[2],h[3],pcb_bottom_z-pcb_tail_length)
        for(i=[0:h[4]-1]) translate([-.6,-i*2.54-.6,0])
            cube([1.2,1.2,pcb_tail_length]);
    for(x=[59,74.24]) pcb_at(x,91,0,pcb_bottom_z-pcb_tail_length)
        for(i=[0:7]) translate([-.6,-i*2.54-.6,0])
            cube([1.2,1.2,pcb_tail_length]);
    for(t=pcb_terminals) pcb_at(t[1],t[2],0,pcb_bottom_z-pcb_tail_length)
        for(x=[0,5.08]) translate([x-.8,-.8,0]) cube([1.6,1.6,pcb_tail_length]);
    pcb_at(82,94,0,pcb_bottom_z-pcb_tail_length)
        for(x=[0,5]) translate([x-.6,-.6,0]) cube([1.2,1.2,pcb_tail_length]);
}

module pcb_populated_envelope() {
    pcb_envelope(); pcb_component_envelopes(); pcb_underside_pins();
}

module pcb_terminal_access_paths() {
    // Provisional straight Ø6 mm driver approach after lifting cartridges and
    // cradles. This does not model a hand, chosen screwdriver or connector latch.
    for(t=pcb_terminals) pcb_at(t[1],t[2],0,pcb_top_z+15)
        for(x=[0,5.08]) translate([x,0,0]) cylinder(d=6,h=lid_z,$fn=32);
}

module pcb_loading_path(harness=false) {
    // Each component sweeps from its OWN underside, not the board underside.
    // This matters for wires which overhang the low pocket walls from above.
    translate([0,0,pcb_bottom_z]) linear_extrude(lid_z+10-pcb_bottom_z)
        projection() pcb_envelope();
    // Terminal leads are connected AFTER insertion: their bend allowance
    // catches the fixed deck ledge if swept through it while connected.
    pcb_component_envelopes(harness=harness,lift=lid_z+10);
    translate([0,0,pcb_bottom_z-pcb_tail_length])
        linear_extrude(lid_z+10-pcb_bottom_z+pcb_tail_length)
            projection() pcb_underside_pins();
}

module pcb_board_loading_path() { pcb_loading_path(); }

module pcb_supports() {
    // Integral floor-rooted peripheral seat, only 0.8 mm under the PCB edge.
    // No broad bearing plate underneath solder tails; gravity seating only.
    pcb_frame() {
        translate([0,0,base_floor_top-eps])
            linear_extrude(pcb_bottom_z-base_floor_top+eps)
                difference() {
                    offset(delta=2) pcb_outline();
                    offset(delta=-0.8) pcb_outline();
                }
        translate([0,0,pcb_bottom_z-eps]) linear_extrude(2.6+eps)
            difference() {
                offset(delta=2) pcb_outline();
                offset(delta=0.5) pcb_outline();
            }
    }
}

module pcb_cradle_pedestal_one() {
    for(sy=[-1,1]) scale([1,sy,1]) {
        translate([83,16,base_floor_top-eps])
            cube([4,4,pcb_cradle_z-base_floor_top+eps]);
        // Small locating peg with a clearance socket in the removable cradle.
        translate([84.25,17.25,pcb_cradle_z-eps]) cube([1.5,1.5,2+eps]);
        translate([0,0,base_floor_top-eps])
            linear_extrude(pcb_cradle_z-base_floor_top+eps) intersection() {
                // Floor-rooted and braced into the shell by 0.2 mm; avoiding
                // an unprintably narrow slot between pillar and enclosure.
                difference() { circle(r=shell_inner_r+0.2); circle(r=143.5); }
                translate([140,15]) square([6,8]);
            }
    }
}

module pcb_cradle_pedestals() {
    for(a=pcb_cradle_angles) rotate([0,0,a]) pcb_cradle_pedestal_one();
}

module pcb_cartridge_bridge_one() {
    // One U-shaped cradle, common to both sites. All cross-PCB members
    // lift out; never union this module into the fixed enclosure/supports.
    difference() {
        union() {
            translate([83,-20,pcb_cradle_z]) cube([4,40,3]);
            for(sy=[-1,1]) scale([1,sy,1]) {
                translate([0,0,pcb_cradle_z]) linear_extrude(3)
                    intersection() {
                        circle(r=145.5);
                        translate([83,16]) square([63,4]);
                    }
                for(x=[85,122]) translate([x,17,pcb_cradle_z]) cube([3,5,3]);
                // Same four L guides and bearing datum as original 40 mm bay.
                for(sx=[-1,1]) translate([cooling_radius,0,0]) scale([sx,1,1]) {
                    translate([20.5,17,pcb_cradle_z]) cube([1.5,5,9]);
                    translate([17,20.5,pcb_cradle_z]) cube([5,1.5,9]);
                }
            }
        }
        for(sy=[-1,1]) scale([1,sy,1])
            translate([84.25-fit,17.25-fit,pcb_cradle_z-eps])
                cube([1.5+2*fit,1.5+2*fit,2+fit+eps]);
    }
}

module pcb_cartridge_bridges() {
    for(a=pcb_cradle_angles) rotate([0,0,a]) pcb_cartridge_bridge_one();
}

module pcb_cartridge_loading_path() {
    // Continuous upward sweep, with conservative +0.01 mm XY growth. Unlike
    // a projected prism this preserves the locating sockets below their roofs.
    minkowski() {
        pcb_cartridge_bridges();
        cube([0.01,0.01,lid_z+10]);
    }
}

module pcb_shell_loading_notches() {
    // Four small interruptions of the FIXED deck ledge are indispensable:
    // R145.5 cradle ends cannot pass its otherwise R142 aperture. Bore/wall,
    // fan, floor and removable deck are unchanged. Apply to shell ledge only.
    translate([0,0,deck_z-3-eps]) linear_extrude(3+2*eps)
        intersection() {
            difference() { circle(r=shell_inner_r); circle(r=deck_r-3.5-eps); }
            offset(delta=0.5) projection() pcb_cartridge_bridges();
        }
}

module pcb_cartridge_bridge_print() {
    translate([-83,22,-pcb_cradle_z]) pcb_cartridge_bridge_one();
}

module pcb_existing_features_keepout_cut() {
    // Apply ONLY to old internals(), not shell/floor/wall. Remove all supports
    // of two affected cartridges, but retain the other ten complete bays.
    for(a=pcb_cradle_angles) rotate([0,0,a])
        translate([cooling_radius-22.1,-22.1,base_floor_top-2*eps])
            cube([44.2,44.2,40]);
    // Superseded devkit pocket only; other module pockets are retained.
    translate([88.9,-28.1,base_floor_top-2*eps]) cube([32.2,56.2,7.1]);
    // Low raceway walls under board/tails and terminal exit are replaced by
    // the new pocket perimeter. Do not erase unrelated peripheral raceway.
    // Radial restriction protects the complete +30 degree support roots;
    // every original cartridge guide lies inside R129. Coarse cutters avoid
    // coincident-face slivers from subtracting exact copies of wire walls.
    translate([0,0,base_floor_top-2*eps]) linear_extrude(7.1)
        intersection() {
            difference() { circle(r=147); circle(r=129); }
            offset(delta=2.2) projection() union() {
                pcb_envelope(); pcb_component_envelopes();
            }
        }
}

module pcb_adapted_internals() {
    assert(sink_w==40 && sink_h==40 && cooling_radius==105 && shell_inner_r==146,
        "PCB prototype adapters require the reviewed 40 mm sink / R105 / R146 geometry");
    difference() { internals(); pcb_existing_features_keepout_cut(); }
    pcb_supports();
    pcb_cradle_pedestals();
}

module pcb_mount_coupon() {
    // 66 x 88 mm local floor coupon: board bay plus central cradle pedestals.
    translate([-80,44,-leg_h]) union() {
        translate([80,-44,leg_h]) cube([66,88,base_floor_t]);
        pcb_supports(); pcb_cradle_pedestal_one();
    }
}
