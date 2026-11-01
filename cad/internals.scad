// Floor-rooted, top-loaded packaging study; no thermal preload or wiring claim.
include <parameters.scad>
use <../cad/lib/sensor.scad>

support_floor_z = leg_h + (is_undef(base_floor_t) ? 3 : base_floor_t);
support_fan_z = is_undef(fan_z) ? 32 : fan_z;
support_fan_w = is_undef(fan_w) ? 120 : fan_w;
support_fan_h = is_undef(fan_h) ? 25 : fan_h;
support_sink_z = deck_top-tec_t-sink_h;
support_motor_z = motor_face_z-motor_h;
support_clearance = 0.5;
support_wall = 1.5;
bridge_lip_t = 2;
bridge_z = support_motor_z-bridge_lip_t;
bridge_post_x = 67;
bridge_post_y = 20;
// name, rotation, radial centre, [radial width, tangential length, height].
// These are unselected BOARD/connector allowances, not verified PCB drawings.
provisional_boards = [
    ["ESP32 devkit", 0, 105, [28,52,13]],
    ["USB PD", 90, 105, [22,30,8]],
    ["buck converter", 180, 105, [25,45,15]],
    ["motor driver", 270, 105, [16,20,12]]
];
board_seat_z = support_floor_z+1.5;

module internal_cooling_frames() {
    for(a=[0:360/cooling_positions:359]) rotate([0,0,a])
        translate([cooling_radius,0,0]) children();
}

module board_frame(board) {
    rotate([0,0,board[1]]) translate([board[2],0,0]) children();
}

module electronics_envelopes(include_controller=true) {
    for(board=provisional_boards) if(include_controller || board[1]!=0) board_frame(board)
        translate([-board[3][0]/2,-board[3][1]/2,board_seat_z])
            cube(board[3]);
}

module electronics_pockets() {
    for(board=provisional_boards) board_frame(board) {
        w = board[3][0]; l = board[3][1];
        outer_w = w+2*(support_clearance+support_wall);
        outer_l = l+2*(support_clearance+support_wall);
        difference() {
            translate([-outer_w/2,-outer_l/2,support_floor_z-eps])
                cube([outer_w,outer_l,7+eps]);
            translate([-w/2-support_clearance,-l/2-support_clearance,
                       board_seat_z])
                cube([w+2*support_clearance,l+2*support_clearance,10]);
            // Open-top lead exit; no inaccessible side-loading tunnel.
            translate([w/2,-4,board_seat_z+1]) cube([5,8,10]);
        }
    }
}

module cartridge_supports() {
    internal_cooling_frames() for(sx=[-1,1],sy=[-1,1])
        scale([sx,sy,1]) {
            // Four small end-bearing seats leave the lower PCB loading well open.
            translate([sink_w/2-3,sink_w/2-3,support_floor_z-eps])
                cube([3,3,support_sink_z-support_floor_z+eps]);
            // Separate floor-rooted L guides bound each nominal sink envelope.
            // Real fin geometry may need an adapter; these are not TEC clamps.
            translate([sink_w/2+support_clearance,sink_w/2-3,
                       support_floor_z-eps])
                cube([support_wall,5,support_sink_z+6-support_floor_z+eps]);
            translate([sink_w/2-3,sink_w/2+support_clearance,
                       support_floor_z-eps])
                cube([5,support_wall,support_sink_z+6-support_floor_z+eps]);
        }
}

module fan_supports() {
    for(sx=[-1,1],sy=[-1,1]) scale([sx,sy,1]) {
        translate([support_fan_w/2-10,support_fan_w/2-10,support_floor_z-eps])
            cube([10,10,support_fan_z-support_floor_z+eps]);
        // Leave the extreme corners clear of the adjacent radial sink guides.
        translate([support_fan_w/2+support_clearance,support_fan_w/2-10,
                   support_floor_z-eps])
            cube([support_wall,7,support_fan_z+6-support_floor_z+eps]);
        translate([support_fan_w/2-10,support_fan_w/2+support_clearance,
                   support_floor_z-eps])
            cube([7,support_wall,support_fan_z+6-support_floor_z+eps]);
    }
}

module fan_inlet_skirt() {
    // Low floor-rooted baffle closes the short discharge-to-suction route.
    // Rigid printed contact with the fan frame; not a qualified airtight seal.
    translate([0,0,support_floor_z-eps]) linear_extrude(support_fan_z-support_floor_z+eps)
        difference() {
            square([fan_skirt_outer,fan_skirt_outer],center=true);
            square([fan_skirt_inner,fan_skirt_inner],center=true);
        }
}

module bridge_post_frames() {
    for(x=[-bridge_post_x,bridge_post_x],y=[-bridge_post_y,bridge_post_y])
        translate([x,y,0]) children();
}

module motor_posts() {
    bridge_post_frames() {
        translate([-2.5,-4,support_floor_z-eps])
            cube([5,8,bridge_z-support_floor_z+eps]);
        translate([-1.5,-2,bridge_z-eps]) cube([3,4,3+eps]);
    }
}

// Separate removable part, shown in ASSEMBLY coordinates. Lower onto the four
// floor posts after inserting the fan. The motor then drops into its 43 mm well.
module motor_bridge() {
    assert(bridge_z > support_fan_z+support_fan_h,
        "Motor bridge needs a positive clearance above the fan");
    difference() {
        union() {
            translate([-23.5,-23.5,bridge_z]) cube([47,47,6.8]);
            for(sx=[-1,1],y=[-bridge_post_y,bridge_post_y]) scale([sx,1,1])
                translate([21.5,y-5,bridge_z]) cube([49.5,10,4.8]);
        }
        // A thin lower lip bears on the bottom perimeter of the motor.
        translate([-19,-19,bridge_z-eps]) cube([38,38,8]);
        translate([-21.5,-21.5,support_motor_z]) cube([43,43,10]);
        bridge_post_frames() translate([-1.5-fit,-2-fit,bridge_z-eps])
            cube([3+2*fit,4+2*fit,3+fit+eps]);
        // Open-top motor lead exit, aligned with the free side of the cradle.
        translate([-4,21, support_motor_z+1]) cube([8,4,10]);
    }
}

module motor_bridge_print() {
    translate([0,0,-bridge_z]) motor_bridge();
}

module wire_channels() {
    // Floor-open annular raceway: two low walls, interrupted at every site.
    // Supply gauges/connectors and complete harness paths are not selected.
    difference() {
        translate([0,0,support_floor_z-eps]) linear_extrude(4+eps)
            union() {
                difference() { circle(r=136.2); circle(r=135); }
                difference() { circle(r=142.2); circle(r=141); }
            }
        for(a=[0:360/cooling_positions:359]) rotate([0,0,a])
            translate([132,-4,support_floor_z-1]) cube([13,8,7]);
    }
    for(a=[0:360/cooling_positions:359]) rotate([0,0,a])
        for(y=[-5.2,4]) translate([130,y,support_floor_z-eps])
            cube([11,1.2,3+eps]);
    // Local top-open fan/motor lead route; no span over the fan insertion path.
    for(y=[-5.2,4]) translate([63,y,support_floor_z-eps])
        cube([17,1.2,3+eps]);
}

module internals() {
    assert(support_sink_z > support_floor_z);
    assert(bridge_post_x-2.5 > support_fan_w/2+support_clearance);
    union() {
        cartridge_supports();
        fan_supports();
        fan_inlet_skirt();
        motor_posts();
        electronics_pockets();
        wire_channels();
    }
}

module supported_equipment_envelopes(include_controller=true) {
    electronics_envelopes(include_controller);
    translate([-support_fan_w/2,-support_fan_w/2,support_fan_z])
        cube([support_fan_w,support_fan_w,support_fan_h]);
    translate([-21,-21,support_motor_z]) cube([42,42,motor_h]);
    internal_cooling_frames() translate([-sink_w/2,-sink_w/2,support_sink_z])
        cube([sink_w,sink_w,sink_h]);
}

module component_support_checks() {
    empty_check("fixed supports / equipment") intersection() {
        internals(); supported_equipment_envelopes();
    }
    empty_check("motor bridge / equipment") intersection() {
        motor_bridge(); supported_equipment_envelopes();
    }
    empty_check("motor bridge / fixed supports") intersection() {
        motor_bridge(); internals();
    }
    empty_check("board top-loading paths / fixed supports") intersection() {
        internals();
        for(board=provisional_boards) board_frame(board)
            translate([-board[3][0]/2,-board[3][1]/2,board_seat_z])
                cube([board[3][0],board[3][1],lid_z-board_seat_z+10]);
    }
    empty_check("fan top-loading path / fixed supports") intersection() {
        internals();
        translate([-support_fan_w/2,-support_fan_w/2,support_fan_z])
            cube([support_fan_w,support_fan_w,lid_z-support_fan_z+10]);
    }
    empty_check("sink top-loading paths / fixed supports") intersection() {
        internals();
        internal_cooling_frames() translate([-sink_w/2,-sink_w/2,support_sink_z])
            cube([sink_w,sink_w,lid_z-support_sink_z+10]);
    }
    empty_check("motor top-loading path / bridge") intersection() {
        motor_bridge();
        translate([-21,-21,support_motor_z]) cube([42,42,lid_z-support_motor_z+10]);
    }
}

module component_loading_paths(include_controller=true) {
    for(board=provisional_boards) if(include_controller || board[1]!=0) board_frame(board)
        translate([-board[3][0]/2,-board[3][1]/2,board_seat_z])
            cube([board[3][0],board[3][1],lid_z-board_seat_z+10]);
    translate([-support_fan_w/2,-support_fan_w/2,support_fan_z])
        cube([support_fan_w,support_fan_w,lid_z-support_fan_z+10]);
    internal_cooling_frames() translate([-sink_w/2,-sink_w/2,support_sink_z])
        cube([sink_w,sink_w,lid_z-support_sink_z+10]);
    translate([-21,-21,support_motor_z]) cube([42,42,lid_z-support_motor_z+10]);
}
